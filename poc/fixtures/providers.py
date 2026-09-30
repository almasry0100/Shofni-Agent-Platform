from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def deterministic_id(prefix: str, seed: str, value: Any) -> str:
    payload = canonical_json({"seed": seed, "value": value}).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def validate_tool_arguments(name: object, arguments: object) -> tuple[bool, str | None]:
    if name != "read_fixture":
        return False, "unknown_tool"
    if not isinstance(arguments, dict) or set(arguments) != {"path"}:
        return False, "arguments_do_not_match_schema"
    path = arguments.get("path")
    if not isinstance(path, str) or not path or "\x00" in path:
        return False, "path_must_be_non_empty_text"
    normalized = path.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(path)
    parts = normalized.split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or not parts
        or parts[0] != "input"
        or any(part in {"", ".", ".."} or ":" in part for part in parts)
    ):
        return False, "path_outside_fixture_input"
    return True, None


def make_structured_tool_call(name: str, arguments: dict[str, Any], seed: str) -> dict[str, Any]:
    return {
        "id": deterministic_id("call", seed, {"name": name, "arguments": arguments}),
        "type": "function",
        "function": {"name": name, "arguments": canonical_json(arguments)},
    }


class NativeToolProviderFixture:
    fixture_name = "NativeToolProviderFixture"

    def respond(self, request: dict[str, Any], seed: str) -> dict[str, Any]:
        name = request.get("tool_name", "read_fixture")
        arguments = request.get("arguments", {"path": "input/alpha.txt"})
        valid, reason = validate_tool_arguments(name, arguments)
        if not valid:
            return {"content": None, "tool_calls": [], "finish_reason": "stop", "schema_error": reason}
        call = make_structured_tool_call(name, arguments, seed)
        return {"content": None, "tool_calls": [call], "finish_reason": "tool_calls"}


class ChatOnlyProviderFixture:
    fixture_name = "ChatOnlyProviderFixture"

    def respond(self, request: dict[str, Any], seed: str) -> dict[str, Any]:
        path = request.get("path", "input/alpha.txt")
        call_text = (
            'I need to use a tool.\n\n'
            'tool_call:\n'
            + canonical_json({"name": "read_fixture", "arguments": {"path": path}})
        )
        return {"content": call_text, "tool_calls": [], "finish_reason": "stop"}


class TextualToolCallFixture:
    fixture_name = "TextualToolCallFixture"

    def response(self, case: str) -> str:
        valid_call = 'tool_call:\n{"name":"read_fixture","arguments":{"path":"input/alpha.txt"}}'
        cases = {
            "valid": "I need to use a tool.\n\n" + valid_call,
            "duplicate": valid_call + "\n\n" + valid_call,
            "prose": "The tool_call function is mentioned, but no action is requested.",
            "narration": "I will read the file next.",
            "fenced": (chr(96) * 3) + "json\n" + (
                '{"name":"read_fixture","arguments":{"path":"input/alpha.txt"}}'
            ) + "\n" + (chr(96) * 3),
            "structured_looking": (
                'function read_fixture({"path":"input/alpha.txt"})'
            ),
            "invalid_schema": (
                'tool_call:\n{"name":"delete_fixture","arguments":{"path":"input/alpha.txt"}}'
            ),
        }
        try:
            return cases[case]
        except KeyError as exc:
            raise ValueError(f"unknown textual-tool fixture case: {case}") from exc


_TEXT_CALL = re.compile(
    r"(?im)^[ \t]*tool_call[ \t]*:[ \t]*\r?\n[ \t]*(\{[^\r\n]*\})[ \t]*$"
)


@dataclass(frozen=True)
class TextualParseResult:
    decision: str
    tool_calls: tuple[dict[str, Any], ...]
    duplicate_count: int
    invalid_match_count: int
    completion_state: str


class _DuplicateJsonKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def parse_textual_tool_call(text: str, seed: str) -> TextualParseResult:
    if not isinstance(text, str):
        raise TypeError("textual tool response must be text")
    if (chr(96) * 3) in text:
        return TextualParseResult("FENCED_TEXT_REJECTED", (), 0, 0, "NOT_FINAL")

    matches = list(_TEXT_CALL.finditer(text))
    if not matches:
        return TextualParseResult("NO_TOOL_INTENT", (), 0, 0, "NARRATION_ONLY" if text.strip() else "EMPTY")

    intents: dict[str, tuple[str, dict[str, Any]]] = {}
    invalid_count = 0
    for match in matches:
        try:
            parsed = json.loads(match.group(1), object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, _DuplicateJsonKey):
            invalid_count += 1
            continue
        if not isinstance(parsed, dict) or set(parsed) != {"name", "arguments"}:
            invalid_count += 1
            continue
        name, arguments = parsed["name"], parsed["arguments"]
        valid, _ = validate_tool_arguments(name, arguments)
        if not valid:
            invalid_count += 1
            continue
        key = canonical_json({"name": name, "arguments": arguments})
        intents[key] = (name, arguments)

    if invalid_count:
        return TextualParseResult("SCHEMA_REJECTED", (), 0, invalid_count, "NOT_FINAL")
    if len(intents) > 1:
        return TextualParseResult("AMBIGUOUS_MULTIPLE_INTENTS", (), 0, 0, "NOT_FINAL")
    if not intents:
        return TextualParseResult("SCHEMA_REJECTED", (), 0, len(matches), "NOT_FINAL")

    (intent_key, (name, arguments)), = intents.items()
    duplicate_count = len(matches) - 1
    call = make_structured_tool_call(name, arguments, seed)
    wrapper_has_narration = bool(re.search(r"\b(?:need to use|will read|i['’]ll read)\b", text, re.IGNORECASE))
    completion_state = "CONTINUATION_REQUIRED" if wrapper_has_narration else "TOOL_CALL_READY"
    return TextualParseResult("TOOL_INTENT_READY", (call,), duplicate_count, 0, completion_state)


class MalformedToolJsonFixture:
    fixture_name = "MalformedToolJsonFixture"

    def payloads(self) -> dict[str, str]:
        normal = {"name": "read_fixture", "arguments": {"path": "input/alpha.txt"}}
        return {
            "trailing_comma": '{"name":"read_fixture","arguments":{"path":"input/alpha.txt",}}',
            "single_quotes": "{'name': 'read_fixture', 'arguments': {'path': 'input/alpha.txt'}}",
            "two_step_trailing_commas": (
                '{"name":"read_fixture","arguments":{"path":"input/alpha.txt",},}'
            ),
            "fenced_trailing_comma": (
                (chr(96) * 3) + "json\n"
                + '{"name":"read_fixture","arguments":{"path":"input/alpha.txt",}}'
                + "\n" + (chr(96) * 3)
            ),
            "stringified_arguments": canonical_json({
                "name": normal["name"],
                "arguments": canonical_json(normal["arguments"]),
            }),
            "harmless_metadata": canonical_json({**normal, "metadata": "fixture-note"}),
            "ambiguous_duplicate_key": (
                '{"name":"read_fixture","arguments":{"path":"input/alpha.txt"},'
                '"arguments":{"path":"input/beta.json"}}'
            ),
            "irrecoverable": "{name: read_fixture, arguments: }",
        }


@dataclass(frozen=True)
class JsonRepairResult:
    status: str
    original_payload: str
    repaired_payload: str
    repair_history: tuple[dict[str, Any], ...]
    tool_call: dict[str, Any] | None
    failure_class: str | None
    repair_attempts: int
    ambiguous: bool


def _safe_literal_to_json(text: str) -> str | None:
    try:
        value = ast.literal_eval(text)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        return None

    def valid_json_value(item: Any) -> bool:
        if item is None or isinstance(item, (str, bool, int)):
            return True
        if isinstance(item, float):
            return item == item and abs(item) != float("inf")
        if isinstance(item, list):
            return all(valid_json_value(child) for child in item)
        if isinstance(item, dict):
            return all(isinstance(key, str) and valid_json_value(child) for key, child in item.items())
        return False

    if not valid_json_value(value):
        return None
    try:
        return canonical_json(value)
    except (TypeError, ValueError):
        return None


def _remove_one_trailing_comma(text: str) -> str | None:
    in_string = False
    escaped = False
    for index, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if character == ",":
            next_index = index + 1
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            if next_index < len(text) and text[next_index] in "}]":
                return text[:index] + text[index + 1 :]
    return None


def _strip_exact_json_fence(text: str) -> str | None:
    fence = chr(96) * 3
    stripped = text.strip()
    if not stripped.startswith(fence) or not stripped.endswith(fence):
        return None
    body = stripped[len(fence) : -len(fence)]
    if body.startswith("json"):
        body = body[4:]
    return body.strip()


def _normalize_parsed_payload(
    parsed: object,
    seed: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    if not isinstance(parsed, dict) or not {"name", "arguments"}.issubset(parsed):
        return None, [], "payload_shape_invalid"
    extras = set(parsed) - {"name", "arguments", "metadata"}
    if extras:
        return None, [], "unexpected_wrapper_fields"
    history: list[dict[str, Any]] = []
    value = dict(parsed)
    if "metadata" in value:
        before = canonical_json(value)
        if not isinstance(value["metadata"], str):
            return None, history, "metadata_field_invalid"
        del value["metadata"]
        history.append({"decision": "drop_harmless_metadata", "before": before, "after": canonical_json(value)})

    arguments = value["arguments"]
    if isinstance(arguments, str):
        before = arguments
        try:
            arguments = json.loads(arguments, object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, _DuplicateJsonKey):
            return None, history, "stringified_arguments_invalid"
        if not isinstance(arguments, dict):
            return None, history, "arguments_must_be_object"
        value["arguments"] = arguments
        history.append({
            "decision": "parse_stringified_arguments",
            "before": before,
            "after": canonical_json(arguments),
        })

    valid, reason = validate_tool_arguments(value["name"], value["arguments"])
    if not valid:
        return None, history, reason or "schema_validation_failed"
    call = make_structured_tool_call(value["name"], value["arguments"], seed)
    return call, history, None


def repair_tool_json(raw_payload: str, seed: str, max_attempts: int = 2) -> JsonRepairResult:
    if max_attempts < 0 or max_attempts > 2:
        raise ValueError("Phase 2 JSON repair is bounded to at most two attempts")

    current = raw_payload
    history: list[dict[str, Any]] = []
    parsed: object | None = None
    ambiguous = False

    while True:
        try:
            parsed = json.loads(current, object_pairs_hook=_unique_object)
            break
        except _DuplicateJsonKey:
            ambiguous = True
            break
        except json.JSONDecodeError:
            if len(history) >= max_attempts:
                break
            replacement = _strip_exact_json_fence(current)
            decision = "strip_exact_json_fence"
            if replacement is None:
                replacement = _remove_one_trailing_comma(current)
                decision = "remove_one_trailing_comma"
            if replacement is None:
                replacement = _safe_literal_to_json(current)
                decision = "normalize_safe_single_quoted_literal"
            if replacement is None or replacement == current:
                break
            history.append({"attempt": len(history) + 1, "decision": decision, "before": current, "after": replacement})
            current = replacement

    call: dict[str, Any] | None = None
    failure_reason: str | None = None
    normalization_history: list[dict[str, Any]] = []
    if parsed is not None and not ambiguous:
        call, normalization_history, failure_reason = _normalize_parsed_payload(parsed, seed)
        if len(history) + len(normalization_history) > max_attempts:
            call = None
            failure_reason = "repair_attempt_limit_exceeded"
        else:
            for item in normalization_history:
                item = dict(item)
                item["attempt"] = len(history) + 1
                history.append(item)

    if call is not None:
        return JsonRepairResult(
            status="REPAIRED" if history else "VALID",
            original_payload=raw_payload,
            repaired_payload=canonical_json({
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"]["arguments"]),
            }),
            repair_history=tuple(history),
            tool_call=call,
            failure_class=None,
            repair_attempts=len(history),
            ambiguous=False,
        )

    return JsonRepairResult(
        status="AMBIGUOUS" if ambiguous else "REJECTED",
        original_payload=raw_payload,
        repaired_payload=current,
        repair_history=tuple(history),
        tool_call=None,
        failure_class="MALFORMED_RESPONSE",
        repair_attempts=len(history),
        ambiguous=ambiguous,
    )
