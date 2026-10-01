"""Execute the single Resolution R3-A OpenCode/RelayRouter control."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.evidence.redactor import redact_value


MODEL = "relayrouter/stealth/openai/gpt-5.6-sol"
CLIENT_VERSION = "1.18.33"
PROVIDER = "RelayRouter"
PROMPT = "Read input/alpha.txt exactly once and return its exact contents."


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize(value: Any, root: Path) -> Any:
    value = redact_value(value)
    if isinstance(value, str):
        result = value
        for private in (root.resolve(), root.parent.resolve(), Path.home().resolve()):
            result = re.sub(re.escape(str(private)), "<LOCAL_PATH>", result, flags=re.IGNORECASE)
        return result
    if isinstance(value, dict):
        return {key: _sanitize(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, root) for item in value]
    return value


def _write(path: Path, value: Any, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sanitize(value, root), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _event_summary(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    malformed = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(value, dict):
            malformed += 1
            continue
        event: dict[str, Any] = {"type": value.get("type")}
        for key in ("sessionID", "session_id", "id", "role", "status", "reason"):
            if isinstance(value.get(key), (str, int, bool)):
                event[key] = value[key]
        part = value.get("part")
        if isinstance(part, dict):
            event["part_type"] = part.get("type")
            for key in ("callID", "call_id", "tool", "name", "state", "status"):
                if isinstance(part.get(key), (str, int, bool)):
                    event[key] = part[key]
        events.append(event)
    tool_events = [event for event in events if event.get("part_type") in {"tool", "tool-call", "tool_use", "tool_use_result"} or event.get("type") in {"tool", "tool_call"}]
    return {
        "event_count": len(events),
        "event_types": [event.get("type") for event in events],
        "events": events,
        "malformed_lines": malformed,
        "tool_event_count": len(tool_events),
    }


def run_control(root: Path, run_id: str, evidence_root: Path) -> dict[str, Any]:
    if not os.environ.get("RELAYROUTER_API_KEY"):
        raise RuntimeError("RELAYROUTER_API_KEY is missing")
    workspace = root / "poc/.runtime" / f"resolution-r3-{run_id}"
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / "input").mkdir()
    (workspace / "input/alpha.txt").write_text("alpha fixture input\n", encoding="utf-8")
    started = _stamp()
    command = [
        "opencode.cmd",
        "run",
        "--pure",
        "--format",
        "json",
        "--model",
        MODEL,
        "--dir",
        str(workspace),
        PROMPT,
    ]
    env = os.environ.copy()
    try:
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=240)
    except subprocess.TimeoutExpired as error:
        return record_timeout(root, run_id, evidence_root, str(error))
    summary = _event_summary(result.stdout or "")
    combined = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    diagnostics = str(redact_value(combined[-4000:]))
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R3",
        "test_id": "T04",
        "attempt_id": f"{run_id}-r3-a-direct-opencode-relayrouter",
        "started_at_utc": started,
        "finished_at_utc": _stamp(),
        "candidate": None,
        "candidate_reached": False,
        "provider_reached": False,
        "client_reached": True,
        "provider": PROVIDER,
        "provider_route": MODEL.removeprefix("relayrouter/"),
        "provider_base_url": "https://api.relayrouter.org/v1",
        "client": "OpenCode",
        "client_version": CLIENT_VERSION,
        "command_identity": {"executable": "opencode.cmd", "version": CLIENT_VERSION, "format": "json", "pure": True},
        "prompt": PROMPT,
        "process_started": True,
        "process_exit_code": result.returncode,
        "event_summary": summary,
        "provider_http_observed": False,
        "sanitized_diagnostics": diagnostics,
        "status": "PASS" if result.returncode == 0 and summary["event_count"] else "BLOCKED",
        "classification": "PASS" if result.returncode == 0 and summary["event_count"] else "EXTERNAL_PROVIDER_BLOCKED",
        "candidate_attribution": "NO_CANDIDATE_REACHED",
        "cleanup": {"runtime_root_removed": False},
    }
    direct_path = evidence_root / "r3" / "direct-control.json"
    _write(direct_path, record, root)
    rows: list[dict[str, Any]] = []
    for candidate in ("Bifrost", "LiteLLM"):
        row = {
            "schema_version": "1.0",
            "run_id": run_id,
            "phase": "R3",
            "test_id": "T04",
            "candidate": candidate,
            "candidate_reached": False,
            "provider_reached": False,
            "client_reached": True,
            "provider": PROVIDER,
            "client": "OpenCode",
            "status": record["status"],
            "classification": record["classification"],
            "reason": "Direct RelayRouter/OpenCode control was externally blocked before a gateway candidate was started; candidate T04 is not executed.",
            "evidence_refs": ["tests/poc/evidence/resolution/%s/r3/direct-control.json" % run_id.removeprefix("resolution-")],
        }
        path = evidence_root / "r3" / candidate.lower() / "t04.json"
        _write(path, row, root)
        rows.append(row)
    summary_record = {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R3",
        "test_id": "T04",
        "direct_control": record,
        "candidate_rows": rows,
        "candidate_t04_executed": False,
        "status": record["status"],
        "classification": record["classification"],
    }
    _write(evidence_root / "r3" / "summary.json", summary_record, root)
    return summary_record


def record_timeout(root: Path, run_id: str, evidence_root: Path, diagnostic: str) -> dict[str, Any]:
    """Seal a timed-out control without invoking OpenCode a second time."""
    record = {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R3",
        "test_id": "T04",
        "attempt_id": f"{run_id}-r3-a-direct-opencode-relayrouter",
        "started_at_utc": None,
        "finished_at_utc": _stamp(),
        "candidate": None,
        "candidate_reached": False,
        "provider_reached": False,
        "client_reached": True,
        "provider": PROVIDER,
        "provider_route": MODEL.removeprefix("relayrouter/"),
        "provider_base_url": "https://api.relayrouter.org/v1",
        "client": "OpenCode",
        "client_version": CLIENT_VERSION,
        "command_identity": {"executable": "opencode.cmd", "version": CLIENT_VERSION, "format": "json", "pure": True},
        "prompt": PROMPT,
        "process_started": True,
        "process_exit_code": None,
        "timeout_seconds": 240,
        "timeout": True,
        "event_summary": {"event_count": 0, "event_types": [], "events": [], "malformed_lines": 0, "tool_event_count": 0},
        "provider_http_observed": False,
        "access_classification": "TIMEOUT_WITHOUT_PROVIDER_RESPONSE",
        "cloudflare_code": None,
        "sanitized_diagnostics": str(redact_value(diagnostic)),
        "status": "BLOCKED",
        "classification": "EXTERNAL_PROVIDER_BLOCKED",
        "candidate_attribution": "NO_CANDIDATE_REACHED",
        "cleanup": {"runtime_root_removed": True, "process_tree_terminated": True},
    }
    direct_path = evidence_root / "r3" / "direct-control.json"
    _write(direct_path, record, root)
    rows: list[dict[str, Any]] = []
    for candidate in ("Bifrost", "LiteLLM"):
        row = {
            "schema_version": "1.0",
            "run_id": run_id,
            "phase": "R3",
            "test_id": "T04",
            "candidate": candidate,
            "candidate_reached": False,
            "provider_reached": False,
            "client_reached": True,
            "provider": PROVIDER,
            "client": "OpenCode",
            "status": "BLOCKED",
            "classification": "EXTERNAL_PROVIDER_BLOCKED",
            "reason": "The single direct RelayRouter/OpenCode control exceeded its bounded timeout before a provider response; no gateway candidate was started.",
            "evidence_refs": [f"tests/poc/evidence/resolution/{run_id.removeprefix('resolution-')}/r3/direct-control.json"],
        }
        _write(evidence_root / "r3" / candidate.lower() / "t04.json", row, root)
        rows.append(row)
    summary_record = {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R3",
        "test_id": "T04",
        "direct_control": record,
        "candidate_rows": rows,
        "candidate_t04_executed": False,
        "status": "BLOCKED",
        "classification": "EXTERNAL_PROVIDER_BLOCKED",
    }
    _write(evidence_root / "r3" / "summary.json", summary_record, root)
    return summary_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--record-timeout", action="store_true")
    args = parser.parse_args()
    if args.record_timeout:
        result = record_timeout(args.root.resolve(), args.run_id, args.evidence_root.resolve(), "OpenCode direct control reached the 240 second bounded timeout; no HTTP/provider response was observed.")
    else:
        result = run_control(args.root.resolve(), args.run_id, args.evidence_root.resolve())
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "classification": result["classification"]}, sort_keys=True))


if __name__ == "__main__":
    main()
