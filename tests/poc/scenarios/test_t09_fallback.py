from __future__ import annotations

from poc.fixtures.scenarios import run_scenario


def test_t09_a_fallback_is_allowed_after_failure_before_any_tool_effect() -> None:
    record = run_scenario("t09_before_tool", "t09-before-seed")

    assert record["result_status"] == "PASS"
    assert len(record["attempt_transitions"]) == 2
    assert record["attempt_transitions"][0]["failure_stage"] == "BEFORE_TOOL_EFFECT"
    assert record["attempt_transitions"][0]["tool_effect_occurred"] is False
    assert record["attempt_transitions"][1]["transition_allowed"] is True
    assert record["normalized_response"]["tool_effect_count"] == 1
    assert record["decisions"][0]["duplicate_effect_count"] == 0


def test_t09_b_reuses_recorded_tool_result_after_provider_failure() -> None:
    record = run_scenario("t09_after_tool", "t09-after-seed")
    transitions = record["attempt_transitions"]
    ledger = record["tool_ledger_outcome"][0]

    assert record["result_status"] == "PASS"
    assert transitions[0]["failure_stage"] == "AFTER_TOOL_RESULT"
    assert transitions[0]["tool_effect_occurred"] is True
    assert transitions[0]["attempt_id"] != transitions[1]["attempt_id"]
    assert transitions[0]["tool_call_id"] == transitions[1]["tool_call_id"]
    assert transitions[0]["operation_id"] == transitions[1]["operation_id"]
    assert record["operation_id"] == ledger["operation_id"]
    assert transitions[1]["existing_result_received"] is True
    assert transitions[1]["tool_call_requested_again"] is False
    assert transitions[1]["tool_effect_reexecuted"] is False
    assert ledger["duplicate_suppression_decision"] == "reuse_recorded_result_without_reexecution"
    assert ledger["side_effect_count"] == 1
    assert ledger["duplicate_effect_count"] == 0
    assert record["normalized_response"]["final_status"] == "FINAL"


def test_narration_after_tool_is_not_marked_as_completion() -> None:
    record = run_scenario("narration_after_tool", "narration-seed")

    assert record["result_status"] == "PASS"
    assert record["normalized_response"]["provider_response"]["tool_calls"] == []
    assert record["normalized_response"]["task_completed"] is False
    assert record["decisions"][0]["completion_state"] == "CONTINUATION_REQUIRED"
