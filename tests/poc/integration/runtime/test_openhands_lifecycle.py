from __future__ import annotations

import json
import subprocess
import sys

from poc.runtime.openhands_backend import OpenHandsRuntimeBackend
from tests.poc.support.fake_candidate import fake_conversation_factory


def test_permanent_openhands_adapter_restores_identity_and_tool_result(tmp_path) -> None:
    root = tmp_path / "runtime"
    first = OpenHandsRuntimeBackend(root, conversation_factory=fake_conversation_factory)
    first.start()
    created = first.create_task(
        {
            "provider": "fixture",
            "model": "fixture-model-a",
            "prompt": "Read input/alpha.txt using read_fixture.",
            "fixture_marker": "alpha\n",
            "tool_mode": "read",
        }
    )
    first.run(created.task_id)
    checkpoint = first.checkpoint(created.task_id)
    before = first.inspect(created.task_id)
    first.stop()

    second = OpenHandsRuntimeBackend(root, conversation_factory=fake_conversation_factory)
    second.start()
    restored = second.resume(checkpoint)
    after = second.inspect(created.task_id)

    assert after.task_id == created.task_id
    assert after.workspace_id == created.workspace_id
    assert after.attempt_id != before.attempt_id
    assert after.last_committed_tool_result_id == before.last_committed_tool_result_id
    assert after.candidate_runtime_ref == created.candidate_runtime_ref
    assert checkpoint.portable_state["candidate_conversation_id"] == created.candidate_runtime_ref
    second.stop()


def test_permanent_openhands_adapter_restores_in_fresh_process(tmp_path) -> None:
    root = tmp_path / "runtime"
    worker = [sys.executable, "-m", "tests.poc.support.runtime_worker"]
    first = subprocess.run(
        worker + ["first", "--root", str(root), "--scenario", "t10"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    metadata = json.loads((root / "worker-metadata.json").read_text(encoding="utf-8"))
    second = subprocess.run(
        worker + ["recover", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    restored = json.loads((root / "worker-result.json").read_text(encoding="utf-8"))
    state = restored["task_state"]
    read_events = [
        event for event in restored["events"]
        if event.get("candidate_event_type") == "ActionEvent"
        and event.get("tool_name") == "read_fixture"
    ]
    operation_id, tool_result = next(iter(restored["tool_results"].items()))

    assert state["task_id"] == metadata["task_id"]
    assert state["workspace_id"] == metadata["workspace_id"]
    assert state["attempt_id"] != metadata["attempt_id_before"]
    assert state["selected_model"] == "model-b"
    assert restored["candidate_conversation_id"] == metadata["candidate_conversation_id"]
    assert read_events and read_events[0]["tool_call_id"] == tool_result["tool_call_id"]
    assert operation_id.endswith(":" + read_events[0]["tool_call_id"])
    assert tool_result["result"] == "alpha\n"
    assert restored["final_result"] == "alpha"


def test_permanent_openhands_adapter_preserves_candidate_identity_separately(tmp_path) -> None:
    backend = OpenHandsRuntimeBackend(tmp_path / "runtime", conversation_factory=fake_conversation_factory)
    backend.start()
    state = backend.create_task(
        {
            "model": "fixture-model-a",
            "prompt": "Read the fixture.",
            "fixture_marker": "alpha\n",
        }
    )
    backend.run(state.task_id)
    checkpoint = backend.checkpoint(state.task_id)
    assert checkpoint.portable_state["candidate_conversation_id"] == state.candidate_runtime_ref
    assert checkpoint.task_id != checkpoint.portable_state["candidate_conversation_id"]
    backend.stop()
