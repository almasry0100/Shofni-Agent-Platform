from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

import pytest

from poc.fixtures.network import NetworkIsolationError, outbound_network_blocked
from poc.fixtures.provider_server import LocalProviderServer, probe_local_provider
from poc.fixtures.scenarios import run_scenario


def test_provider_server_binds_to_loopback_serves_fixture_and_releases_port() -> None:
    result = probe_local_provider("provider-server-seed")

    assert result["result_status"] == "PASS"
    assert result["server"]["bind_address"] == "127.0.0.1"
    assert result["server"]["selected_port"] > 0
    assert result["server"]["fixture_version"]
    assert result["server"]["fixture_hash"].startswith("sha256:")
    assert result["server"]["startup_result"] == "STARTED"
    assert result["server"]["shutdown_result"] == "STOPPED"
    assert result["server_port_released"] is True
    assert result["normalized_response"]["tool_calls"] == []

    record = run_scenario("provider_server_smoke", "provider-server-seed")
    assert record["result_status"] == "PASS"
    assert record["decisions"][0]["local_only"] is True
    assert record["decisions"][0]["port_released"] is True


def test_provider_server_rejects_non_loopback_bind_address() -> None:
    with pytest.raises(ValueError, match="loopback"):
        LocalProviderServer("0.0.0.0")


def test_provider_server_exposes_openai_models_chat_and_responses() -> None:
    with LocalProviderServer() as server:
        base_url = f"http://{server.bind_address}:{server.port}"
        with urllib.request.urlopen(f"{base_url}/v1/models", timeout=3.0) as response:
            models = json.loads(response.read())
        assert models["data"][0]["id"] == "fixture-chat-only"

        chat_request = {
            "model": "fixture-chat-only",
            "user": "bridge-chat-smoke",
            "messages": [{"role": "user", "content": "Use the fixture tool."}],
        }
        chat = _post_json(f"{base_url}/v1/chat/completions", chat_request)
        assert chat["object"] == "chat.completion"
        assert chat["choices"][0]["message"]["content"].startswith("I need to use a tool.")
        assert chat["choices"][0]["finish_reason"] == "stop"

        responses_request = {
            "model": "fixture-chat-only",
            "metadata": {"shofni_fixture_seed": "bridge-responses-smoke"},
            "input": "Use the fixture tool.",
        }
        response = _post_json(f"{base_url}/v1/responses", responses_request)
        assert response["object"] == "response"
        assert response["status"] == "completed"
        assert response["output_text"].startswith("I need to use a tool.")


def test_provider_server_streams_chat_and_returns_synthetic_rate_limit() -> None:
    with LocalProviderServer() as server:
        base_url = f"http://{server.bind_address}:{server.port}"
        stream_request = {
            "model": "fixture-chat-only",
            "user": "bridge-stream-smoke",
            "messages": [{"role": "user", "content": "Stream the fixture response."}],
            "stream": True,
        }
        body = json.dumps(stream_request).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3.0) as response:
            stream = response.read().decode("utf-8")
        assert "data: [DONE]" in stream
        assert '"object":"chat.completion.chunk"' in stream
        assert '"finish_reason":"stop"' in stream

        error_request = {
            "model": "fixture-chat-only",
            "user": "phase3-bifrost-rate-limit",
            "messages": [{"role": "user", "content": "Trigger the synthetic error."}],
        }
        with pytest.raises(urllib.error.HTTPError) as error:
            _post_json(f"{base_url}/v1/chat/completions", error_request)
        assert error.value.code == 429
        assert json.loads(error.value.read())["error"]["code"] == "rate_limit_exceeded"


def test_network_guard_blocks_outbound_tcp_and_allows_loopback() -> None:
    with outbound_network_blocked() as guard:
        with pytest.raises(NetworkIsolationError):
            socket.create_connection(("198.51.100.17", 80), timeout=0.1)
        with LocalProviderServer():
            pass
    assert guard.blocked_attempts == 1
    assert guard.local_connections == 0


def _post_json(url: str, value: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3.0) as response:
        result = json.loads(response.read())
    assert isinstance(result, dict)
    return result
