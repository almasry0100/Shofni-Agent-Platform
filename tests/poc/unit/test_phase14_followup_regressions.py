from __future__ import annotations

import subprocess

import pytest

from poc.adapters.bifrost_http import BifrostHTTPBackend
from poc.adapters.litellm_http import LiteLLMHTTPBackend
from poc.runners import phase11_composition
from poc.runners.phase14_d_f2_t03 import _assistant_message, _continuation_request, _messages_config, _reserve_one_shot


def test_phase11_mounts_use_explicit_bind_syntax(tmp_path):
    mount = phase11_composition._docker_bind_mount(tmp_path / "source", "/workspace", readonly=True)

    assert mount.startswith("type=bind,source=")
    assert mount.endswith(",target=/workspace,readonly")
    assert ":/workspace" not in mount


def test_bifrost_model_namespace_is_normalized_and_missing_routes_fail():
    present = phase11_composition._route_probe(
        [{"id": "openai/gpt-5.4-mini"}, {"id": "openai/gpt-5.5"}],
        ("gpt-5.4-mini", "gpt-5.5"),
    )
    missing = phase11_composition._route_probe(
        [{"id": "openai/gpt-5.4-mini"}],
        ("gpt-5.4-mini", "gpt-5.5"),
    )

    assert present["status"] == "PASS"
    assert present["selected_routes_present"] is True
    assert missing["status"] == "FAIL"
    assert missing["missing_routes"] == ["gpt-5.5"]


def test_phase11_subprocess_capture_is_utf8_safe(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(phase11_composition.subprocess, "run", fake_run)

    phase11_composition._run(["docker", "version"])

    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_phase11_rejects_host_loopback_for_runtime_gateway():
    phase11_composition._validate_runtime_gateway_url(
        "http://shofni-gateway:8080/openai/v1",
        "shofni-gateway",
        8080,
    )

    with pytest.raises(ValueError, match="container DNS name"):
        phase11_composition._validate_runtime_gateway_url(
            "http://127.0.0.1:50800/openai/v1",
            "shofni-gateway",
            8080,
        )


def test_phase11_process_diagnostics_keep_bounded_sanitized_tails(tmp_path):
    root = tmp_path / "workspace"
    stdout = "x" * 3500 + str(root) + "\\secret.txt" + "y" * 200
    result = subprocess.CompletedProcess(["docker"], 17, stdout, "failure")

    diagnostic = phase11_composition._process_diagnostic(result, root)

    assert diagnostic["exit_code"] == 17
    assert len(diagnostic["stdout_tail"]) <= 4000
    assert str(root) not in diagnostic["stdout_tail"]
    assert diagnostic["stderr_tail"] == "failure"


def test_gateway_adapters_capture_startup_with_utf8_replacement(monkeypatch, tmp_path):
    captured = []

    def fake_run(command, **kwargs):
        captured.append(kwargs)
        return subprocess.CompletedProcess(command, 125, "caf\u00e9", "startup failure")

    monkeypatch.setattr(subprocess, "run", fake_run)
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "bifrost-http").write_bytes(b"binary")
    bifrost = BifrostHTTPBackend(
        artifact_dir=artifact_dir,
        app_dir=tmp_path / "bifrost-app",
        image_ref="example/bifrost@sha256:" + "a" * 64,
        network_name="test-network",
        provider_url="https://api.a6api.com",
        host_port=18080,
        container_name="bifrost-test",
    )
    config_dir = tmp_path / "litellm-config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("model_list: []\n", encoding="utf-8")
    litellm = LiteLLMHTTPBackend(
        config_dir=config_dir,
        image_ref="example/litellm@sha256:" + "b" * 64,
        network_name="test-network",
        host_port=14000,
        container_name="litellm-test",
    )

    with pytest.raises(RuntimeError):
        bifrost.start()
    with pytest.raises(RuntimeError):
        litellm.start()

    assert len(captured) == 2
    assert all(kwargs["encoding"] == "utf-8" and kwargs["errors"] == "replace" for kwargs in captured)
    assert bifrost._startup_process_result.stdout == "caf\u00e9"
    assert litellm._startup_process_result.stderr == "startup failure"


def test_t03_continuation_maps_the_same_tool_call_id_once():
    assistant_content = [{"type": "tool_use", "id": "toolu_123", "name": "read_fixture", "input": {"path": "input/alpha.txt"}}]

    continuation = _continuation_request("gpt-5.4-mini", assistant_content, "toolu_123", "alpha fixture input\n")

    result_block = continuation["messages"][2]["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "toolu_123"
    assert result_block["content"] == "alpha fixture input\n"
    assert continuation["tool_choice"] == {"type": "auto"}


def test_t03_message_envelopes_require_protocol_stop_semantics():
    response = {"type": "message", "role": "assistant", "stop_reason": "tool_use", "content": []}

    assert _assistant_message(response, "tool_use")
    assert not _assistant_message(response, ("end_turn", "stop_sequence"))


def test_t03_one_shot_reservation_rejects_replay(tmp_path):
    _reserve_one_shot(tmp_path, "phase14-test")
    reservation = (tmp_path / "t03-one-shot-reservation.json").read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="already reserved"):
        _reserve_one_shot(tmp_path, "phase14-test")

    assert (tmp_path / "t03-one-shot-reservation.json").read_text(encoding="utf-8") == reservation


def test_t03_gateway_configs_use_inherited_a6api_environment_without_retries():
    bifrost, _, _ = _messages_config("Bifrost")
    _, litellm, _ = _messages_config("LiteLLM")

    assert bifrost["providers"]["openai"]["keys"][0]["value"] == "env.A6API_KEY"
    assert bifrost["providers"]["openai"]["network_config"]["max_retries"] == 0
    assert "api_key: os.environ/A6API_KEY" in litellm
    assert "num_retries: 0" in litellm
