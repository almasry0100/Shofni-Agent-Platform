from __future__ import annotations

import json
import sqlite3
import subprocess
import sys


def _run_boundary(tmp_path, scenario: str, expected_exit: int):
    root = tmp_path / scenario
    worker = [sys.executable, "-m", "tests.poc.support.runtime_worker"]
    first = subprocess.run(
        worker + ["first", "--root", str(root), "--scenario", scenario],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    metadata = json.loads((root / "worker-metadata.json").read_text(encoding="utf-8"))
    checkpoint = json.loads(
        (root / "checkpoints" / f"{metadata['checkpoint_id']}.json").read_text(encoding="utf-8")
    )
    pending = json.loads(
        (root / "tasks" / metadata["task_id"] / "state.json").read_text(encoding="utf-8")
    )
    operation_id = next(iter(pending["pending_operations"]))
    ledger_rows_before_restore = 0
    if scenario == "t11-after-append":
        with sqlite3.connect(
            str(root / "tasks" / metadata["task_id"] / "workspace" / "state" / "ledger.sqlite")
        ) as connection:
            ledger_rows_before_restore = connection.execute(
                "SELECT COUNT(*) FROM ledger WHERE operation_id = ?", (operation_id,)
            ).fetchone()[0]
    recovery = subprocess.run(
        worker + ["recover", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    restored = json.loads((root / "worker-result.json").read_text(encoding="utf-8"))
    results = restored["tool_results"]
    result = results[operation_id]
    events = restored["events"]
    action_index = next(
        index for index, event in enumerate(events)
        if event.get("candidate_event_type") == "ActionEvent"
        and event.get("tool_call_id") == result["tool_call_id"]
    )
    observation_index = next(
        index for index, event in enumerate(events)
        if event.get("candidate_event_type") == "ObservationEvent"
        and event.get("tool_call_id") == result["tool_call_id"]
    )
    assert checkpoint["task_id"] == metadata["task_id"]
    assert first.returncode == expected_exit
    assert recovery.returncode == 0
    assert operation_id in pending["pending_operations"]
    assert action_index < observation_index
    assert restored["task_state"]["task_id"] == metadata["task_id"]
    assert restored["task_state"]["workspace_id"] == metadata["workspace_id"]
    assert restored["task_state"]["attempt_id"] != metadata["attempt_id_before"]
    assert restored["candidate_conversation_id"] == metadata["candidate_conversation_id"]
    assert len(results) == 1
    assert result["operation_id"] == operation_id
    assert result["ledger_rows"] == 1
    assert restored["ledger_row_count"] == 1
    return result, ledger_rows_before_restore


def test_t11_crash_before_append_reuses_operation_through_runtime_recovery(tmp_path) -> None:
    result, rows_before = _run_boundary(tmp_path, "t11-before-append", 71)
    assert rows_before == 0
    assert result["ledger_rows"] == 1
    assert result["duplicate_suppressed"] is False


def test_t11_crash_after_append_suppresses_duplicate_through_runtime_recovery(tmp_path) -> None:
    result, rows_before = _run_boundary(tmp_path, "t11-after-append", 73)
    assert rows_before == 1
    assert result["ledger_rows"] == 1
    assert result["duplicate_suppressed"] is True
