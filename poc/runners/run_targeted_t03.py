"""Run only the targeted Anthropic Messages to A6api OpenAI-route T03 path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_value
from poc.runners.level2_phase5 import (
    CANDIDATES,
    PROVIDERS,
    _json,
    _model_ids,
    _run_live_test,
    _start_live_backend,
    _stop_live_backend,
)


BASE_RUN_ID = "level2-remediation-20260930T194948Z"
DIAGNOSTIC_RUN_ID = "targeted-b-20260930T225000Z"
PREVIOUS_DIAGNOSTIC_RUN_ID = "targeted-b-20260930T213000Z"
INCONCLUSIVE_DIAGNOSTIC_RUN_ID = "targeted-b-20260930T224500Z"
ROUTE_MODEL = "gpt-5.4-mini"
LITELLM_MESSAGES_ALIAS = "a6api-anthropic"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _bifrost_translated_messages_config(provider: Any) -> dict[str, Any]:
    secret = os.environ[provider.key_env]
    openai_provider = {
        "keys": [{
            "name": "shofni-a6api-openai-compatible",
            "value": secret,
            "weight": 1.0,
            "models": [ROUTE_MODEL],
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
        "providers": {"openai": openai_provider},
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


def _litellm_translated_messages_config(provider: Any) -> str:
    return "\n".join([
        "model_list:",
        f"  - model_name: {LITELLM_MESSAGES_ALIAS}",
        "    litellm_params:",
        f"      model: openai/{ROUTE_MODEL}",
        f"      api_base: {provider.base_url}",
        "      api_key: os.environ/SHOFNI_PROVIDER_KEY",
        "general_settings:",
        "  disable_spend_logs: true",
        "litellm_settings:",
        "  num_retries: 0",
        "  request_timeout: 90",
        "",
    ])


def _translated_wire_contract(candidate: str) -> dict[str, Any]:
    if candidate == "Bifrost":
        return {
            "inbound_protocol": "Anthropic Messages",
            "gateway_endpoint": "/anthropic/v1/messages",
            "inbound_model_id": ROUTE_MODEL,
            "provider_selected": "openai",
            "a6api_model_route_id": ROUTE_MODEL,
            "upstream_url_base": "https://api.a6api.com",
            "upstream_protocol": "OpenAI Responses",
            "upstream_url_path": "/v1/responses",
            "system_role_mapping": "Anthropic top-level system/messages -> Responses input items",
            "max_tokens_mapping": "max_tokens -> max_output_tokens",
            "tool_schema_mapping": "Anthropic input_schema -> Responses function parameters",
            "tool_choice_mapping": "Anthropic type=tool/name -> Responses type=function/name",
            "unsupported_anthropic_only_fields": [],
        }
    return {
        "inbound_protocol": "Anthropic Messages",
        "gateway_endpoint": "/v1/messages",
        "inbound_model_id": LITELLM_MESSAGES_ALIAS,
        "provider_selected": "openai",
        "a6api_model_route_id": ROUTE_MODEL,
        "upstream_url_base": "https://api.a6api.com",
        "upstream_protocol": "OpenAI Responses",
        "upstream_url_path": "/v1/responses",
        "system_role_mapping": "Anthropic system/messages -> Responses instructions/input message items",
        "max_tokens_mapping": "max_tokens -> max_output_tokens",
        "tool_schema_mapping": "Anthropic input_schema -> Responses function parameters with strict=false",
        "tool_choice_mapping": "Anthropic type=tool/name -> Responses type=function/name",
        "unsupported_anthropic_only_fields": [],
    }


def _normalized_t03_request(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 256,
        "messages": [{
            "role": "user",
            "content": "Use the read_fixture tool exactly once with path input/alpha.txt.",
        }],
        "tools": [{
            "name": "read_fixture",
            "description": "Read one fixture file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }],
        "tool_choice": {"type": "tool", "name": "read_fixture"},
    }


def _translated_t03_request() -> dict[str, Any]:
    return {
        "model": ROUTE_MODEL,
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
    }


def _candidate_cleanup(root: Path, candidate_name: str, run_id: str, temp_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    provider = PROVIDERS["A6api"]
    candidate = CANDIDATES[candidate_name]
    cleanup: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    route = _translated_wire_contract(candidate_name)
    if not os.environ.get(provider.key_env):
        raise RuntimeError("A6API_KEY is unavailable")
    override = (
        {"provider_config_override": _bifrost_translated_messages_config(provider)}
        if candidate_name == "Bifrost"
        else {"litellm_config_override": _litellm_translated_messages_config(provider)}
    )
    with tempfile.TemporaryDirectory(prefix=f"batch-b-t03-{candidate_name.lower()}-", dir=root / "poc/.runtime") as temp_name:
        runtime_root = Path(temp_name)
        active = _start_live_backend(root, candidate, provider, run_id, runtime_root, **override)
        try:
            inbound_model = ROUTE_MODEL if candidate_name == "Bifrost" else LITELLM_MESSAGES_ALIAS
            for repetition in range(1, 4):
                result = _run_live_test(
                    active.backend,
                    "Claude Code",
                    provider,
                    "T03",
                    repetition,
                    model_id=ROUTE_MODEL,
                    anthropic_model_id=inbound_model,
                )
                result.update({
                    "candidate": candidate_name,
                    "client_version": "2.1.278",
                    "provider": "A6api",
                    "model_id": ROUTE_MODEL,
                    "inbound_model_id": inbound_model,
                    "protocol": "Anthropic Messages",
                    "candidate_execution": True,
                    "evidence_type": "LIVE_PROVIDER_EVIDENCE",
                    "run_id": run_id,
                    "upstream_wire_contract": route,
                    "wire_evidence": {
                        "inbound_client_protocol": "Anthropic Messages",
                        "gateway_endpoint": route["gateway_endpoint"],
                        "normalized_request": _normalized_t03_request(inbound_model),
                        "provider_selected": route["provider_selected"],
                        "a6api_model_route_id": ROUTE_MODEL,
                        "upstream_protocol": route["upstream_protocol"],
                        "upstream_url_path": route["upstream_url_path"],
                        "upstream_request": _translated_t03_request(),
                        "provider_http_status": (
                            200
                            if result.get("status") == "PASS" or result.get("observations", {}).get("response_id")
                            else result.get("provider_http_status")
                        ),
                        "redacted_provider_error_body": result.get("redacted_provider_error_body"),
                        "failure_class": result.get("failure_class"),
                    },
                    "root_cause_correction": "Route Anthropic Messages ingress to A6api's inventory-listed OpenAI-compatible gpt-5.4-mini model instead of native Anthropic passthrough.",
                    "evidence_refs": [],
                })
                records.append(redact_value(result))
        finally:
            cleanup_result = _stop_live_backend(active)
    cleanup_result["temporary_config_removed"] = not runtime_root.exists()
    cleanup.append(cleanup_result)
    return records, cleanup, route


def run(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    evidence_dir = root / "tests/poc/evidence/level2" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    base_path = root / "tests/poc/evidence/level2" / BASE_RUN_ID / "matrix.json"
    base_matrix = json.loads(base_path.read_text(encoding="utf-8"))
    if base_matrix.get("run_id") != BASE_RUN_ID:
        raise ValueError("validated Phase 5 base matrix identity does not match")

    diagnostic_ref = f"tests/poc/evidence/level2/{DIAGNOSTIC_RUN_ID}/targeted-diagnostics.json"
    previous_diagnostic_ref = f"tests/poc/evidence/level2/{PREVIOUS_DIAGNOSTIC_RUN_ID}/targeted-diagnostics.json"
    inconclusive_diagnostic_ref = f"tests/poc/evidence/level2/{INCONCLUSIVE_DIAGNOSTIC_RUN_ID}/targeted-diagnostics.json"
    if not (root / diagnostic_ref).is_file():
        raise FileNotFoundError(diagnostic_ref)

    records: list[dict[str, Any]] = []
    cleanup: list[dict[str, Any]] = []
    wire_contracts: dict[str, dict[str, Any]] = {}
    for candidate_name in ("Bifrost", "LiteLLM"):
        candidate_records, candidate_cleanup, route = _candidate_cleanup(root, candidate_name, run_id, root / "poc/.runtime")
        wire_contracts[candidate_name] = route
        cleanup.extend(candidate_cleanup)
        for record in candidate_records:
            repetition = record["repetition"]
            target = evidence_dir / "runs" / candidate_name.lower() / "a6api" / "claude-code" / f"{repetition}-T03.json"
            relative = target.relative_to(root).as_posix()
            record["evidence_refs"] = [relative, diagnostic_ref]
            _json(target, record)
            records.append(record)

    timestamp = _timestamp()
    carried_forward_live_provider_requests = int(base_matrix.get("live_provider_requests", 0))
    total_live_provider_requests = carried_forward_live_provider_requests + len(records)
    rows = [*base_matrix["rows"], *records]
    for row in rows:
        if row.get("run_id") == BASE_RUN_ID and row.get("test_id") == "T03":
            row["historical_attempt"] = True
    base_matrix.update({
        "run_id": run_id,
        "observed_at": timestamp,
        "status": "PARTIAL",
        "candidate_executions": True,
        "execution_mode": "Targeted T03 reruns only; prior Phase 5 rows carried forward with their original run IDs.",
        "repetitions_requested": 3,
        "live_provider_requests": total_live_provider_requests,
        "current_run_live_provider_requests": len(records),
        "targeted_t03_run_id": run_id,
        "targeted_diagnostic_run_id": DIAGNOSTIC_RUN_ID,
        "targeted_diagnostic_refs": {
            "A6api": diagnostic_ref,
            "RelayRouter": diagnostic_ref,
        },
        "targeted_diagnostic_history_refs": [previous_diagnostic_ref, inconclusive_diagnostic_ref, diagnostic_ref],
        "targeted_t03_wire_contracts": wire_contracts,
        "rows": rows,
        "cleanup": cleanup,
        "carried_forward_from_run_id": BASE_RUN_ID,
        "candidate_source_modified": False,
    })
    matrix_path = evidence_dir / "matrix.json"
    _json(matrix_path, base_matrix)
    (evidence_dir / "matrix.sha256").write_text(_sha256(matrix_path) + "\n", encoding="utf-8")

    target_status = "PASS" if len(records) == 6 and all(row["status"] == "PASS" for row in records) else "FAIL"
    manifest = {
        "phase": "phase_5",
        "run_id": run_id,
        "batch_run_id": "batch-b-remediation-20260930T155149Z",
        "created_at_utc": timestamp,
        "result_status": "PARTIAL",
        "targeted_t03_status": target_status,
        "targeted_t03_repetitions": {name: 3 for name in ("Bifrost", "LiteLLM")},
        "candidate_source_modified": False,
        "candidate_processes_started": 2,
        "live_provider_requests": total_live_provider_requests,
        "current_run_live_provider_requests": len(records),
        "provider_key_presence": {"A6api": bool(os.environ.get("A6API_KEY"))},
        "raw_evidence_created": False,
        "candidate_tree_hashes_referenced": {name: "docs/poc/candidate-lock.json" for name in CANDIDATES},
        "cleanup": cleanup,
        "carried_forward_from_run_id": BASE_RUN_ID,
        "targeted_diagnostic_ref": diagnostic_ref,
        "evidence_files": ["matrix.json", "matrix.sha256", "manifest.json"],
    }
    (evidence_dir / "manifest.json").write_text(
        json.dumps(redact_value(manifest), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "run_id": run_id,
        "targeted_t03_status": target_status,
        "records": records,
        "cleanup": cleanup,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    result = run(args.root, args.run_id)
    print(json.dumps({"run_id": result["run_id"], "targeted_t03_status": result["targeted_t03_status"]}, sort_keys=True))
    return 0 if result["targeted_t03_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
