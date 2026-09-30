from __future__ import annotations

import json

from poc.fixtures.providers import deterministic_id
from poc.fixtures.scenarios import run_scenario
from poc.fixtures.streaming import StreamingToolFixture, assemble_stream


def test_stream_reassembly_preserves_exact_tool_id_arguments_and_order() -> None:
    seed = "stream-seed"
    fixture = StreamingToolFixture()
    events = fixture.events(seed)

    first = assemble_stream(events)
    second = assemble_stream(fixture.events(seed))
    assert first == second
    assert first.status == "COMPLETE"
    assert first.tool_call_id == deterministic_id(
        "call", seed, {"name": "read_fixture", "path": "input/alpha.txt"}
    )
    assert json.loads(first.arguments_json) == {"path": "input/alpha.txt"}
    assert first.terminal_event_count == 1
    assert [event["sequence"] for event in first.normalized_events] == list(range(len(events)))
    assert first.normalized_events[-1]["event_type"] == "response.completed"

    record = run_scenario("t08_stream_complete", seed)
    assert record["result_status"] == "PASS"
    assert record["tool_call_id"] == first.tool_call_id


def test_stream_without_terminal_event_is_classified_as_incomplete() -> None:
    result = assemble_stream(StreamingToolFixture().events("incomplete", include_terminal=False))

    assert result.status == "INCOMPLETE"
    assert result.failure_class == "STREAMING_FAILURE"
    assert result.tool_call is None
    assert result.terminal_event_count == 0
    assert run_scenario("t08_stream_incomplete", "incomplete")["result_status"] == "PASS"


def test_truncated_argument_fragment_is_classified_as_malformed() -> None:
    result = assemble_stream(StreamingToolFixture().events("truncated", truncate_arguments=True))

    assert result.status == "MALFORMED"
    assert result.failure_class == "STREAMING_FAILURE"
    assert result.tool_call is None
    assert run_scenario("t08_stream_malformed_arguments", "truncated")["result_status"] == "PASS"


def test_duplicate_terminal_semantic_events_are_rejected() -> None:
    events = list(StreamingToolFixture().events("duplicate-terminal"))
    duplicate_terminal = dict(events[-1])
    duplicate_terminal["sequence"] = len(events)
    events.append(duplicate_terminal)

    result = assemble_stream(events)
    assert result.status == "MALFORMED"
    assert result.terminal_event_count == 2
    assert result.tool_call is None
