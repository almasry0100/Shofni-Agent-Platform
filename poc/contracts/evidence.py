from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from ._serialization import JSONValue
from poc.evidence.schema import EvidenceEnvelope


class EvidenceRecordKind(str, Enum):
    REQUEST = "request"
    EVENT = "event"
    TOOL = "tool"
    STATE = "state"
    ERROR = "error"


@dataclass(frozen=True)
class RedactedEvidenceRecord:
    kind: EvidenceRecordKind
    envelope: EvidenceEnvelope
    payload: JSONValue


@runtime_checkable
class EvidenceRecorder(Protocol):
    def append(self, record: RedactedEvidenceRecord) -> None: ...
