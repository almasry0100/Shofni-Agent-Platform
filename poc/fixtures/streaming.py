from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .providers import deterministic_id, validate_tool_arguments


class StreamingToolFixture:
    fixture_name = "StreamingToolFixture"

    def events(
        self,
        seed: str,
        *,
        include_terminal: bool = True,
        truncate_arguments: bool = False,
    ) -> tuple[dict[str, Any], ...]:
        tool_call_id = deterministic_id("call", seed, {"name": "read_fixture", "path": "input/alpha.txt"})
        arguments = '{"path":"input/alpha.txt"}'
        split_at = max(1, len(arguments) // 2)
        second_arguments = arguments[split_at:]
        if truncate_arguments:
            second_arguments = second_arguments[:-1]
        identifier_split = max(1, len(tool_call_id) // 2)
        events: list[dict[str, Any]] = [
            {
                "sequence": 0,
                "event_type": "response.content.delta",
                "content_delta": "Inspecting the fixture input.",
                "tool_call_id_fragment": "",
                "arguments_fragment": "",
                "terminal": False,
            },
            {
                "sequence": 1,
                "event_type": "response.output_item.added",
                "content_delta": "",
                "tool_call_id_fragment": tool_call_id[:identifier_split],
                "arguments_fragment": arguments[:split_at],
                "terminal": False,
            },
            {
                "sequence": 2,
                "event_type": "response.function_call_arguments.delta",
                "content_delta": "",
                "tool_call_id_fragment": tool_call_id[identifier_split:],
                "arguments_fragment": second_arguments,
                "terminal": False,
            },
        ]
        if include_terminal:
            events.append({
                "sequence": len(events),
                "event_type": "response.completed",
                "content_delta": "",
                "tool_call_id_fragment": "",
                "arguments_fragment": "",
                "terminal": True,
                "finish_reason": "tool_calls",
            })
        return tuple(events)


@dataclass(frozen=True)
class StreamAssemblyResult:
    status: str
    normalized_events: tuple[dict[str, Any], ...]
    tool_call_id: str | None
    arguments_json: str | None
    tool_call: dict[str, Any] | None
    terminal_event_count: int
    failure_class: str | None
    failure_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "normalized_events": list(self.normalized_events),
            "tool_call_id": self.tool_call_id,
            "arguments_json": self.arguments_json,
            "tool_call": self.tool_call,
            "terminal_event_count": self.terminal_event_count,
            "failure_class": self.failure_class,
            "failure_reason": self.failure_reason,
        }


def assemble_stream(events: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> StreamAssemblyResult:
    normalized = tuple(dict(event) for event in events)
    terminal_indexes = [index for index, event in enumerate(normalized) if event.get("terminal") is True]
    terminal_count = len(terminal_indexes)
    if any(event.get("sequence") != index for index, event in enumerate(normalized)):
        return StreamAssemblyResult(
            "MALFORMED", normalized, None, None, None, terminal_count,
            "STREAMING_FAILURE", "event_order_invalid",
        )
    if terminal_count == 0:
        return StreamAssemblyResult(
            "INCOMPLETE", normalized, None, None, None, 0,
            "STREAMING_FAILURE", "terminal_event_missing",
        )
    if terminal_count != 1 or terminal_indexes[0] != len(normalized) - 1:
        return StreamAssemblyResult(
            "MALFORMED", normalized, None, None, None, terminal_count,
            "STREAMING_FAILURE", "terminal_event_multiplicity_or_order_invalid",
        )

    identifier_parts: list[str] = []
    argument_parts: list[str] = []
    for event in normalized[:-1]:
        if event.get("event_type") not in {
            "response.content.delta",
            "response.output_item.added",
            "response.function_call_arguments.delta",
        }:
            return StreamAssemblyResult(
                "MALFORMED", normalized, None, None, None, terminal_count,
                "STREAMING_FAILURE", "event_type_invalid",
            )
        identifier_parts.append(event.get("tool_call_id_fragment", ""))
        argument_parts.append(event.get("arguments_fragment", ""))

    tool_call_id = "".join(identifier_parts)
    arguments_json = "".join(argument_parts)
    if not tool_call_id or not arguments_json:
        return StreamAssemblyResult(
            "INCOMPLETE", normalized, tool_call_id or None, arguments_json or None, None, terminal_count,
            "STREAMING_FAILURE", "tool_call_fragments_incomplete",
        )
    try:
        import json

        arguments = json.loads(arguments_json)
    except (ValueError, TypeError):
        return StreamAssemblyResult(
            "MALFORMED", normalized, tool_call_id, arguments_json, None, terminal_count,
            "STREAMING_FAILURE", "arguments_json_malformed",
        )
    valid, reason = validate_tool_arguments("read_fixture", arguments)
    if not valid:
        return StreamAssemblyResult(
            "MALFORMED", normalized, tool_call_id, arguments_json, None, terminal_count,
            "STREAMING_FAILURE", reason,
        )
    call = {
        "id": tool_call_id,
        "type": "function",
        "function": {"name": "read_fixture", "arguments": arguments_json},
    }
    return StreamAssemblyResult(
        "COMPLETE", normalized, tool_call_id, arguments_json, call, terminal_count, None, None
    )
