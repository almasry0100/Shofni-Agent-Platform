from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Mapping

from ._serialization import JSONMapping, JSONValue, timestamp_from_json, timestamp_to_json


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    schema_version: str
    task_id: str
    session_id: str
    workspace_id: str
    timestamp_utc: datetime
    parent_checkpoint_id: str | None
    portable_state: JSONMapping | None
    candidate_snapshot_ref: str | None

    def __post_init__(self) -> None:
        for name in ("checkpoint_id", "schema_version", "task_id", "session_id", "workspace_id"):
            _required_text(getattr(self, name), name)
        if self.parent_checkpoint_id is not None:
            _required_text(self.parent_checkpoint_id, "parent_checkpoint_id")
        if self.candidate_snapshot_ref is not None:
            _required_text(self.candidate_snapshot_ref, "candidate_snapshot_ref")
        if (self.portable_state is None) == (self.candidate_snapshot_ref is None):
            raise ValueError("checkpoint must contain portable_state or candidate_snapshot_ref, but not both")
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() is None:
            raise ValueError("timestamp_utc must include a timezone")
        object.__setattr__(self, "timestamp_utc", self.timestamp_utc.astimezone(timezone.utc))

    def to_dict(self) -> JSONMapping:
        return {
            "checkpoint_id": self.checkpoint_id,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "timestamp_utc": timestamp_to_json(self.timestamp_utc),
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "portable_state": self.portable_state,
            "candidate_snapshot_ref": self.candidate_snapshot_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Checkpoint:
        required = {
            "checkpoint_id",
            "schema_version",
            "task_id",
            "session_id",
            "workspace_id",
            "timestamp_utc",
            "parent_checkpoint_id",
            "portable_state",
            "candidate_snapshot_ref",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"Checkpoint is missing fields: {', '.join(sorted(missing))}")
        state = value["portable_state"]
        if state is not None and (not isinstance(state, dict) or not all(isinstance(k, str) for k in state)):
            raise TypeError("portable_state must be a JSON object or null")
        parent_id = value["parent_checkpoint_id"]
        snapshot_ref = value["candidate_snapshot_ref"]
        if parent_id is not None and not isinstance(parent_id, str):
            raise TypeError("parent_checkpoint_id must be a string or null")
        if snapshot_ref is not None and not isinstance(snapshot_ref, str):
            raise TypeError("candidate_snapshot_ref must be a string or null")
        return cls(
            checkpoint_id=_required_text(value["checkpoint_id"], "checkpoint_id"),
            schema_version=_required_text(value["schema_version"], "schema_version"),
            task_id=_required_text(value["task_id"], "task_id"),
            session_id=_required_text(value["session_id"], "session_id"),
            workspace_id=_required_text(value["workspace_id"], "workspace_id"),
            timestamp_utc=timestamp_from_json(value["timestamp_utc"], "timestamp_utc"),
            parent_checkpoint_id=parent_id,
            portable_state=state,
            candidate_snapshot_ref=snapshot_ref,
        )
