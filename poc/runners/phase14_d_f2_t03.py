"""Execute one bounded Claude Code T03 protocol attempt per locked gateway."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.adapters.bifrost_http import BifrostHTTPBackend
from poc.adapters.litellm_http import LiteLLMHTTPBackend
from poc.evidence.redactor import redact_value
from poc.evidence.taxonomy import FailureClass
from poc.fixtures.workspace import DisposableWorkspace
from poc.runners.level2_phase5 import CANDIDATES, PROVIDERS, _LiveBackend, _allocate_port, _stop_live_backend
from poc.runners.phase11_composition import (
    BIFROST_ARTIFACT,
    BIFROST_IMAGE,
    LITELLM_IMAGE,
    LITELLM_WHEEL,
    _route_probe,
)


MODEL = "gpt-5.4-mini"
LITELLM_MESSAGES_ALIAS = "a6api-anthropic"
PROMPT = "Use the read_fixture tool exactly once with path input/alpha.txt."
TOOL_RESULT_PATH = "input/alpha.txt"
TOOL = {
    "name": "read_fixture",
    "description": "Read one fixture file.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize(value: Any, root: Path) -> Any:
    if isinstance(value, str):
        result = str(redact_value(value))
        for private_root in (root.resolve(), root.parent.resolve(), Path.home().resolve()):
            result = re.sub(re.escape(str(private_root)), "<LOCAL_PATH>", result, flags=re.IGNORECASE)
        return result
    if isinstance(value, dict):
        return {key: _sanitize(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, root) for item in value]
    return value


def _write(path: Path, value: Any, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sanitize(value, root), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _tool_use_blocks(response: dict[str, Any]) -> list[dict[str, Any]]:
    content = response.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict) and block.get("type") == "tool_use"]


def _assistant_message(response: dict[str, Any], expected_stop_reason: str | tuple[str, ...]) -> bool:
    reasons = (expected_stop_reason,) if isinstance(expected_stop_reason, str) else expected_stop_reason
    return (
        response.get("type") == "message"
        and response.get("role") == "assistant"
        and response.get("stop_reason") in reasons
        and isinstance(response.get("content"), list)
    )


def _reserve_one_shot(output_root: Path, run_id: str) -> None:
    reservation = output_root / "t03-one-shot-reservation.json"
    result_paths = [output_root / f"{candidate.lower()}-t03.json" for candidate in ("Bifrost", "LiteLLM")]
    if reservation.exists() or any(path.exists() for path in result_paths):
        raise FileExistsError("the authorized T03 follow-up attempt is already reserved or has evidence")
    payload = json.dumps({
        "schema_version": "1.0",
        "run_id": run_id,
        "scope": "one T03 gateway-protocol attempt per locked candidate",
        "attempt_ids": [f"{run_id}-{name.lower()}-t03-attempt-1" for name in ("Bifrost", "LiteLLM")],
        "reserved_at_utc": _timestamp(),
    }, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    with reservation.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def _continuation_request(model: str, assistant_content: list[dict[str, Any]], call_id: str, result: str) -> dict[str, Any]:
    return {
        "protocol": "messages",
        "model": model,
        "max_tokens": 256,
        "messages": [
            {"role": "user", "content": PROMPT},
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call_id, "content": result}]},
        ],
        "tools": [TOOL],
        "tool_choice": {"type": "auto"},
    }


def _messages_config(candidate_name: str) -> tuple[dict[str, Any] | None, str | None, str]:
    if candidate_name == "Bifrost":
        provider = {
            "keys": [{"name": "shofni-a6api-openai-compatible", "value": "env.A6API_KEY", "weight": 1.0, "models": [MODEL]}],
            "network_config": {
                "base_url": "https://api.a6api.com",
                "default_request_timeout_in_seconds": 90,
                "max_retries": 0,
                "allow_private_network": False,
            },
        }
        config = {
            "version": 2,
            "providers": {"openai": provider},
            "framework": {"pricing": {
                "pricing_url": "file:///data/pricing.json",
                "model_parameters_url": "file:///data/model-parameters.json",
                "mcp_library_sync_interval": 0,
                "live_models_sync_interval": 0,
            }},
            "config_store": {"enabled": False},
            "logs_store": {"enabled": False},
            "client": {"disable_db_pings_in_health": True},
        }
        return config, None, MODEL
    config = "\n".join([
        "model_list:",
        f"  - model_name: {LITELLM_MESSAGES_ALIAS}",
        "    litellm_params:",
        f"      model: openai/{MODEL}",
        "      api_base: https://api.a6api.com",
        "      api_key: os.environ/A6API_KEY",
        "general_settings:",
        "  disable_spend_logs: true",
        "litellm_settings:",
        "  num_retries: 0",
        "  request_timeout: 90",
        "",
    ])
    return None, config, LITELLM_MESSAGES_ALIAS


def _docker(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def _start_gateway(root: Path, candidate_name: str, run_id: str, temp_root: Path):
    if not os.environ.get("A6API_KEY"):
        raise RuntimeError("A6API_KEY is missing")
    provider = PROVIDERS["A6api"]
    spec = CANDIDATES[candidate_name]
    suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{candidate_name}".lower())[-45:]
    network = f"shofni-df2-{suffix}"
    container = f"shofni-df2-gateway-{suffix}"
    created = _docker(["docker", "network", "create", network])
    if created.returncode != 0:
        raise RuntimeError("Docker could not create the follow-up network")
    port = _allocate_port()
    provider_config, litellm_config, inbound_model = _messages_config(candidate_name)
    try:
        if candidate_name == "Bifrost":
            app_dir = temp_root / "bifrost-app"
            backend = BifrostHTTPBackend(
                artifact_dir=(root / BIFROST_ARTIFACT).parent,
                app_dir=app_dir,
                image_ref=BIFROST_IMAGE,
                network_name=network,
                provider_url=provider.base_url,
                host_port=port,
                container_name=container,
                provider_config=provider_config,
                environment={"A6API_KEY": None},
            )
        else:
            config_dir = temp_root / "litellm-config"
            config_dir.mkdir(parents=True, exist_ok=False)
            (config_dir / "config.yaml").write_text(litellm_config or "", encoding="utf-8", newline="\n")
            backend = LiteLLMHTTPBackend(
                config_dir=config_dir,
                image_ref=LITELLM_IMAGE,
                network_name=network,
                host_port=port,
                container_name=container,
                environment={"A6API_KEY": None},
            )
        backend.start()
    except BaseException:
        _docker(["docker", "rm", "--force", container])
        _docker(["docker", "network", "rm", network])
        raise
    active = _LiveBackend(backend, spec, provider, network, temp_root)
    return active, inbound_model


def _cleanup(active: _LiveBackend, temp_root: Path) -> dict[str, Any]:
    result = _stop_live_backend(active)
    result["temporary_config_removed"] = not temp_root.exists()
    return result


def _run_pair(root: Path, candidate_name: str, run_id: str, output_root: Path) -> dict[str, Any]:
    attempt_id = f"{run_id}-{candidate_name.lower()}-t03-attempt-1"
    started = _timestamp()
    provider = "A6api"
    gateway_endpoint = "/anthropic/v1/messages" if candidate_name == "Bifrost" else "/v1/messages"
    upstream = {
        "client_protocol": "Anthropic Messages",
        "canonical_translation": "Anthropic Messages -> gateway canonical request -> OpenAI Responses",
        "gateway_endpoint": gateway_endpoint,
        "provider": provider,
        "provider_route": MODEL,
        "provider_protocol": "OpenAI Responses",
        "provider_path": "/v1/responses",
        "provider_base_url": "https://api.a6api.com",
        "configured_retry_count": 0,
    }
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "started_at_utc": started,
        "candidate": candidate_name,
        "candidate_tree_hash": "sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe" if candidate_name == "Bifrost" else "sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb",
        "gateway_artifact_identity": {
            "Bifrost": {
                "binary_path": BIFROST_ARTIFACT,
                "binary_sha256": "sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5",
                "container_image": BIFROST_IMAGE,
            },
            "LiteLLM": {
                "runtime_image": LITELLM_IMAGE,
                "wheel_path": LITELLM_WHEEL,
                "wheel_sha256": "sha256:762b286fe81491f242040b14f28338da0ebf4f32fea50972b6969ee578011d52",
            },
        }[candidate_name],
        "client": "Claude Code",
        "client_version": "2.1.278",
        "client_execution_backend": "CLIENT",
        "test_id": "T03",
        "provider": provider,
        "model_id": MODEL,
        "configured_upstream_route": upstream,
        "upstream_request_observability": "NOT_INSTRUMENTED_BY_GATEWAY_HTTP_CLIENT",
        "client_execution_mode": "RAW_PROTOCOL_EQUIVALENT_GATEWAY_PROBE",
        "actual_claude_code_invoked": False,
        "claude_code_client_validation": "UNVERIFIED",
        "claim_limitations": [
            "This probes the Anthropic Messages gateway boundary and continuation flow.",
            "It does not prove actual Claude Code parsing or client-side schema acceptance.",
            "The A6api route and OpenAI Responses path are configured; upstream HTTP telemetry is not directly observed.",
        ],
        "status": "FAIL",
        "failure_class": None,
        "provider_key_presence": "PRESENT" if os.environ.get("A6API_KEY") else "MISSING",
        "gateway_request_attempts": 0,
        "gateway_http_statuses": [],
        "tool_execution_count": 0,
        "cleanup": None,
    }
    temp_root: Path | None = None
    active: _LiveBackend | None = None
    try:
        runtime_dir = root / "poc/.runtime"
        with tempfile.TemporaryDirectory(prefix=f"phase14-df2-{candidate_name.lower()}-", dir=runtime_dir) as temp_name:
            temp_root = Path(temp_name)
            active, inbound_model = _start_gateway(root, candidate_name, run_id, temp_root)
            record["gateway_identity"] = {
                "container": active.backend.container_name,
                "network": active.network,
                "readiness": "PASS",
                "inbound_model_id": inbound_model,
            }
            route_probe = _route_probe(active.backend.list_models(), (inbound_model,))
            record["route_probe"] = route_probe
            if route_probe["status"] != "PASS":
                record.update({"status": "BLOCKED", "failure_class": "ROUTE_NOT_AVAILABLE"})
            else:
                request = {
                    "protocol": "messages",
                    "model": inbound_model,
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": PROMPT}],
                    "tools": [TOOL],
                    "tool_choice": {"type": "tool", "name": "read_fixture"},
                }
                record["normalized_request"] = request
                try:
                    record["gateway_request_attempts"] = 1
                    first = active.backend.request(request)
                    record["gateway_http_statuses"].append(200)
                    record["initial_response"] = first
                    calls = _tool_use_blocks(first)
                    record["native_tool_calls"] = calls
                    record["tool_call_ids"] = [call.get("id") for call in calls if isinstance(call.get("id"), str)]
                    if not _assistant_message(first, "tool_use"):
                        record.update({"status": "FAIL", "failure_class": FailureClass.PROTOCOL_TRANSLATION_FAILURE.value})
                    elif len(calls) != 1:
                        record.update({"status": "FAIL", "failure_class": FailureClass.MODEL_BEHAVIOR_FAILURE.value})
                    else:
                        call = calls[0]
                        call_id = call.get("id")
                        arguments = call.get("input")
                        record["tool_schema"] = TOOL["input_schema"]
                        record["tool_name"] = call.get("name")
                        record["tool_arguments"] = arguments
                        if call.get("name") != TOOL["name"]:
                            record.update({"status": "FAIL", "failure_class": FailureClass.TOOL_SCHEMA_FAILURE.value})
                        elif not isinstance(call_id, str) or not call_id or not isinstance(arguments, dict) or arguments.get("path") != TOOL_RESULT_PATH:
                            record.update({"status": "FAIL", "failure_class": "TOOL_ARGUMENT_OR_CORRELATION_FAILURE"})
                        else:
                            with DisposableWorkspace(seed=attempt_id) as workspace:
                                tool_result = workspace.read_text(arguments["path"])
                            record["tool_execution_count"] = 1
                            record["tool_result_mapping"] = {"tool_use_id": call_id, "result": tool_result}
                            content = first.get("content")
                            if not isinstance(content, list):
                                record.update({"status": "FAIL", "failure_class": "CLIENT_PROTOCOL_FAILURE"})
                            else:
                                continuation = _continuation_request(inbound_model, content, call_id, tool_result)
                                record["continuation_request"] = continuation
                                try:
                                    record["gateway_request_attempts"] = 2
                                    final = active.backend.request(continuation)
                                    record["gateway_http_statuses"].append(200)
                                    record["continuation_response"] = final
                                    extra_calls = _tool_use_blocks(final)
                                    record["continuation_tool_call_count"] = len(extra_calls)
                                    text = "".join(block.get("text", "") for block in final.get("content", []) if isinstance(block, dict) and block.get("type") == "text")
                                    record["final_response"] = {
                                        "response_id": final.get("id"),
                                        "text": text,
                                        "stop_reason": final.get("stop_reason"),
                                    }
                                    if extra_calls:
                                        record.update({"status": "FAIL", "failure_class": "DUPLICATE_TOOL_REQUEST"})
                                    elif not _assistant_message(final, ("end_turn", "stop_sequence")):
                                        record.update({"status": "FAIL", "failure_class": FailureClass.PROTOCOL_TRANSLATION_FAILURE.value})
                                    elif text.strip():
                                        record.update({"status": "PASS", "failure_class": None})
                                    else:
                                        record.update({"status": "FAIL", "failure_class": FailureClass.MODEL_BEHAVIOR_FAILURE.value})
                                except Exception as error:
                                    status_code = getattr(error, "status_code", None)
                                    if status_code is not None:
                                        record["gateway_http_statuses"].append(status_code)
                                    record.update({"status": "FAIL", "failure_class": active.backend.classify_error(error).value, "continuation_error": {"type": type(error).__name__, "message": str(error)}})
                except Exception as error:
                    status_code = getattr(error, "status_code", None)
                    if status_code is not None:
                        record["gateway_http_statuses"].append(status_code)
                    record.update({"status": "FAIL", "failure_class": active.backend.classify_error(error).value, "initial_error": {"type": type(error).__name__, "message": str(error)}})
    except Exception as error:
        record.update({"status": "FAIL", "failure_class": "GATEWAY_OR_SETUP_FAILURE", "setup_error": {"type": type(error).__name__, "message": str(error)}})
    finally:
        if active is not None:
            record["cleanup"] = _cleanup(active, temp_root or Path())
        elif temp_root is not None:
            record["cleanup"] = {"temporary_config_removed": not temp_root.exists()}
    path = output_root / f"{candidate_name.lower()}-t03.json"
    _write(path, record, root)
    record["evidence_path"] = path.as_posix()
    return record


def run_t03(root: Path, run_id: str, output_root: Path) -> dict[str, Any]:
    root = root.resolve()
    from poc.runners.phase11_composition import _validate_live_inputs

    _validate_live_inputs(root)
    output_root.mkdir(parents=True, exist_ok=True)
    _reserve_one_shot(output_root, run_id)
    rows = [_run_pair(root, candidate, run_id, output_root) for candidate in ("Bifrost", "LiteLLM")]
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "D-F2/T03",
        "provider": "A6api",
        "model_id": MODEL,
        "attempts_per_candidate": 1,
        "rows": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "PARTIAL",
        "gateway_request_attempts": sum(row["gateway_request_attempts"] for row in rows),
        "upstream_provider_request_observability": "NOT_INSTRUMENTED_BY_GATEWAY_HTTP_CLIENT",
    }
