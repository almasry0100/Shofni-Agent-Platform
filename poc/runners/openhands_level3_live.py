"""Opt-in live Level 3 controls for the permanent OpenHands adapter."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from poc.contracts.checkpoint import Checkpoint
from poc.runtime.openhands_backend import OpenHandsRuntimeBackend


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object in {path.name}")
    return value


def _run_model_a(runtime_root: Path, evidence_root: Path, model_a: str) -> None:
    backend = OpenHandsRuntimeBackend(runtime_root)
    backend.start()
    state = backend.create_task(
        {
            "provider": "A6api",
            "model": model_a,
            "prompt": (
                "Use the read_fixture tool exactly once to read input/alpha.txt. "
                "Do not narrate the read; emit the tool action and wait for its result."
            ),
            "fixture_marker": "alpha\n",
            "tool_mode": "read",
        }
    )
    backend.run(state.task_id)
    state_after_a = backend.inspect(state.task_id)
    checkpoint = backend.checkpoint(state.task_id)
    record = backend._load(backend._paths(state.task_id))
    _write_json(evidence_root / "model-a-state.json", {
        "task_id": state.task_id,
        "workspace_id": state.workspace_id,
        "attempt_id": state_after_a.attempt_id,
        "session_id": state.session_id,
        "candidate_conversation_id": state.candidate_runtime_ref,
        "checkpoint_id": checkpoint.checkpoint_id,
        "candidate_events": record["events"],
        "tool_results": record["tool_results"],
        "provider": state.selected_provider,
        "model": model_a,
    })
    backend.stop()


def _run_restore(runtime_root: Path, evidence_root: Path, model_b: str) -> None:
    before = _load_json(evidence_root / "model-a-state.json")
    checkpoint = Checkpoint.from_dict(
        _load_json(runtime_root / "checkpoints" / f"{before['checkpoint_id']}.json")
    )
    backend = OpenHandsRuntimeBackend(runtime_root)
    backend.start()
    restored = backend.resume(checkpoint)
    backend.switch_model(restored.task_id, model_b)
    backend.send_message(
        restored.task_id,
        "Resume with the saved tool result and answer with its exact content.",
    )
    backend.run(restored.task_id)
    final = backend.inspect(restored.task_id)
    record = backend._load(backend._paths(restored.task_id))
    _write_json(evidence_root / "restored-state.json", {
        "task_state": final.to_dict(),
        "candidate_events": record["events"],
        "tool_results": record["tool_results"],
        "final_result": record["final_result"],
        "candidate_conversation_id": record["conversation_id"],
        "provider": record["provider"],
        "model": record["model"],
    })
    backend.stop()


def run_t10(
    runtime_root: Path,
    evidence_root: Path,
    model_a: str,
    model_b: str,
    attempt_id: str,
) -> dict[str, Any]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    command_prefix = [sys.executable, "-m", "poc.runners.openhands_level3_live"]
    first = subprocess.run(
        command_prefix + [
            "--stage", "model-a", "--runtime-root", str(runtime_root),
            "--evidence-root", str(evidence_root), "--model-a", model_a,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        env=os.environ.copy(),
    )
    if not (evidence_root / "model-a-state.json").is_file():
        raise RuntimeError("model A process did not persist its checkpoint evidence")
    second = subprocess.run(
        command_prefix + [
            "--stage", "restore", "--runtime-root", str(runtime_root),
            "--evidence-root", str(evidence_root), "--model-b", model_b,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        env=os.environ.copy(),
    )
    before = _load_json(evidence_root / "model-a-state.json")
    after = _load_json(evidence_root / "restored-state.json")
    final_state = after["task_state"]
    actions = [
        {
            "candidate_event_id": event.get("candidate_event_id"),
            "tool_name": event.get("tool_name"),
            "tool_call_id": event.get("tool_call_id"),
            "action": event.get("action"),
        }
        for event in after["candidate_events"]
        if event.get("candidate_event_type") == "ActionEvent"
    ]
    gates = {
        "model_a_process_exited_cleanly": first.returncode == 0,
        "model_a_runtime_terminated_before_restore": first.returncode is not None,
        "fresh_restore_process_succeeded": second.returncode == 0,
        "same_task_id": final_state["task_id"] == before["task_id"],
        "same_workspace_id": final_state["workspace_id"] == before["workspace_id"],
        "new_attempt_id_explicit": final_state["attempt_id"] != before["attempt_id"],
        "model_b_selected": final_state["selected_model"] == model_b,
        "read_fixture_action_observed": any(event.get("tool_name") == "read_fixture" for event in actions),
        "prior_tool_result_preserved": bool(after["tool_results"]),
        "successful_final_result": isinstance(after["final_result"], str) and bool(after["final_result"]),
    }
    result = {
        "attempt_id": attempt_id,
        "schema_version": "1.0",
        "status": "PASS" if all(gates.values()) else "INCOMPLETE",
        "provider": "A6api",
        "model_a": model_a,
        "model_b": model_b,
        "key_presence": "PRESENT" if os.environ.get("A6API_KEY") else "MISSING",
        "task_id": before["task_id"],
        "workspace_id": before["workspace_id"],
        "session_id": before["session_id"],
        "attempt_id_before_restart": before["attempt_id"],
        "attempt_id_after_restart": final_state["attempt_id"],
        "same_task_id": gates["same_task_id"],
        "same_workspace_id": gates["same_workspace_id"],
        "new_attempt_id_explicit": gates["new_attempt_id_explicit"],
        "gates": gates,
        "model_a_process_exit_code": first.returncode,
        "restore_process_exit_code": second.returncode,
        "checkpoint_id": before["checkpoint_id"],
        "candidate_conversation_id": before["candidate_conversation_id"],
        "candidate_action_events": actions,
        "tool_result": after["tool_results"],
        "final_selected_model": final_state["selected_model"],
        "final_result": after["final_result"],
        "process_boundary": "model A and restore ran in separate child processes; model A exited before restore started",
    }
    _write_json(evidence_root / "t10-live.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("orchestrate", "model-a", "restore"), default="orchestrate")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--model-a", default="gpt-5.4-mini")
    parser.add_argument("--model-b", default="gpt-5.5")
    parser.add_argument("--attempt-id", default=os.environ.get("SHOFNI_ATTEMPT_ID", "level3-corrective-live"))
    args = parser.parse_args()
    if args.stage == "model-a":
        _run_model_a(args.runtime_root, args.evidence_root, args.model_a)
        return
    if args.stage == "restore":
        _run_restore(args.runtime_root, args.evidence_root, args.model_b)
        return
    print(json.dumps(
        run_t10(args.runtime_root, args.evidence_root, args.model_a, args.model_b, args.attempt_id),
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
