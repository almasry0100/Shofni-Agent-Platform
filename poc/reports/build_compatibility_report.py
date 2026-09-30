from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CAPABILITIES = (
    "chat",
    "streaming",
    "native_tools",
    "emulated_tools",
    "tool_result",
    "sequential_continuation",
    "parallel_tools",
    "responses",
    "anthropic_messages",
    "chat_completions",
    "error_normalization",
    "fallback_eligibility",
)
PAIRINGS = (
    ("Codex", "0.159.0", "A6api", "Responses"),
    ("Claude Code", "2.1.278", "A6api", "Anthropic Messages"),
    ("OpenCode", "1.18.33", "A6api", "Chat Completions"),
    ("OpenCode", "1.18.33", "RelayRouter", "Chat Completions"),
)
CAPABILITY_TESTS = {
    "chat": ("T01", "T03", "T04"),
    "streaming": ("T08",),
    "native_tools": ("T01", "T03", "T07"),
    "emulated_tools": ("T04",),
    "tool_result": ("T07",),
    "sequential_continuation": ("T07",),
    "parallel_tools": (),
    "responses": ("T01",),
    "anthropic_messages": ("T03",),
    "chat_completions": ("T04", "T07", "T08"),
    "error_normalization": (),
    "fallback_eligibility": (),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _evidence_files(root: Path, base: Path) -> list[str]:
    if base.is_file():
        return [_relative(root, base)]
    return [
        _relative(root, path)
        for name in ("result.json", "provenance.json", "manifest.json")
        for path in [base / name]
        if path.is_file()
    ]


def _setup_history(root: Path, remediation: dict[str, Any], candidate: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for attempt in remediation["attempts"][candidate.lower()]["attempts"]:
        base = root / attempt["evidence_path"]
        history.append(
            {
                "attempt_id": attempt["attempt_id"],
                "status": attempt["status"],
                "historical": bool(attempt.get("historical", False)),
                "evidence_references": _evidence_files(root, base),
            }
        )
    return history


def _level2_runs(root: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for matrix_path in sorted((root / "tests/poc/evidence/level2").glob("*/matrix.json")):
        matrix = _read_json(matrix_path)
        manifest_path = matrix_path.with_name("manifest.json")
        runs.append(
            {
                "run_id": matrix["run_id"],
                "status": matrix["status"],
                "observed_at": matrix["observed_at"],
                "matrix": matrix,
                "evidence_references": [
                    _relative(root, matrix_path),
                    *([_relative(root, manifest_path)] if manifest_path.is_file() else []),
                ],
            }
        )
    if not runs:
        raise ValueError("no sealed Level 2 matrices found")
    return sorted(runs, key=lambda run: (run["observed_at"], run["run_id"]))


def _latest_setup_path(root: Path, remediation: dict[str, Any], candidate: str) -> Path:
    attempt_id = remediation["attempts"][candidate.lower()]["latest_attempt_id"]
    for attempt in remediation["attempts"][candidate.lower()]["attempts"]:
        if attempt["attempt_id"] == attempt_id:
            return root / attempt["evidence_path"]
    raise ValueError(f"latest setup attempt is missing: {candidate}/{attempt_id}")


def _artifact_identity(root: Path, remediation: dict[str, Any], candidate: str) -> tuple[str | None, dict[str, Any]]:
    base = _latest_setup_path(root, remediation, candidate)
    provenance_path = base / "provenance.json"
    provenance = _read_json(provenance_path) if provenance_path.is_file() else {}
    if candidate == "Bifrost":
        digest = provenance.get("artifact_sha256")
        identity = {
            "artifact_sha256": digest,
            "candidate_tree_hash": provenance.get("candidate_tree_hash"),
            "go_toolchain_image": provenance.get("go_toolchain_image"),
        }
    else:
        digest = provenance.get("runtime_image_digest") or provenance.get("wheel_sha256")
        identity = {
            "runtime_image_digest": provenance.get("runtime_image_digest"),
            "wheel_sha256": provenance.get("wheel_sha256"),
            "candidate_tree_hash": provenance.get("candidate_tree_hash"),
            "python_base_image": provenance.get("python_base_image"),
            "rust_build_image": provenance.get("rust_build_image"),
            "uv_image": provenance.get("uv_image"),
        }
    return digest, {key: value for key, value in identity.items() if value is not None}


def _pair_rows(matrix: dict[str, Any], candidate: str, client: str, provider: str) -> list[dict[str, Any]]:
    return [
        row
        for row in matrix["rows"]
        if row.get("candidate") == candidate
        and row.get("client") == client
        and row.get("provider") == provider
        and row.get("evidence_type") == "LIVE_PROVIDER_EVIDENCE"
    ]


def _state(rows: list[dict[str, Any]]) -> str:
    statuses = {row.get("status") for row in rows}
    if not rows:
        return "UNVERIFIED"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "FAIL" in statuses:
        return "FAIL"
    if statuses == {"PASS"}:
        return "PASS"
    return "UNVERIFIED"


def _failure_class(rows: list[dict[str, Any]]) -> str | None:
    failures = sorted({row["failure_class"] for row in rows if row.get("failure_class")})
    if not failures:
        return None
    return failures[0] if len(failures) == 1 else "MIXED_FAILURES"


def _behavior(rows: list[dict[str, Any]]) -> str:
    modes = sorted({row.get("behavior_mode") for row in rows if row.get("behavior_mode")})
    if not modes:
        return "UNVERIFIED"
    return modes[0] if len(modes) == 1 else "MIXED"


def _capability(name: str, rows: list[dict[str, Any]]) -> dict[str, str]:
    selected = [row for row in rows if row.get("test_id") in CAPABILITY_TESTS[name]]
    probed = _state(selected)
    behavior = _behavior(selected)
    effective = probed
    if probed == "PASS" and name in {
        "native_tools",
        "streaming",
        "sequential_continuation",
        "chat",
        "responses",
        "anthropic_messages",
        "chat_completions",
    }:
        effective = behavior if behavior in {"NATIVE", "EMULATED"} else "PASS"
    if probed == "PASS" and name == "emulated_tools":
        effective = "EMULATED" if behavior == "EMULATED" else "UNVERIFIED"
    return {
        "declared": "UNVERIFIED",
        "probed": probed,
        "observed": probed,
        "effective": effective,
        "behavior": behavior,
    }


def _pairing_history_refs(
    runs: list[dict[str, Any]],
    candidate: str,
    client: str,
    provider: str,
) -> list[str]:
    refs: set[str] = set()
    for run in runs:
        rows = _pair_rows(run["matrix"], candidate, client, provider)
        if rows:
            refs.update(run["evidence_references"])
            for row in rows:
                refs.update(row.get("evidence_refs", []))
    return sorted(refs)


def _record(
    root: Path,
    remediation: dict[str, Any],
    runs: list[dict[str, Any]],
    latest_matrix: dict[str, Any],
    lock_lookup: dict[str, dict[str, Any]],
    candidate: str,
    client: str,
    client_version: str,
    provider: str,
    protocol: str,
) -> dict[str, Any]:
    rows = _pair_rows(latest_matrix, candidate, client, provider)
    setup_history = _setup_history(root, remediation, candidate)
    setup_refs = sorted({ref for item in setup_history for ref in item["evidence_references"]})
    refs = sorted({*setup_refs, *_pairing_history_refs(runs, candidate, client, provider)})
    lineage_path = root / "tests/poc/evidence/phase-4/historical-sanitization-lineage.json"
    if candidate == "LiteLLM" and lineage_path.is_file():
        refs.append(_relative(root, lineage_path))
        refs = sorted(set(refs))
    artifact, artifact_identity = _artifact_identity(root, remediation, candidate)
    source = lock_lookup[candidate]
    model_ids = sorted({str(row.get("model_id")) for row in rows if row.get("model_id")})
    return {
        "gateway_candidate": candidate,
        "candidate_source": source["sanitized_local_path"],
        "candidate_source_tree_hash": source["tree_hash"],
        "candidate_artifact": artifact,
        "candidate_artifact_identity": artifact_identity,
        "client": client,
        "client_version": client_version,
        "protocol": protocol,
        "provider": provider,
        "model_id": model_ids[0] if len(model_ids) == 1 else model_ids or "UNVERIFIED",
        "observed_at": latest_matrix["observed_at"],
        "status": _state(rows),
        "setup_status": remediation["attempts"][candidate.lower()]["status"],
        "failure_class": _failure_class(rows),
        "capabilities": {name: _capability(name, rows) for name in CAPABILITIES},
        "evidence_types": sorted({"SOURCE_INSPECTION_EVIDENCE", *(row.get("evidence_type", "") for row in rows)}),
        "evidence_references": refs,
        "historical_setup_attempts": setup_history,
        "observed_failures": [
            {
                "test_id": row["test_id"],
                "repetition": row.get("repetition"),
                "failure_class": row.get("failure_class"),
                "status": row.get("status"),
            }
            for row in rows
            if row.get("status") == "FAIL"
        ],
    }


def build_reports(root: Path) -> dict[str, str]:
    root = root.resolve()
    remediation_path = root / "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json"
    original_manifest_path = root / "poc/runs/batch-b-20260930T150128Z/manifest.json"
    lock_path = root / "docs/poc/candidate-lock.json"
    remediation = _read_json(remediation_path)
    original_manifest = _read_json(original_manifest_path)
    lock = _read_json(lock_path)
    runs = _level2_runs(root)
    latest = runs[-1]
    latest_matrix = latest["matrix"]
    candidate_lookup = {entry["candidate_name"]: entry for entry in lock["candidates"]}

    records: list[dict[str, Any]] = []
    for candidate in ("Bifrost", "LiteLLM"):
        for client, client_version, provider, protocol in PAIRINGS:
            records.append(
                _record(
                    root,
                    remediation,
                    runs,
                    latest_matrix,
                    candidate_lookup,
                    candidate,
                    client,
                    client_version,
                    provider,
                    protocol,
                )
            )
    records.extend(
        {
            "gateway_candidate": None,
            "candidate_source": None,
            "candidate_source_tree_hash": None,
            "candidate_artifact": None,
            "candidate_artifact_identity": {},
            "client": pairing["client"],
            "client_version": pairing["client_version"],
            "protocol": "Direct client/provider pairing",
            "provider": pairing["provider"],
            "model_id": "NOT_APPLICABLE",
            "observed_at": latest_matrix["observed_at"],
            "status": "NOT_APPLICABLE",
            "setup_status": "NOT_APPLICABLE",
            "failure_class": None,
            "capabilities": {name: "NOT_APPLICABLE" for name in CAPABILITIES},
            "evidence_types": ["SOURCE_INSPECTION_EVIDENCE"],
            "evidence_references": [pairing["evidence_ref"]],
            "reason": pairing["reason"],
        }
        for pairing in latest_matrix["not_applicable_pairings"]
    )

    for record in records:
        for reference in record["evidence_references"]:
            if not (root / reference).is_file():
                raise ValueError(f"missing evidence reference: {reference}")

    setup_history = {
        candidate: _setup_history(root, remediation, candidate)
        for candidate in ("Bifrost", "LiteLLM")
    }
    historical_level2_runs = [
        {
            "run_id": run["run_id"],
            "status": run["status"],
            "observed_at": run["observed_at"],
            "evidence_references": run["evidence_references"],
        }
        for run in runs
    ]
    report = {
        "schema_version": "1.1",
        "report_id": remediation["remediation_run_id"],
        "original_batch_run_id": original_manifest["run_id"],
        "observed_at": latest_matrix["observed_at"],
        "phase_3_status": remediation["attempts"]["bifrost"]["status"],
        "phase_4_status": remediation["attempts"]["litellm"]["status"],
        "phase_5_status": latest_matrix["status"],
        "candidate_decision": "NONE",
        "records": records,
        "scenario_rows": latest_matrix["rows"],
        "synthetic_controls": [
            row for row in latest_matrix["rows"] if row.get("evidence_type") == "SYNTHETIC_FIXTURE_EVIDENCE"
        ],
        "phase_2_fixture_controls": latest_matrix["phase_2_fixture_controls"],
        "historical_setup_attempts": setup_history,
        "historical_level2_runs": historical_level2_runs,
        "historical_sanitization_lineage": "tests/poc/evidence/phase-4/historical-sanitization-lineage.json"
        if (root / "tests/poc/evidence/phase-4/historical-sanitization-lineage.json").is_file()
        else None,
        "original_batch_manifest": "poc/runs/batch-b-20260930T150128Z/manifest.json",
        "remediation_manifest": "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json",
    }

    markdown = [
        "# Level 2 Compatibility Matrix",
        "",
        f"Observed at: {latest_matrix['observed_at']}",
        "",
        "This report uses the newest validated setup and Level 2 observations as the current state. Earlier BLOCKED and FAIL attempts remain listed in the evidence references and history fields. No gateway winner is selected.",
        "",
        "| Gateway | Client | Provider | Protocol | Status | Failure | Artifact |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in records:
        markdown.append(
            f"| {record['gateway_candidate'] or 'Direct'} | {record['client']} | {record['provider']} | {record['protocol']} | {record['status']} | {record['failure_class'] or ''} | {record['candidate_artifact'] or ''} |"
        )
    markdown.extend(
        [
            "",
            f"Current setup states: Bifrost `{report['phase_3_status']}`, LiteLLM `{report['phase_4_status']}`. Current Phase 5 status is `{report['phase_5_status']}`. Synthetic controls remain separate from live candidate execution.",
            "",
            "Historical setup attempts and all sealed Level 2 run matrices are retained in `historical_setup_attempts` and `historical_level2_runs`.",
            "",
        ]
    )

    gateway_lines = [
        "# Gateway Results",
        "",
        "This report records candidate-specific evidence independently and does not rank candidates or select a winner.",
        "",
    ]
    for candidate in ("Bifrost", "LiteLLM"):
        source = candidate_lookup[candidate]
        setup = remediation["attempts"][candidate.lower()]
        artifact, identity = _artifact_identity(root, remediation, candidate)
        attempt_summary = ", ".join(
            f"{item['attempt_id']}={item['status']}"
            for item in _setup_history(root, remediation, candidate)
        )
        gateway_lines.extend(
            [
                f"## {candidate}",
                "",
                f"- Current setup: **{setup['status']}**; current artifact: `{artifact or 'UNVERIFIED'}`.",
                f"- Source identity: `{source['tree_hash']}` ({source['hash_exclusions']['included_file_count']} included files).",
                f"- Artifact identity: `{json.dumps(identity, sort_keys=True)}`.",
                f"- Historical setup attempts: {attempt_summary}.",
                f"- Current live Phase 5 observations: see `{latest['run_id']}`; current report status is `{report['phase_5_status']}`.",
                f"- License boundary: {source['license']}",
                "",
            ]
        )
    gateway_lines.extend(
        [
            "## Operational observations",
            "",
            "The current run used three repetitions per authorized live pairing. Cleanup evidence records container removal, network removal, port release, and temporary configuration removal. No secret values are persisted.",
            "",
            "Phase 2 synthetic fixture controls are reported separately and do not establish gateway support.",
            "",
        ]
    )
    return {
        "docs/poc/compatibility-matrix.json": _canonical_json(report),
        "docs/poc/compatibility-matrix.md": "\n".join(markdown),
        "docs/poc/gateway-results.md": "\n".join(gateway_lines),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    for relative_path, content in build_reports(args.root).items():
        destination = args.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
