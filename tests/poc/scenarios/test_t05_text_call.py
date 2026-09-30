from __future__ import annotations

import pytest

from poc.fixtures.providers import (
    NativeToolProviderFixture,
    TextualToolCallFixture,
    make_structured_tool_call,
    parse_textual_tool_call,
)
from poc.fixtures.scenarios import run_scenario


@pytest.mark.parametrize(
    ("case", "expected_decision", "expected_call_count"),
    [
        ("valid", "TOOL_INTENT_READY", 1),
        ("duplicate", "TOOL_INTENT_READY", 1),
        ("prose", "NO_TOOL_INTENT", 0),
        ("narration", "NO_TOOL_INTENT", 0),
        ("fenced", "FENCED_TEXT_REJECTED", 0),
        ("structured_looking", "NO_TOOL_INTENT", 0),
        ("invalid_schema", "SCHEMA_REJECTED", 0),
    ],
)
def test_textual_tool_corpus_has_deterministic_schema_checked_decisions(
    case: str,
    expected_decision: str,
    expected_call_count: int,
) -> None:
    fixture = TextualToolCallFixture()
    text = fixture.response(case)

    first = parse_textual_tool_call(text, "t05-seed")
    second = parse_textual_tool_call(text, "t05-seed")
    assert first == second
    assert first.decision == expected_decision
    assert len(first.tool_calls) == expected_call_count
    if case == "duplicate":
        assert first.duplicate_count == 1
    if expected_call_count == 0:
        assert run_scenario(f"t05_text_{case}", "t05-seed")["tool_ledger_outcome"] == []
    else:
        assert len(run_scenario(f"t05_text_{case}", "t05-seed")["tool_ledger_outcome"]) == 1


def test_native_structured_call_ids_are_seeded_and_canonical() -> None:
    request = {"tool_name": "read_fixture", "arguments": {"path": "input/alpha.txt"}}
    fixture = NativeToolProviderFixture()

    first = fixture.respond(request, "stable-seed")
    second = fixture.respond(request, "stable-seed")
    changed_seed = fixture.respond(request, "different-seed")

    assert first == second
    assert first["tool_calls"][0]["id"] == make_structured_tool_call(
        "read_fixture", {"path": "input/alpha.txt"}, "stable-seed"
    )["id"]
    assert first["tool_calls"][0]["id"] != changed_seed["tool_calls"][0]["id"]
