from __future__ import annotations

from poc.runtime.openhands_backend import OpenHandsRuntimeBackend
from tests.poc.support.fake_candidate import fake_conversation_factory


def test_restore_creates_explicit_new_attempt_without_new_task(tmp_path) -> None:
    backend = OpenHandsRuntimeBackend(tmp_path / "runtime", conversation_factory=fake_conversation_factory)
    backend.start()
    state = backend.create_task(
        {"model": "fixture-model-a", "prompt": "Read input/alpha.txt.", "fixture_marker": "alpha\n"}
    )
    backend.run(state.task_id)
    checkpoint = backend.checkpoint(state.task_id)
    old_attempt = backend.inspect(state.task_id).attempt_id
    backend.stop()

    restored_backend = OpenHandsRuntimeBackend(
        tmp_path / "runtime", conversation_factory=fake_conversation_factory
    )
    restored_backend.start()
    restored_backend.resume(checkpoint)
    restored = restored_backend.inspect(state.task_id)
    assert restored.task_id == state.task_id
    assert restored.workspace_id == state.workspace_id
    assert restored.attempt_id != old_attempt
    restored_backend.stop()
