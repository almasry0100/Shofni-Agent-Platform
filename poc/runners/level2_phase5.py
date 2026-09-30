"""Candidate-neutral Level 2 live and synthetic evidence runner.

The runner deliberately speaks the public HTTP protocols instead of importing
either candidate implementation.  This keeps the same probe logic reusable for
Bifrost and LiteLLM while making the client protocol represented by each row
explicit.  Provider credentials are read only into process memory and never
written to evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from poc.adapters.bifrost_http import BifrostHTTPBackend
from poc.adapters.litellm_http import LiteLLMHTTPBackend
from poc.evidence.redactor import redact_string, redact_value
from poc.evidence.taxonomy import FailureClass


BIFROST_IMAGE = "docker.io/library/golang:1.27.0-bookworm@sha256:ba5ef6614ca131b80a635fc6a7b715d9ee8a7f333debdbb81afb68259c7d48d4"
LITELLM_IMAGE = "shofni-litellm-oss-remediation:1.104.0@sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280"
PYTHON_IMAGE = "docker.io/library/python:3.13.7-slim-bookworm@sha256:781449467ffb6f04218f09b1ecdcdc7d22b289ee5da9ec498b024e24ad7a6db7"
BIFROST_ARTIFACT = "poc/.runtime/bifrost/artifacts/bifrost-http"
LITELLM_ARTIFACT = "poc/.runtime/litellm/artifacts/litellm-1.104.0-cp310-abi3-manylinux_2_34_x86_64.whl"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    key_env: str
    openai_model: str
    anthropic_model: str
    lite_openai_alias: str
    lite_anthropic_alias: str


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    artifact: str
    image: str
    setup_phase: str


PROVIDERS = {
    "A6api": ProviderSpec(
        "A6api",
        "https://api.a6api.com",
        "A6API_KEY",
        "gpt-5.4-mini",
        "claude-sonnet-4-5",
        "a6api-openai",
        "a6api-anthropic",
    ),
    "RelayRouter": ProviderSpec(
        "RelayRouter",
        "https://api.relayrouter.org/v1",
        "RELAYROUTER_API_KEY",
        "stealth/openai/gpt-5.6-sol",
        "stealth/openai/gpt-5.6-sol",
        "relay-openai",
        "relay-anthropic",
    ),
}
CANDIDATES = {
    "Bifrost": CandidateSpec("Bifrost", BIFROST_ARTIFACT, BIFROST_IMAGE, "phase3"),
    "LiteLLM": CandidateSpec("LiteLLM", LITELLM_ARTIFACT, LITELLM_IMAGE, "phase4"),
}
PAIRINGS = (
    ("Codex", "0.159.0", "A6api"),
    ("Claude Code", "2.1.278", "A6api"),
    ("OpenCode", "1.18.33", "A6api"),
    ("OpenCode", "1.18.33", "RelayRouter"),
)
VALID_TESTS = ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09-A", "T09-B")


def _run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError("Docker operation failed")
    return result


def _allocate_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _port_released(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _exists(name: str) -> bool:
    return _run(["docker", "inspect", name], check=False).returncode == 0


def _stop(name: str) -> bool:
    _run(["docker", "stop", "--time", "8", name], check=False)
    if _exists(name):
        _run(["docker", "rm", "--force", name], check=False)
    return not _exists(name)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact_value(value), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _canonical(value: Any) -> str:
    return json.dumps(redact_value(value), sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _error_class(error: BaseException, backend: Any | None = None) -> str:
    try:
        if backend is not None:
            classified = backend.classify_error(error)
            return getattr(classified, "value", str(classified))
    except Exception:
        pass
    message = str(error).lower()
    if "rate" in message or "429" in message:
        return FailureClass.RATE_LIMIT.value
    if "auth" in message or "401" in message or "403" in message:
        return FailureClass.AUTH_ERROR.value
    if "billing" in message or "402" in message or "credit" in message:
        return FailureClass.BILLING_ERROR.value
    if isinstance(error, (TimeoutError, ConnectionError)):
        return FailureClass.PROVIDER_FAILURE.value
    return FailureClass.GATEWAY_FAILURE.value


def _text_from_chat(value: dict[str, Any]) -> str | None:
    choices = value.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    return None


def _text_from_responses(value: dict[str, Any]) -> str | None:
    if isinstance(value.get("output_text"), str):
        return value["output_text"]
    output = value.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or not isinstance(item.get("content"), list):
                continue
            for part in item["content"]:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    return part["text"]
    return None


def _openai_tool_calls(value: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    choices = value.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("tool_calls"), list):
            for call in message["tool_calls"]:
                if isinstance(call, dict):
                    calls.append(call)
    output = value.get("output")
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") in {"function_call", "tool_call"}:
                calls.append(item)
    return calls


def _anthropic_tool_calls(value: dict[str, Any]) -> list[dict[str, Any]]:
    content = value.get("content")
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]


def _textual_tool_call(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    match = re.search(r"tool_call\s*:\s*(```json\s*)?(\{.*?\})(?:\s*```)?", value, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(2))
    except json.JSONDecodeError:
        return {"malformed": True}
    return parsed if isinstance(parsed, dict) else {"malformed": True}


def _stream_summary(events: list[dict[str, Any]], protocol: str) -> dict[str, Any]:
    if protocol == "messages":
        event_types = [event.get("type") for event in events if isinstance(event, dict)]
        text_events = [event for event in events if event.get("type") == "content_block_delta"]
        terminal = "message_stop" in event_types
        return {
            "event_count": len(events),
            "event_types": event_types[:30],
            "text_delta_count": len(text_events),
            "terminal_event": terminal,
            "valid": bool(events) and terminal,
        }
    finishes: list[str] = []
    deltas = 0
    for event in events:
        choices = event.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
            if isinstance(choice.get("finish_reason"), str):
                finishes.append(choice["finish_reason"])
            delta = choice.get("delta")
            if isinstance(delta, dict) and ("content" in delta or "tool_calls" in delta):
                deltas += 1
    return {
        "event_count": len(events),
        "finish_reasons": finishes,
        "delta_count": deltas,
        "terminal_event": bool(finishes),
        "valid": bool(events) and bool(finishes),
    }


def _fixture_reference(test_id: str, candidate: str) -> list[str]:
    phase2 = "tests/poc/evidence/phase-2/phase2-20260930T132937Z"
    mapping = {
        "T02": f"{phase2}/scenarios/t02_chat_only/record.json",
        "T05": f"{phase2}/scenarios/t05_text_valid/record.json",
        "T06": f"{phase2}/scenarios/t06_trailing_comma/record.json",
        "T09-A": f"{phase2}/scenarios/t09_before_tool/record.json",
        "T09-B": f"{phase2}/scenarios/t09_after_tool/record.json",
    }
    setup = (
        "tests/poc/evidence/phase-3/phase3-remediation-20260930T180800Z/result.json"
        if candidate == "Bifrost"
        else "tests/poc/evidence/phase-4/phase4-remediation-20260930T192000Z/result.json"
    )
    return [setup, mapping[test_id]]


def _bifrost_config(provider: ProviderSpec, secret: str) -> dict[str, Any]:
    base = {
        "keys": [{
            "name": f"shofni-{provider.name.lower()}",
            "value": secret,
            "weight": 1.0,
            "models": [provider.openai_model, provider.anthropic_model],
        }],
        "network_config": {
            "base_url": provider.base_url,
            "default_request_timeout_in_seconds": 90,
            "max_retries": 0,
            "allow_private_network": False,
        },
    }
    return {
        "version": 2,
        "providers": {"openai": base, "anthropic": base},
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


def _litellm_config(provider: ProviderSpec) -> str:
    lines = [
        "model_list:",
        "  - model_name: " + provider.lite_openai_alias,
        "    litellm_params:",
        "      model: openai/" + provider.openai_model,
        "      api_base: " + provider.base_url,
        "      api_key: os.environ/SHOFNI_PROVIDER_KEY",
        "  - model_name: " + provider.lite_anthropic_alias,
        "    litellm_params:",
        "      model: anthropic/" + provider.anthropic_model,
        "      api_base: " + provider.base_url,
        "      api_key: os.environ/SHOFNI_PROVIDER_KEY",
        "general_settings:",
        "  disable_spend_logs: true",
        "litellm_settings:",
        "  num_retries: 0",
        "  request_timeout: 90",
    ]
    return "\n".join(lines) + "\n"


def _fixture_sidecar(root: Path, network: str, name: str) -> None:
    _run([
        "docker", "run", "-d", "--name", name, "--platform", "linux/amd64", "--network", network,
        "--mount", f"type=bind,source={root / 'poc'},target=/workspace/poc,readonly",
        "--env", "PYTHONPATH=/workspace", "--env", "SHOFNI_FIXTURE_PORT=8081",
        PYTHON_IMAGE, "python", "-m", "poc.fixtures.fixture_sidecar",
    ])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if not _exists(name):
            break
        probe = _run([
            "docker", "exec", name, "python", "-c",
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2).read()",
        ], check=False)
        if probe.returncode == 0:
            return
        time.sleep(0.25)
    raise RuntimeError("fixture sidecar did not become ready")


class _LiveBackend:
    def __init__(self, backend: Any, candidate: CandidateSpec, provider: ProviderSpec, network: str, runtime_root: Path) -> None:
        self.backend = backend
        self.candidate = candidate
        self.provider = provider
        self.network = network
        self.runtime_root = runtime_root


def _start_live_backend(
    root: Path,
    candidate: CandidateSpec,
    provider: ProviderSpec,
    run_id: str,
    temp_root: Path,
    *,
    provider_config_override: dict[str, Any] | None = None,
    litellm_config_override: str | None = None,
) -> _LiveBackend:
    secret = os.environ.get(provider.key_env)
    if not secret:
        raise RuntimeError(f"{provider.key_env} is not present")
    suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{candidate.name}-{provider.name}".lower())[-45:]
    network = f"shofni-l2-{suffix}"
    container = f"shofni-gateway-{suffix}"
    _run(["docker", "network", "create", network])
    port = _allocate_port()
    if candidate.name == "Bifrost":
        app_dir = temp_root / "bifrost-app"
        backend = BifrostHTTPBackend(
            artifact_dir=(root / candidate.artifact).parent,
            app_dir=app_dir,
            image_ref="docker.io/library/golang:1.27.0-bookworm@sha256:ba5ef6614ca131b80a635fc6a7b715d9ee8a7f333debdbb81afb68259c7d48d4",
            network_name=network,
            provider_url=provider.base_url,
            host_port=port,
            container_name=container,
            provider_config=provider_config_override or _bifrost_config(provider, secret),
        )
    else:
        config_dir = temp_root / "litellm-config"
        config_dir.mkdir(parents=True, exist_ok=False)
        config_text = litellm_config_override or _litellm_config(provider)
        (config_dir / "config.yaml").write_text(config_text, encoding="utf-8", newline="\n")
        backend = LiteLLMHTTPBackend(
            config_dir=config_dir,
            image_ref=candidate.image,
            network_name=network,
            host_port=port,
            container_name=container,
            environment={"SHOFNI_PROVIDER_KEY": secret},
        )
    try:
        backend.start()
    except BaseException:
        _stop(container)
        _run(["docker", "network", "rm", network], check=False)
        raise
    return _LiveBackend(backend, candidate, provider, network, temp_root)


def _stop_live_backend(active: _LiveBackend) -> dict[str, Any]:
    backend = active.backend
    container = backend.container_name
    port = backend.host_port
    errors: list[str] = []
    try:
        backend.stop()
    except Exception as error:
        errors.append(type(error).__name__)
    removed = _stop(container)
    _run(["docker", "network", "rm", active.network], check=False)
    network_removed = _run(["docker", "network", "inspect", active.network], check=False).returncode != 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not _port_released(port):
        time.sleep(0.2)
    return {
        "candidate_container_removed": removed,
        "network_removed": network_removed,
        "api_port_released": _port_released(port),
        "temporary_config_removed": None,
        "errors": errors,
    }


def _probe_stream(backend: Any, request: dict[str, Any], protocol: str) -> dict[str, Any]:
    events = list(backend.stream(request))
    return _stream_summary(events, protocol)


def _run_live_test(
    backend: Any,
    client: str,
    provider: ProviderSpec,
    test_id: str,
    repetition: int,
    *,
    model_id: str | None = None,
    anthropic_model_id: str | None = None,
) -> dict[str, Any]:
    model = model_id or provider.openai_model
    anthropic_model = anthropic_model_id or provider.anthropic_model
    result: dict[str, Any] = {
        "test_id": test_id,
        "client": client,
        "provider": provider.name,
        "repetition": repetition,
        "status": "FAIL",
        "behavior_mode": "UNVERIFIED",
        "failure_class": None,
        "observations": {},
    }
    try:
        if test_id == "T01":
            response = backend.request({
                "protocol": "responses",
                "model": model,
                "input": "Use the read_fixture function exactly once with path input/alpha.txt. Return no prose before the call.",
                "tools": [{"type": "function", "name": "read_fixture", "description": "Read one fixture file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}],
                "tool_choice": {"type": "function", "name": "read_fixture"},
            })
            calls = _openai_tool_calls(response)
            result["observations"] = {"response_id": response.get("id"), "tool_call_count": len(calls), "tool_calls": calls[:3]}
            result["status"] = "PASS" if calls else "FAIL"
            result["behavior_mode"] = "NATIVE" if calls else "UNVERIFIED"
            if not calls:
                result["failure_class"] = FailureClass.MODEL_BEHAVIOR_FAILURE.value
        elif test_id == "T03":
            response = backend.request({
                "protocol": "messages",
                "model": anthropic_model,
                "max_tokens": 256,
                "messages": [{"role": "user", "content": "Use the read_fixture tool exactly once with path input/alpha.txt."}],
                "tools": [{"name": "read_fixture", "description": "Read one fixture file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}],
                "tool_choice": {"type": "tool", "name": "read_fixture"},
            })
            calls = _anthropic_tool_calls(response)
            result["observations"] = {"response_id": response.get("id"), "tool_call_count": len(calls), "tool_calls": calls[:3]}
            result["status"] = "PASS" if calls else "FAIL"
            result["behavior_mode"] = "NATIVE" if calls else "UNVERIFIED"
            if not calls:
                result["failure_class"] = FailureClass.MODEL_BEHAVIOR_FAILURE.value
        elif test_id == "T04":
            response = backend.request({
                "model": model,
                "messages": [{"role": "user", "content": "Respond with a concise greeting and no tool call."}],
            })
            text = _text_from_chat(response)
            pseudo = _textual_tool_call(text)
            result["observations"] = {"response_id": response.get("id"), "text": text, "textual_tool_call": pseudo}
            result["status"] = "PASS" if isinstance(text, str) and text.strip() else "FAIL"
            result["behavior_mode"] = "EMULATED" if pseudo else "UNSUPPORTED" if provider.name == "RelayRouter" else "NATIVE"
            if result["status"] != "PASS":
                result["failure_class"] = FailureClass.PROVIDER_FAILURE.value
        elif test_id == "T08":
            protocol = "messages" if client == "Claude Code" else "chat"
            if protocol == "messages":
                request = {"protocol": "messages", "model": anthropic_model, "max_tokens": 128, "messages": [{"role": "user", "content": "Say stream-ok."}], "stream": True}
            else:
                request = {"model": model, "messages": [{"role": "user", "content": "Say stream-ok."}], "stream": True}
            summary = _probe_stream(backend, request, protocol)
            result["observations"] = summary
            result["status"] = "PASS" if summary["valid"] else "FAIL"
            result["behavior_mode"] = "NATIVE" if summary["valid"] else "UNVERIFIED"
            if result["status"] != "PASS":
                result["failure_class"] = FailureClass.STREAMING_FAILURE.value
        elif test_id == "T07":
            response = backend.request({
                "model": model,
                "messages": [{"role": "user", "content": "Call read_fixture exactly once with path input/alpha.txt."}],
                "tools": [{"type": "function", "function": {"name": "read_fixture", "description": "Read one fixture file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}],
                "tool_choice": "required",
            })
            calls = _openai_tool_calls(response)
            if calls:
                call = calls[0]
                call_id = call.get("id") or call.get("call_id") or "tool-call"
                function = call.get("function") if isinstance(call, dict) else None
                name = function.get("name") if isinstance(function, dict) else call.get("name")
                arguments = function.get("arguments") if isinstance(function, dict) else call.get("arguments")
                continued = backend.request({
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Call read_fixture exactly once with path input/alpha.txt."},
                        response.get("choices", [{}])[0].get("message", {}) if isinstance(response.get("choices"), list) else {},
                        {"role": "tool", "tool_call_id": call_id, "name": name or "read_fixture", "content": "fixture-content"},
                    ],
                })
                text = _text_from_chat(continued)
                result["observations"] = {"first_tool_call": {"name": name, "arguments": arguments, "id": call_id}, "continuation_response_id": continued.get("id"), "final_text_present": bool(text)}
                result["status"] = "PASS" if text else "FAIL"
                result["behavior_mode"] = "NATIVE"
            else:
                result["observations"] = {"first_tool_call_count": 0}
                result["failure_class"] = FailureClass.CONTINUATION_FAILURE.value
        else:
            raise ValueError(f"unsupported live test {test_id}")
    except Exception as error:
        result["status"] = "FAIL"
        result["failure_class"] = _error_class(error, backend)
        result["observations"] = {"error_type": type(error).__name__, "error": redact_string(str(error))}
        status_code = getattr(error, "status_code", None)
        if isinstance(status_code, int):
            result["provider_http_status"] = status_code
            result["redacted_provider_error_body"] = redact_value(getattr(error, "body", {}))
    return redact_value(result)


def _synthetic_rows(candidate: str, run_id: str) -> list[dict[str, Any]]:
    rows = []
    for test_id in ("T02", "T05", "T06", "T09-A", "T09-B"):
        rows.append({
            "test_id": test_id,
            "candidate": candidate,
            "client": "candidate-neutral fixture harness",
            "client_version": None,
            "provider": "Shofni synthetic fixture",
            "model_id": "synthetic",
            "protocol": "candidate-neutral fixture contract",
            "status": "PASS",
            "behavior_mode": "EMULATED" if test_id in {"T02", "T05", "T06"} else "NATIVE",
            "failure_class": None,
            "fixture_control_status": "PASS_IN_PHASE_2_ONLY",
            "candidate_execution": False,
            "evidence_type": "SYNTHETIC_FIXTURE_EVIDENCE",
            "evidence_refs": _fixture_reference(test_id, candidate),
            "run_id": run_id,
        })
    return rows


def _latest_setup(manifest: dict[str, Any], candidate: str) -> dict[str, Any]:
    return manifest["attempts"][candidate.lower()]


def _model_ids(candidate_name: str, provider: ProviderSpec) -> tuple[str, str]:
    if candidate_name == "Bifrost":
        return provider.openai_model, provider.anthropic_model
    return provider.lite_openai_alias, provider.lite_anthropic_alias


def _live_evidence_ref(run_id: str, record: dict[str, Any]) -> str:
    repetition = record.get("repetition", "startup")
    test_id = str(record["test_id"]).replace("/", "-")
    return (
        f"tests/poc/evidence/level2/{run_id}/runs/"
        f"{record['candidate'].lower()}/{record['provider'].lower()}/"
        f"{record['client'].lower().replace(' ', '-')}/"
        f"{repetition}-{test_id}.json"
    )


def run_phase5(root: Path, run_id: str, repetitions: int = 3) -> dict[str, Any]:
    root = root.resolve()
    evidence_dir = root / "tests/poc/evidence/level2" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    remediation_path = root / "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json"
    remediation = json.loads(remediation_path.read_text(encoding="utf-8"))
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    execution_records: list[dict[str, Any]] = []
    cleanup: list[dict[str, Any]] = []
    provider_key_presence = {
        "A6api": bool(os.environ.get(PROVIDERS["A6api"].key_env)),
        "RelayRouter": bool(os.environ.get(PROVIDERS["RelayRouter"].key_env)),
    }
    setup_states = {candidate: _latest_setup(remediation, candidate) for candidate in CANDIDATES}
    for candidate_name, candidate in CANDIDATES.items():
        rows.extend(_synthetic_rows(candidate_name, run_id))
        if setup_states[candidate_name].get("status") != "PASS":
            for client, version, provider_name in PAIRINGS:
                for test_id in ("T01", "T03", "T04", "T07", "T08"):
                    if (test_id == "T01" and client != "Codex") or (test_id == "T03" and client != "Claude Code") or (test_id == "T04" and client != "OpenCode"):
                        continue
                    rows.append({
                        "test_id": test_id, "candidate": candidate_name, "client": client, "client_version": version,
                        "provider": provider_name, "model_id": "unverified", "protocol": "live protocol probe",
                        "status": "BLOCKED", "behavior_mode": "UNVERIFIED", "failure_class": FailureClass.SETUP_FAILURE.value,
                        "candidate_execution": False, "evidence_type": "SOURCE_INSPECTION_EVIDENCE",
                        "evidence_refs": [f"tests/poc/evidence/phase-{candidate.setup_phase}/{setup_states[candidate_name]['latest_attempt_id']}/result.json"],
                        "run_id": run_id,
                    })
            continue
        for provider_name in ("A6api", "RelayRouter"):
            provider = PROVIDERS[provider_name]
            if not provider_key_presence[provider.name]:
                continue
            provider_pairings = [pairing for pairing in PAIRINGS if pairing[2] == provider_name]
            with tempfile.TemporaryDirectory(prefix=f"phase5-{candidate_name.lower()}-{provider_name.lower()}-", dir=root / "poc/.runtime") as temp_name:
                temp_root = Path(temp_name)
                active: _LiveBackend | None = None
                cleanup_result: dict[str, Any] | None = None
                try:
                    active = _start_live_backend(root, candidate, provider, run_id, temp_root)
                    openai_model, anthropic_model = _model_ids(candidate_name, provider)
                    for client, version, _ in provider_pairings:
                        tests = ["T01"] if client == "Codex" else ["T03"] if client == "Claude Code" else ["T04", "T07", "T08"]
                        for repetition in range(1, repetitions + 1):
                            for test_id in tests:
                                record = _run_live_test(
                                    active.backend,
                                    client,
                                    provider,
                                    test_id,
                                    repetition,
                                    model_id=openai_model,
                                    anthropic_model_id=anthropic_model,
                                )
                                record.update({
                                    "candidate": candidate_name,
                                    "client_version": version,
                                    "model_id": openai_model if client != "Claude Code" else anthropic_model,
                                    "protocol": "Responses" if test_id == "T01" else "Anthropic Messages" if test_id == "T03" else "Chat Completions",
                                    "candidate_execution": True,
                                    "evidence_type": "LIVE_PROVIDER_EVIDENCE",
                                    "run_id": run_id,
                                    "evidence_refs": [],
                                })
                                rows.append(record)
                                execution_records.append(record)
                except Exception as error:
                    for client, version, _ in provider_pairings:
                        tests = ["T01"] if client == "Codex" else ["T03"] if client == "Claude Code" else ["T04", "T07", "T08"]
                        for test_id in tests:
                            record = {
                                "test_id": test_id, "candidate": candidate_name, "client": client, "client_version": version,
                                "provider": provider_name, "model_id": _model_ids(candidate_name, provider)[0] if client != "Claude Code" else _model_ids(candidate_name, provider)[1],
                                "protocol": "Responses" if test_id == "T01" else "Anthropic Messages" if test_id == "T03" else "Chat Completions",
                                "status": "FAIL", "behavior_mode": "UNVERIFIED", "failure_class": _error_class(error),
                                "candidate_execution": False, "evidence_type": "LIVE_PROVIDER_EVIDENCE", "run_id": run_id,
                                "evidence_refs": [], "observations": {"error_type": type(error).__name__, "error": redact_string(str(error))},
                            }
                            rows.append(record)
                            execution_records.append(record)
                finally:
                    if active is not None:
                        cleanup_result = _stop_live_backend(active)
            if cleanup_result is not None:
                cleanup_result["temporary_config_removed"] = not temp_root.exists()
                cleanup.append(cleanup_result)

        for row in rows:
            if row.get("candidate") == candidate_name and row.get("evidence_type") == "LIVE_PROVIDER_EVIDENCE":
                row["evidence_refs"] = [_live_evidence_ref(run_id, row)]

    for record in execution_records:
        repetition = record.get("repetition", "startup")
        target = evidence_dir / "runs" / record["candidate"].lower() / record["provider"].lower() / record["client"].lower().replace(" ", "-") / f"{repetition}-{record['test_id']}.json"
        _json(target, record)

    for row in rows:
        row.setdefault("evidence_refs", [])
    valid_rows = [row for row in rows if row["status"] in {"PASS", "FAIL", "BLOCKED"}]
    live_failures = [row for row in valid_rows if row.get("evidence_type") == "LIVE_PROVIDER_EVIDENCE" and row["status"] == "FAIL"]
    blocked = [row for row in valid_rows if row["status"] == "BLOCKED"]
    status = "PASS" if not live_failures and not blocked and all(row["status"] == "PASS" for row in valid_rows) else "PARTIAL"
    matrix = {
        "schema_version": "1.1",
        "phase": "phase_5",
        "run_id": run_id,
        "batch_run_id": "batch-b-remediation-20260930T155149Z",
        "observed_at": timestamp,
        "status": status,
        "evidence_type": "MIXED_LIVE_AND_SYNTHETIC_EVIDENCE",
        "candidate_executions": bool(execution_records),
        "execution_mode": "candidate-neutral HTTP protocol probes; installed client versions represented by protocol rows",
        "provider_key_presence": provider_key_presence,
        "repetitions_requested": repetitions,
        "rows": rows,
        "not_applicable_pairings": [
            {"client": "Codex", "client_version": "0.159.0", "provider": "RelayRouter", "status": "NOT_APPLICABLE", "reason": "Known unsupported direct pairing; not a gateway failure.", "evidence_ref": "docs/05-client-targets.md"},
            {"client": "Claude Code", "client_version": "2.1.278", "provider": "RelayRouter", "status": "NOT_APPLICABLE", "reason": "Known unsupported direct pairing; not a gateway failure.", "evidence_ref": "docs/05-client-targets.md"},
        ],
        "phase_2_fixture_controls": {"status": "PASS", "scope": "Shofni fixture/harness only; synthetic rows do not establish live provider behavior.", "evidence_ref": "tests/poc/evidence/phase-2/phase2-20260930T132937Z/result.json"},
        "cleanup": cleanup,
        "live_provider_requests": len(execution_records),
    }
    _json(evidence_dir / "matrix.json", matrix)
    manifest = {
        "phase": "phase_5",
        "run_id": run_id,
        "batch_run_id": "batch-b-remediation-20260930T155149Z",
        "created_at_utc": timestamp,
        "result_status": status,
        "candidate_source_modified": False,
        "candidate_processes_started": len({row["candidate"] for row in execution_records}),
        "live_provider_requests": len(execution_records),
        "provider_key_presence": provider_key_presence,
        "raw_evidence_created": False,
        "candidate_tree_hashes_referenced": {name: "docs/poc/candidate-lock.json" for name in CANDIDATES},
        "cleanup": cleanup,
        "evidence_files": ["matrix.json", "manifest.json"],
    }
    _json(evidence_dir / "manifest.json", manifest)
    (evidence_dir / "matrix.sha256").write_text(_sha256(evidence_dir / "matrix.json") + "\n", encoding="utf-8")
    return matrix


def _next_run_id(root: Path) -> str:
    stem = "level2-remediation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = stem
    suffix = 1
    while (root / "tests/poc/evidence/level2" / candidate).exists():
        candidate = f"{stem}-{suffix:02d}"
        suffix += 1
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the candidate-neutral Batch B Phase 5 suite.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args(argv)
    if args.repetitions < 1 or args.repetitions > 3:
        parser.error("repetitions must be between 1 and 3")
    result = run_phase5(args.root, args.run_id or _next_run_id(args.root), args.repetitions)
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "live_provider_requests": result["live_provider_requests"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
