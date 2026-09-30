from __future__ import annotations

import pytest

from poc.fixtures.providers import MalformedToolJsonFixture, repair_tool_json
from poc.fixtures.scenarios import run_scenario


@pytest.mark.parametrize(
    ("case", "should_repair", "expected_attempts"),
    [
        ("trailing_comma", True, 1),
        ("single_quotes", True, 1),
        ("two_step_trailing_commas", True, 2),
        ("fenced_trailing_comma", True, 2),
        ("stringified_arguments", True, 1),
        ("harmless_metadata", True, 1),
        ("ambiguous_duplicate_key", False, 0),
        ("irrecoverable", False, 0),
    ],
)
def test_malformed_tool_json_is_repaired_deterministically_and_within_bound(
    case: str,
    should_repair: bool,
    expected_attempts: int,
) -> None:
    payload = MalformedToolJsonFixture().payloads()[case]

    first = repair_tool_json(payload, "t06-seed")
    second = repair_tool_json(payload, "t06-seed")
    record = run_scenario(
        "t06_ambiguous_duplicate_keys" if case == "ambiguous_duplicate_key"
        else "t06_irrecoverable" if case == "irrecoverable"
        else {
            "trailing_comma": "t06_trailing_comma",
            "single_quotes": "t06_single_quotes",
            "two_step_trailing_commas": "t06_two_step_repair",
            "fenced_trailing_comma": "t06_fenced_repair",
            "stringified_arguments": "t06_stringified_arguments",
            "harmless_metadata": "t06_harmless_metadata",
        }[case],
        "t06-seed",
    )

    assert first == second
    assert first.repair_attempts == expected_attempts
    assert first.repair_attempts <= 2
    assert (first.tool_call is not None) is should_repair
    assert record["result_status"] == "PASS"
    assert record["normalized_request"]["original_payload"] == payload
    if should_repair:
        assert first.original_payload != first.repaired_payload
        assert len(record["tool_ledger_outcome"]) == 1
    else:
        assert first.tool_call is None
        assert record["tool_ledger_outcome"] == []
        if case == "ambiguous_duplicate_key":
            assert first.ambiguous is True


def test_repair_never_accepts_more_than_two_attempts() -> None:
    with pytest.raises(ValueError, match="at most two"):
        repair_tool_json("{}", "t06-seed", max_attempts=3)
