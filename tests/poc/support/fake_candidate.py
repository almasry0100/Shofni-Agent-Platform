from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from poc.contracts._serialization import JSONMapping


@dataclass
class FakeAction:
    name: str
    arguments: dict[str, Any]

    def model_dump(self, **_: Any) -> JSONMapping:
        return dict(self.arguments)


@dataclass
class FakeMessage:
    role: str
    content: str


class FakeEvent:
    def __init__(
        self,
        event_id: str,
        *,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        action: FakeAction | None = None,
        role: str | None = None,
        content: str | None = None,
    ) -> None:
        self.id = event_id
        self.tool_name = tool_name
        self.tool_call_id = tool_call_id
        self.action = action
        self.llm_message = (
            FakeMessage(role, content or "") if role is not None else None
        )


class ActionEvent(FakeEvent):
    pass


class ObservationEvent(FakeEvent):
    pass


class MessageEvent(FakeEvent):
    pass


class FakeCandidateConversation:
    """Deterministic stand-in for SDK event/action boundaries in offline tests."""

    def __init__(
        self,
        record: JSONMapping,
        persistence: Path,
        resume: bool,
        event_callback,
        fixture_reader,
        ledger_appender,
    ) -> None:
        self._record = record
        self._persistence = persistence
        self._resume = resume
        self._emit = event_callback
        self._read = fixture_reader
        self._append = ledger_appender
        self._events: list[FakeEvent] = []
        self._model = str(record["model"])
        self.messages: list[str] = []
        self.closed = False
        self.switched_to: str | None = None

    @property
    def conversation_id(self) -> str:
        return str(self._record["conversation_id"])

    def send_message(self, message: str) -> None:
        self.messages.append(message)

    def run(self) -> None:
        if self._record.get("tool_mode") == "append":
            self._emit_action(
                "append_ledger",
                "append-call-1",
                {"value": self._record["ledger_value"]},
            )
            result = self._append(self._record["ledger_value"])
            self._emit_observation("append_ledger", "append-call-1", result)
            self._emit_message("assistant", "ledger-complete")
            return
        if self._model == str(self._record.get("model")) and not self._record.get("tool_results"):
            self._emit_action("read_fixture", "read-call-1", {"path": "input/alpha.txt"})
            result = self._read("input/alpha.txt")
            self._record["tool_completed"] = True
            self._emit_observation("read_fixture", "read-call-1", {"result": result})
            self._emit_message("assistant", result.strip())
        else:
            self._emit_message("assistant", "alpha")

    def switch_model(self, model: str, api_key: str, base_url: str) -> None:
        self._model = model
        self.switched_to = model

    def event_projection(self) -> list[JSONMapping]:
        result: list[JSONMapping] = []
        for event in self._events:
            item: JSONMapping = {
                "candidate_event_type": type(event).__name__,
                "candidate_event_id": event.id,
            }
            if event.tool_name:
                item["tool_name"] = event.tool_name
            if event.tool_call_id:
                item["tool_call_id"] = event.tool_call_id
            if event.action is not None:
                item["action"] = event.action.model_dump()
            if event.llm_message is not None:
                item["role"] = event.llm_message.role
                item["content"] = event.llm_message.content
            result.append(item)
        return result

    def record_recovered_tool_result(
        self, tool_name: str, tool_call_id: str, action_id: str, result: JSONMapping
    ) -> None:
        self._emit_observation(tool_name, tool_call_id, result, action_id=action_id)

    def close(self) -> None:
        self.closed = True

    def _emit_action(self, tool_name: str, call_id: str, arguments: dict[str, Any]) -> None:
        event = ActionEvent(
            f"action-{call_id}",
            tool_name=tool_name,
            tool_call_id=call_id,
            action=FakeAction(tool_name, arguments),
        )
        self._events.append(event)
        self._emit(event)

    def _emit_observation(
        self,
        tool_name: str,
        call_id: str,
        result: JSONMapping,
        *,
        action_id: str | None = None,
    ) -> None:
        event = ObservationEvent(
            f"observation-{call_id}-{len(self._events)}",
            tool_name=tool_name,
            tool_call_id=call_id,
        )
        self._events.append(event)
        self._emit(event)

    def _emit_message(self, role: str, content: str) -> None:
        event = MessageEvent(f"message-{len(self._events)}", role=role, content=content)
        self._events.append(event)
        self._emit(event)


def fake_conversation_factory(*args):
    return FakeCandidateConversation(*args)
