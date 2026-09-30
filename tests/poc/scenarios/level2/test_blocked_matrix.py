import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MATRIX = ROOT / "tests/poc/evidence/level2/level2-20260930T150128Z/matrix.json"


def test_candidate_scenarios_are_explicitly_blocked_and_reference_setup_evidence():
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    expected_tests = {"T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09-A", "T09-B"}
    assert {row["test_id"] for row in matrix["rows"]} == expected_tests
    assert len(matrix["rows"]) == len(expected_tests) * 2
    for row in matrix["rows"]:
        assert row["status"] == "BLOCKED"
        assert row["behavior_mode"] == "UNVERIFIED"
        assert row["failure_class"] == "SETUP_FAILURE"
        assert row["evidence_refs"]
        assert all((ROOT / reference).is_file() for reference in row["evidence_refs"])


def test_unsupported_direct_pairings_remain_not_applicable():
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert {(row["client"], row["provider"], row["status"]) for row in matrix["not_applicable_pairings"]} == {
        ("Codex", "RelayRouter", "NOT_APPLICABLE"),
        ("Claude Code", "RelayRouter", "NOT_APPLICABLE"),
    }


def test_phase_2_fixture_pass_is_not_candidate_evidence():
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert matrix["candidate_executions"] is False
    assert matrix["phase_2_fixture_controls"]["status"] == "PASS"
    assert "do not establish either gateway candidate" in matrix["phase_2_fixture_controls"]["scope"]
