from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from ._serialization import JSONValue


class ToolExecutionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_call_id: str
    operation_id: str
    status: ToolExecutionStatus
    result: JSONValue


@runtime_checkable
class ToolExecutionBackend(Protocol):
    def execute(
        self,
        call: JSONValue,
        tool_call_id: str,
        operation_id: str,
    ) -> ToolExecutionResult: ...

    def lookup(self, operation_id: str) -> ToolExecutionResult | None: ...

    def record(self, result: ToolExecutionResult) -> None: ...
