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


class BifrostHTTPBackend:
    def __init__(
        self,
        artifact_dir: Path,
        app_dir: Path,
        image_ref: str,
        network_name: str,
        provider_url: str,
        host_port: int,
        container_name: str,
        client_container: str | None = None,
        provider_config: Mapping[str, Any] | None = None,
        environment: Mapping[str, str | None] | None = None,
        readiness_timeout: float = 60.0,
    ) -> None:
        if "@sha256:" not in image_ref or image_ref.endswith(":latest"):
            raise ValueError("Bifrost runtime image must be pinned by digest")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container_name):
            raise ValueError("container name contains unsupported characters")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", network_name):
            raise ValueError("Docker network name contains unsupported characters")
        self.artifact_dir = artifact_dir.resolve()
        self.app_dir = app_dir.resolve()
        self.image_ref = image_ref
        self.network_name = network_name
        self.provider_url = provider_url.rstrip("/")
        self.host_port = host_port
        self.container_name = container_name
        self.client_container = client_container
        self.provider_config = dict(provider_config or {})
        self.environment = dict(environment or {})
        self.readiness_timeout = readiness_timeout
        self.base_url = f"http://127.0.0.1:{host_port}"
        self._started = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("Bifrost backend is already running")
        if not (self.artifact_dir / "bifrost-http").is_file():
            raise FileNotFoundError("Bifrost executable is missing from the artifact directory")
        self.app_dir.mkdir(parents=True, exist_ok=False)
        default_config = {
            "version": 2,
            "providers": {
                "openai": {
                    "keys": [{
                        "name": "shofni-synthetic-fixture",
                        "value": "fixture-only-placeholder",
                        "weight": 1.0,
                        "models": ["fixture-chat-only"],
                    }],
                    "network_config": {
                        "base_url": self.provider_url,
                        "default_request_timeout_in_seconds": 10,
                        "max_retries": 0,
                        "allow_private_network": True,
                    },
                },
            },
            "framework": {
                "pricing": {
                    "pricing_url": "file:///data/pricing.json",
                    "model_parameters_url": "file:///data/model-parameters.json",
                    "mcp_library_sync_interval": 0,
                    "live_models_sync_interval": 0,
                },
            },
            "config_store": {"enabled": False},
            "logs_store": {"enabled": False},
            "client": {"disable_db_pings_in_health": True},
        }
        config = self.provider_config or default_config
        (self.app_dir / "pricing.json").write_text("{}\n", encoding="utf-8")
        (self.app_dir / "model-parameters.json").write_text("{}\n", encoding="utf-8")
        (self.app_dir / "config.json").write_text(
            json.dumps(config, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        command = [
            "docker", "run", "--rm", "-d", "--name", self.container_name,
            "--platform", "linux/amd64",
            "--network", self.network_name,
            "--publish", f"127.0.0.1:{self.host_port}:8080",
            "--mount", f"type=bind,source={self.artifact_dir},target=/opt/bifrost,readonly",
            "--mount", f"type=bind,source={self.app_dir},target=/data",
            "--env", "BIFROST_HOST=0.0.0.0",
            self.image_ref,
            "/opt/bifrost/bifrost-http", "-host", "0.0.0.0", "-port", "8080",
            "-app-dir", "/data", "-log-level", "error",
        ]
        for name, value in sorted(self.environment.items()):
            command[command.index(self.image_ref):command.index(self.image_ref)] = [
                "--env", name if value is None else f"{name}={value}"
            ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError("Docker could not start the pinned Bifrost runtime")
        self._started = True
        deadline = time.monotonic() + self.readiness_timeout
        while time.monotonic() < deadline:
            if not self._container_running():
                raise RuntimeError("Bifrost container exited before health became ready")
            try:
                if self.health().get("status") == "ok":
                    return
            except (GatewayRequestError, OSError, URLError, ValueError):
                time.sleep(0.25)
        raise TimeoutError("Bifrost health endpoint did not become ready")

    def stop(self) -> None:
        if not self._started:
            return
        result = subprocess.run(
            ["docker", "stop", "--time", "10", self.container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        self._started = False
        if result.returncode != 0 and self._container_running():
            raise RuntimeError("Docker could not stop the Bifrost runtime")

    def health(self) -> JSONMapping:
        return self._request("GET", "/health")

    def request(self, request: JSONMapping) -> JSONMapping:
        payload = dict(request)
        protocol = payload.pop("protocol", None)
        if protocol == "messages":
            return self._request(
                "POST",
                "/anthropic/v1/messages",
                payload,
                headers={"anthropic-version": "2023-06-01", "x-api-key": "shofni-live-client"},
            )
        path = "/openai/v1/responses" if protocol == "responses" or "input" in payload else "/openai/v1/chat/completions"
        return self._request("POST", path, payload)

    def stream(self, request: JSONMapping) -> Iterator[JSONMapping]:
        payload = dict(request)
        protocol = payload.pop("protocol", None)
        headers: dict[str, str] = {}
        if protocol == "messages":
            path = "/anthropic/v1/messages"
            headers = {"anthropic-version": "2023-06-01", "x-api-key": "shofni-live-client"}
        else:
            path = "/openai/v1/responses" if protocol == "responses" or "input" in payload else "/openai/v1/chat/completions"
        payload["stream"] = True
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if self.client_container is not None:
            raw = self._network_request("POST", path, body, "text/event-stream", headers)
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
                    raise ValueError("Bifrost stream contained invalid JSON") from exc
                if not isinstance(event, dict):
                    raise ValueError("Bifrost stream event must be a JSON object")
                yield event
            return
        outbound = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream", **headers},
            method="POST",
        )
        try:
            response = urlopen(outbound, timeout=60.0)
        except HTTPError as exc:
            raise GatewayRequestError(exc.code, _read_error_body(exc)) from None
        except URLError as exc:
            raise ConnectionError("Bifrost stream request failed") from None
        with response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
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
                    raise ValueError("Bifrost stream contained invalid JSON") from exc
                if not isinstance(event, dict):
                    raise ValueError("Bifrost stream event must be a JSON object")
                yield event

    def list_models(self) -> list[JSONMapping]:
        response = self._request("GET", "/openai/v1/models")
        models = response.get("data")
        if not isinstance(models, list) or any(not isinstance(model, dict) for model in models):
            raise ValueError("Bifrost model listing has an invalid shape")
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
        headers: Mapping[str, str] | None = None,
    ) -> JSONMapping:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if self.client_container is not None:
            raw = self._network_request(method, path, body, "application/json", headers or {})
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("Bifrost response must be a JSON object")
            return value
        outbound = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json", **(headers or {})},
            method=method,
        )
        try:
            response = urlopen(outbound, timeout=30.0)
        except HTTPError as exc:
            raise GatewayRequestError(exc.code, _read_error_body(exc)) from None
        except URLError as exc:
            raise ConnectionError("Bifrost request failed") from None
        with response:
            value = json.loads(response.read())
        if not isinstance(value, dict):
            raise ValueError("Bifrost response must be a JSON object")
        return value

    def _network_request(
        self,
        method: str,
        path: str,
        body: bytes | None,
        accept: str,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        if self.client_container is None:
            raise RuntimeError("internal HTTP client is not configured")
        script = (
            "import base64,json,sys,urllib.error,urllib.request\n"
            "base,path,method,accept,encoded,encoded_headers=sys.argv[1:]\n"
            "data=base64.b64decode(encoded) if encoded else None\n"
            "extra=json.loads(encoded_headers)\n"
            "request_headers={'Content-Type':'application/json','Accept':accept,**extra}\n"
            "req=urllib.request.Request(base+path,data=data,headers=request_headers,method=method)\n"
            "try:\n"
            "    with urllib.request.urlopen(req,timeout=30) as response:\n"
            "        print(json.dumps({'status':response.status,'body':base64.b64encode(response.read()).decode('ascii')}))\n"
            "except urllib.error.HTTPError as error:\n"
            "    print(json.dumps({'status':error.code,'body':base64.b64encode(error.read()).decode('ascii')}))"
        )
        encoded = "" if body is None else base64.b64encode(body).decode("ascii")
        encoded_headers = json.dumps(dict(headers or {}), separators=(",", ":"))
        network_base_url = f"http://{self.container_name}:8080"
        result = subprocess.run(
            [
                "docker", "exec", self.client_container, "python", "-c", script,
                network_base_url, path, method, accept, encoded, encoded_headers,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ConnectionError("internal Bifrost request failed")
        try:
            envelope = json.loads(result.stdout)
            status = int(envelope["status"])
            response_body = base64.b64decode(envelope["body"])
        except (KeyError, TypeError, ValueError, base64.binascii.Error) as exc:
            raise ValueError("internal Bifrost response was malformed") from exc
        if status >= 400:
            try:
                error_body = json.loads(response_body)
            except ValueError:
                error_body = {}
            raise GatewayRequestError(status, error_body if isinstance(error_body, dict) else {})
        return response_body

    def _container_running(self) -> bool:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", self.container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"


def _read_error_body(error: HTTPError) -> dict[str, Any]:
    try:
        body = json.loads(error.read(65536))
    except (OSError, ValueError):
        return {}
    return body if isinstance(body, dict) else {}
