from __future__ import annotations

import pytest

from poc.evidence.resolution import ResolutionEvidenceError, resolution_record
from poc.evidence.resolution_manifest import ResolutionManifestError, validate_resolution_manifest
from poc.evidence.taxonomy import ResolutionClass


def test_external_provider_block_requires_candidate_not_reached() -> None:
    record = resolution_record(
        result_status=ResolutionClass.BLOCKED,
        classification=ResolutionClass.EXTERNAL_PROVIDER_BLOCKED,
        candidate_reached=False,
        provider_reached=False,
        client_reached=True,
        candidate="Bifrost",
        provider="RelayRouter",
        client="OpenCode",
        test_id="T04",
        evidence_refs=("tests/poc/evidence/resolution/example/t04.json",),
    )
    assert record["candidate_reached"] is False

    with pytest.raises(ResolutionEvidenceError, match="candidate_reached=false"):
        resolution_record(
            result_status=ResolutionClass.BLOCKED,
            classification=ResolutionClass.EXTERNAL_PROVIDER_BLOCKED,
            candidate_reached=True,
            provider_reached=True,
            client_reached=True,
            evidence_refs=("evidence.json",),
        )


def test_resolution_pass_rejects_unrelated_failure_classification() -> None:
    with pytest.raises(ResolutionEvidenceError, match="PASS status"):
        resolution_record(
            result_status=ResolutionClass.PASS,
            classification=ResolutionClass.SETUP_FAILURE,
            candidate_reached=True,
            provider_reached=True,
            client_reached=True,
            evidence_refs=("evidence.json",),
        )


def test_manifest_requires_all_resolution_phases_and_candidates() -> None:
    base = {
        "schema_version": "1.0",
        "run_id": "resolution-example",
        "resolution_plan_sha256": "a" * 64,
        "resolution_plan_tracking_state": "UNTRACKED",
        "starting_repository": {"branch": "main", "head": "abc"},
        "candidate_identities": [{"candidate": name} for name in ("Bifrost", "LiteLLM", "OpenHands", "Mastra")],
        "phases": {f"R{i}": {"status": "PENDING"} for i in range(10)},
        "decision": {},
        "cleanup": {},
        "commit": False,
        "push": False,
    }
    validate_resolution_manifest(base)
    invalid = dict(base)
    invalid["phases"] = {"R0": {"status": "PASS"}}
    with pytest.raises(ResolutionManifestError, match="R0 through R9"):
        validate_resolution_manifest(invalid)
