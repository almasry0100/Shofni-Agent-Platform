from __future__ import annotations

import json
import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


GATEWAYS = ("Bifrost", "LiteLLM")
TEST_ORDER = ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09-A", "T09-B", "T12")
PROTOCOLS = {
    ("Codex", "A6api"): "Responses",
    ("Claude Code", "A6api"): "Anthropic Messages",
    ("OpenCode", "A6api"): "Chat Completions",
    ("OpenCode", "RelayRouter"): "Chat Completions",
    ("candidate-neutral fixture harness", "Shofni synthetic fixture"): "candidate-neutral fixture contract",
}
RELAYROUTER_TESTS = {"T04", "T07", "T08"}
FIXTURE_TESTS = {"T02", "T05", "T06", "T09-A", "T09-B"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _rows_by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("candidate") not in GATEWAYS or row.get("test_id") not in TEST_ORDER[:-1]:
            continue
        test_id = row["test_id"]
        provider = row.get("provider")
        client = row.get("client")
        evidence_type = row.get("evidence_type")
        if test_id in FIXTURE_TESTS:
            applicable = (
                provider == "Shofni synthetic fixture"
                and client == "candidate-neutral fixture harness"
                and evidence_type == "SYNTHETIC_FIXTURE_EVIDENCE"
            )
        elif test_id == "T01":
            applicable = provider == "A6api" and client == "Codex" and evidence_type == "LIVE_PROVIDER_EVIDENCE"
        elif test_id == "T03":
            applicable = provider == "A6api" and client == "Claude Code" and evidence_type == "LIVE_PROVIDER_EVIDENCE"
        else:
            applicable = (
                test_id in {"T04", "T07", "T08"}
                and provider in {"A6api", "RelayRouter"}
                and client == "OpenCode"
                and evidence_type == "LIVE_PROVIDER_EVIDENCE"
            )
        if not applicable:
            continue
        key = (
            row["candidate"],
            row["test_id"],
            provider,
            client,
            evidence_type,
        )
        grouped[key].append(row)
    return grouped


def _attempt_from_matrix(row: dict[str, Any], matrix_ref: str) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id"),
        "test_id": row["test_id"],
        "repetition": row.get("repetition"),
        "status": row.get("status", "UNVERIFIED"),
        "failure_class": row.get("failure_class"),
        "candidate_execution": row.get("candidate_execution", False),
        "behavior_mode": row.get("behavior_mode", "UNVERIFIED"),
        "evidence_type": row.get("evidence_type", "UNVERIFIED"),
        "evidence_refs": sorted(set(row.get("evidence_refs", []))),
        "source_matrix_ref": matrix_ref,
    }


def _attempt_identity(attempt: dict[str, Any]) -> tuple[Any, ...]:
    return (
        attempt.get("run_id"),
        attempt.get("test_id"),
        attempt.get("repetition"),
        attempt.get("status"),
        attempt.get("failure_class"),
        tuple(attempt.get("evidence_refs", [])),
    )


def _aggregate_status(rows: list[dict[str, Any]]) -> str:
    statuses = {row.get("status") for row in rows}
    if not rows:
        return "UNVERIFIED"
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if statuses == {"PASS"}:
        return "PASS"
    return "UNVERIFIED"


def _protocol(client: str, provider: str) -> str:
    return PROTOCOLS.get((client, provider), "UNVERIFIED")


def _distinct(values: list[Any]) -> list[Any]:
    return sorted({value for value in values if value is not None}, key=str)


def _readiness_status(rows: list[dict[str, Any]]) -> str:
    statuses = {row["current_effective_result"]["status"] for row in rows}
    if not rows:
        return "UNVERIFIED"
    if any(row["externally_blocked"] for row in rows) and all(
        row["externally_blocked"] or row["current_effective_result"]["status"] == "PASS"
        for row in rows
    ):
        return "BLOCKED_EXTERNAL_PROVIDER"
    if "FAIL" in statuses:
        return "FAILED_COMPATIBILITY"
    if "BLOCKED" in statuses or "UNVERIFIED" in statuses:
        return "PARTIAL"
    if statuses == {"PASS"}:
        return "READY"
    return "PARTIAL"


def _capability_summary(
    rows: list[dict[str, Any]],
    candidate: str,
    test_ids: set[str],
    providers: set[str],
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if row["candidate"] == candidate
        and row["test_id"] in test_ids
        and row["provider"] in providers
        and row["live_vs_fixture"] == "LIVE"
    ]
    statuses = {row["current_effective_result"]["status"] for row in selected}
    if not selected:
        status = "UNVERIFIED"
    elif "BLOCKED" in statuses and all(value in {"BLOCKED", "PASS"} for value in statuses):
        status = "PARTIAL" if "PASS" in statuses else "BLOCKED_EXTERNAL_PROVIDER"
    elif "FAIL" in statuses and "PASS" in statuses:
        status = "PARTIAL"
    elif "FAIL" in statuses:
        status = "FAILED_COMPATIBILITY"
    elif statuses == {"PASS"}:
        status = "READY"
    else:
        status = "PARTIAL"
    return {
        "status": status,
        "observations": [
            {
                "test_id": row["test_id"],
                "provider": row["provider"],
                "client": row["client"],
                "status": row["current_effective_result"]["status"],
                "candidate_attribution": row["candidate_attribution"],
                "evidence_refs": row["evidence_refs"],
            }
            for row in selected
        ],
        "evidence_refs": sorted({ref for row in selected for ref in row["evidence_refs"]}),
    }


def _t12(rows: list[dict[str, Any]], run_id: str, observed_at: str) -> dict[str, Any]:
    eligibility: dict[str, dict[str, Any]] = {}
    for candidate in GATEWAYS:
        candidate_rows = [row for row in rows if row["candidate"] == candidate and row["test_id"] != "T12"]
        failures = [
            row
            for row in candidate_rows
            if row["candidate_controlled"] and row["current_effective_result"]["status"] == "FAIL"
        ]
        other_blockers = [
            row
            for row in candidate_rows
            if not row["externally_blocked"]
            and row["live_vs_fixture"] == "LIVE"
            and row["current_effective_result"]["status"] in {"BLOCKED", "UNVERIFIED"}
        ]
        if failures:
            status = "INELIGIBLE"
        elif other_blockers:
            status = "NO_DECISION_YET"
        else:
            status = "PENDING_R7_REVIEW"
        eligibility[candidate] = {
            "status": status,
            "candidate_controlled_mandatory_failures": [
                {
                    "test_id": row["test_id"],
                    "provider": row["provider"],
                    "client": row["client"],
                    "failure_class": row["current_effective_result"].get("failure_class"),
                    "evidence_refs": row["evidence_refs"],
                }
                for row in failures
            ],
            "unresolved_mandatory_evidence": [
                {
                    "test_id": row["test_id"],
                    "provider": row["provider"],
                    "client": row["client"],
                    "failure_class": row["current_effective_result"].get("failure_class"),
                    "candidate_reached": row["candidate_reached"],
                    "evidence_refs": row["evidence_refs"],
                }
                for row in other_blockers
            ],
            "external_readiness_blockers_excluded_from_architecture_failure": [
                {
                    "test_id": row["test_id"],
                    "provider": row["provider"],
                    "client": row["client"],
                    "evidence_refs": row["evidence_refs"],
                }
                for row in candidate_rows
                if row["externally_blocked"]
            ],
        }

    pair_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["test_id"] == "T12" or row["live_vs_fixture"] != "LIVE":
            continue
        pair_groups[(row["candidate"], row["provider"], row["client"])].append(row)
    readiness: list[dict[str, Any]] = []
    for (candidate, provider, client), group in sorted(pair_groups.items()):
        status = _readiness_status(group)
        reached = any(row["candidate_reached"] for row in group)
        if status == "BLOCKED_EXTERNAL_PROVIDER":
            attribution = "EXTERNAL_PROVIDER_BLOCKED_BEFORE_CANDIDATE"
        elif status == "FAILED_COMPATIBILITY":
            attribution = "CANDIDATE_REACHED_COMPATIBILITY_FAILURE" if reached else "UNATTRIBUTED_FAILURE"
        elif status == "READY":
            attribution = "CANDIDATE_REACHED_PASS" if reached else "CANDIDATE_NEUTRAL"
        else:
            attribution = "PARTIAL_OR_UNVERIFIED"
        readiness.append(
            {
                "gateway_candidate": candidate,
                "provider": provider,
                "client": client,
                "protocol": _protocol(client, provider),
                "status": status,
                "candidate_reached": reached,
                "candidate_attribution": attribution,
                "test_ids": sorted({row["test_id"] for row in group}),
                "provider_reached": any(row["current_effective_result"]["provider_reached"] for row in group),
                "client_reached": any(row["current_effective_result"]["client_reached"] for row in group),
                "evidence_refs": sorted({ref for row in group for ref in row["evidence_refs"]}),
            }
        )

    capability_tests = {
        "native_tools": ({"T01", "T03", "T07"}, {"A6api"}),
        "emulated_tools": ({"T04"}, {"RelayRouter"}),
        "streaming": ({"T08"}, {"A6api", "RelayRouter"}),
        "sequential_continuation": ({"T07"}, {"A6api", "RelayRouter"}),
    }
    capabilities = {
        candidate: {
            name: _capability_summary(rows, candidate, tests, providers)
            for name, (tests, providers) in capability_tests.items()
        }
        for candidate in GATEWAYS
    }
    for candidate in GATEWAYS:
        fixture_rows = [row for row in rows if row["candidate"] == candidate and row["test_id"] in {"T09-A", "T09-B"}]
        capabilities[candidate]["fallback"] = {
            "status": "UNVERIFIED",
            "fixture_control_status": _aggregate_status(fixture_rows),
            "candidate_attribution": "CANDIDATE_NEUTRAL_FIXTURE_ONLY",
            "evidence_refs": sorted({ref for row in fixture_rows for ref in row["evidence_refs"]}),
        }

    readiness_by_provider: dict[str, str] = {}
    for provider in ("A6api", "RelayRouter"):
        statuses = {item["status"] for item in readiness if item["provider"] == provider}
        if "FAILED_COMPATIBILITY" in statuses:
            readiness_by_provider[provider] = "FAILED_COMPATIBILITY"
        elif "BLOCKED_EXTERNAL_PROVIDER" in statuses:
            readiness_by_provider[provider] = "BLOCKED_EXTERNAL_PROVIDER"
        elif statuses == {"READY"}:
            readiness_by_provider[provider] = "READY"
        elif statuses:
            readiness_by_provider[provider] = "PARTIAL"
        else:
            readiness_by_provider[provider] = "UNVERIFIED"

    fixture_controls = [
        {
            "candidate_label_in_source": row["candidate"],
            "test_id": row["test_id"],
            "status": row["current_effective_result"]["status"],
            "candidate_attribution": "CANDIDATE_NEUTRAL_FIXTURE_ONLY",
            "candidate_execution": False,
            "candidate_reached": False,
            "provider_reached": False,
            "client_reached": True,
            "evidence_refs": row["evidence_refs"],
        }
        for row in rows
        if row["live_vs_fixture"] == "FIXTURE"
    ]
    evidence_refs = sorted({ref for row in rows for ref in row["evidence_refs"]})
    return {
        "schema_version": "1.0",
        "test_id": "T12",
        "run_id": run_id,
        "observed_at_utc": observed_at,
        "architecture_candidate_eligibility": eligibility,
        "compatibility_readiness": readiness,
        "readiness_by_provider": readiness_by_provider,
        "capabilities": capabilities,
        "effective_capability": {
            candidate: {name: value["status"] for name, value in candidate_caps.items()}
            for candidate, candidate_caps in capabilities.items()
        },
        "fixture_controls": fixture_controls,
        "evidence_refs": evidence_refs,
    }


def build_resolution_ledger(root: Path, run_id: str) -> dict[str, Any]:
    """Reconcile immutable Level 2 history with Resolution R2/R3 attribution."""

    root = root.resolve()
    matrix_paths = sorted((root / "tests/poc/evidence/level2").glob("*/matrix.json"))
    if not matrix_paths:
        raise ValueError("no Level 2 matrices found")
    matrices = [(_read_json(path), path) for path in matrix_paths]
    matrices.sort(key=lambda item: (item[0]["observed_at"], item[0]["run_id"]))
    latest, latest_path = matrices[-1]
    evidence_run_id = run_id.removeprefix("resolution-")
    r2_dir = root / "tests/poc/evidence/resolution" / evidence_run_id / "r2"
    r3_dir = root / "tests/poc/evidence/resolution" / evidence_run_id / "r3"
    r2_summary_path = r2_dir / "summary.json"
    r3_summary_path = r3_dir / "summary.json"
    r3_direct_path = r3_dir / "direct-control.json"
    r2 = _read_json(r2_summary_path)
    r3 = _read_json(r3_summary_path)
    r3_direct = _read_json(r3_direct_path)
    _validate_refs(root, [r2, r3, r3_direct])

    historical: dict[tuple[str, str, str, str, str], dict[tuple[Any, ...], dict[str, Any]]] = defaultdict(dict)
    source_matrices: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    for matrix, matrix_path in matrices:
        matrix_ref = _relative(root, matrix_path)
        for key, grouped_rows in _rows_by_key(matrix.get("rows", [])).items():
            source_matrices[key].add(matrix_ref)
            for row in grouped_rows:
                attempt = _attempt_from_matrix(row, matrix_ref)
                historical[key][_attempt_identity(attempt)] = attempt

    r2_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in r2["records"]:
        if record.get("test_id") == "T03" and record.get("candidate") in GATEWAYS:
            r2_rows[record["candidate"]].append(record)

    external_relayrouter_block = (
        r3.get("classification") == "EXTERNAL_PROVIDER_BLOCKED"
        and r3_direct.get("candidate_reached") is False
        and r3_direct.get("provider_reached") is False
    )
    r2_summary_ref = _relative(root, r2_summary_path)
    r3_summary_ref = _relative(root, r3_summary_path)
    r3_direct_ref = _relative(root, r3_direct_path)
    r3_refs = [r3_summary_ref, r3_direct_ref]

    current_groups = _rows_by_key(latest.get("rows", []))
    all_keys = sorted(set(historical) | set(current_groups))
    ledger_rows: list[dict[str, Any]] = []
    for key in all_keys:
        candidate, test_id, provider, client, evidence_type = key
        source_rows = current_groups.get(key, [])
        history_rows = historical.get(key, {})
        history_attempts = list(history_rows.values())
        history_attempts.sort(key=lambda item: (item.get("run_id") or "", item.get("repetition") or 0, item["status"]))
        is_fixture = evidence_type == "SYNTHETIC_FIXTURE_EVIDENCE"
        effective_status = _aggregate_status(source_rows)
        failure_classes = _distinct([row.get("failure_class") for row in source_rows])
        candidate_reached = any(bool(row.get("candidate_execution")) for row in source_rows)
        externally_blocked = False
        candidate_attribution = "CANDIDATE_NEUTRAL_FIXTURE_ONLY" if is_fixture else (
            "CANDIDATE_REACHED_PASS" if effective_status == "PASS" else "CANDIDATE_REACHED_FAILURE"
        )
        unresolved_reason = None
        attribution_refs: list[str] = []
        if test_id == "T03" and provider == "A6api" and client == "Claude Code":
            fresh = r2_rows.get(candidate, [])
            if len(fresh) != 3:
                raise ValueError(f"R2 must contain exactly three fixed T03 repetitions for {candidate}")
            effective_status = "PASS" if all(item.get("status") == "PASS" for item in fresh) else (
                "FAIL" if all(item.get("candidate_reached") is True for item in fresh) else "BLOCKED"
            )
            failure_classes = _distinct([
                item.get("attribution_classification") or item.get("classification")
                for item in fresh
                if item.get("status") != "PASS"
            ])
            candidate_reached = all(item.get("candidate_reached") is True for item in fresh)
            candidate_attribution = (
                "CANDIDATE_REACHED_PASS" if effective_status == "PASS" else
                "CANDIDATE_REACHED_FAILURE" if effective_status == "FAIL" else
                "EVIDENCE_OBSERVABILITY_FAILURE_BEFORE_CANDIDATE_CORRELATION"
            )
            unresolved_reason = (
                "All three Claude Code processes exited with client failure and produced no tool/result event. "
                "Only the separate model-list probe was observed; the T03 gateway request and provider-bound request "
                "were not correlated, so the client failure cannot be attributed to either gateway candidate."
                if effective_status == "BLOCKED" else None
            )
            attribution_refs = [r2_summary_ref, *[
                _relative(root, r2_dir / "bifrost" / f"rep-{item['repetition']}.json")
                if candidate == "Bifrost"
                else _relative(root, r2_dir / "litellm" / f"rep-{item['repetition']}.json")
                for item in sorted(fresh, key=lambda value: value["repetition"])
            ]]
            for item in fresh:
                attempt = {
                    "run_id": run_id,
                    "phase": "R2",
                    "attempt_id": item["attempt_id"],
                    "test_id": "T03",
                    "repetition": item["repetition"],
                    "status": item["status"],
                    "failure_class": item.get("classification"),
                    "candidate_attribution": item.get("candidate_attribution", "UNATTRIBUTED_CLIENT_FAILURE"),
                    "candidate_execution": item.get("candidate_reached", False),
                    "behavior_mode": "UNVERIFIED",
                    "evidence_type": "LIVE_PROVIDER_EVIDENCE",
                    "evidence_refs": [
                        _relative(root, r2_dir / candidate.lower() / f"rep-{item['repetition']}.json"),
                        r2_summary_ref,
                    ],
                    "source_matrix_ref": None,
                }
                history_rows[_attempt_identity(attempt)] = attempt
            history_attempts = list(history_rows.values())
            history_attempts.sort(key=lambda item: (item.get("run_id") or "", item.get("repetition") or 0, item["status"]))
        elif external_relayrouter_block and provider == "RelayRouter" and test_id in RELAYROUTER_TESTS:
            effective_status = "BLOCKED"
            failure_classes = ["EXTERNAL_PROVIDER_BLOCKED"]
            candidate_reached = False
            externally_blocked = True
            candidate_attribution = "EXTERNAL_PROVIDER_BLOCKED_BEFORE_CANDIDATE"
            unresolved_reason = (
                "The fresh direct OpenCode/RelayRouter control timed out before a provider response; "
                "R4 applies that external attribution to RelayRouter T04/T07/T08."
            )
            attribution_refs = list(r3_refs)
        elif not source_rows:
            unresolved_reason = "No current row exists in the latest Level 2 matrix."
            effective_status = "UNVERIFIED"
            candidate_attribution = "UNVERIFIED"

        current_refs = sorted({ref for row in source_rows for ref in row.get("evidence_refs", [])})
        history_refs = sorted({ref for item in history_attempts for ref in item.get("evidence_refs", [])})
        evidence_refs = sorted({*current_refs, *history_refs, *attribution_refs})
        candidate_controlled = not is_fixture and candidate_reached and not externally_blocked
        live_vs_fixture = "FIXTURE" if is_fixture else "LIVE"
        behaviors = _distinct([row.get("behavior_mode") for row in source_rows])
        if test_id == "T03" and provider == "A6api" and client == "Claude Code":
            behaviors = ["UNVERIFIED"]
        effective_result = {
            "status": effective_status,
            "classification": failure_classes[0] if len(failure_classes) == 1 else ("MIXED_FAILURES" if failure_classes else None),
            "failure_class": failure_classes[0] if len(failure_classes) == 1 else ("MIXED_FAILURES" if failure_classes else None),
            "candidate_reached": candidate_reached,
            "provider_reached": bool(
                not externally_blocked
                and not (test_id == "T03" and provider == "A6api" and client == "Claude Code")
                and any(row.get("status") == "PASS" for row in source_rows)
            ),
            "client_reached": bool(
                any(row.get("status") in {"PASS", "FAIL", "BLOCKED"} for row in source_rows)
                or attribution_refs
            ),
            "unresolved_reason": unresolved_reason,
        }
        ledger_rows.append(
            {
                "row_id": f"{candidate}:{test_id}:{provider}:{client}",
                "run_id": run_id,
                "candidate": candidate,
                "test_id": test_id,
                "provider": provider,
                "client": client,
                "protocol": _protocol(client, provider),
                "live_vs_fixture": live_vs_fixture,
                "evidence_type": evidence_type,
                "behavior_mode": behaviors[0] if len(behaviors) == 1 else ("MIXED" if behaviors else "UNVERIFIED"),
                "candidate_reached": candidate_reached,
                "provider_reached": effective_result["provider_reached"],
                "client_reached": effective_result["client_reached"],
                "candidate_controlled": candidate_controlled,
                "externally_blocked": externally_blocked,
                "candidate_attribution": candidate_attribution,
                "current_effective_result": effective_result,
                "historical_attempts": history_attempts,
                "evidence_refs": evidence_refs,
                "source_matrix_refs": sorted(source_matrices.get(key, set())),
                "attribution_evidence_refs": sorted(set(attribution_refs)),
                "rerun_required": False,
                "rerun_reason": "Current Resolution evidence settles attribution or the fixed repetition block; no authorized residual rerun remains for this row.",
            }
        )

    # The current matrix may not list T12 as a scenario row; it is a generated
    # report row for each gateway so its architecture/readiness split is explicit.
    observed_at = max(
        r2["records"][-1]["finished_at_utc"],
        r3_direct["finished_at_utc"],
        latest["observed_at"],
    )
    t12 = _t12(ledger_rows, run_id, observed_at)
    for candidate in GATEWAYS:
        ledger_rows.append(
            {
                "row_id": f"{candidate}:T12:REPORT_GENERATION",
                "run_id": run_id,
                "candidate": candidate,
                "test_id": "T12",
                "provider": "Multiple",
                "client": "Multiple",
                "protocol": "Resolution reconciliation report",
                "live_vs_fixture": "MIXED_REPORT",
                "evidence_type": "RESOLUTION_REPORT_EVIDENCE",
                "behavior_mode": "MIXED",
                "candidate_reached": False,
                "candidate_controlled": False,
                "externally_blocked": False,
                "candidate_attribution": "ATTRIBUTION_BY_SOURCE_ROW",
                "current_effective_result": {
                    "status": "PASS",
                    "classification": "PASS",
                    "failure_class": None,
                    "candidate_reached": False,
                    "provider_reached": False,
                    "client_reached": False,
                    "unresolved_reason": None,
                },
                "provider_reached": False,
                "client_reached": False,
                "historical_attempts": [],
                "evidence_refs": t12["evidence_refs"],
                "source_matrix_refs": [_relative(root, latest_path)],
                "attribution_evidence_refs": sorted({r2_summary_ref, *r3_refs}),
                "rerun_required": False,
                "rerun_reason": None,
                "t12_architecture_candidate_eligibility": t12["architecture_candidate_eligibility"][candidate],
                "t12_compatibility_readiness": [
                    item for item in t12["compatibility_readiness"] if item["gateway_candidate"] == candidate
                ],
            }
        )

    ledger_rows.sort(key=lambda row: (GATEWAYS.index(row["candidate"]), TEST_ORDER.index(row["test_id"]), row["provider"], row["client"]))
    _validate_refs(root, ledger_rows)
    _validate_refs(root, [t12])
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "latest_level2_run_id": latest["run_id"],
        "latest_level2_matrix_ref": _relative(root, latest_path),
        "observed_at_utc": observed_at,
        "rows": ledger_rows,
        "t12": t12,
    }


def write_resolution_artifacts(root: Path, run_id: str, revision: str | None = None) -> dict[str, str]:
    """Write the canonical R4 ledger and its separately consumable T12 report."""

    root = root.resolve()
    if revision is not None and not re.fullmatch(r"[a-z0-9-]+", revision):
        raise ValueError("revision must contain only lowercase letters, digits, and hyphens")
    ledger = build_resolution_ledger(root, run_id)
    evidence_run_id = run_id.removeprefix("resolution-")
    output_dir = root / "tests/poc/evidence/resolution" / evidence_run_id / "r4"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{revision}" if revision else ""
    outputs = {
        "canonical_ledger": output_dir / f"canonical-ledger{suffix}.json",
        "t12_report": output_dir / f"t12-report{suffix}.json",
    }
    payloads = {
        "canonical_ledger": ledger,
        "t12_report": ledger["t12"],
    }
    written: dict[str, str] = {}
    for name, destination in outputs.items():
        content = json.dumps(payloads[name], ensure_ascii=True, sort_keys=True, indent=2) + "\n"
        if destination.exists():
            if destination.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing to replace different R4 evidence: {destination}")
        else:
            destination.write_text(content, encoding="utf-8", newline="\n")
        written[name] = _relative(root, destination)
    return written


def _validate_refs(root: Path, values: list[dict[str, Any]]) -> None:
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"evidence_refs", "source_matrix_refs", "attribution_evidence_refs"} and isinstance(item, list):
                    missing = [ref for ref in item if isinstance(ref, str) and not (root / ref).is_file()]
                    if missing:
                        raise ValueError("missing evidence reference(s): " + ", ".join(missing))
                if key == "evidence_path" and isinstance(item, str):
                    if item.startswith("tests/") and not (root / item).is_file():
                        raise ValueError("missing evidence path: " + item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for value in values:
        visit(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Resolution R4 canonical ledger and T12 report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--revision")
    args = parser.parse_args(argv)
    print(json.dumps(write_resolution_artifacts(args.root, args.run_id, args.revision), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
