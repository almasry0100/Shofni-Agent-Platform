from __future__ import annotations

import errno
import hashlib
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_string

from . import FIXTURE_VERSION
from .providers import ChatOnlyProviderFixture, deterministic_id


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
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "fixture_version": FIXTURE_VERSION})
            return
        if self.path == "/v1/models":
            self._send_json(200, {
                "object": "list",
                "data": [{"id": "fixture-chat-only", "object": "model", "owned_by": "shofni-fixture"}],
            })
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path not in {"/v1/chat/completions", "/v1/responses"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("request body length is invalid")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid_fixture_request"})
            return

        if self.path == "/v1/chat/completions" and isinstance(request.get("seed"), str) and "messages" not in request:
            self._send_json(200, self.server.fixture.respond(request, request["seed"]))
            return

        seed = self._fixture_seed(request, self.path)
        if seed == "phase3-bifrost-rate-limit":
            self._send_json(429, {
                "error": {
                    "message": "synthetic fixture rate limit",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                },
            })
            return

        metadata = request.get("metadata")
        fixture_request = {
            "path": metadata.get("shofni_fixture_path", "input/alpha.txt") if isinstance(metadata, dict) else "input/alpha.txt",
        }
        output = self.server.fixture.respond(fixture_request, seed)
        if self.path == "/v1/responses":
            self._send_json(200, self._responses_response(request, seed, output["content"] or ""))
        elif request.get("stream") is True:
            self._send_chat_stream(request, seed, output["content"] or "")
        else:
            self._send_json(200, self._chat_response(request, seed, output["content"] or ""))

    @staticmethod
    def _fixture_seed(request: dict[str, Any], path: str) -> str:
        metadata = request.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("shofni_fixture_seed"), str):
            return metadata["shofni_fixture_seed"]
        user = request.get("user")
        if isinstance(user, str) and user:
            return user
        messages = request.get("messages")
        if isinstance(messages, list):
            for message in messages:
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if isinstance(content, str) and "phase3-bifrost-rate-limit" in content:
                    return "phase3-bifrost-rate-limit"
        return "openai-responses-fixture" if path == "/v1/responses" else "openai-chat-fixture"

    @staticmethod
    def _chat_response(request: dict[str, Any], seed: str, content: str) -> dict[str, Any]:
        model = request.get("model") if isinstance(request.get("model"), str) else "fixture-chat-only"
        return {
            "id": deterministic_id("chatcmpl", seed, request),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": len(content.split()), "total_tokens": 1 + len(content.split())},
        }

    @staticmethod
    def _responses_response(request: dict[str, Any], seed: str, content: str) -> dict[str, Any]:
        response_id = deterministic_id("resp", seed, request)
        message_id = deterministic_id("msg", seed, request)
        model = request.get("model") if isinstance(request.get("model"), str) else "fixture-chat-only"
        return {
            "id": response_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "model": model,
            "output": [{
                "id": message_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content, "annotations": []}],
            }],
            "output_text": content,
            "usage": {
                "input_tokens": 1,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": len(content.split()),
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 1 + len(content.split()),
            },
        }

    def _send_chat_stream(self, request: dict[str, Any], seed: str, content: str) -> None:
        model = request.get("model") if isinstance(request.get("model"), str) else "fixture-chat-only"
        completion_id = deterministic_id("chatcmpl", seed, request)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        events = [{"role": "assistant"}]
        events.extend({"content": content[index : index + 24]} for index in range(0, len(content), 24))
        for delta in events:
            self._write_sse({
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
            })
        self._write_sse({
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        })
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except OSError:
            return

    def _write_sse(self, value: dict[str, Any]) -> None:
        body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            self.wfile.write(b"data: " + body + b"\n\n")
            self.wfile.flush()
        except OSError:
            return

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
