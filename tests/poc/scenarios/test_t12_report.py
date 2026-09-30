import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from poc.reports.build_compatibility_report import build_reports


def test_report_build_is_deterministic_and_references_sealed_evidence():
    first = build_reports(ROOT)
    second = build_reports(ROOT)
    assert first == second
    report = json.loads(first["docs/poc/compatibility-matrix.json"])
    assert len(report["records"]) == 10
    assert report["candidate_decision"] == "NONE"
    assert report["phase_3_status"] == "PASS"
    assert report["phase_4_status"] == "PASS"
    assert report["phase_5_status"] == "PARTIAL"
    expected = {
        ("Bifrost", "Codex", "A6api"): "PASS",
        ("Bifrost", "Claude Code", "A6api"): "FAIL",
        ("Bifrost", "OpenCode", "A6api"): "PASS",
        ("Bifrost", "OpenCode", "RelayRouter"): "FAIL",
        ("LiteLLM", "Codex", "A6api"): "PASS",
        ("LiteLLM", "Claude Code", "A6api"): "FAIL",
        ("LiteLLM", "OpenCode", "A6api"): "PASS",
        ("LiteLLM", "OpenCode", "RelayRouter"): "FAIL",
    }
    for record in report["records"][:8]:
        assert record["candidate_artifact"].startswith("sha256:")
        assert record["status"] == expected[(record["gateway_candidate"], record["client"], record["provider"])]
        assert any(attempt["status"] == "BLOCKED" for attempt in record["historical_setup_attempts"])
    for record in report["records"]:
        assert all((ROOT / reference).is_file() for reference in record["evidence_references"])
    assert {run["run_id"] for run in report["historical_level2_runs"]} >= {
        "level2-20260930T150128Z",
        "level2-remediation-20260930T200500Z",
        "level2-remediation-20260930T194948Z",
    }


def test_report_preserves_synthetic_and_not_applicable_boundaries():
    report = json.loads(build_reports(ROOT)["docs/poc/compatibility-matrix.json"])
    direct = [record for record in report["records"] if record["gateway_candidate"] is None]
    assert {(record["client"], record["provider"], record["status"]) for record in direct} == {
        ("Codex", "RelayRouter", "NOT_APPLICABLE"),
        ("Claude Code", "RelayRouter", "NOT_APPLICABLE"),
    }
    assert report["phase_2_fixture_controls"]["status"] == "PASS"
    assert len(report["synthetic_controls"]) == 10
    assert all(row["status"] == "PASS" for row in report["synthetic_controls"])
    assert {row["status"] for row in report["scenario_rows"] if row["evidence_type"] == "LIVE_PROVIDER_EVIDENCE"} == {"PASS", "FAIL"}
