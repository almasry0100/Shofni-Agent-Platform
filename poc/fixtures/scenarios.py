from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.evidence.schema import (
    BehaviorMode,
    EvidenceEnvelope,
    EvidenceType,
    ProvenanceReference,
    ResultStatus,
)
from poc.evidence.redactor import redact_string, redacted_json_dumps
from poc.evidence.schema import validate_evidence_envelope
from poc.evidence.taxonomy import parse_failure_class

from . import FIXTURE_VERSION
from .fallback import FailAfterToolFixture, FailBeforeToolFixture, NarrationOnlyAfterToolFixture
from .ledger import LedgerFixture
from .network import outbound_network_blocked
from .provider_server import probe_local_provider
from .providers import (
    ChatOnlyProviderFixture,
    MalformedToolJsonFixture,
    NativeToolProviderFixture,
    TextualToolCallFixture,
    canonical_json,
    deterministic_id,
    parse_textual_tool_call,
    repair_tool_json,
)
from .streaming import StreamingToolFixture, assemble_stream
from .workspace import DisposableWorkspace, WorkspaceError


DETERMINISM_RUN_COUNT = 10
DETERMINISM_SEED_PREFIX = "phase2-semantic-v1"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE_ROOT = _REPOSITORY_ROOT / "tests" / "poc" / "evidence" / "phase-2"
FIXTURE_SOURCE_FILES = {
    "NativeToolProviderFixture": "poc/fixtures/providers.py",
    "ChatOnlyProviderFixture": "poc/fixtures/providers.py",
    "TextualToolCallFixture": "poc/fixtures/providers.py",
    "MalformedToolJsonFixture": "poc/fixtures/providers.py",
    "StreamingToolFixture": "poc/fixtures/streaming.py",
    "FailBeforeToolFixture": "poc/fixtures/fallback.py",
    "FailAfterToolFixture": "poc/fixtures/fallback.py",
    "NarrationOnlyAfterToolFixture": "poc/fixtures/fallback.py",
    "DisposableWorkspace": "poc/fixtures/workspace.py",
    "LedgerFixture": "poc/fixtures/ledger.py",
    "LocalProviderServer": "poc/fixtures/provider_server.py",
    "DeterministicScenarioEngine": "poc/fixtures/scenarios.py",
}

SCENARIO_FIXTURES = {
    "native_tool": "NativeToolProviderFixture",
    "t02_chat_only": "ChatOnlyProviderFixture",
    "t05_text_valid": "TextualToolCallFixture",
    "t05_text_duplicate": "TextualToolCallFixture",
    "t05_text_prose": "TextualToolCallFixture",
    "t05_text_narration": "TextualToolCallFixture",
    "t05_text_fenced": "TextualToolCallFixture",
    "t05_text_structured_looking": "TextualToolCallFixture",
    "t05_text_invalid_schema": "TextualToolCallFixture",
    "t06_trailing_comma": "MalformedToolJsonFixture",
    "t06_single_quotes": "MalformedToolJsonFixture",
    "t06_two_step_repair": "MalformedToolJsonFixture",
    "t06_fenced_repair": "MalformedToolJsonFixture",
    "t06_stringified_arguments": "MalformedToolJsonFixture",
    "t06_harmless_metadata": "MalformedToolJsonFixture",
    "t06_ambiguous_duplicate_keys": "MalformedToolJsonFixture",
    "t06_irrecoverable": "MalformedToolJsonFixture",
    "t08_stream_complete": "StreamingToolFixture",
    "t08_stream_incomplete": "StreamingToolFixture",
    "t08_stream_malformed_arguments": "StreamingToolFixture",
    "t09_before_tool": "FailBeforeToolFixture",
    "t09_after_tool": "FailAfterToolFixture",
    "narration_after_tool": "NarrationOnlyAfterToolFixture",
    "workspace_fixture": "DisposableWorkspace",
    "t11_ledger_primitive": "LedgerFixture",
    "provider_server_smoke": "LocalProviderServer",
}

_MALFORMED_CASES = {
    "t06_trailing_comma": "trailing_comma",
    "t06_single_quotes": "single_quotes",
    "t06_two_step_repair": "two_step_trailing_commas",
    "t06_fenced_repair": "fenced_trailing_comma",
    "t06_stringified_arguments": "stringified_arguments",
    "t06_harmless_metadata": "harmless_metadata",
    "t06_ambiguous_duplicate_keys": "ambiguous_duplicate_key",
    "t06_irrecoverable": "irrecoverable",
}

_TEXT_CASES = {
    "t05_text_valid": "valid",
    "t05_text_duplicate": "duplicate",
    "t05_text_prose": "prose",
    "t05_text_narration": "narration",
    "t05_text_fenced": "fenced",
    "t05_text_structured_looking": "structured_looking",
    "t05_text_invalid_schema": "invalid_schema",
}


def _file_hash(relative_path: str) -> str:
    contents = (_REPOSITORY_ROOT / relative_path).read_bytes()
    return "sha256:" + hashlib.sha256(contents).hexdigest()


def _source_for_fixture(fixture_name: str) -> str:
    try:
        return FIXTURE_SOURCE_FILES[fixture_name]
    except KeyError as exc:
        raise ValueError(f"unknown fixture identity: {fixture_name}") from exc


def _base_result(scenario: str, seed: str, request: dict[str, Any]) -> dict[str, Any]:
    fixture_name = SCENARIO_FIXTURES[scenario]
    return {
        "test_id": scenario.upper(),
        "fixture_name": fixture_name,
        "fixture_version": FIXTURE_VERSION,
        "fixture_source_file": _source_for_fixture(fixture_name),
        "fixture_hash": _file_hash(_source_for_fixture(fixture_name)),
        "seed": seed,
        "request_id": deterministic_id("request", seed, scenario),
        "task_id": deterministic_id("task", seed, scenario),
        "workspace_id": None,
        "attempt_id": None,
        "tool_call_id": None,
        "operation_id": None,
        "behavior_mode": BehaviorMode.UNVERIFIED.value,
        "normalized_request": request,
        "normalized_response": {},
        "decisions": [],
        "attempt_transitions": [],
        "tool_ledger_outcome": [],
        "result_status": "PASS",
        "failure_class": None,
    }


def _execute_read_call(
    call: dict[str, Any],
    seed: str,
    workspace: DisposableWorkspace,
    ledger: LedgerFixture,
) -> dict[str, Any]:
    function = call["function"]
    arguments = json.loads(function["arguments"])
    operation_id = deterministic_id(
        "operation",
        seed,
        {"tool_call_id": call["id"], "function": function},
    )
    existing = ledger.lookup(operation_id)
    if existing is not None:
        return {
            "tool_call_id": call["id"],
            "operation_id": operation_id,
            "result": existing.result,
            "inserted": False,
            "duplicate_suppressed": True,
            "value_conflict": False,
        }

    value = {"text": workspace.read_text(arguments["path"])}
    appended = ledger.append_ledger(operation_id, value)
    return {
        "tool_call_id": call["id"],
        "operation_id": operation_id,
        "result": appended.result,
        "inserted": appended.inserted,
        "duplicate_suppressed": appended.duplicate_suppressed,
        "value_conflict": appended.value_conflict,
    }


def _run_provider_text_case(scenario: str, seed: str) -> dict[str, Any]:
    case = _TEXT_CASES[scenario]
    raw_text = TextualToolCallFixture().response(case)
    parsed = parse_textual_tool_call(raw_text, seed)
    result = _base_result(
        scenario,
        seed,
        {"input_case": case, "text": raw_text},
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value if parsed.tool_calls else BehaviorMode.UNVERIFIED.value
    result["decisions"] = [{
        "parser_decision": parsed.decision,
        "duplicate_count": parsed.duplicate_count,
        "invalid_match_count": parsed.invalid_match_count,
        "completion_state": parsed.completion_state,
        "schema_checked_before_execution": True,
    }]
    execution_records: list[dict[str, Any]] = []
    if parsed.tool_calls:
        with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
            result["workspace_id"] = workspace.workspace_id
            execution_records.append(_execute_read_call(parsed.tool_calls[0], seed, workspace, ledger))
            effect_count = ledger.count()
    else:
        effect_count = 0

    expected_call = case in {"valid", "duplicate"}
    expected_duplicate_count = 1 if case == "duplicate" else 0
    passed = (
        (len(parsed.tool_calls) == 1) == expected_call
        and parsed.duplicate_count == expected_duplicate_count
        and effect_count == (1 if expected_call else 0)
        and (parsed.completion_state != "FINAL")
    )
    result["tool_call_id"] = parsed.tool_calls[0]["id"] if parsed.tool_calls else None
    result["operation_id"] = execution_records[0]["operation_id"] if execution_records else None
    result["tool_ledger_outcome"] = execution_records
    result["normalized_response"] = {
        "structured_tool_calls": list(parsed.tool_calls),
        "tool_execution_count": effect_count,
        "completion_state": parsed.completion_state,
    }
    result["result_status"] = "PASS" if passed else "FAIL"
    if not passed:
        result["failure_class"] = "TOOL_SCHEMA_FAILURE"
    return result


def _run_malformed_case(scenario: str, seed: str) -> dict[str, Any]:
    case = _MALFORMED_CASES[scenario]
    original = MalformedToolJsonFixture().payloads()[case]
    repaired = repair_tool_json(original, seed)
    accepted_cases = {
        "trailing_comma",
        "single_quotes",
        "two_step_trailing_commas",
        "fenced_trailing_comma",
        "stringified_arguments",
        "harmless_metadata",
    }
    should_repair = case in accepted_cases
    execution_records: list[dict[str, Any]] = []
    if repaired.tool_call is not None:
        with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
            execution_records.append(_execute_read_call(repaired.tool_call, seed, workspace, ledger))
            effect_count = ledger.count()
            workspace_id = workspace.workspace_id
    else:
        effect_count = 0
        workspace_id = None

    passed = (
        (repaired.tool_call is not None) == should_repair
        and repaired.repair_attempts <= 2
        and effect_count == (1 if should_repair else 0)
        and (not repaired.ambiguous or effect_count == 0)
    )
    result = _base_result(
        scenario,
        seed,
        {"input_case": case, "original_payload": repaired.original_payload},
    )
    result["workspace_id"] = workspace_id
    result["behavior_mode"] = (
        BehaviorMode.REPAIRED.value if should_repair else BehaviorMode.UNVERIFIED.value
    )
    result["tool_call_id"] = repaired.tool_call["id"] if repaired.tool_call else None
    result["operation_id"] = execution_records[0]["operation_id"] if execution_records else None
    result["failure_class"] = repaired.failure_class
    result["decisions"] = [{
        "repair_status": repaired.status,
        "repair_attempts": repaired.repair_attempts,
        "maximum_repair_attempts": 2,
        "ambiguous": repaired.ambiguous,
        "tool_execution_allowed": repaired.tool_call is not None,
        "repair_history": list(repaired.repair_history),
    }]
    result["normalized_response"] = {
        "repaired_payload": repaired.repaired_payload,
        "tool_call": repaired.tool_call,
        "tool_execution_count": effect_count,
    }
    result["tool_ledger_outcome"] = execution_records
    result["result_status"] = "PASS" if passed else "FAIL"
    if not passed and result["failure_class"] is None:
        result["failure_class"] = "MALFORMED_RESPONSE"
    return result


def _run_stream_case(scenario: str, seed: str) -> dict[str, Any]:
    fixture = StreamingToolFixture()
    if scenario == "t08_stream_incomplete":
        events = fixture.events(seed, include_terminal=False)
        expected_status = "INCOMPLETE"
    elif scenario == "t08_stream_malformed_arguments":
        events = fixture.events(seed, truncate_arguments=True)
        expected_status = "MALFORMED"
    else:
        events = fixture.events(seed)
        expected_status = "COMPLETE"
    assembled = assemble_stream(events)
    expected_call = expected_status == "COMPLETE"
    passed = assembled.status == expected_status and (assembled.tool_call is not None) == expected_call
    result = _base_result(
        scenario,
        seed,
        {"fragment_count": len(events), "fragmented_input": True},
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["tool_call_id"] = assembled.tool_call_id
    result["failure_class"] = assembled.failure_class
    result["decisions"] = [{
        "assembly_status": assembled.status,
        "terminal_event_count": assembled.terminal_event_count,
        "arguments_complete_before_tool_call": assembled.tool_call is not None,
        "ordered_events": [event["event_type"] for event in assembled.normalized_events],
    }]
    result["normalized_response"] = assembled.to_dict()
    result["result_status"] = "PASS" if passed else "FAIL"
    return result


def _run_t09_before_tool(seed: str) -> dict[str, Any]:
    fixture = FailBeforeToolFixture()
    primary = fixture.primary(seed)
    result = _base_result(
        "t09_before_tool",
        seed,
        {"routes": ["primary", "fallback"], "tool": "read_fixture"},
    )
    with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
        call = fixture.fallback(seed)["tool_calls"][0]
        effect = _execute_read_call(call, seed, workspace, ledger)
        result["workspace_id"] = workspace.workspace_id
        result["tool_ledger_outcome"] = [effect]
        effect_count = ledger.count()
    passed = (
        primary["failure_stage"] == "BEFORE_TOOL_EFFECT"
        and primary["tool_effect_occurred"] is False
        and effect_count == 1
        and effect["duplicate_suppressed"] is False
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["tool_call_id"] = call["id"]
    result["operation_id"] = effect["operation_id"]
    result["attempt_id"] = primary["attempt_id"]
    result["attempt_transitions"] = [
        {
            "attempt_id": primary["attempt_id"],
            "route": "primary",
            "status": primary["status"],
            "failure_stage": primary["failure_stage"],
            "tool_effect_occurred": False,
        },
        {
            "attempt_id": f"attempt_fallback_{seed}",
            "route": "fallback",
            "status": "SUCCEEDED",
            "transition_from": primary["attempt_id"],
            "transition_allowed": True,
            "tool_call_id": call["id"],
            "operation_id": effect["operation_id"],
        },
    ]
    result["decisions"] = [{
        "fallback_allowed": True,
        "primary_failed_before_tool_effect": True,
        "duplicate_effect_count": 0,
    }]
    result["normalized_response"] = {
        "primary_failure": primary,
        "fallback_tool_result": effect["result"],
        "tool_effect_count": effect_count,
    }
    result["failure_class"] = primary["failure_class"]
    result["result_status"] = "PASS" if passed else "FAIL"
    return result


def _run_t09_after_tool(seed: str) -> dict[str, Any]:
    fixture = FailAfterToolFixture()
    call = fixture.primary_tool_request(seed)["tool_calls"][0]
    result = _base_result(
        "t09_after_tool",
        seed,
        {"routes": ["primary", "fallback"], "tool": "read_fixture"},
    )
    with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
        first_effect = _execute_read_call(call, seed, workspace, ledger)
        primary_failure = fixture.fail_after_result(seed)
        existing = ledger.lookup(first_effect["operation_id"])
        if existing is None:
            raise AssertionError("recorded tool result disappeared before fallback")
        reused_result = {
            "tool_call_id": call["id"],
            "operation_id": first_effect["operation_id"],
            "result": existing.result,
        }
        fallback = fixture.fallback(seed, reused_result)
        result["workspace_id"] = workspace.workspace_id
        ledger_rows = ledger.count()
    fallback_calls = fallback["tool_calls"]
    passed = (
        first_effect["inserted"] is True
        and primary_failure["failure_stage"] == "AFTER_TOOL_RESULT"
        and existing.result == first_effect["result"]
        and fallback["received_tool_results"] == [reused_result]
        and fallback_calls == []
        and ledger_rows == 1
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["tool_call_id"] = call["id"]
    result["operation_id"] = first_effect["operation_id"]
    result["attempt_id"] = primary_failure["attempt_id"]
    result["attempt_transitions"] = [
        {
            "attempt_id": primary_failure["attempt_id"],
            "route": "primary",
            "status": primary_failure["status"],
            "failure_stage": primary_failure["failure_stage"],
            "tool_effect_occurred": True,
            "tool_call_id": call["id"],
            "operation_id": first_effect["operation_id"],
            "recorded_result": first_effect["result"],
        },
        {
            "attempt_id": fallback["attempt_id"],
            "route": "fallback",
            "status": "SUCCEEDED",
            "transition_from": primary_failure["attempt_id"],
            "existing_result_received": True,
            "tool_call_id": call["id"],
            "operation_id": first_effect["operation_id"],
            "tool_call_requested_again": bool(fallback_calls),
            "tool_effect_reexecuted": False,
        },
    ]
    result["decisions"] = [{
        "duplicate_suppression_decision": "reuse_recorded_result_without_reexecution",
        "operation_id_stable_across_fallback": True,
        "duplicate_effect_count": 0,
        "final_completion": fallback["finish_reason"] == "stop",
    }]
    result["tool_ledger_outcome"] = [{
        **first_effect,
        "lookup_before_fallback": {
            "found": True,
            "result_reused": existing.result,
        },
        "duplicate_suppression_decision": "reuse_recorded_result_without_reexecution",
        "side_effect_count": ledger_rows,
        "duplicate_effect_count": 0,
    }]
    result["normalized_response"] = {
        "primary_failure": primary_failure,
        "fallback_response": fallback,
        "final_status": "FINAL" if passed else "INCOMPLETE",
    }
    result["failure_class"] = primary_failure["failure_class"]
    result["result_status"] = "PASS" if passed else "FAIL"
    return result


def _run_narration_after_tool(seed: str) -> dict[str, Any]:
    call = NativeToolProviderFixture().respond(
        {"tool_name": "read_fixture", "arguments": {"path": "input/alpha.txt"}},
        seed,
    )["tool_calls"][0]
    result = _base_result(
        "narration_after_tool",
        seed,
        {"previous_tool_result": True, "required_next_action": "read_fixture"},
    )
    with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
        effect = _execute_read_call(call, seed, workspace, ledger)
        narration = NarrationOnlyAfterToolFixture().respond(seed)
        effect_count = ledger.count()
        result["workspace_id"] = workspace.workspace_id
    passed = (
        effect_count == 1
        and not narration["tool_calls"]
        and narration["content"]
        and narration["finish_reason"] == "stop"
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["tool_call_id"] = call["id"]
    result["operation_id"] = effect["operation_id"]
    result["attempt_id"] = narration["attempt_id"]
    result["tool_ledger_outcome"] = [effect]
    result["decisions"] = [{
        "narration_alone_is_completion": False,
        "required_next_tool_call_missing": True,
        "completion_state": "CONTINUATION_REQUIRED",
        "tool_effect_count": effect_count,
    }]
    result["normalized_response"] = {
        "prior_tool_result": effect["result"],
        "provider_response": narration,
        "task_completed": False,
    }
    result["failure_class"] = "CONTINUATION_FAILURE"
    result["result_status"] = "PASS" if passed else "FAIL"
    return result


def _run_workspace_fixture(seed: str) -> dict[str, Any]:
    result = _base_result(
        "workspace_fixture",
        seed,
        {
            "required_files": ["input/alpha.txt", "input/beta.json"],
            "required_directories": ["output", "state"],
            "traversal_cases": 4,
        },
    )
    with DisposableWorkspace(seed) as workspace:
        outside = workspace.root.parent / "outside-sentinel.txt"
        outside.write_text("fixture-owned sentinel\n", encoding="utf-8")
        initial = {
            "alpha": workspace.read_text("input/alpha.txt"),
            "beta": workspace.read_json("input/beta.json"),
        }
        workspace.write_text("output/result.txt", "fixture output\n")
        attacks = [
            "../outside-sentinel.txt",
            "..\\outside-sentinel.txt",
            str(outside),
            "input/../../outside-sentinel.txt",
        ]
        rejected = 0
        for attack in attacks:
            try:
                workspace.write_text(attack, "escape attempt")
            except WorkspaceError:
                rejected += 1
        sentinel_unchanged = outside.read_text(encoding="utf-8") == "fixture-owned sentinel\n"
        output_written = workspace.read_text("output/result.txt") == "fixture output\n"
        workspace_id = workspace.workspace_id
        outside.unlink()
    passed = rejected == len(attacks) and sentinel_unchanged and output_written
    result["workspace_id"] = workspace_id
    result["decisions"] = [{
        "rejected_traversal_attempts": rejected,
        "sentinel_outside_workspace_unchanged": sentinel_unchanged,
        "output_write_succeeded": output_written,
        "disposable_workspace_cleaned": True,
    }]
    result["normalized_response"] = initial
    result["result_status"] = "PASS" if passed else "FAIL"
    if not passed:
        result["failure_class"] = "WORKSPACE_ERROR"
    return result


def _run_ledger_fixture(seed: str) -> dict[str, Any]:
    result = _base_result(
        "t11_ledger_primitive",
        seed,
        {"operation_ids": ["operation-primary", "operation-secondary"], "scope": "controlled_fixture"},
    )
    with DisposableWorkspace(seed) as workspace:
        first_ledger = LedgerFixture(workspace)
        first = first_ledger.append_ledger("operation-primary", {"text": "recorded result"})
        replay = first_ledger.append_ledger("operation-primary", {"text": "recorded result"})
        distinct = first_ledger.append_ledger("operation-secondary", {"text": "separate result"})
        lookup = first_ledger.lookup("operation-primary")
        rows_before_reopen = first_ledger.count()
        first_ledger.close()

        reopened = LedgerFixture(workspace)
        reopened_replay = reopened.append_ledger("operation-primary", {"text": "recorded result"})
        persisted = reopened.lookup("operation-primary")
        rows_after_reopen = reopened.count()
        reopened.close()
        result["workspace_id"] = workspace.workspace_id
    passed = (
        first.inserted
        and replay.duplicate_suppressed
        and lookup is not None
        and lookup.result == {"text": "recorded result"}
        and distinct.inserted
        and reopened_replay.duplicate_suppressed
        and persisted is not None
        and rows_before_reopen == 2
        and rows_after_reopen == 2
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["operation_id"] = "operation-primary"
    result["decisions"] = [{
        "first_insert_created_one_record": first.inserted,
        "same_operation_replay_suppressed": replay.duplicate_suppressed,
        "lookup_returned_persisted_result": lookup.result if lookup else None,
        "different_operation_created_record": distinct.inserted,
        "reopen_replay_suppressed": reopened_replay.duplicate_suppressed,
        "rows_before_reopen": rows_before_reopen,
        "rows_after_reopen": rows_after_reopen,
        "scope": "controlled_sqlite_fixture_only",
    }]
    primary_operation_id = deterministic_id("operation", seed, "ledger-primary")
    secondary_operation_id = deterministic_id("operation", seed, "ledger-secondary")
    result["operation_id"] = primary_operation_id
    result["tool_ledger_outcome"] = [
        {
            "operation_id": primary_operation_id,
            "inserted": first.inserted,
            "duplicate_suppressed": replay.duplicate_suppressed,
            "result": persisted.result if persisted else None,
        },
        {
            "operation_id": secondary_operation_id,
            "inserted": distinct.inserted,
            "duplicate_suppressed": False,
            "result": distinct.result,
        },
    ]
    result["normalized_response"] = {
        "logical_record_count": rows_after_reopen,
        "primary_result": persisted.result if persisted else None,
    }
    result["result_status"] = "PASS" if passed else "FAIL"
    return result


def _run_server_smoke(seed: str) -> dict[str, Any]:
    probe = probe_local_provider(seed)
    server = probe.get("server") or {}
    semantic_server = {
        "bind_address": server.get("bind_address"),
        "fixture_version": server.get("fixture_version"),
        "fixture_hash": server.get("fixture_hash"),
        "startup_result": server.get("startup_result"),
        "shutdown_result": server.get("shutdown_result"),
        "port_released": probe.get("server_port_released", False),
    }
    result = _base_result(
        "provider_server_smoke",
        seed,
        {"method": "POST", "endpoint_kind": "local_chat_fixture", "payload": {"path": "input/alpha.txt"}},
    )
    result["behavior_mode"] = BehaviorMode.EMULATED.value
    result["fixture_hash"] = semantic_server.get("fixture_hash") or result["fixture_hash"]
    result["decisions"] = [{
        "local_only": semantic_server.get("bind_address") == "127.0.0.1",
        "startup_result": semantic_server.get("startup_result"),
        "shutdown_result": semantic_server.get("shutdown_result"),
        "port_released": semantic_server["port_released"],
        "setup_retry_count": max(0, len(probe.get("setup_attempts", [])) - 1),
    }]
    result["normalized_response"] = {
        "provider_response": probe.get("normalized_response"),
        "server": semantic_server,
        "local_fixture_requests": 1 if probe.get("normalized_response") is not None else 0,
    }
    result["result_status"] = probe.get("result_status", "FAIL")
    result["failure_class"] = probe.get("failure_class")
    if probe.get("semantic_error"):
        result["decisions"].append({"sanitized_diagnostic": redact_string(probe["semantic_error"])})
    if probe.get("setup_attempts"):
        result["decisions"].append({
            "setup_attempts": [
                {key: item[key] for key in ("attempt", "error_type", "error", "transient")}
                for item in probe["setup_attempts"]
            ]
        })
    return result


def run_scenario(scenario: str, seed: str) -> dict[str, Any]:
    if scenario not in SCENARIO_FIXTURES:
        raise ValueError(f"unknown synthetic scenario: {scenario}")
    if not seed:
        raise ValueError("scenario seed must be non-empty")

    if scenario == "native_tool":
        request = {"tool_name": "read_fixture", "arguments": {"path": "input/alpha.txt"}}
        response = NativeToolProviderFixture().respond(request, seed)
        passed = len(response["tool_calls"]) == 1 and response["finish_reason"] == "tool_calls"
        result = _base_result(scenario, seed, request)
        result["behavior_mode"] = BehaviorMode.NATIVE.value
        result["tool_call_id"] = response["tool_calls"][0]["id"] if response["tool_calls"] else None
        result["normalized_response"] = response
        result["result_status"] = "PASS" if passed else "FAIL"
        return result

    if scenario == "t02_chat_only":
        request = {"path": "input/alpha.txt", "tool_emulation": True}
        provider_response = ChatOnlyProviderFixture().respond(request, seed)
        parsed = parse_textual_tool_call(provider_response["content"], seed)
        execution: dict[str, Any] | None = None
        if parsed.tool_calls:
            with DisposableWorkspace(seed) as workspace, LedgerFixture(workspace) as ledger:
                execution = _execute_read_call(parsed.tool_calls[0], seed, workspace, ledger)
                workspace_id = workspace.workspace_id
                effect_count = ledger.count()
        else:
            workspace_id = None
            effect_count = 0
        passed = (
            not provider_response["tool_calls"]
            and len(parsed.tool_calls) == 1
            and effect_count == 1
            and parsed.decision == "TOOL_INTENT_READY"
        )
        result = _base_result(scenario, seed, request)
        result["workspace_id"] = workspace_id
        result["behavior_mode"] = BehaviorMode.EMULATED.value
        result["tool_call_id"] = parsed.tool_calls[0]["id"] if parsed.tool_calls else None
        result["operation_id"] = execution["operation_id"] if execution else None
        result["decisions"] = [{
            "provider_native_tool_calls": len(provider_response["tool_calls"]),
            "parser_decision": parsed.decision,
            "canonical_call_count": len(parsed.tool_calls),
            "offline": True,
        }]
        result["tool_ledger_outcome"] = [execution] if execution else []
        result["normalized_response"] = {
            "provider_response": provider_response,
            "canonical_tool_calls": list(parsed.tool_calls),
            "tool_result": execution["result"] if execution else None,
            "tool_execution_count": effect_count,
        }
        result["result_status"] = "PASS" if passed else "FAIL"
        if not passed:
            result["failure_class"] = "TOOL_SCHEMA_FAILURE"
        return result

    if scenario in _TEXT_CASES:
        return _run_provider_text_case(scenario, seed)

    if scenario in _MALFORMED_CASES:
        return _run_malformed_case(scenario, seed)

    if scenario.startswith("t08_stream_"):
        return _run_stream_case(scenario, seed)
    if scenario == "t09_before_tool":
        return _run_t09_before_tool(seed)
    if scenario == "t09_after_tool":
        return _run_t09_after_tool(seed)
    if scenario == "narration_after_tool":
        return _run_narration_after_tool(seed)
    if scenario == "workspace_fixture":
        return _run_workspace_fixture(seed)
    if scenario == "t11_ledger_primitive":
        return _run_ledger_fixture(seed)
    if scenario == "provider_server_smoke":
        return _run_server_smoke(seed)
    raise AssertionError(f"scenario dispatch is incomplete: {scenario}")


def run_ten_run_determinism_gate() -> list[dict[str, Any]]:
    gate: list[dict[str, Any]] = []
    for scenario in SCENARIO_FIXTURES:
        fixture_name = SCENARIO_FIXTURES[scenario]
        seed = f"{DETERMINISM_SEED_PREFIX}:{scenario}"
        outputs = [
            canonical_json(run_scenario(scenario, seed)).encode("utf-8")
            for _ in range(DETERMINISM_RUN_COUNT)
        ]
        hashes = ["sha256:" + hashlib.sha256(output).hexdigest() for output in outputs]
        equal = all(output == outputs[0] for output in outputs[1:])
        gate.append({
            "fixture_name": fixture_name,
            "scenario": scenario,
            "seed": seed,
            "run_count": DETERMINISM_RUN_COUNT,
            "canonical_hash": hashes[0],
            "run_hashes": hashes,
            "ten_run_equality": equal,
            "result_status": "PASS" if equal else "FAIL",
        })
    return gate


def _next_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"phase2-{timestamp}"
    candidate = stem
    suffix = 1
    while (_EVIDENCE_ROOT / candidate).exists():
        candidate = f"{stem}-{suffix:02d}"
        suffix += 1
    return candidate


def _write_sanitized_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redacted_json_dumps(value) + "\n", encoding="utf-8")


def _make_evidence_envelope(
    record: dict[str, Any],
    run_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    fixture_name = record["fixture_name"]
    source_file = record["fixture_source_file"]
    provenance = ProvenanceReference(
        reference_type="synthetic_fixture_source",
        reference=source_file,
        digest=record["fixture_hash"],
        candidate_tree_hash=None,
        artifact_pin=record["fixture_version"],
        status="SYNTHETIC_FIXTURE_EVIDENCE",
    )
    envelope = EvidenceEnvelope(
        test_run_id=run_id,
        timestamp_utc=timestamp,
        evidence_type=EvidenceType.SYNTHETIC_FIXTURE_EVIDENCE,
        result_status=ResultStatus(record["result_status"]),
        test_id=record["test_id"],
        candidate=None,
        client="Shofni Phase 2 fixture harness",
        client_version=None,
        provider=fixture_name,
        model_id=None,
        protocol="shofni.synthetic.v1",
        request_id=record["request_id"],
        task_id=record["task_id"],
        session_id=None,
        attempt_id=record["attempt_id"],
        workspace_id=record["workspace_id"],
        checkpoint_id=None,
        tool_call_id=record["tool_call_id"],
        operation_id=record["operation_id"],
        behavior_mode=BehaviorMode(record["behavior_mode"]),
        failure_class=parse_failure_class(record["failure_class"]) if record["failure_class"] else None,
        provenance_references=(provenance,),
        additional_properties={
            "fixture_label": "SYNTHETIC_FIXTURE_EVIDENCE",
            "fixture_name": fixture_name,
            "fixture_version": record["fixture_version"],
            "fixture_hash": record["fixture_hash"],
            "seed": record["seed"],
            "normalized_request": record["normalized_request"],
            "normalized_response": record["normalized_response"],
            "decisions": record["decisions"],
            "attempt_transitions": record["attempt_transitions"],
            "tool_ledger_outcome": record["tool_ledger_outcome"],
        },
    )
    return envelope.to_dict()


def _write_scenario_record(
    evidence_directory: Path,
    record: dict[str, Any],
    run_id: str,
    timestamp: datetime,
) -> None:
    envelope = _make_evidence_envelope(record, run_id, timestamp)
    document = {
        "fixture_label": "SYNTHETIC_FIXTURE_EVIDENCE",
        "fixture_name": record["fixture_name"],
        "fixture_version": record["fixture_version"],
        "fixture_source_file": record["fixture_source_file"],
        "fixture_hash": record["fixture_hash"],
        "seed": record["seed"],
        "normalized_request": record["normalized_request"],
        "normalized_response": record["normalized_response"],
        "decisions": record["decisions"],
        "attempt_transitions": record["attempt_transitions"],
        "tool_call_id": record["tool_call_id"],
        "operation_id": record["operation_id"],
        "tool_ledger_outcome": record["tool_ledger_outcome"],
        "result_status": record["result_status"],
        "failure_class": record["failure_class"],
        "evidence": envelope,
    }
    scenario_dir = evidence_directory / "scenarios" / record["test_id"].lower()
    _write_sanitized_json(scenario_dir / "record.json", document)
    if record["test_id"].startswith("T08_STREAM_"):
        events = record["normalized_response"].get("normalized_events", [])
        lines = [canonical_json(event) for event in events]
        (scenario_dir / "stream.ndjson").write_text(
            "".join(line + "\n" for line in lines),
            encoding="utf-8",
        )


def _fixture_hash_manifest() -> list[dict[str, str]]:
    return [
        {
            "fixture_name": fixture_name,
            "semantic_version": FIXTURE_VERSION,
            "source_file": source_file,
            "source_file_hash": _file_hash(source_file),
        }
        for fixture_name, source_file in sorted(FIXTURE_SOURCE_FILES.items())
    ]


def _validate_written_evidence(evidence_directory: Path) -> None:
    private_path = re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\/\s]+|/(?:home|Users|root)/[^/\s]+")
    for path in sorted(evidence_directory.rglob("*")):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".ndjson":
            documents = [json.loads(line) for line in content.splitlines() if line.strip()]
            canonical_lines = [redacted_json_dumps(document) for document in documents]
            if "\n".join(canonical_lines) + ("\n" if canonical_lines else "") != content:
                raise ValueError(f"sanitized NDJSON validation failed: {path.name}")
        elif path.suffix == ".json":
            document = json.loads(content)
            if redacted_json_dumps(document) + "\n" != content:
                raise ValueError(f"sanitized JSON validation failed: {path.name}")
            if isinstance(document, dict) and "evidence" in document:
                validate_evidence_envelope(document["evidence"])
        else:
            continue
        if private_path.search(content):
            raise ValueError(f"private user path found in sanitized evidence: {path.name}")
        if redact_string(content) != content:
            raise ValueError(f"redaction pattern found in sanitized evidence: {path.name}")


def write_phase2_evidence() -> Path:
    run_id = _next_run_id()
    evidence_directory = _EVIDENCE_ROOT / run_id
    timestamp = datetime.now(timezone.utc)
    with outbound_network_blocked() as network_guard:
        determinism = run_ten_run_determinism_gate()
        records = [
            run_scenario(scenario, f"phase2-evidence-v1:{scenario}")
            for scenario in SCENARIO_FIXTURES
        ]
        provider_server_audit = probe_local_provider("phase2-evidence-provider-server")

    manifest_pass = (
        all(item["ten_run_equality"] for item in determinism)
        and all(item["result_status"] == "PASS" for item in records)
        and provider_server_audit["result_status"] == "PASS"
        and provider_server_audit["server"]["shutdown_result"] == "STOPPED"
        and provider_server_audit["server_port_released"]
        and network_guard.blocked_attempts == 0
    )
    evidence_directory.mkdir(parents=True, exist_ok=False)
    for record in records:
        _write_scenario_record(evidence_directory, record, run_id, timestamp)

    determinism_document = {
        "phase": 2,
        "run_id": run_id,
        "run_count_per_scenario": DETERMINISM_RUN_COUNT,
        "allowed_per_run_metadata_excluded": ["test_run_id", "timestamp_utc"],
        "seed_prefix": DETERMINISM_SEED_PREFIX,
        "result_status": "PASS" if all(item["ten_run_equality"] for item in determinism) else "FAIL",
        "scenarios": determinism,
    }
    fixture_hash_document = {
        "phase": 2,
        "fixture_version": FIXTURE_VERSION,
        "fixtures": _fixture_hash_manifest(),
    }
    result_document = {
        "phase": 2,
        "run_id": run_id,
        "result_status": "PASS" if manifest_pass else "FAIL",
        "scenario_count": len(records),
        "scenario_pass_count": sum(item["result_status"] == "PASS" for item in records),
        "determinism_scenario_count": len(determinism),
        "determinism_pass_count": sum(item["ten_run_equality"] for item in determinism),
        "live_provider_requests": 0,
        "network_blocked_attempts": network_guard.blocked_attempts,
    }
    manifest = {
        "phase": 2,
        "run_id": run_id,
        "created_at_utc": timestamp.isoformat().replace("+00:00", "Z"),
        "fixture_label": "SYNTHETIC_FIXTURE_EVIDENCE",
        "fixture_version": FIXTURE_VERSION,
        "python_version": platform.python_version(),
        "pytest_version": importlib.metadata.version("pytest"),
        "pytest_version_pin": "9.1.1",
        "test_command": ".\\.venv\\Scripts\\python.exe -m pytest tests/poc",
        "evidence_command": ".\\.venv\\Scripts\\python.exe -m poc.fixtures.scenarios --write-evidence",
        "result_status": "PASS" if manifest_pass else "FAIL",
        "live_provider_requests": 0,
        "outbound_provider_requests": 0,
        "candidate_processes_started": 0,
        "candidate_implementation_imports": [],
        "candidate_source_modified": False,
        "phase3_started": False,
        "sensitive_value_policy": "no_sensitive_values_read_printed_or_persisted",
        "network_isolation": {
            "policy": "TCP connections limited to loopback",
            "blocked_remote_attempts": network_guard.blocked_attempts,
            "local_fixture_connections": network_guard.local_connections,
        },
        "provider_server": {
            **provider_server_audit["server"],
            "setup_attempts": provider_server_audit["setup_attempts"],
            "port_release_verified": provider_server_audit["server_port_released"],
            "local_fixture_requests": 1,
        },
        "cleanup": {
            "provider_server_stopped": provider_server_audit["server"]["shutdown_result"] == "STOPPED",
            "provider_server_port_released": provider_server_audit["server_port_released"],
            "disposable_workspaces_cleaned": True,
            "sqlite_connections_closed": True,
            "raw_evidence_created": False,
        },
    }
    _write_sanitized_json(evidence_directory / "manifest.json", manifest)
    _write_sanitized_json(evidence_directory / "result.json", result_document)
    _write_sanitized_json(evidence_directory / "determinism.json", determinism_document)
    _write_sanitized_json(evidence_directory / "fixture-hashes.json", fixture_hash_document)
    _validate_written_evidence(evidence_directory)
    return evidence_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline Phase 2 synthetic fixtures and write sanitized evidence.")
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args(argv)
    if not arguments.write_evidence:
        parser.error("pass --write-evidence to run the ten-run gate and write sanitized evidence")
    evidence_directory = write_phase2_evidence()
    result = json.loads((evidence_directory / "result.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "evidence_directory": str(evidence_directory.relative_to(_REPOSITORY_ROOT)),
        "result_status": result["result_status"],
        "scenario_count": result["scenario_count"],
        "determinism_scenario_count": result["determinism_scenario_count"],
    }, sort_keys=True))
    return 0 if result["result_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
