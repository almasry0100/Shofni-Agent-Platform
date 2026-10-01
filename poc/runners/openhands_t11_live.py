"""Run T11 crash-boundary controls through the permanent OpenHands adapter."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from poc.contracts.checkpoint import Checkpoint
from poc.runtime.openhands_backend import OpenHandsRuntimeBackend


EXPECTED_EXIT_CODES = {
    "before_append": 71,
    "after_append_before_checkpoint": 73,
}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object in {path.name}")
    return value


def _last_json_line(output: str) -> dict[str, Any]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            value = json.loads(line)
            if isinstance(value, dict):
                return value
    raise RuntimeError("child process did not emit a JSON result")


def _stage_first(runtime_root: Path, model: str, boundary: str) -> None:
    backend = OpenHandsRuntimeBackend(runtime_root)
    backend.start()
    state = backend.create_task(
        {
            "provider": "A6api",
            "model": model,
            "prompt": (
                "Use append_ledger exactly once with the JSON value "
                '{"marker":"alpha"}. Emit the append_ledger action now and do not narrate.'
            ),
            "tool_mode": "append",
            "crash_boundary": boundary,
            "ledger_value": {"marker": "alpha"},
        }
    )
    checkpoint = backend.checkpoint(state.task_id)
    _write_json(
        runtime_root / "orchestration.json",
        {
            "task_id": state.task_id,
            "workspace_id": state.workspace_id,
            "attempt_id_before": state.attempt_id,
            "candidate_conversation_id": state.candidate_runtime_ref,
            "checkpoint_id": checkpoint.checkpoint_id,
            "model": model,
            "boundary": boundary,
        },
    )
    # The configured boundary exits this child after the candidate action reaches the adapter.
    backend.run(state.task_id)
    backend.stop()


def _stage_recover(runtime_root: Path) -> dict[str, Any]:
    metadata = _load_json(runtime_root / "orchestration.json")
    checkpoint = Checkpoint.from_dict(
        _load_json(runtime_root / "checkpoints" / f"{metadata['checkpoint_id']}.json")
    )
    backend = OpenHandsRuntimeBackend(runtime_root)
    backend.start()
    restored = backend.resume(checkpoint)
    record = backend._load(backend._paths(restored.task_id))
    ledger_path = backend._paths(restored.task_id).workspace / "state" / "ledger.sqlite"
    with sqlite3.connect(str(ledger_path)) as connection:
        operation_id = next(iter(record["tool_results"]), None)
        row_count = (
            connection.execute(
                "SELECT COUNT(*) FROM ledger WHERE operation_id = ?", (operation_id,)
            ).fetchone()[0]
            if operation_id
            else 0
        )
    tool_result = record["tool_results"].get(operation_id) if operation_id else None
    result = {
        "task_id": restored.task_id,
        "workspace_id": restored.workspace_id,
        "attempt_id_after": restored.attempt_id,
        "candidate_conversation_id": restored.candidate_runtime_ref,
        "operation_id_after": operation_id,
        "tool_result": tool_result,
        "ledger_row_count": int(row_count),
        "lifecycle_status": restored.lifecycle_status.value,
        "events": [
            {
                "candidate_event_type": event.get("candidate_event_type"),
                "tool_name": event.get("tool_name"),
                "tool_call_id": event.get("tool_call_id"),
            }
            for event in record["events"]
        ],
    }
    _write_json(runtime_root / "recovery-result.json", result)
    backend.stop()
    return result


def _summarize_recovered(runtime_root: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    task_id = str(metadata["task_id"])
    task_root = runtime_root / "tasks" / task_id
    record = _load_json(task_root / "state.json")
    tool_results = record.get("tool_results", {})
    operation_id = next(iter(tool_results), None)
    ledger_path = task_root / "workspace" / "state" / "ledger.sqlite"
    with sqlite3.connect(str(ledger_path)) as connection:
        row_count = (
            connection.execute(
                "SELECT COUNT(*) FROM ledger WHERE operation_id = ?", (operation_id,)
            ).fetchone()[0]
            if operation_id
            else 0
        )
    task_state = record["task_state"]
    return {
        "task_id": task_state["task_id"],
        "workspace_id": task_state["workspace_id"],
        "attempt_id_after": task_state["attempt_id"],
        "candidate_conversation_id": record["conversation_id"],
        "operation_id_after": operation_id,
        "tool_result": tool_results.get(operation_id) if operation_id else None,
        "ledger_row_count": int(row_count),
        "lifecycle_status": task_state["lifecycle_status"],
        "events": [
            {
                "candidate_event_type": event.get("candidate_event_type"),
                "tool_name": event.get("tool_name"),
                "tool_call_id": event.get("tool_call_id"),
            }
            for event in record.get("events", [])
        ],
    }


def _run_boundary(runtime_root: Path, evidence_root: Path, model: str, boundary: str, attempt_id: str) -> dict[str, Any]:
    boundary_root = runtime_root / boundary
    boundary_evidence = evidence_root / boundary
    boundary_root.mkdir(parents=True, exist_ok=True)
    first = subprocess.run(
        [
            sys.executable,
            "-m",
            "poc.runners.openhands_t11_live",
            "--stage",
            "first",
            "--runtime-root",
            str(boundary_root),
            "--model",
            model,
            "--boundary",
            boundary,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
        env=os.environ.copy(),
    )
    metadata = _load_json(boundary_root / "orchestration.json")
    pending_state = _load_json(
        boundary_root / "tasks" / str(metadata["task_id"]) / "state.json"
    )
    pending_operations = pending_state.get("pending_operations", {})
    operation_id_before = next(iter(pending_operations), None)
    action_observed = any(
        event.get("candidate_event_type") == "ActionEvent"
        and event.get("tool_name") == "append_ledger"
        for event in pending_state.get("events", [])
    )
    expected_exit = EXPECTED_EXIT_CODES[boundary]
    recovery = subprocess.run(
        [
            sys.executable,
            "-m",
            "poc.runners.openhands_t11_live",
            "--stage",
            "recover",
            "--runtime-root",
            str(boundary_root),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
        env=os.environ.copy(),
    )
    recovered = _summarize_recovered(boundary_root, metadata)
    tool_result = recovered.get("tool_result") or {}
    duplicate_expected = boundary == "after_append_before_checkpoint"
    gates = {
        "first_process_exited_at_boundary": first.returncode == expected_exit,
        "first_process_gone_before_recovery": first.returncode is not None,
        "recovery_process_succeeded": recovery.returncode == 0,
        "candidate_append_action_observed": action_observed,
        "same_task_id": recovered.get("task_id") == metadata["task_id"],
        "same_workspace_id": recovered.get("workspace_id") == metadata["workspace_id"],
        "new_attempt_id_explicit": recovered.get("attempt_id_after") != metadata["attempt_id_before"],
        "same_operation_id": recovered.get("operation_id_after") == operation_id_before,
        "one_durable_ledger_row": recovered.get("ledger_row_count") == 1,
        "one_logical_result": tool_result.get("result") == {"marker": "alpha"},
        "expected_duplicate_behavior": tool_result.get("duplicate_suppressed") is duplicate_expected,
        "final_completion": recovered.get("lifecycle_status") == "COMPLETED",
    }
    result = {
        "attempt_id": attempt_id,
        "boundary": boundary,
        "status": "PASS" if all(gates.values()) else "INCOMPLETE",
        "provider": "A6api",
        "model": model,
        "expected_crash_exit_code": expected_exit,
        "first_process_exit_code": first.returncode,
        "recovery_process_exit_code": recovery.returncode,
        "task_id": metadata["task_id"],
        "workspace_id": metadata["workspace_id"],
        "attempt_id_before": metadata["attempt_id_before"],
        "attempt_id_after": recovered.get("attempt_id_after"),
        "candidate_conversation_id": metadata["candidate_conversation_id"],
        "checkpoint_id": metadata["checkpoint_id"],
        "operation_id_before": operation_id_before,
        "operation_id_after": recovered.get("operation_id_after"),
        "ledger_row_count": recovered.get("ledger_row_count"),
        "duplicate_suppressed": tool_result.get("duplicate_suppressed"),
        "logical_result": tool_result.get("result"),
        "process_boundary": "first child terminated before recovery child started",
        "gates": gates,
    }
    _write_json(boundary_evidence / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("first", "recover", "orchestrate"), default="orchestrate")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--boundary", choices=tuple(EXPECTED_EXIT_CODES))
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--attempt-id", default=os.environ.get("SHOFNI_ATTEMPT_ID", "level3-t11-live"))
    args = parser.parse_args()

    if args.stage == "first":
        if args.boundary is None:
            raise SystemExit("--boundary is required for first stage")
        _stage_first(args.runtime_root, args.model, args.boundary)
        return
    if args.stage == "recover":
        result = _stage_recover(args.runtime_root)
        if args.result_path is not None:
            _write_json(args.result_path, result)
        print(json.dumps(result, sort_keys=True))
        return
    if args.evidence_root is None:
        raise SystemExit("--evidence-root is required for orchestrate stage")
    results = [
        _run_boundary(args.runtime_root, args.evidence_root, args.model, boundary, args.attempt_id)
        for boundary in EXPECTED_EXIT_CODES
    ]
    print(json.dumps({"attempt_id": args.attempt_id, "status": "PASS" if all(item["status"] == "PASS" for item in results) else "INCOMPLETE", "boundaries": results}, sort_keys=True))


if __name__ == "__main__":
    main()
