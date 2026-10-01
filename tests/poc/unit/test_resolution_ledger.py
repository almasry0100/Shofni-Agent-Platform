from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from poc.evidence.resolution_ledger import build_resolution_ledger


RUN_ID = "resolution-20261001T180545Z"


def _row(ledger: dict, candidate: str, test_id: str, provider: str) -> dict:
    return next(
        row
        for row in ledger["rows"]
        if row["candidate"] == candidate and row["test_id"] == test_id and row["provider"] == provider
    )


def test_resolution_ledger_preserves_history_and_applies_r2_r3_attribution() -> None:
    ledger = build_resolution_ledger(ROOT, RUN_ID)

    assert ledger == build_resolution_ledger(ROOT, RUN_ID)
    assert len(ledger["rows"]) == 28
    assert len({row["row_id"] for row in ledger["rows"]}) == len(ledger["rows"])

    for candidate in ("Bifrost", "LiteLLM"):
        t03 = _row(ledger, candidate, "T03", "A6api")
        assert t03["current_effective_result"]["status"] == "BLOCKED"
        assert t03["current_effective_result"]["classification"] == "EVIDENCE_OBSERVABILITY_FAILURE"
        assert t03["candidate_reached"] is False
        assert t03["candidate_controlled"] is False
        assert t03["current_effective_result"]["provider_reached"] is False
        r2_attempts = [item for item in t03["historical_attempts"] if item.get("phase") == "R2"]
        assert len(r2_attempts) == 3
        assert all(item["status"] == "FAIL" and item["candidate_execution"] is False for item in r2_attempts)
        assert any(item["run_id"] == "level2-remediation-20260930T194948Z" for item in t03["historical_attempts"])

        for test_id in ("T04", "T07", "T08"):
            relay = _row(ledger, candidate, test_id, "RelayRouter")
            assert relay["current_effective_result"]["status"] == "BLOCKED"
            assert relay["current_effective_result"]["classification"] == "EXTERNAL_PROVIDER_BLOCKED"
            assert relay["candidate_reached"] is False
            assert relay["candidate_controlled"] is False
            assert relay["externally_blocked"] is True
            assert any(item["status"] == "FAIL" for item in relay["historical_attempts"])
            assert "tests/poc/evidence/resolution/20261001T180545Z/r3/direct-control.json" in relay["evidence_refs"]

        fixture = _row(ledger, candidate, "T09-B", "Shofni synthetic fixture")
        assert fixture["current_effective_result"]["status"] == "PASS"
        assert fixture["live_vs_fixture"] == "FIXTURE"
        assert fixture["candidate_controlled"] is False
        assert fixture["candidate_attribution"] == "CANDIDATE_NEUTRAL_FIXTURE_ONLY"

    t12 = ledger["t12"]
    assert t12["architecture_candidate_eligibility"]["Bifrost"]["status"] == "NO_DECISION_YET"
    assert t12["architecture_candidate_eligibility"]["LiteLLM"]["status"] == "NO_DECISION_YET"
    assert t12["readiness_by_provider"]["RelayRouter"] == "BLOCKED_EXTERNAL_PROVIDER"
    assert t12["readiness_by_provider"]["A6api"] == "PARTIAL"
    assert set(t12["effective_capability"]["Bifrost"]) == {
        "native_tools",
        "emulated_tools",
        "streaming",
        "sequential_continuation",
        "fallback",
    }
    assert t12["effective_capability"]["Bifrost"]["emulated_tools"] == "BLOCKED_EXTERNAL_PROVIDER"
    assert t12["effective_capability"]["Bifrost"]["fallback"] == "UNVERIFIED"
