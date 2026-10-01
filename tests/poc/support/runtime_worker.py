from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from poc.contracts.checkpoint import Checkpoint
from poc.runtime.openhands_backend import OpenHandsRuntimeBackend
from tests.poc.support.fake_candidate import fake_conversation_factory


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def _first(root: Path, scenario: str) -> None:
    backend = OpenHandsRuntimeBackend(root, conversation_factory=fake_conversation_factory)
    backend.start()
    spec: dict[str, Any] = {
        "provider": "fixture",
        "model": "model-a",
        "prompt": "Use the configured deterministic fixture tool.",
        "fixture_marker": "alpha\n",
        "tool_mode": "read" if scenario == "t10" else "append",
        "ledger_value": {"marker": "alpha"},
    }
    if scenario == "t11-before-append":
        spec["crash_boundary"] = "before_append"
    elif scenario == "t11-after-append":
        spec["crash_boundary"] = "after_append_before_checkpoint"
    state = backend.create_task(spec)
    checkpoint = backend.checkpoint(state.task_id)
    _save(
        root / "worker-metadata.json",
        {
            "task_id": state.task_id,
            "workspace_id": state.workspace_id,
            "attempt_id_before": state.attempt_id,
            "candidate_conversation_id": state.candidate_runtime_ref,
            "checkpoint_id": checkpoint.checkpoint_id,
            "scenario": scenario,
        },
    )
    backend.run(state.task_id)
    backend.stop()


def _recover(root: Path) -> None:
    metadata = _load(root / "worker-metadata.json")
    checkpoint = Checkpoint.from_dict(
        _load(root / "checkpoints" / f"{metadata['checkpoint_id']}.json")
    )
    backend = OpenHandsRuntimeBackend(root, conversation_factory=fake_conversation_factory)
    backend.start()
    state = backend.resume(checkpoint)
    scenario = metadata["scenario"]
    if scenario == "t10":
        backend.switch_model(state.task_id, "model-b")
        backend.send_message(state.task_id, "Resume with the saved tool result.")
        backend.run(state.task_id)
        state = backend.inspect(state.task_id)
    record = backend._load(backend._paths(state.task_id))
    tool_results = record["tool_results"]
    ledger_path = backend._paths(state.task_id).workspace / "state" / "ledger.sqlite"
    row_count = 0
    if scenario != "t10":
        with sqlite3.connect(str(ledger_path)) as connection:
            row_count = connection.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    _save(
        root / "worker-result.json",
        {
            "task_state": state.to_dict(),
            "candidate_conversation_id": record["conversation_id"],
            "events": record["events"],
            "tool_results": tool_results,
            "final_result": record["final_result"],
            "ledger_row_count": row_count,
        },
    )
    backend.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("first", "recover"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scenario", choices=("t10", "t11-before-append", "t11-after-append"))
    args = parser.parse_args()
    if args.stage == "first":
        if args.scenario is None:
            parser.error("first stage requires --scenario")
        _first(args.root, args.scenario)
    else:
        _recover(args.root)


if __name__ == "__main__":
    main()
