"""Bounded live controls used by the Resolution run."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_value
from poc.runners.level2_phase5 import _stop_live_backend
from poc.runners.phase11_composition import _route_probe
from poc.runners.phase14_d_f2_t03 import _start_gateway


MODEL = "gpt-5.4-mini"
PROMPT = "Use the Read tool exactly once to read input/alpha.txt. Return the exact file content."


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize(value: Any, root: Path) -> Any:
    value = redact_value(value)
    if isinstance(value, str):
        for private in (root.resolve(), root.parent.resolve(), Path.home().resolve()):
            value = re.sub(re.escape(str(private)), "<LOCAL_PATH>", value, flags=re.IGNORECASE)
        return value
    if isinstance(value, dict):
        return {key: _sanitize(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, root) for item in value]
    return value


def _write(path: Path, value: Any, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sanitize(value, root), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _event_summary(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    malformed = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(value, dict):
            malformed += 1
            continue
        event: dict[str, Any] = {"type": value.get("type")}
        if isinstance(value.get("subtype"), str):
            event["subtype"] = value["subtype"]
        if isinstance(value.get("session_id"), str):
            event["session_id"] = value["session_id"]
        message = value.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                blocks = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    item = {"type": block.get("type")}
                    for key in ("id", "name", "tool_use_id"):
                        if isinstance(block.get(key), str):
                            item[key] = block[key]
                    if isinstance(block.get("input"), dict):
                        item["input_keys"] = sorted(block["input"].keys())
                    blocks.append(item)
                event["content"] = blocks
        result = value.get("result")
        if isinstance(result, str):
            event["result_present"] = bool(result.strip())
        events.append(event)
    tool_uses = [block for event in events for block in event.get("content", []) if block.get("type") == "tool_use"]
    tool_results = [block for event in events for block in event.get("content", []) if block.get("type") == "tool_result"]
    return {
        "event_count": len(events),
        "event_types": [event.get("type") for event in events],
        "events": events,
        "malformed_lines": malformed,
        "tool_use_count": len(tool_uses),
        "tool_result_count": len(tool_results),
        "tool_uses": tool_uses,
        "tool_results": tool_results,
        "result_event_present": any(event.get("result_present") for event in events),
    }


def _run_claude(workspace: Path, base_url: str, model: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    env = os.environ.copy()
    for name in ("A6API_KEY", "RELAYROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env.pop(name, None)
    env.update(
        {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_API_KEY": "resolution-client",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CI": "1",
        }
    )
    command = [
        "claude.cmd",
        "--bare",
        "--safe-mode",
        "-p",
        PROMPT,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--tools",
        "Read",
        "--allowed-tools",
        "Read",
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
    ]
    result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=240)
    return result, _event_summary(result.stdout or "")


def run_actual_claude_t03(root: Path, run_id: str, evidence_root: Path, repetitions: int = 3) -> dict[str, Any]:
    if repetitions != 3:
        raise ValueError("Resolution T03 requires exactly three fixed repetitions")
    evidence_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for candidate in ("Bifrost", "LiteLLM"):
        for repetition in range(1, repetitions + 1):
            attempt_id = f"{run_id}-{candidate.lower()}-t03-rep-{repetition}"
            candidate_root = evidence_root / candidate.lower() / f"rep-{repetition}"
            workspace = candidate_root / "workspace"
            workspace.joinpath("input").mkdir(parents=True, exist_ok=True)
            workspace.joinpath("input/alpha.txt").write_text("alpha fixture input\n", encoding="utf-8")
            record: dict[str, Any] = {
                "schema_version": "1.0",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "phase": "R2",
                "test_id": "T03",
                "repetition": repetition,
                "candidate": candidate,
                "candidate_reached": False,
                "candidate_route_probe_reached": False,
                "candidate_request_observed": False,
                "provider_reached": False,
                "provider_request_observed": False,
                "client_reached": True,
                "client": "Claude Code",
                "client_version": "2.1.278",
                "provider": "A6api",
                "model_id": MODEL,
                "configured_provider_route": "https://api.a6api.com/v1/responses",
                "configured_retry_count": 0,
                "started_at_utc": _stamp(),
                "status": "FAIL",
                "classification": "SETUP_FAILURE",
            }
            active = None
            temp_root: Path | None = None
            try:
                with tempfile.TemporaryDirectory(prefix=f"resolution-r2-{candidate.lower()}-{repetition}-", dir=root / "poc/.runtime") as temp_name:
                    temp_root = Path(temp_name)
                    active, inbound_model = _start_gateway(root, candidate, attempt_id, temp_root)
                    prefix = "/anthropic" if candidate == "Bifrost" else ""
                    base_url = active.backend.base_url + prefix
                    route_probe = _route_probe(active.backend.list_models(), (inbound_model,))
                    record.update({
                        "candidate_route_probe_reached": True,
                        "gateway_identity": {"host_route": base_url, "inbound_model": inbound_model, "network": active.network, "container": active.backend.container_name},
                        "route_probe": route_probe,
                    })
                    if route_probe.get("status") != "PASS":
                        record["classification"] = "SETUP_FAILURE"
                    else:
                        result, summary = _run_claude(workspace, base_url, inbound_model)
                        record.update({
                            "client_process_exit_code": result.returncode,
                            "client_process_started": True,
                            "client_output": summary,
                            "candidate_reached": summary["event_count"] > 0,
                            "candidate_request_observed": summary["event_count"] > 0,
                            "tool_execution_count": summary["tool_result_count"],
                            "gateway_http_statuses": "NOT_EXPOSED_BY_CLIENT_ADAPTER",
                            "upstream_observability": {"configured_route": "https://api.a6api.com/v1/responses", "observed_provider_request": False, "source": "gateway_logs_not_instrumented"},
                        })
                        valid_client_flow = result.returncode == 0 and summary["tool_use_count"] == 1 and summary["tool_result_count"] == 1 and summary["result_event_present"] and record["upstream_observability"]["observed_provider_request"]
                        if valid_client_flow:
                            record["status"] = "PASS" if summary["event_count"] > 0 else "FAIL"
                            record["classification"] = "PASS" if summary["event_count"] > 0 else "EVIDENCE_OBSERVABILITY_FAILURE"
                        else:
                            record["classification"] = "CLIENT_FAILURE" if result.returncode != 0 else (
                                "EVIDENCE_OBSERVABILITY_FAILURE"
                                if not record["upstream_observability"]["observed_provider_request"]
                                else "PROTOCOL_TRANSLATION_FAILURE"
                            )
                        record["provider_reached"] = record["upstream_observability"]["observed_provider_request"]
                        record["provider_request_observed"] = record["provider_reached"]
                        record["candidate_attribution"] = (
                            "CANDIDATE_REACHED_RESULT"
                            if record["candidate_reached"]
                            else "UNATTRIBUTED_CLIENT_FAILURE"
                        )
                        record["attribution_classification"] = (
                            "EVIDENCE_OBSERVABILITY_FAILURE"
                            if not record["candidate_reached"] or not record["provider_reached"]
                            else record["classification"]
                        )
            except subprocess.TimeoutExpired:
                record.update({"classification": "CLIENT_FAILURE", "timeout": True})
            except Exception as error:
                record.update({"classification": "SETUP_FAILURE", "error_type": type(error).__name__})
            finally:
                if active is not None:
                    cleanup = _stop_live_backend(active)
                else:
                    cleanup = {}
                cleanup["temporary_config_removed"] = temp_root is not None and not temp_root.exists()
                record["cleanup"] = cleanup
            record["finished_at_utc"] = _stamp()
            evidence_run_id = run_id.removeprefix("resolution-")
            record["evidence_path"] = f"tests/poc/evidence/resolution/{evidence_run_id}/r2/{candidate.lower()}/rep-{repetition}.json"
            _write(evidence_root / candidate.lower() / f"rep-{repetition}.json", record, root)
            records.append(record)
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R2",
        "test_id": "T03",
        "required_repetitions_per_candidate": repetitions,
        "records": records,
        "status": "PASS" if all(record["status"] == "PASS" for record in records) else "PARTIAL",
        "candidate_reached": any(record["candidate_reached"] for record in records),
        "provider_reached": any(record["provider_reached"] for record in records),
        "client_reached": any(record["client_reached"] for record in records),
        "candidate_request_observed": any(record["candidate_request_observed"] for record in records),
        "upstream_observability": "NOT_OBSERVED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    result = run_actual_claude_t03(args.root.resolve(), args.run_id, args.evidence_root.resolve())
    _write(args.evidence_root / "summary.json", result, args.root.resolve())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
