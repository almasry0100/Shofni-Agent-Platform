from __future__ import annotations

import errno
import hashlib
import ipaddress
import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_string

from . import FIXTURE_VERSION
from .providers import ChatOnlyProviderFixture


_TRANSIENT_SETUP_ERRNOS = {
    errno.EADDRINUSE,
    errno.EADDRNOTAVAIL,
    errno.ENOBUFS,
}


def _source_hash() -> str:
    return "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class _FixtureHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    fixture = ChatOnlyProviderFixture()


class _FixtureHandler(BaseHTTPRequestHandler):
    server: _FixtureHttpServer

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self._send_json(200, {"status": "ok", "fixture_version": FIXTURE_VERSION})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("request body length is invalid")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict) or not isinstance(request.get("seed"), str):
                raise ValueError("request must contain a string seed")
            response = self.server.fixture.respond(request, request["seed"])
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid_fixture_request"})
            return
        self._send_json(200, response)

    def _send_json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class LocalProviderServer:
    """A minimal deterministic provider endpoint bound to an explicit loopback IP."""

    def __init__(self, bind_address: str = "127.0.0.1") -> None:
        try:
            parsed_address = ipaddress.ip_address(bind_address)
        except ValueError as exc:
            raise ValueError("provider fixture server requires a loopback IP literal") from exc
        if not parsed_address.is_loopback:
            raise ValueError("provider fixture server cannot bind outside loopback")
        self.bind_address = bind_address
        self.port: int | None = None
        self._httpd: _FixtureHttpServer | None = None
        self._thread: threading.Thread | None = None
        self.startup_result = "NOT_STARTED"
        self.shutdown_result = "NOT_STOPPED"

    @property
    def fixture_hash(self) -> str:
        return _source_hash()

    def start(self) -> LocalProviderServer:
        if self._httpd is not None:
            raise RuntimeError("provider fixture server is already active")
        server = _FixtureHttpServer((self.bind_address, 0), _FixtureHandler)
        self._httpd = server
        self.port = int(server.server_address[1])
        self._thread = threading.Thread(
            target=server.serve_forever,
            name="shofni-local-provider-fixture",
            daemon=True,
        )
        try:
            self._thread.start()
        except BaseException:
            server.server_close()
            self._httpd = None
            self._thread = None
            self.port = None
            raise
        self.startup_result = "STARTED"
        return self

    def stop(self) -> bool:
        server, thread = self._httpd, self._thread
        if server is None:
            self.shutdown_result = "NOT_RUNNING"
            return True
        if thread is not None and thread.is_alive():
            server.shutdown()
            thread.join(timeout=5.0)
        server.server_close()
        stopped = thread is None or not thread.is_alive()
        self.shutdown_result = "STOPPED" if stopped else "STOP_FAILED"
        self._httpd = None
        self._thread = None
        return stopped

    def verify_port_released(self) -> bool:
        if self.port is None:
            return False
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((self.bind_address, self.port))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    def audit(self) -> dict[str, Any]:
        return {
            "bind_address": self.bind_address,
            "selected_port": self.port,
            "fixture_version": FIXTURE_VERSION,
            "fixture_hash": self.fixture_hash,
            "startup_result": self.startup_result,
            "shutdown_result": self.shutdown_result,
        }

    def __enter__(self) -> LocalProviderServer:
        return self.start()

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.stop()


def probe_local_provider(seed: str) -> dict[str, Any]:
    setup_attempts: list[dict[str, Any]] = []
    server: LocalProviderServer | None = None
    for attempt in range(1, 3):
        server = LocalProviderServer()
        try:
            server.start()
            break
        except OSError as exc:
            setup_attempts.append({
                "attempt": attempt,
                "error_type": type(exc).__name__,
                "error": redact_string(str(exc)),
                "transient": exc.errno in _TRANSIENT_SETUP_ERRNOS,
            })
            server.stop()
            if attempt == 1 and exc.errno in _TRANSIENT_SETUP_ERRNOS:
                continue
            return {
                "result_status": "FAIL",
                "failure_class": "SETUP_FAILURE",
                "server": server.audit(),
                "setup_attempts": setup_attempts,
                "normalized_response": None,
            }
        except Exception as exc:
            setup_attempts.append({
                "attempt": attempt,
                "error_type": type(exc).__name__,
                "error": redact_string(str(exc)),
                "transient": False,
            })
            server.stop()
            return {
                "result_status": "FAIL",
                "failure_class": "SETUP_FAILURE",
                "server": server.audit(),
                "setup_attempts": setup_attempts,
                "normalized_response": None,
            }

    if server is None or server.port is None:
        return {
            "result_status": "FAIL",
            "failure_class": "SETUP_FAILURE",
            "server": None,
            "setup_attempts": setup_attempts,
            "normalized_response": None,
        }

    response: dict[str, Any] | None = None
    semantic_error: str | None = None
    try:
        body = json.dumps({"seed": seed, "path": "input/alpha.txt"}).encode("utf-8")
        request = urllib.request.Request(
            f"http://{server.bind_address}:{server.port}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3.0) as result:
            if result.status != 200:
                raise RuntimeError(f"fixture endpoint returned HTTP {result.status}")
            value = json.loads(result.read())
            if not isinstance(value, dict):
                raise RuntimeError("fixture endpoint did not return a JSON object")
            response = value
    except (OSError, urllib.error.URLError, ValueError, RuntimeError) as exc:
        semantic_error = redact_string(f"{type(exc).__name__}: {exc}")
    stopped = server.stop()
    released = server.verify_port_released()
    status = "PASS" if semantic_error is None and stopped and released else "FAIL"
    return {
        "result_status": status,
        "failure_class": None if status == "PASS" else "PROVIDER_FAILURE",
        "server": server.audit(),
        "server_port_released": released,
        "setup_attempts": setup_attempts,
        "normalized_response": response,
        "semantic_error": semantic_error,
    }
