"""Targeted Batch B provider and gateway diagnostics.

This runner records one fresh request per failed live path. It preserves the
original Phase 5 matrices and writes only redacted diagnostic evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.adapters.bifrost_http import GatewayRequestError as BifrostGatewayRequestError
from poc.adapters.litellm_http import GatewayRequestError as LiteLLMGatewayRequestError
from poc.evidence.redactor import redact_string, redact_value
from poc.runners.level2_phase5 import CANDIDATES, PROVIDERS, _start_live_backend, _stop_live_backend


T03_REQUEST = {
    "protocol": "messages",
    "model": "claude-sonnet-4-5",
    "max_tokens": 256,
    "messages": [
        {"role": "user", "content": "Use the read_fixture tool exactly once with path input/alpha.txt."}
    ],
    "tools": [
        {
            "name": "read_fixture",
            "description": "Read one fixture file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ],
    "tool_choice": {"type": "tool", "name": "read_fixture"},
}

RELAY_CHAT_REQUEST = {
    "model": "stealth/openai/gpt-5.6-sol",
    "messages": [{"role": "user", "content": "Reply with OK."}],
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _request_id(value: Any) -> str | None:
    if isinstance(value, dict):
        request_id = value.get("request_id")
        if isinstance(request_id, str):
            return request_id
        for item in value.values():
            found = _request_id(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _request_id(item)
            if found:
                return found
    return None


def _http_json(
    *,
    control: str,
    base_url: str,
    path: str,
    key_env: str,
    auth_header: str,
    model: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    key = os.environ.get(key_env)
    record: dict[str, Any] = {
        "control": control,
        "endpoint_path": path,
        "model": model,
        "key_env": key_env,
        "key_present": bool(key),
        "request_headers": {
            "auth_header_present": auth_header.casefold() == "authorization" and bool(key),
            "vendor_key_header_present": auth_header.casefold() == "x-api-key" and bool(key),
            "content_type": "application/json",
            "accept": "application/json",
        },
        "request": redact_value(payload),
    }
    if not key:
        record.update({"status": "UNAVAILABLE", "failure_class": "AUTH_ERROR"})
        return record
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        auth_header: ("Bearer " + key) if auth_header.casefold() == "authorization" else key,
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:
            raw = response.read()
            parsed = json.loads(raw)
            record.update({"status": response.status, "response": redact_value(parsed), "request_id": _request_id(parsed)})
            return record
    except urllib.error.HTTPError as error:
        raw = error.read(65536)
        try:
            parsed: Any = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            parsed = {"raw_body": raw.decode("utf-8", "replace")}
        record.update({"status": error.code, "response": redact_value(parsed), "request_id": _request_id(parsed)})
        return record
    except Exception as error:  # pragma: no cover - live diagnostic boundary
        record.update(
            {
                "status": "ERROR",
                "error_type": type(error).__name__,
                "error": redact_string(str(error)),
            }
        )
        return record


def _container_logs(container_name: str) -> str:
    result = subprocess.run(
        ["docker", "logs", "--tail", "250", container_name],
        capture_output=True,
        text=True,
        check=False,
    )
    return redact_string(((result.stdout or "") + (result.stderr or "")).strip())[-16000:]


def _gateway_request(candidate: str, provider: str) -> dict[str, Any]:
    if provider == "A6api":
        request = dict(T03_REQUEST)
        if candidate == "LiteLLM":
            request["model"] = "a6api-anthropic"
        return request
    request = dict(RELAY_CHAT_REQUEST)
    if candidate == "LiteLLM":
        request["model"] = "relay-openai"
    return request


def _gateway_metadata(candidate: str, provider: str) -> dict[str, Any]:
    if provider == "A6api":
        if candidate == "Bifrost":
            return {
                "inbound_client_protocol": "Anthropic Messages",
                "gateway_endpoint": "/anthropic/v1/messages",
                "provider_selected": "anthropic",
                "model_route_id": "claude-sonnet-4-5",
                "model_alias": None,
                "configured_upstream_protocol": "Anthropic Messages adapter",
                "required_upstream_protocol": "OpenAI Chat Completions or Responses",
                "configured_upstream_url_path": "/v1/messages",
                "wire_path_source": "Bifrost AnthropicProvider buildRequestURL(..., /v1/messages, ...) and Anthropic Responses handler",
            }
        return {
            "inbound_client_protocol": "Anthropic Messages",
            "gateway_endpoint": "/v1/messages",
            "provider_selected": "anthropic/claude-sonnet-4-5",
            "model_route_id": "claude-sonnet-4-5",
            "model_alias": "a6api-anthropic",
            "configured_upstream_protocol": "Anthropic Messages translation",
            "required_upstream_protocol": "OpenAI Chat Completions or Responses",
            "configured_upstream_url_path": "/v1/messages",
            "wire_path_source": "LiteLLM AnthropicMessagesConfig.get_complete_url appends /v1/messages",
        }
    return {
        "inbound_client_protocol": "OpenAI Chat Completions",
        "gateway_endpoint": "/openai/v1/chat/completions" if candidate == "Bifrost" else "/v1/chat/completions",
        "provider_selected": "openai/stealth/openai/gpt-5.6-sol" if candidate == "LiteLLM" else "openai",
        "model_route_id": "stealth/openai/gpt-5.6-sol",
        "model_alias": "relay-openai" if candidate == "LiteLLM" else None,
        "configured_upstream_protocol": "OpenAI Chat Completions",
        "required_upstream_protocol": "OpenAI Chat Completions",
        "configured_upstream_url_path": "/v1/chat/completions",
    }


def _run_gateway_probe(root: Path, candidate_name: str, provider_name: str, run_id: str) -> dict[str, Any]:
    candidate = CANDIDATES[candidate_name]
    provider = PROVIDERS[provider_name]
    request = _gateway_request(candidate_name, provider_name)
    metadata = _gateway_metadata(candidate_name, provider_name)
    record: dict[str, Any] = {
        "diagnostic_type": "gateway_probe",
        "run_id": run_id,
        "observed_at": _timestamp(),
        "candidate": candidate_name,
        "provider": provider_name,
        "key_env": provider.key_env,
        "key_present": bool(os.environ.get(provider.key_env)),
        "gateway": metadata,
        "normalized_request": redact_value({key: value for key, value in request.items() if key != "protocol"}),
        "request_shape": {
            "protocol": "Anthropic Messages" if provider_name == "A6api" else "OpenAI Chat Completions",
            "tools": bool(request.get("tools")),
            "tool_choice": request.get("tool_choice") is not None,
            "stream": bool(request.get("stream", False)),
        },
    }
    if not os.environ.get(provider.key_env):
        record.update({"status": "UNAVAILABLE", "failure_class": "AUTH_ERROR"})
        return record
    with tempfile.TemporaryDirectory(prefix=f"batch-b-diagnostic-{candidate_name.lower()}-{provider_name.lower()}-", dir=root / "poc/.runtime") as temp_name:
        temp_root = Path(temp_name)
        network = None
        active = None
        try:
            active = _start_live_backend(root, candidate, provider, run_id, temp_root)
            network = active.network
            try:
                response = active.backend.request(request)
                record.update({
                    "status": "PASS",
                    "response": redact_value(response),
                    "request_id": _request_id(response),
                    "failure_class": None,
                })
            except (BifrostGatewayRequestError, LiteLLMGatewayRequestError) as error:
                body = redact_value(error.body)
                record.update({
                    "status": "FAIL",
                    "provider_http_status": error.status_code,
                    "redacted_provider_error_body": body,
                    "request_id": _request_id(error.body),
                    "failure_class": active.backend.classify_error(error).value,
                    "error_type": type(error).__name__,
                })
            except Exception as error:  # pragma: no cover - live diagnostic boundary
                record.update({
                    "status": "FAIL",
                    "failure_class": "GATEWAY_FAILURE",
                    "error_type": type(error).__name__,
                    "error": redact_string(str(error)),
                })
            record["gateway_container_logs"] = _container_logs(active.backend.container_name)
            record["container_name_recorded"] = True
        except Exception as error:  # pragma: no cover - live diagnostic boundary
            record.update({
                "status": "FAIL",
                "failure_class": "GATEWAY_FAILURE",
                "error_type": type(error).__name__,
                "error": redact_string(str(error)),
            })
        finally:
            if active is not None:
                record["cleanup"] = _stop_live_backend(active)
            elif network:
                subprocess.run(["docker", "network", "rm", network], capture_output=True, text=True, check=False)
    return redact_value(record)


def run(root: Path, run_id: str, *, include_gateways: bool = True) -> dict[str, Any]:
    root = root.resolve()
    evidence_dir = root / "tests/poc/evidence/level2" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    controls = [
        _http_json(
            control="A6api direct OpenAI Chat Completions with T03 tool schema",
            base_url="https://api.a6api.com",
            path="/v1/chat/completions",
            key_env="A6API_KEY",
            auth_header="Authorization",
            model="gpt-5.4-mini",
            payload={
                "model": "gpt-5.4-mini",
                "messages": [{
                    "role": "user",
                    "content": "Call read_fixture exactly once with path input/alpha.txt.",
                }],
                "max_tokens": 256,
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "read_fixture",
                        "description": "Read one fixture file.",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    },
                }],
                "tool_choice": {"type": "function", "function": {"name": "read_fixture"}},
            },
        ),
        _http_json(
            control="A6api direct OpenAI Responses minimum chat",
            base_url="https://api.a6api.com",
            path="/v1/responses",
            key_env="A6API_KEY",
            auth_header="Authorization",
            model="gpt-5.4-mini",
            payload={"model": "gpt-5.4-mini", "input": "Reply with OK.", "max_output_tokens": 16},
        ),
        _http_json(
            control="A6api direct OpenAI Chat Completions",
            base_url="https://api.a6api.com",
            path="/v1/chat/completions",
            key_env="A6API_KEY",
            auth_header="Authorization",
            model="gpt-5.4-mini",
            payload={"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 16},
        ),
        _http_json(
            control="A6api direct OpenAI Responses with T03 tool schema",
            base_url="https://api.a6api.com",
            path="/v1/responses",
            key_env="A6API_KEY",
            auth_header="Authorization",
            model="gpt-5.4-mini",
            payload={
                "model": "gpt-5.4-mini",
                "input": [{
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": "Use the read_fixture tool exactly once with path input/alpha.txt.",
                    }],
                }],
                "max_output_tokens": 256,
                "tools": [{
                    "type": "function",
                    "name": "read_fixture",
                    "description": "Read one fixture file.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                    "strict": False,
                }],
                "tool_choice": {"type": "function", "name": "read_fixture"},
            },
        ),
        _http_json(
            control="A6api direct native Anthropic Messages /messages",
            base_url="https://api.a6api.com",
            path="/messages",
            key_env="A6API_KEY",
            auth_header="x-api-key",
            model="claude-sonnet-4-5",
            payload={"model": "claude-sonnet-4-5", "max_tokens": 256, "messages": [{"role": "user", "content": "Reply with OK."}]},
        ),
        _http_json(
            control="A6api direct native Anthropic Messages /v1/messages",
            base_url="https://api.a6api.com",
            path="/v1/messages",
            key_env="A6API_KEY",
            auth_header="x-api-key",
            model="claude-sonnet-4-5",
            payload={"model": "claude-sonnet-4-5", "max_tokens": 256, "messages": [{"role": "user", "content": "Reply with OK."}]},
        ),
        _http_json(
            control="RelayRouter direct chat-only",
            base_url="https://api.relayrouter.org/v1",
            path="/chat/completions",
            key_env="RELAYROUTER_API_KEY",
            auth_header="Authorization",
            model="stealth/openai/gpt-5.6-sol",
            payload=RELAY_CHAT_REQUEST,
        ),
    ]
    if not include_gateways:
        controls = controls[:2]
    gateways = [
        _run_gateway_probe(root, "Bifrost", "A6api", run_id),
        _run_gateway_probe(root, "LiteLLM", "A6api", run_id),
        _run_gateway_probe(root, "Bifrost", "RelayRouter", run_id),
        _run_gateway_probe(root, "LiteLLM", "RelayRouter", run_id),
    ] if include_gateways else []
    result = {
        "schema_version": "1.0",
        "diagnostic_run_id": run_id,
        "batch_run_id": "batch-b-remediation-20260930T155149Z",
        "observed_at": _timestamp(),
        "scope": "T03 A6api translation diagnosis and RelayRouter chat-only dependency diagnosis" if include_gateways else "A6api direct OpenAI Chat Completions T03 tool-schema control",
        "candidate_source_modified": False,
        "sensitive_values_written": False,
        "direct_controls": controls,
        "gateway_probes": gateways,
        "inventory_evidence": [
            "docs/a6api-models.md",
            "docs/relayrouter-models.md",
            "docs/04-provider-docs.md",
        ],
    }
    (evidence_dir / "targeted-diagnostics.json").write_text(
        json.dumps(redact_value(result), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "phase": "phase_5",
        "diagnostic_run_id": run_id,
        "batch_run_id": "batch-b-remediation-20260930T155149Z",
        "evidence_type": "TARGETED_DIAGNOSTIC_EVIDENCE",
        "evidence_files": ["targeted-diagnostics.json", "manifest.json"],
        "candidate_source_modified": False,
        "sensitive_values_written": False,
        "direct_control_count": len(controls),
        "gateway_probe_count": len(gateways),
        "inventory_evidence": result["inventory_evidence"],
    }
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--direct-only", action="store_true")
    args = parser.parse_args(argv)
    result = run(args.root, args.run_id, include_gateways=not args.direct_only)
    print(json.dumps({"diagnostic_run_id": result["diagnostic_run_id"], "gateway_probe_count": len(result["gateway_probes"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
