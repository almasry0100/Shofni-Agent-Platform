from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

from ._serialization import JSONMapping


class TaskLifecycleStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    INTERRUPTED = "INTERRUPTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_text(value: object, field_name: str) -> str | None:
    if value is not None and (not isinstance(value, str) or not value):
        raise ValueError(f"{field_name} must be a non-empty string or null")
    return value


@dataclass(frozen=True)
class TaskState:
    task_id: str
    session_id: str
    attempt_id: str
    workspace_id: str
    selected_provider: str | None
    selected_model: str | None
    lifecycle_status: TaskLifecycleStatus
    last_committed_tool_call_id: str | None
    last_committed_tool_result_id: str | None
    candidate_runtime_ref: str | None

    def __post_init__(self) -> None:
        for name in ("task_id", "session_id", "attempt_id", "workspace_id"):
            _required_text(getattr(self, name), name)
        for name in (
            "selected_provider",
            "selected_model",
            "last_committed_tool_call_id",
            "last_committed_tool_result_id",
            "candidate_runtime_ref",
        ):
            _optional_text(getattr(self, name), name)

    def to_dict(self) -> JSONMapping:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "attempt_id": self.attempt_id,
            "workspace_id": self.workspace_id,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "lifecycle_status": self.lifecycle_status.value,
            "last_committed_tool_call_id": self.last_committed_tool_call_id,
            "last_committed_tool_result_id": self.last_committed_tool_result_id,
            "candidate_runtime_ref": self.candidate_runtime_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> TaskState:
        required = {
            "task_id",
            "session_id",
            "attempt_id",
            "workspace_id",
            "selected_provider",
            "selected_model",
            "lifecycle_status",
            "last_committed_tool_call_id",
            "last_committed_tool_result_id",
            "candidate_runtime_ref",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"TaskState is missing fields: {', '.join(sorted(missing))}")
        try:
            status = TaskLifecycleStatus(_required_text(value["lifecycle_status"], "lifecycle_status"))
        except ValueError as exc:
            raise ValueError("lifecycle_status is not a supported TaskLifecycleStatus") from exc
        return cls(
            task_id=_required_text(value["task_id"], "task_id"),
            session_id=_required_text(value["session_id"], "session_id"),
            attempt_id=_required_text(value["attempt_id"], "attempt_id"),
            workspace_id=_required_text(value["workspace_id"], "workspace_id"),
            selected_provider=_optional_text(value["selected_provider"], "selected_provider"),
            selected_model=_optional_text(value["selected_model"], "selected_model"),
            lifecycle_status=status,
            last_committed_tool_call_id=_optional_text(
                value["last_committed_tool_call_id"], "last_committed_tool_call_id"
            ),
            last_committed_tool_result_id=_optional_text(
                value["last_committed_tool_result_id"], "last_committed_tool_result_id"
            ),
            candidate_runtime_ref=_optional_text(value["candidate_runtime_ref"], "candidate_runtime_ref"),
        )
