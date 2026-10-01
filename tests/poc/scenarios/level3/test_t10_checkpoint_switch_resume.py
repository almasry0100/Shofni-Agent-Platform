from __future__ import annotations

from poc.runtime.openhands_backend import OpenHandsRuntimeBackend
from tests.poc.support.fake_candidate import fake_conversation_factory


def test_t10_checkpoint_switch_resume_requires_candidate_action_and_continuity(tmp_path) -> None:
    backend = OpenHandsRuntimeBackend(tmp_path / "runtime", conversation_factory=fake_conversation_factory)
    backend.start()
    state = backend.create_task(
        {
            "provider": "fixture",
            "model": "model-a-tool-capable",
            "prompt": "Use read_fixture on input/alpha.txt, then wait.",
            "fixture_marker": "alpha\n",
            "tool_mode": "read",
        }
    )
    backend.run(state.task_id)
    before = backend.inspect(state.task_id)
    assert before.last_committed_tool_call_id == "read-call-1"
    checkpoint = backend.checkpoint(state.task_id)
    backend.stop()

    fresh = OpenHandsRuntimeBackend(tmp_path / "runtime", conversation_factory=fake_conversation_factory)
    fresh.start()
    fresh.resume(checkpoint)
    fresh.switch_model(state.task_id, "model-b")
    fresh.send_message(state.task_id, "Resume and provide the saved result.")
    fresh.run(state.task_id)
    final = fresh.inspect(state.task_id)
    assert final.task_id == state.task_id
    assert final.workspace_id == state.workspace_id
    assert final.attempt_id != before.attempt_id
    assert final.selected_model == "model-b"
    assert final.last_committed_tool_result_id == before.last_committed_tool_result_id
    fresh.stop()
