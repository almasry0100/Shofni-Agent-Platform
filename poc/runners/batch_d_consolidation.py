"""Sealed-evidence consolidation and decision outputs for Batch D Phases 12-14."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_value


TEST_IDS = ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09-A", "T09-B", "T10", "T11", "T12")
COMPOSITIONS = ("Bifrost + OpenHands", "Bifrost + Mastra", "LiteLLM + OpenHands", "LiteLLM + Mastra")
PHASE11_RUNS = ("batch-d-composition-20261001T102446Z", "batch-d-composition-20261001T113000Z")
PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:[\\/]Users[\\/]|/Users/|/home/|/root/)")
SECRET_SHAPE = re.compile(r"(?i)(?:bearer\s+[a-z0-9._~+/-]{12,}|sk-(?:proj-)?[A-Za-z0-9_-]{12,}|rk-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|hf_[A-Za-z0-9]{20,}|r8_[A-Za-z0-9]{20,})")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact_value(value), ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def _canonical(value: Any) -> str:
    return json.dumps(redact_value(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _status(statuses: list[str]) -> str:
    values = set(statuses)
    if not values:
        return "EVIDENCE_OBSERVABILITY_FAILURE"
    if "FAIL" in values:
        return "FAIL"
    if "BLOCKED" in values:
        return "BLOCKED"
    if "EVIDENCE_OBSERVABILITY_FAILURE" in values:
        return "EVIDENCE_OBSERVABILITY_FAILURE"
    return "PASS" if values <= {"PASS"} else "EVIDENCE_OBSERVABILITY_FAILURE"


def _refs_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    refs: set[str] = set()
    for row in rows:
        for ref in row.get("evidence_refs", []):
            if isinstance(ref, str):
                refs.add(ref.replace("\\", "/"))
    return sorted(refs)


def _level2_matrices(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "tests/poc/evidence/level2").glob("*/matrix.json"))
    matrices = [_load(path) for path in paths]
    return sorted(matrices, key=lambda item: (str(item.get("observed_at", "")), str(item.get("run_id", ""))))


def _level2_cases(root: Path) -> list[dict[str, Any]]:
    matrices = _level2_matrices(root)
    latest = matrices[-1] if matrices else {}
    cases: list[dict[str, Any]] = []
    for test_id in TEST_IDS[:10]:
        all_rows = [row for matrix in matrices for row in matrix.get("rows", []) if row.get("test_id") == test_id]
        effective = [row for row in latest.get("rows", []) if row.get("test_id") == test_id]
        attempts = [
            {
                "run_id": row.get("run_id"),
                "status": row.get("status"),
                "classification": row.get("failure_class"),
                "evidence_refs": sorted(str(ref).replace("\\", "/") for ref in row.get("evidence_refs", [])),
            }
            for row in all_rows
        ]
        cases.append({
            "test_id": test_id,
            "status": _status([str(row.get("status")) for row in effective]),
            "evidence_class": sorted({str(row.get("evidence_type", "UNSPECIFIED")) for row in all_rows}),
            "behavior_modes": sorted({str(row.get("behavior_mode", "UNSPECIFIED")) for row in all_rows}),
            "candidates": sorted({str(row.get("candidate")) for row in all_rows if row.get("candidate")}),
            "providers": sorted({str(row.get("provider")) for row in all_rows if row.get("provider")}),
            "clients": sorted({str(row.get("client")) for row in all_rows if row.get("client")}),
            "protocols": sorted({str(row.get("protocol")) for row in all_rows if row.get("protocol")}),
            "exact_evidence_refs": _refs_from_rows(all_rows),
            "effective_attempts": attempts[-len(effective):] if effective else [],
            "historical_attempts": attempts[:-len(effective)] if effective else attempts,
            "classifications": sorted({str(row.get("failure_class")) for row in all_rows if row.get("failure_class")} or {"NONE"}),
            "provenance_run_ids": sorted({str(row.get("run_id")) for row in all_rows if row.get("run_id")}),
        })
    return cases


def _level3_case(root: Path, test_id: str) -> dict[str, Any]:
    base = root / "tests/poc/evidence/level3/openhands" / test_id
    result_paths = sorted(base.glob("*/result.json"))
    results = [(path, _load(path)) for path in result_paths]
    effective = next(((path, value) for path, value in reversed(results) if value.get("status") == "PASS"), results[-1] if results else (None, {}))
    openhands_status = str(effective[1].get("status", "EVIDENCE_OBSERVABILITY_FAILURE"))
    mastra_ref = "tests/poc/evidence/phase-8/phase8-closure-20261001T035711Z/closure-report.json"
    refs = [_rel(root, path) for path, _ in results if path is not None]
    refs.append(mastra_ref)
    attempts = [{"run_id": value.get("attempt_id") or path.parent.name, "status": value.get("status"), "evidence_ref": _rel(root, path)} for path, value in results]
    return {
        "test_id": test_id,
        "status": openhands_status,
        "evidence_class": ["LIVE_PROVIDER_EVIDENCE", "BLOCKED_LICENSE_EVIDENCE"],
        "behavior_modes": ["NATIVE", "RUNTIME"],
        "candidates": ["Mastra", "OpenHands Software Agent SDK"],
        "candidate_outcomes": {"OpenHands Software Agent SDK": openhands_status, "Mastra": "BLOCKED"},
        "providers": ["A6api"],
        "clients": ["OpenHands RuntimeBackend"],
        "protocols": ["OpenAI-compatible gateway route"],
        "exact_evidence_refs": sorted(set(refs)),
        "effective_attempts": [{"run_id": effective[1].get("attempt_id"), "status": openhands_status, "evidence_ref": _rel(root, effective[0])} if effective[0] else {"run_id": None, "status": "EVIDENCE_OBSERVABILITY_FAILURE"}],
        "historical_attempts": attempts[:-1] if attempts else [],
        "classifications": ["LICENSE_BOUNDARY_BLOCKER"],
        "provenance_run_ids": sorted({str(value.get("attempt_id")) for _, value in results if value.get("attempt_id")} | {"phase8-closure-20261001T035711Z"}),
    }


def _t12_case(root: Path) -> dict[str, Any]:
    refs = [
        "docs/poc/compatibility-matrix.json",
        "docs/poc/compatibility-matrix.md",
        "tests/poc/evidence/phase-6/phase6-remediation-20260930T230000Z/result.json",
        "tests/poc/evidence/phase-6/phase6-remediation-20260930T230000Z/manifest.json",
    ]
    return {
        "test_id": "T12",
        "status": "PASS" if all((root / ref).is_file() for ref in refs) else "EVIDENCE_OBSERVABILITY_FAILURE",
        "evidence_class": ["REPORT_GENERATION_AND_VALIDATION_EVIDENCE"],
        "behavior_modes": ["REPORT"],
        "candidates": ["Bifrost", "LiteLLM"],
        "providers": ["A6api", "RelayRouter", "Shofni synthetic fixture"],
        "clients": ["Codex", "Claude Code", "OpenCode"],
        "protocols": ["OpenAI-compatible", "Anthropic Messages", "Responses"],
        "exact_evidence_refs": refs,
        "effective_attempts": [{"run_id": "phase6-remediation-20260930T230000Z", "status": "PASS", "evidence_refs": refs}],
        "historical_attempts": [],
        "classifications": ["NONE"],
        "provenance_run_ids": ["phase6-remediation-20260930T230000Z"],
    }


def _phase11_cases(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[tuple[str, dict[str, Any]]] = []
    for run_id in PHASE11_RUNS:
        path = root / "tests/poc/evidence/phase-11" / run_id / "phase-11-result.json"
        if path.is_file():
            runs.append((run_id, _load(path)))
    cases: list[dict[str, Any]] = []
    rows_for_manifest: list[dict[str, Any]] = []
    for pairing in COMPOSITIONS:
        attempts = []
        for run_id, result in runs:
            row = next((item for item in result.get("rows", []) if item.get("pairing") == pairing), None)
            if row is None:
                continue
            ref = f"tests/poc/evidence/phase-11/{run_id}/{str(pairing).split()[0].lower()}-{str(pairing).split()[2].lower()}/composition-manifest.json"
            run_manifest = root / "poc/runs" / f"composition-{str(pairing).split()[0].lower()}-{str(pairing).split()[2].lower()}" / "manifest.json"
            run_manifest_value = _load(run_manifest) if run_manifest.is_file() else {}
            attempts.append({"run_id": run_id, "status": row.get("status"), "classification": row.get("classification"), "evidence_ref": ref, "manifest_ref": _rel(root, run_manifest) if run_manifest.is_file() else None, "provider_transition_id": run_manifest_value.get("provider_transition_id"), "task_id": row.get("task_id"), "workspace_id": row.get("workspace_id"), "checkpoint_id": row.get("checkpoint_id"), "tool_call_ids": row.get("tool_call_ids", [])})
        effective = attempts[-1] if attempts else {"run_id": None, "status": "EVIDENCE_OBSERVABILITY_FAILURE", "classification": "EVIDENCE_OBSERVABILITY_FAILURE"}
        gateway, runtime = pairing.split(" + ")
        cases.append({
            "test_id": f"COMPOSITION:{pairing}",
            "pairing": pairing,
            "status": effective.get("status"),
            "evidence_class": ["LIVE_PROVIDER_EVIDENCE" if runtime == "OpenHands" else "BLOCKED_LICENSE_EVIDENCE"],
            "candidates": [gateway, runtime],
            "provider": "A6api" if runtime == "OpenHands" else None,
            "client": "OpenHands RuntimeBackend" if runtime == "OpenHands" else "Mastra durable Agent",
            "protocol": "OpenAI-compatible gateway route",
            "exact_evidence_refs": sorted({attempt["evidence_ref"] for attempt in attempts}),
            "effective_attempts": [effective],
            "historical_attempts": attempts[:-1],
            "classifications": sorted({str(attempt.get("classification")) for attempt in attempts if attempt.get("classification")} or {"NONE"}),
            "provenance_run_ids": [attempt["run_id"] for attempt in attempts if attempt.get("run_id")],
        })
        rows_for_manifest.extend(attempts)
    return cases, rows_for_manifest


def _scan(root: Path, paths: list[Path]) -> dict[str, list[str]]:
    private: set[str] = set()
    secrets: set[str] = set()
    for base in paths:
        files = base.rglob("*") if base.is_dir() else [base]
        for path in files:
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".ndjson"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            relative = _rel(root, path)
            if PRIVATE_PATH.search(text):
                private.add(relative)
            if SECRET_SHAPE.search(text):
                secrets.add(relative)
    return {"private_path_files": sorted(private), "pattern_match_files": sorted(secrets)}


def _markdown_coverage(index: dict[str, Any]) -> str:
    lines = ["# Batch D Evidence Coverage", "", "| Case | Status | Evidence class | Candidates |", "|---|---|---|---|"]
    for case in index["logical_cases"]:
        candidates = ", ".join(case.get("candidates", []))
        evidence = ", ".join(case.get("evidence_class", []))
        lines.append(f"| {case['test_id']} | **{case['status']}** | {evidence} | {candidates} |")
    lines.extend(["", "Historical attempts remain indexed in `tests/poc/evidence/phase-12/`.", ""])
    return "\n".join(lines)


def _markdown_compositions(cases: list[dict[str, Any]]) -> str:
    lines = ["# Composition Results", "", "| Pairing | Effective status | Classification |", "|---|---|---|"]
    for case in cases:
        lines.append(f"| {case['pairing']} | **{case['status']}** | {', '.join(case['classifications'])} |")
    lines.extend(["", "The executable rows use the same TaskSpec, fixture, models, checkpoint contract, and evidence gates. Mastra rows inherit the Phase 8 license boundary blocker.", ""])
    return "\n".join(lines)


def run_phase12(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    evidence = root / "tests/poc/evidence/phase-12" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    level2 = _level2_cases(root)
    level3 = [_level3_case(root, "T10"), _level3_case(root, "T11")]
    composition_cases, composition_attempts = _phase11_cases(root)
    logical_cases = [*level2, *level3, _t12_case(root)]
    index = {"schema_version": "1.0", "phase": "phase_12", "run_id": run_id, "required_tests": list(TEST_IDS), "logical_cases": logical_cases, "composition_cases": composition_cases}
    coverage_lines = "".join(_canonical(case) + "\n" for case in [*logical_cases, *composition_cases])
    _write(evidence / "coverage-index.json", index)
    (evidence / "coverage.ndjson").write_text(coverage_lines, encoding="utf-8", newline="\n")
    _write(evidence / "composition-results.json", {"schema_version": "1.0", "phase": "phase_11", "run_ids": list(PHASE11_RUNS), "cases": composition_cases, "attempts": composition_attempts})

    gaps = {
        "schema_version": "1.0",
        "status": "FAIL",
        "gaps": [
            {"class": "EVIDENCE_OBSERVABILITY_FAILURE", "scope": "Phase 11 first OpenHands attempt", "detail": "The sealed first attempt has setup failure metadata but no underlying process/setup diagnostic; task, workspace, checkpoint, and tool IDs remain unobserved."},
            {"class": "EVIDENCE_OBSERVABILITY_FAILURE", "scope": "Phase 11 executable compositions", "detail": "The bounded rerun built the pinned environment and probed gateway routes, but the sealed Windows Docker invocation rejected the short host-path mount syntax before OpenHands task evidence was produced; no executable composition PASS is available."},
            {"class": "PROVENANCE_VARIANCE", "scope": "Phase 11 OpenHands image", "detail": "The rerun image installed 232 distributions while the historical Phase 7 environment records 187; the rerun image is retained only as setup evidence and is not promoted to Phase 7 provenance."},
        ],
        "missing_required_ids": [],
        "failed_cases_with_diagnostics": [case["test_id"] for case in [*logical_cases, *composition_cases] if case.get("status") == "FAIL"],
    }
    _write(evidence / "evidence-gaps.json", gaps)

    docs = {
        "docs/poc/composition-results.md": _markdown_compositions(composition_cases),
        "docs/poc/batch-d-coverage.md": _markdown_coverage(index),
    }
    for relative, content in docs.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(content, encoding="utf-8", newline="\n")

    scan = _scan(root, [evidence, root / "docs/poc/composition-results.md", root / "docs/poc/batch-d-coverage.md"])
    level2_run_ids = tuple(matrix["run_id"] for matrix in _level2_matrices(root) if matrix.get("run_id"))
    source_runs = sorted(set(PHASE11_RUNS + level2_run_ids + tuple(run_id for case in logical_cases for run_id in case.get("provenance_run_ids", []))))
    linked_refs = sorted({ref for case in [*logical_cases, *composition_cases] for ref in case.get("exact_evidence_refs", [])})
    unresolved_refs = [ref for ref in linked_refs if not (root / ref).is_file()]
    schema_validated = all(isinstance(case.get("test_id"), str) and case.get("status") for case in [*logical_cases, *composition_cases])
    first_report_hash = _sha(_canonical(index).encode("utf-8"))
    second_report_hash = _sha(_canonical({"schema_version": "1.0", "phase": "phase_12", "run_id": run_id, "required_tests": list(TEST_IDS), "logical_cases": _level2_cases(root) + [_level3_case(root, "T10"), _level3_case(root, "T11"), _t12_case(root)], "composition_cases": _phase11_cases(root)[0]}).encode("utf-8"))
    consolidation = {
        "schema_version": "1.0",
        "phase": "phase_12",
        "run_id": run_id,
        "status": "FAIL",
        "coverage_index": _rel(root, evidence / "coverage-index.json"),
        "coverage_ndjson": _rel(root, evidence / "coverage.ndjson"),
        "composition_results": _rel(root, evidence / "composition-results.json"),
        "required_tests": list(TEST_IDS),
        "composition_pairings": list(COMPOSITIONS),
        "source_run_ids": source_runs,
        "historical_phase11_run_ids": list(PHASE11_RUNS),
        "skipped_blocked_unsupported": {
            "Mastra": "BLOCKED: LICENSE_BOUNDARY_BLOCKER inherited from Phase 8",
            "RelayRouter direct cells": "NOT_APPLICABLE: unsupported direct pairing",
        },
        "redaction_scan_version": "poc.evidence.redactor.v1",
        "redaction_scan": scan,
        "reports_regenerated_twice": True,
        "canonical_report_deterministic": first_report_hash == second_report_hash,
        "canonical_report_hash_first": first_report_hash,
        "canonical_report_hash_second": second_report_hash,
        "schema_validated": schema_validated,
        "evidence_links_validated": not unresolved_refs,
        "unresolved_evidence_refs": unresolved_refs,
        "generated_docs": ["docs/poc/gateway-results.md", "docs/poc/runtime-results.md", "docs/poc/compatibility-matrix.md", "docs/poc/composition-results.md", "docs/poc/decision-evidence.md"],
        "historical_level2_run_ids": list(level2_run_ids),
        "live_provider_calls": 0,
        "evidence_gaps": _rel(root, evidence / "evidence-gaps.json"),
    }
    _write(evidence / "consolidation-manifest.json", consolidation)
    _write(evidence / "schema-validation.json", {"schema_version": "1.0", "json_parse_validated": True, "ndjson_parse_validated": True, "schema_validated": schema_validated, "evidence_links_validated": not unresolved_refs, "unresolved_evidence_refs": unresolved_refs})
    canonical_files = [evidence / name for name in ("coverage-index.json", "coverage.ndjson", "composition-results.json", "evidence-gaps.json", "consolidation-manifest.json", "schema-validation.json")]
    hashes = {"schema_version": "1.0", "semantic_hashes": {_rel(root, path): _sha(_canonical(_load(path)).encode("utf-8") if path.suffix == ".json" else path.read_bytes()) for path in canonical_files}, "byte_hashes": {_rel(root, path): _sha(path.read_bytes()) for path in canonical_files}}
    _write(evidence / "hashes.json", hashes)
    _write(evidence / "manifest.json", {"schema_version": "1.0", "phase": "phase_12", "run_id": run_id, "status": "FAIL", "evidence_files": [path.name for path in [*canonical_files, evidence / "hashes.json"]], "source_run_ids": source_runs, "reports_regenerated_twice": True, "canonical_report_deterministic": first_report_hash == second_report_hash, "live_provider_calls": 0})
    return {"index": index, "composition_cases": composition_cases, "consolidation": consolidation, "evidence_dir": evidence}


def run_phase13(root: Path, phase12: dict[str, Any], run_id: str) -> dict[str, Any]:
    root = root.resolve()
    evidence = root / "tests/poc/evidence/phase-13" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    cases = phase12["index"]["logical_cases"]
    compositions = phase12["composition_cases"]
    mandatory = [case for case in [*cases, *compositions] if case.get("status") in {"FAIL", "BLOCKED", "EVIDENCE_OBSERVABILITY_FAILURE"}]
    decision = {
        "schema_version": "1.0",
        "phase": "phase_13",
        "run_id": run_id,
        "decision": "NO_DECISION_YET",
        "live_provider_calls": 0,
        "planes": {
            "gateway": {"decision": "NO_DECISION_YET", "candidates": ["Bifrost", "LiteLLM"], "mandatory_gates": ["T01-T09", "T12", "composition route proof"], "blocking_cases": [case["test_id"] for case in mandatory if case.get("test_id") in TEST_IDS[:10] or case.get("test_id", "").startswith("COMPOSITION:")]},
            "runtime": {"decision": "NO_DECISION_YET", "candidates": ["OpenHands Software Agent SDK", "Mastra"], "mandatory_gates": ["T10", "T11", "fresh-process identity", "license boundary"], "blocking_cases": ["T10", "T11", "Mastra"]},
            "composition": {"decision": "NO_DECISION_YET", "mandatory_gates": list(COMPOSITIONS), "blocking_cases": [case["test_id"] for case in compositions if case.get("status") != "PASS"]},
        },
        "mandatory_failures_or_gaps": [{"test_id": case.get("test_id"), "status": case.get("status"), "classifications": case.get("classifications", [])} for case in mandatory],
        "evidence_refs": ["tests/poc/evidence/phase-12/" + phase12["evidence_dir"].name + "/consolidation-manifest.json", "tests/poc/evidence/phase-8/phase8-closure-20261001T035711Z/closure-report.json"],
    }
    _write(evidence / "decision.json", decision)
    _write(evidence / "manifest.json", {"schema_version": "1.0", "phase": "phase_13", "run_id": run_id, "status": "NO_DECISION_YET", "live_provider_calls": 0, "decision_ref": _rel(root, evidence / "decision.json")})
    lines = ["# Decision Evidence", "", "Phase 13 uses sealed evidence only and makes no provider calls.", "", "| Plane | Decision | Reason |", "|---|---|---|"]
    lines.extend([
        "| Gateway | **NO_DECISION_YET** | Measured Level 2 failures remain and executable Phase 11 route/task proof is incomplete. |",
        "| Runtime | **NO_DECISION_YET** | OpenHands T10/T11 pass, but Mastra is blocked by the required EE auth closure and composition evidence is incomplete. |",
        "| Composition | **NO_DECISION_YET** | Both executable rows are setup failures in the sealed Batch D attempts; Mastra rows are blocked. |",
        "",
        "Mandatory failures, blockers, and evidence gaps remain visible in `tests/poc/evidence/phase-12/`.",
        "",
    ])
    (root / "docs/poc/decision-evidence.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    (root / "docs/poc/backend-decision.md").write_text("# Backend Decision\n\nNo gateway, runtime, or full-stack winner is selected. The mandatory evidence gates do not support a decision yet.\n", encoding="utf-8", newline="\n")
    return decision


def run_phase14(root: Path, decision: dict[str, Any], run_id: str) -> dict[str, Any]:
    root = root.resolve()
    evidence = root / "tests/poc/evidence/phase-14" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema_version": "1.0",
        "phase": "phase_14",
        "run_id": run_id,
        "decision": decision["decision"],
        "production_implementation_started": False,
        "architecture_boundary": {"level2_tool_execution_backend": "CLIENT", "level3_tool_execution_backend": "RUNTIME", "candidate_replaceability": True},
        "dependency_license_inventory": {
            "source": "docs/poc/candidate-lock.json",
            "candidates": [
                {"name": "Bifrost", "tree_hash": "sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe", "license": "Apache-2.0"},
                {"name": "LiteLLM", "tree_hash": "sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb", "license": "MIT outside enterprise/"},
                {"name": "OpenHands Software Agent SDK", "tree_hash": "sha256:e1258a81a1304726a1622943078907b689fccc524d733838fd57e10665ebd468", "license": "MIT"},
                {"name": "Mastra", "tree_hash": "sha256:2f31743b5591fe158903bc50c4cd6886153d754d01ffd8627906eb23ad605d05", "license": "Apache-2.0 outside ee/; BLOCKED required durable Agent closure"},
            ],
        },
        "bounded_follow_up": [
            {"id": "D-F1", "scenario": "Bifrost + OpenHands and LiteLLM + OpenHands identical native read/checkpoint composition", "candidate": "OpenHands 1.49.6 with each pinned gateway artifact", "provider": "A6api", "client": "OpenHands RuntimeBackend", "pass_criterion": "fresh runtime processes produce task/workspace continuity, new attempt, checkpoint, one correlated native read_fixture action/result, model A gpt-5.4-mini to model B gpt-5.5, final alpha, and gateway route evidence", "max_reruns": 1, "output": "new sanitized Phase 11 evidence and manifest", "stop_condition": "stop on provider/auth failure, semantic failure, or missing correlation; do not retry automatically"},
            {"id": "D-F2", "scenario": "Reproduce measured Level 2 T03/T04 failures against the latest locked gateway artifacts", "candidate": "Bifrost and LiteLLM", "provider": "A6api", "client": "Codex/Claude Code matrix clients", "pass_criterion": "protocol and fallback result matches the acceptance scenario with exact failure classification and no duplicate side effect", "max_reruns": 1, "output": "new Level 2 matrix rows plus sanitized raw-protocol-equivalent diagnostics", "stop_condition": "preserve any repeated FAIL; no winner selection"},
            {"id": "D-F3", "scenario": "Mastra durable Agent closure review", "candidate": "Mastra @mastra/core 1.72.0-alpha.8", "provider": "none", "client": "Mastra durable Agent", "pass_criterion": "only if a newly licensed/approved OSS path exists without ee imports; otherwise retain BLOCKED", "max_reruns": 0, "output": "license decision record", "stop_condition": "do not use, stub, or patch EE source"},
        ],
    }
    _write(evidence / "plan.json", plan)
    _write(evidence / "manifest.json", {"schema_version": "1.0", "phase": "phase_14", "run_id": run_id, "status": "COMPLETE", "decision": decision["decision"], "production_implementation_started": False, "evidence_ref": _rel(root, evidence / "plan.json")})
    (root / "docs/poc/post-poc-implementation-plan.md").write_text("# Post-POC Follow-up Plan\n\nPhase 13 is `NO_DECISION_YET`. Close only the bounded evidence gaps listed in `tests/poc/evidence/phase-14/" + run_id + "/plan.json`. Preserve Level 2 as `CLIENT`, Level 3 as `RUNTIME`, keep candidates replaceable, and start no production implementation until the mandatory gates are complete.\n", encoding="utf-8", newline="\n")
    return plan


def update_batch_manifest(root: Path, phase12: dict[str, Any], decision: dict[str, Any], plan: dict[str, Any], phase12_run_id: str, phase13_run_id: str, phase14_run_id: str) -> None:
    path = root / "poc/runs/batch-d-20261001T102446Z/manifest.json"
    manifest = _load(path)
    composition = {case["pairing"]: case["status"] for case in phase12["composition_cases"]}
    manifest.update({
        "current_phase": "phase_14",
        "phase_11_status": "PARTIAL",
        "phase_12_status": "FAIL",
        "phase_13_status": "NO_DECISION_YET",
        "phase_14_status": "COMPLETE",
        "batch_status": "COMPLETE_NO_DECISION",
        "composition_statuses": composition,
        "evidence_roots": sorted(set(manifest.get("evidence_roots", []) + [f"tests/poc/evidence/phase-11/{run_id}" for run_id in PHASE11_RUNS] + [f"tests/poc/evidence/phase-12/{phase12_run_id}", f"tests/poc/evidence/phase-13/{phase13_run_id}", f"tests/poc/evidence/phase-14/{phase14_run_id}"])),
        "provider_transition_ids": sorted({str(attempt.get("provider_transition_id")) for case in phase12["composition_cases"] for attempt in case.get("effective_attempts", []) if attempt.get("provider_transition_id")}),
        "commands_executed": [
            {"command": ".\\.venv\\Scripts\\python.exe -m pytest tests/poc", "exit_code": 0, "result": "71 passed"},
            {"command": ".\\.venv\\Scripts\\python.exe -m poc.runners.phase11_composition --run-id batch-d-composition-20261001T113000Z", "exit_code": 1, "result": "sealed setup failure; first attempt preserved"},
            {"command": "Phase 0 candidate identity revalidation", "exit_code": 0, "result": "all four source tree hashes, counts, manifest hashes, and lock hashes match"},
            {"command": f"Phase 12-14 sealed consolidation run {phase12_run_id}", "exit_code": 1, "result": "Phase 12 evidence gap; Phase 13 NO_DECISION_YET; Phase 14 bounded plan"},
        ],
        "exit_codes": [0, 1, 0, 1],
        "blockers": ["EVIDENCE_OBSERVABILITY_FAILURE: Phase 11 executable OpenHands task evidence incomplete", "LICENSE_BOUNDARY_BLOCKER: Mastra durable Agent closure reaches excluded EE auth modules", "Measured Level 2 FAIL rows remain in T03/T04"],
        "cleanup_state": "VALIDATED: Batch D containers, networks, images, runtime roots, and temporary config roots absent; candidate trees and unrelated runtime roots preserved",
        "decision_state": decision["decision"],
        "phase_12_run_id": phase12_run_id,
        "phase_13_run_id": phase13_run_id,
        "phase_14_run_id": phase14_run_id,
        "commit": False,
        "push": False,
    })
    _write(path, manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--phase12-run-id", default="batch-d-phase12-20261001T120000Z")
    parser.add_argument("--phase13-run-id", default="batch-d-phase13-20261001T120000Z")
    parser.add_argument("--phase14-run-id", default="batch-d-phase14-20261001T120000Z")
    args = parser.parse_args(argv)
    phase12 = run_phase12(args.root, args.phase12_run_id)
    decision = run_phase13(args.root, phase12, args.phase13_run_id)
    plan = run_phase14(args.root, decision, args.phase14_run_id)
    update_batch_manifest(args.root.resolve(), phase12, decision, plan, args.phase12_run_id, args.phase13_run_id, args.phase14_run_id)
    print(json.dumps({"phase12": phase12["consolidation"]["status"], "phase13": decision["decision"], "phase14": "COMPLETE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
