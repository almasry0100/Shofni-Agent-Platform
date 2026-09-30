from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.reports.build_compatibility_report import build_reports


REPORT_FILES = (
    "docs/poc/compatibility-matrix.json",
    "docs/poc/compatibility-matrix.md",
    "docs/poc/gateway-results.md",
)
REQUIRED_TESTS = {"T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09-A", "T09-B"}
_PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:[\\/]Users[\\/]|/Users/|/home/|/root/)")
_SECRET_SHAPES = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{12,}"),
    re.compile(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{12,}|rk-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|hf_[A-Za-z0-9]{20,}|r8_[A-Za-z0-9]{20,})\b"),
)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _semantic_hash(relative_path: str, content: str) -> str:
    if relative_path.endswith(".json"):
        parsed = json.loads(content)
        canonical = json.dumps(parsed, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return _sha256(canonical.encode("utf-8"))
    return _sha256(content.replace("\r\n", "\n").encode("utf-8"))


def _write_reports(root: Path, reports: dict[str, str]) -> None:
    for relative_path, content in reports.items():
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")


def _next_run_id(root: Path) -> str:
    stem = "phase6-remediation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = stem
    suffix = 1
    while (root / "tests/poc/evidence/phase-6" / candidate).exists():
        candidate = f"{stem}-{suffix:02d}"
        suffix += 1
    return candidate


def _level2_matrices(root: Path) -> list[dict[str, Any]]:
    matrices = []
    for matrix_path in sorted((root / "tests/poc/evidence/level2").glob("*/matrix.json")):
        matrices.append(json.loads(matrix_path.read_text(encoding="utf-8")))
    if not matrices:
        raise ValueError("no Level 2 matrices found")
    return sorted(matrices, key=lambda value: (value["observed_at"], value["run_id"]))


def _hygiene_scan(root: Path, paths: list[Path]) -> tuple[list[str], list[str]]:
    private_paths: set[str] = set()
    secret_files: set[str] = set()
    for base in paths:
        candidates = base.rglob("*") if base.is_dir() else [base]
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".ndjson"}:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            relative = path.relative_to(root).as_posix()
            if _PRIVATE_PATH.search(content):
                private_paths.add(relative)
            if any(pattern.search(content) for pattern in _SECRET_SHAPES):
                secret_files.add(relative)
    return sorted(private_paths), sorted(secret_files)


def run_phase6(root: Path, run_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    run_id = run_id or _next_run_id(root)
    evidence_dir = root / "tests/poc/evidence/phase-6" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)

    first = build_reports(root)
    _write_reports(root, first)
    second = build_reports(root)
    _write_reports(root, second)
    if first != second:
        raise ValueError("report generation is not deterministic")

    report = json.loads((root / "docs/poc/compatibility-matrix.json").read_text(encoding="utf-8"))
    matrices = _level2_matrices(root)
    latest_matrix = matrices[-1]
    all_references = [
        reference
        for record in report["records"]
        for reference in record["evidence_references"]
    ]
    evidence_references_validated = all((root / reference).is_file() for reference in all_references)
    json_parse_validated = True
    for reference in all_references:
        if reference.endswith(".json"):
            json.loads((root / reference).read_text(encoding="utf-8"))
    observed_tests = {row["test_id"] for row in report["scenario_rows"]}
    required_t01_t09_states_present = REQUIRED_TESTS <= observed_tests
    unsupported_pairings_not_applicable = all(
        record["status"] == "NOT_APPLICABLE"
        for record in report["records"]
        if record["gateway_candidate"] is None
    )
    synthetic_evidence_separate = all(
        row.get("candidate_execution") is False
        for row in report["synthetic_controls"]
    ) and all(
        row.get("evidence_type") == "LIVE_PROVIDER_EVIDENCE"
        for row in report["scenario_rows"]
        if row.get("candidate_execution") is True
    )
    report_hashes = {
        relative: _sha256((root / relative).read_bytes())
        for relative in REPORT_FILES
    }
    semantic_hashes = {
        relative: _semantic_hash(relative, first[relative])
        for relative in REPORT_FILES
    }
    new_private_paths, new_secret_files = _hygiene_scan(
        root,
        [
            root / "docs/poc/compatibility-matrix.json",
            root / "docs/poc/compatibility-matrix.md",
            root / "docs/poc/gateway-results.md",
            root / "tests/poc/evidence/level2",
            root / "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json",
        ],
    )
    historical_private_paths, historical_secret_files = _hygiene_scan(
        root,
        [root / "tests/poc/evidence/phase-4", root / "tests/poc/evidence/phase-3"],
    )
    result = {
        "phase": "phase_6",
        "run_id": run_id,
        "batch_run_id": report["report_id"],
        "observed_at": report["observed_at"],
        "status": "PASS" if evidence_references_validated and json_parse_validated and required_t01_t09_states_present and unsupported_pairings_not_applicable and synthetic_evidence_separate else "FAIL",
        "candidate_decision": report["candidate_decision"],
        "reports_deterministic": first == second,
        "evidence_references_validated": evidence_references_validated,
        "json_parse_validated": json_parse_validated,
        "required_t01_t09_states_present": required_t01_t09_states_present,
        "unsupported_pairings_not_applicable": unsupported_pairings_not_applicable,
        "synthetic_evidence_separate_from_live": synthetic_evidence_separate,
        "new_output_private_paths": new_private_paths,
        "new_output_secret_shape_files": new_secret_files,
        "historical_immutable_private_path_files": historical_private_paths,
        "historical_secret_shape_files": historical_secret_files,
        "historical_setup_attempts_preserved": all(
            any(item["status"] == "BLOCKED" for item in history)
            for history in report["historical_setup_attempts"].values()
        ),
        "historical_level2_runs": [run["run_id"] for run in report["historical_level2_runs"]],
        "latest_level2_run_id": latest_matrix["run_id"],
        "candidate_scenario_statuses": {
            status: sum(
                1
                for row in report["scenario_rows"]
                if row.get("candidate_execution") and row.get("status") == status
            )
            for status in ("PASS", "FAIL", "BLOCKED")
        },
        "live_provider_requests": latest_matrix["live_provider_requests"],
        "report_hashes": report_hashes,
        "semantic_hashes": semantic_hashes,
    }
    (evidence_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "phase": "phase_6",
        "run_id": run_id,
        "batch_run_id": report["report_id"],
        "status": result["status"],
        "evidence_type": "REPORT_GENERATION_AND_VALIDATION_EVIDENCE",
        "generated_files": [*REPORT_FILES, "poc/reports/build_compatibility_report.py"],
        "source_evidence": [
            "poc/runs/batch-b-20260930T150128Z/manifest.json",
            "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json",
            "tests/poc/evidence/phase-4/historical-sanitization-lineage.json",
            *[f"tests/poc/evidence/level2/{run_id}/matrix.json" for run_id in result["historical_level2_runs"]],
        ],
        "report_hashes": report_hashes,
        "semantic_hashes": semantic_hashes,
        "evidence_files": ["result.json", "manifest.json"],
    }
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    remediation_path = root / "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json"
    remediation = json.loads(remediation_path.read_text(encoding="utf-8"))
    new_phase5_runs = [
        matrix["run_id"]
        for matrix in matrices
        if matrix["run_id"] != "level2-20260930T150128Z"
    ]
    remediation["new_phase_5_runs"] = new_phase5_runs
    remediation["live_provider_run_ids"] = [
        matrix["run_id"]
        for matrix in matrices
        if matrix["run_id"] != "level2-20260930T150128Z" and matrix.get("candidate_executions")
    ]
    remediation["latest_phase_5_run_id"] = latest_matrix["run_id"]
    remediation["phase_6_status"] = result["status"]
    remediation["report_regeneration"] = {
        "status": result["status"],
        "run_id": run_id,
        "reports_deterministic": result["reports_deterministic"],
        "semantic_hashes": semantic_hashes,
        "evidence": f"tests/poc/evidence/phase-6/{run_id}",
    }
    remediation["status"] = "PARTIAL" if result["status"] == "PASS" and latest_matrix["status"] == "PARTIAL" else result["status"]
    remediation_path.write_text(
        json.dumps(remediation, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate Batch B Phase 6 reports.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    result = run_phase6(args.root, args.run_id)
    print(json.dumps({"run_id": result["run_id"], "status": result["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
