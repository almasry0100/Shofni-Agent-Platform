from __future__ import annotations

import base64
import json
import re
import socket
import subprocess
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from poc.contracts._serialization import JSONMapping
from poc.evidence.taxonomy import FailureClass, FailureTaxonomyClass


class GatewayRequestError(RuntimeError):
    def __init__(self, status_code: int, body: Mapping[str, Any]) -> None:
        self.status_code = status_code
        self.body = dict(body)
        super().__init__(f"gateway returned HTTP {status_code}")


class LiteLLMHTTPBackend:
    def __init__(
        self,
        config_dir: Path,
        image_ref: str,
        network_name: str,
        host_port: int,
        container_name: str,
        client_container: str | None = None,
        environment: Mapping[str, str | None] | None = None,
        readiness_timeout: float = 90.0,
    ) -> None:
        if "@sha256:" not in image_ref or image_ref.endswith(":latest"):
            raise ValueError("LiteLLM runtime image must be pinned by digest")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container_name):
            raise ValueError("container name contains unsupported characters")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", network_name):
            raise ValueError("Docker network name contains unsupported characters")
        self.config_dir = config_dir.resolve()
        self.image_ref = image_ref
        self.network_name = network_name
        self.host_port = host_port
        self.container_name = container_name
        self.client_container = client_container
        self.environment = dict(environment or {})
        self.readiness_timeout = readiness_timeout
        self.base_url = f"http://127.0.0.1:{host_port}"
        self._started = False
        self._startup_process_result: subprocess.CompletedProcess[str] | None = None

    def start(self) -> None:
        if self._started:
            raise RuntimeError("LiteLLM backend is already running")
        config_path = self.config_dir / "config.yaml"
        if not config_path.is_file():
            raise FileNotFoundError("LiteLLM proxy configuration is missing")
        command = [
            "docker", "run", "-d", "--name", self.container_name,
            "--platform", "linux/amd64",
            "--network", self.network_name,
            "--publish", f"127.0.0.1:{self.host_port}:4000",
            "--mount", f"type=bind,source={self.config_dir},target=/data,readonly",
            "--env", "LITELLM_LOG=ERROR",
            "--env", "LITELLM_DANGEROUSLY_PERMIT_WEAK_OR_UNSET_MASTER_KEY=true",
            self.image_ref,
            "-m", "litellm.proxy.proxy_cli",
            "--config", "/data/config.yaml",
            "--host", "0.0.0.0",
            "--port", "4000",
            "--num_workers", "1",
        ]
        for name, value in sorted(self.environment.items()):
            command[5:5] = ["--env", name if value is None else f"{name}={value}"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self._startup_process_result = result
        if result.returncode != 0:
            raise RuntimeError("Docker could not start the pinned LiteLLM runtime")
        self._started = True
        deadline = time.monotonic() + self.readiness_timeout
        while time.monotonic() < deadline:
            if not self._container_running():
                logs = self._logs()
                raise RuntimeError("LiteLLM container exited before health became ready: " + logs[-1000:])
            try:
                health = self.liveliness()
                if health == "I'm alive!" or health == {"status": "ok"}:
                    return
            except (GatewayRequestError, OSError, URLError, ValueError):
                time.sleep(0.25)
        raise TimeoutError("LiteLLM health/liveliness endpoint did not become ready")

    def stop(self) -> None:
        if not self._started and not self._container_exists():
            return
        result = subprocess.run(
            ["docker", "stop", "--time", "10", self.container_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if self._container_exists():
            subprocess.run(["docker", "rm", "--force", self.container_name], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self._started = False
        if result.returncode != 0 and self._container_exists():
            raise RuntimeError("Docker could not stop the LiteLLM runtime")

    def liveliness(self) -> object:
        return self._request("GET", "/health/liveliness", expect_object=False)

    def readiness(self) -> object:
        return self._request("GET", "/health/readiness", expect_object=False)

    def request(self, request: JSONMapping) -> JSONMapping:
        payload = dict(request)
        protocol = payload.pop("protocol", None)
        path = "/v1/messages" if protocol == "messages" else ("/v1/responses" if protocol == "responses" or "input" in payload else "/v1/chat/completions")
        headers = {"anthropic-version": "2023-06-01", "x-api-key": "shofni-live-client"} if protocol == "messages" else None
        value = self._request("POST", path, payload, headers=headers)
        if not isinstance(value, dict):
            raise ValueError("LiteLLM response must be a JSON object")
        return value

    def stream(self, request: JSONMapping) -> Iterator[JSONMapping]:
        payload = dict(request)
        protocol = payload.pop("protocol", None)
        path = "/v1/messages" if protocol == "messages" else ("/v1/responses" if protocol == "responses" or "input" in payload else "/v1/chat/completions")
        payload["stream"] = True
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"anthropic-version": "2023-06-01", "x-api-key": "shofni-live-client"} if protocol == "messages" else None
        raw = self._raw_request("POST", path, body, "text/event-stream", headers=headers)
        for raw_line in raw.decode("utf-8").splitlines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            if not data:
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError as exc:
                raise ValueError("LiteLLM stream contained invalid JSON") from exc
            if not isinstance(event, dict):
                raise ValueError("LiteLLM stream event must be a JSON object")
            yield event

    def list_models(self) -> list[JSONMapping]:
        response = self._request("GET", "/v1/models")
        if not isinstance(response, dict):
            raise ValueError("LiteLLM model listing is not an object")
        models = response.get("data")
        if not isinstance(models, list) or any(not isinstance(model, dict) for model in models):
            raise ValueError("LiteLLM model listing has an invalid shape")
        return models

    def classify_error(self, error: object) -> FailureTaxonomyClass:
        status = getattr(error, "status_code", None)
        body = getattr(error, "body", None)
        if isinstance(error, HTTPError):
            status = error.code
        if isinstance(body, Mapping):
            details = body.get("error")
            if isinstance(details, Mapping):
                code = " ".join(str(details.get(field, "")) for field in ("type", "code", "message")).lower()
                if "rate_limit" in code or "rate limit" in code:
                    return FailureClass.RATE_LIMIT
                if "billing" in code or "insufficient_quota" in code:
                    return FailureClass.BILLING_ERROR
                if "auth" in code or "unauthorized" in code or "invalid_api_key" in code:
                    return FailureClass.AUTH_ERROR
        if status in (401, 403):
            return FailureClass.AUTH_ERROR
        if status == 402:
            return FailureClass.BILLING_ERROR
        if status == 429:
            return FailureClass.RATE_LIMIT
        if isinstance(error, (ConnectionError, TimeoutError, URLError)) or (isinstance(status, int) and status >= 500):
            return FailureClass.GATEWAY_FAILURE
        if isinstance(status, int) and 400 <= status < 500:
            return FailureClass.CLIENT_FAILURE
        return FailureClass.GATEWAY_FAILURE

    def port_released(self) -> bool:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", self.host_port))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        expect_object: bool = True,
        headers: Mapping[str, str] | None = None,
    ) -> object:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        raw = self._raw_request(method, path, body, "application/json", headers=headers)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("LiteLLM response was not JSON") from exc
        if expect_object and not isinstance(value, dict):
            raise ValueError("LiteLLM response must be a JSON object")
        return value

    def _raw_request(
        self,
        method: str,
        path: str,
        body: bytes | None,
        accept: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        if self.client_container is not None:
            return self._network_request(method, path, body, accept, headers or {})
        outbound = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json", "Accept": accept, **(headers or {})},
            method=method,
        )
        try:
            with urlopen(outbound, timeout=60.0) as response:
                return response.read()
        except HTTPError as exc:
            raise GatewayRequestError(exc.code, _read_error_body(exc)) from None
        except URLError as exc:
            raise ConnectionError("LiteLLM request failed") from None

    def _network_request(
        self,
        method: str,
        path: str,
        body: bytes | None,
        accept: str,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        script = (
            "import base64,json,sys,urllib.error,urllib.request\n"
            "base,path,method,accept,encoded,encoded_headers=sys.argv[1:]\n"
            "data=base64.b64decode(encoded) if encoded else None\n"
            "extra=json.loads(encoded_headers)\n"
            "request_headers={'Content-Type':'application/json','Accept':accept,**extra}\n"
            "req=urllib.request.Request(base+path,data=data,headers=request_headers,method=method)\n"
            "try:\n"
            "    with urllib.request.urlopen(req,timeout=45) as response:\n"
            "        print(json.dumps({'status':response.status,'body':base64.b64encode(response.read()).decode('ascii')}))\n"
            "except urllib.error.HTTPError as error:\n"
            "    print(json.dumps({'status':error.code,'body':base64.b64encode(error.read()).decode('ascii')}))"
        )
        encoded = "" if body is None else base64.b64encode(body).decode("ascii")
        encoded_headers = json.dumps(dict(headers or {}), separators=(",", ":"))
        network_base_url = f"http://{self.container_name}:4000"
        result = subprocess.run(
            [
                "docker", "exec", self.client_container or "", "python", "-c", script,
                network_base_url, path, method, accept, encoded, encoded_headers,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            raise ConnectionError("internal LiteLLM request failed")
        try:
            envelope = json.loads(result.stdout)
            status = int(envelope["status"])
            response_body = base64.b64decode(envelope["body"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, base64.binascii.Error) as exc:
            raise ValueError("internal LiteLLM response was malformed") from exc
        if status >= 400:
            try:
                error_body = json.loads(response_body)
            except ValueError:
                error_body = {}
            raise GatewayRequestError(status, error_body if isinstance(error_body, dict) else {})
        return response_body

    def _container_exists(self) -> bool:
        result = subprocess.run(
            ["docker", "inspect", self.container_name], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        return result.returncode == 0

    def _container_running(self) -> bool:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", self.container_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def _logs(self) -> str:
        result = subprocess.run(
            ["docker", "logs", self.container_name], capture_output=True, text=False, check=False,
        )
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")
        return (stdout + stderr).strip()


def _read_error_body(error: HTTPError) -> dict[str, Any]:
    try:
        body = json.loads(error.read(65536))
    except (OSError, ValueError):
        return {}
    return body if isinstance(body, dict) else {}
