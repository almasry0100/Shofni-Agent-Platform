"""Opt-in Batch D Phase 11 gateway/runtime composition runner.

The runner keeps the gateway alive while two separate OpenHands child
processes execute model A and restore/model B. Provider credentials stay in
the gateway container environment and are never passed to the runtime child.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from poc.adapters.bifrost_http import BifrostHTTPBackend
from poc.adapters.litellm_http import LiteLLMHTTPBackend
from poc.evidence.redactor import redact_value


RUN_ID_PREFIX = "batch-d-composition-"
MODEL_A = "gpt-5.4-mini"
MODEL_B = "gpt-5.5"
BIFROST_IMAGE = "docker.io/library/golang:1.27.0-bookworm@sha256:ba5ef6614ca131b80a635fc6a7b715d9ee8a7f333debdbb81afb68259c7d48d4"
LITELLM_IMAGE = "shofni-litellm-oss-remediation:1.104.0@sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280"
BIFROST_ARTIFACT = "poc/.runtime/bifrost/artifacts-remediation/bifrost-http"
LITELLM_WHEEL = "poc/.runtime/litellm/artifacts/litellm-1.104.0-cp310-abi3-manylinux_2_34_x86_64.whl"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact_value(value), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _run(command: list[str], *, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {command[0]}")
    return result


def _tail_text(value: str, limit: int = 4000, root: Path | None = None) -> str:
    result = str(redact_value(value[-limit:]))
    if root is not None:
        for private_root in (root.resolve(), root.parent.resolve(), Path.home().resolve()):
            result = re.sub(re.escape(str(private_root)), "<LOCAL_PATH>", result, flags=re.IGNORECASE)
    return result


def _docker_bind_mount(source: Path, target: str, *, readonly: bool = False) -> str:
    mount = f"type=bind,source={source.resolve()},target={target}"
    return mount + (",readonly" if readonly else "")


def _matches_model_route(model_id: object, requested_model: str) -> bool:
    if not isinstance(model_id, str):
        return False
    return model_id == requested_model or model_id.rsplit("/", 1)[-1] == requested_model


def _route_probe(models: list[dict[str, Any]], requested_models: tuple[str, ...]) -> dict[str, Any]:
    model_ids = sorted(str(item["id"]) for item in models if isinstance(item.get("id"), str) and item["id"])
    missing = [requested for requested in requested_models if not any(_matches_model_route(item.get("id"), requested) for item in models)]
    return {
        "status": "PASS" if not missing else "FAIL",
        "model_ids": model_ids,
        "requested_routes": list(requested_models),
        "missing_routes": missing,
        "selected_routes_present": not missing,
    }


def _validate_runtime_gateway_url(url: str, container: str, internal_port: int) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != container or parsed.port != internal_port:
        raise ValueError("OpenHands runtime must use the gateway container DNS name and internal port")


def _process_diagnostic(result: subprocess.CompletedProcess[str], root: Path | None = None) -> dict[str, Any]:
    return {
        "exit_code": result.returncode,
        "stdout_tail": _tail_text(result.stdout or "", root=root),
        "stderr_tail": _tail_text(result.stderr or "", root=root),
    }


def _stop_container(name: str) -> None:
    _run(["docker", "stop", "--time", "8", name])
    _run(["docker", "rm", "--force", name])


def _docker_logs(name: str) -> str:
    result = _run(["docker", "logs", name])
    return redact_value((result.stdout or "") + (result.stderr or ""))


def _bifrost_config() -> dict[str, Any]:
    key = {
        "name": "shofni-a6api",
        "value": "env.A6API_KEY",
        "weight": 1.0,
        "models": [MODEL_A, MODEL_B],
    }
    provider = {
        "keys": [key],
        "network_config": {
            "base_url": "https://api.a6api.com",
            "default_request_timeout_in_seconds": 90,
            "max_retries": 0,
            "allow_private_network": False,
        },
    }
    return {
        "version": 2,
        "providers": {"openai": provider},
        "framework": {"pricing": {
            "pricing_url": "file:///data/pricing.json",
            "model_parameters_url": "file:///data/model-parameters.json",
            "mcp_library_sync_interval": 0,
            "live_models_sync_interval": 0,
        }},
        "config_store": {"enabled": False},
        "logs_store": {"enabled": False},
        "client": {"disable_db_pings_in_health": True},
    }


def _litellm_config() -> str:
    return "\n".join([
        "model_list:",
        f"  - model_name: {MODEL_A}",
        "    litellm_params:",
        f"      model: openai/{MODEL_A}",
        "      api_base: https://api.a6api.com",
        "      api_key: os.environ/A6API_KEY",
        f"  - model_name: {MODEL_B}",
        "    litellm_params:",
        f"      model: openai/{MODEL_B}",
        "      api_base: https://api.a6api.com",
        "      api_key: os.environ/A6API_KEY",
        "general_settings:",
        "  disable_spend_logs: true",
        "litellm_settings:",
        "  num_retries: 0",
        "  request_timeout: 90",
        "",
    ])


def _start_gateway(root: Path, gateway: str, run_id: str, temp_root: Path, network: str) -> tuple[Any, str, str, str, str]:
    if not os.environ.get("A6API_KEY"):
        raise RuntimeError("A6API_KEY is missing")
    suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{gateway}".lower())[-45:]
    container = f"shofni-d-gateway-{suffix}"
    port = _port()
    if gateway == "Bifrost":
        app_dir = temp_root / "bifrost-app"
        config = _bifrost_config()
        backend = BifrostHTTPBackend(
            artifact_dir=(root / BIFROST_ARTIFACT).parent,
            app_dir=app_dir,
            image_ref=BIFROST_IMAGE,
            network_name=network,
            provider_url="https://api.a6api.com",
            host_port=port,
            container_name=container,
            provider_config=config,
            environment={"A6API_KEY": None},
        )
        base_url_suffix = "/openai/v1"
    else:
        config_dir = temp_root / "litellm-config"
        config_dir.mkdir(parents=True, exist_ok=False)
        (config_dir / "config.yaml").write_text(_litellm_config(), encoding="utf-8", newline="\n")
        backend = LiteLLMHTTPBackend(
            config_dir=config_dir,
            image_ref=LITELLM_IMAGE,
            network_name=network,
            host_port=port,
            container_name=container,
            environment={"A6API_KEY": None},
        )
        base_url_suffix = "/v1"
    try:
        backend.start()
    except BaseException as error:
        startup_result = getattr(backend, "_startup_process_result", None)
        diagnostics = _process_diagnostic(startup_result, root) if startup_result is not None else {
            "exit_code": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }
        diagnostics["gateway_readiness"] = "FAIL"
        try:
            diagnostics["container_logs_tail"] = _tail_text(_docker_logs(container), 8000, root)
        except Exception as log_error:
            diagnostics["container_logs_error"] = type(log_error).__name__
        inspect = _run(["docker", "inspect", "--format", "{{.State.Status}}|{{.State.ExitCode}}", container])
        if inspect.returncode == 0:
            state, _, exit_code = inspect.stdout.strip().partition("|")
            diagnostics["container_state"] = state
            diagnostics["container_exit_code"] = int(exit_code) if exit_code.isdigit() else None
        else:
            diagnostics["container_state"] = "UNAVAILABLE"
            diagnostics["container_exit_code"] = None
        _stop_container(container)
        _run(["docker", "network", "rm", network])
        wrapped = RuntimeError(f"gateway startup failed: {type(error).__name__}")
        wrapped.startup_diagnostics = diagnostics
        raise wrapped from error
    internal_port = 8080 if gateway == "Bifrost" else 4000
    internal_url = f"http://{container}:{internal_port}{base_url_suffix}"
    return backend, network, container, backend.base_url + base_url_suffix, internal_url


def _validate_live_inputs(root: Path) -> None:
    if not os.environ.get("A6API_KEY"):
        raise RuntimeError("A6API_KEY is missing")
    bifrost = root / BIFROST_ARTIFACT
    if not bifrost.is_file() or _sha256(bifrost) != "sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5":
        raise RuntimeError("Bifrost artifact does not match sealed provenance")
    wheel = root / LITELLM_WHEEL
    if not wheel.is_file() or _sha256(wheel) != "sha256:762b286fe81491f242040b14f28338da0ebf4f32fea50972b6969ee578011d52":
        raise RuntimeError("LiteLLM wheel does not match sealed provenance")
    inventory = (root / "docs/a6api-models.md").read_text(encoding="utf-8")
    if MODEL_A not in inventory or MODEL_B not in inventory:
        raise RuntimeError("selected A6api routes are absent from the committed inventory")


def _run_openhands(root: Path, runtime_image: str, network: str, runtime_root: Path, evidence_root: Path, gateway_url: str, attempt_id: str) -> tuple[int, int, dict[str, Any]]:
    env = os.environ.copy()
    env.pop("A6API_KEY", None)
    env.pop("A6API_BASE_URL", None)
    env["PYTHONPATH"] = "/workspace"
    mounted_evidence = _docker_bind_mount(evidence_root, "/evidence")
    mounted_runtime = _docker_bind_mount(runtime_root, "/runtime")
    source_mount = _docker_bind_mount(root, "/workspace", readonly=True)
    command = ["docker", "run", "--rm", "--network", network, "--platform", "linux/amd64", "--mount", source_mount, "--mount", mounted_evidence, "--mount", mounted_runtime, "--env", "PYTHONPATH=/workspace", "--env", f"SHOFNI_ATTEMPT_ID={attempt_id}", runtime_image, "/opt/openhands/bin/python", "-m", "poc.runners.openhands_level3_live"]
    first_command = command + ["--stage", "model-a", "--runtime-root", "/runtime", "--evidence-root", "/evidence", "--model-a", MODEL_A, "--base-url", gateway_url, "--gateway-mode"]
    first = subprocess.run(
        first_command,
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=300,
    )
    diagnostics: dict[str, Any] = {
        "model_a": _process_diagnostic(first, root),
    }
    if not (evidence_root / "model-a-state.json").is_file():
        return first.returncode, -1, {
            "error_type": "RuntimeSetupFailure",
            "error": "model A did not produce checkpoint evidence",
            "process_diagnostics": diagnostics,
        }
    second_command = command + ["--stage", "restore", "--runtime-root", "/runtime", "--evidence-root", "/evidence", "--model-b", MODEL_B, "--base-url", gateway_url, "--gateway-mode"]
    second = subprocess.run(
        second_command,
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=300,
    )
    diagnostics["restore"] = _process_diagnostic(second, root)
    if not (evidence_root / "restored-state.json").is_file():
        return first.returncode, second.returncode, {
            "error_type": "RuntimeSetupFailure",
            "error": "restore process did not produce restored-state evidence",
            "process_diagnostics": diagnostics,
        }
    before = json.loads((evidence_root / "model-a-state.json").read_text(encoding="utf-8"))
    after = json.loads((evidence_root / "restored-state.json").read_text(encoding="utf-8"))
    result = {
        "attempt_id": attempt_id,
        "provider": "A6api",
        "model_a": MODEL_A,
        "model_b": MODEL_B,
        "task_id": before["task_id"],
        "task_id_after_restart": after["task_state"]["task_id"],
        "workspace_id": before["workspace_id"],
        "session_id": before["session_id"],
        "session_id_after_restart": after["task_state"]["session_id"],
        "attempt_id_before_restart": before["attempt_id"],
        "attempt_id_after_restart": after["task_state"]["attempt_id"],
        "workspace_id_after_restart": after["task_state"]["workspace_id"],
        "checkpoint_id": before["checkpoint_id"],
        "candidate_conversation_id": before["candidate_conversation_id"],
        "tool_results": after["tool_results"],
        "candidate_events": after["candidate_events"],
        "final_result": after["final_result"],
        "model_a_process_exit_code": first.returncode,
        "restore_process_exit_code": second.returncode,
        "process_diagnostics": diagnostics,
    }
    return first.returncode, second.returncode, result


def _pair(root: Path, evidence_root: Path, gateway: str, run_id: str) -> dict[str, Any]:
    pair_root = evidence_root / f"{gateway.lower()}-openhands"
    pair_root.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    runtime_root = root / "poc/.runtime" / f"batch-d-{run_id}-{gateway.lower()}-runtime"
    gateway_obj = None
    network = container = gateway_url = internal_gateway_url = runtime_image = None
    temp_parent = root / "poc/.runtime" / f"batch-d-{run_id}-{gateway.lower()}"
    temp_parent.mkdir(parents=True, exist_ok=False)
    setup_context: dict[str, Any] = {"gateway": gateway, "network": None, "runtime_image": None}
    try:
        suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{gateway}".lower())[-45:]
        network = f"shofni-d-{suffix}"
        setup_context["network"] = network
        _run(["docker", "network", "create", network], check=True)
        runtime_image = f"shofni-openhands-phase11:{run_id}"
        setup_context["runtime_image"] = runtime_image
        candidate_root = root.parent / "software-agent-sdk-main"
        dockerfile = root / "poc/.runtime/openhands/phase11-env/Dockerfile"
        build = _run(["docker", "build", "--platform", "linux/amd64", "--file", str(dockerfile), "--tag", runtime_image, str(candidate_root)])
        if build.returncode != 0:
            setup_context["runtime_build"] = _process_diagnostic(build, root)
            raise RuntimeError("pinned OpenHands environment build failed")
        setup_context["runtime_build"] = _process_diagnostic(build, root)
        try:
            gateway_obj, network, container, gateway_url, internal_gateway_url = _start_gateway(root, gateway, run_id, temp_parent, network)
            setup_context["gateway_readiness"] = {"status": "PASS", "container": container}
            startup_result = getattr(gateway_obj, "_startup_process_result", None)
            setup_context["gateway_startup"] = _process_diagnostic(startup_result, root) if startup_result is not None else {
                "exit_code": None,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        except Exception as error:
            setup_context["gateway_readiness"] = {"status": "FAIL", "error_type": type(error).__name__, "error": _tail_text(str(error), root=root)}
            if hasattr(error, "startup_diagnostics"):
                setup_context["gateway_startup"] = error.startup_diagnostics
            raise
        setup_context.update({"container": container, "host_gateway_url": gateway_url, "runtime_gateway_url": internal_gateway_url})
        try:
            listed_models = gateway_obj.list_models()
            setup_context["gateway_probe"] = _route_probe(listed_models, (MODEL_A, MODEL_B))
        except Exception as error:
            setup_context["gateway_probe"] = {"status": "FAIL", "error_type": type(error).__name__, "error": _tail_text(str(error), root=root)}
            raise
        if setup_context["gateway_probe"]["status"] != "PASS":
            raise RuntimeError("selected A6api model routes are unavailable at the gateway")
        internal_port = 8080 if gateway == "Bifrost" else 4000
        _validate_runtime_gateway_url(internal_gateway_url, container, internal_port)
        try:
            first_exit, second_exit, live = _run_openhands(root, runtime_image, network, runtime_root, pair_root, internal_gateway_url, f"{run_id}-{gateway.lower()}-openhands")
        except Exception as error:
            first_exit, second_exit, live = -1, -1, {"error_type": type(error).__name__, "error": _tail_text(str(error), root=root), "process_diagnostics": {}}
            setup_context["runtime_execution"] = {"error_type": type(error).__name__, "error": _tail_text(str(error), root=root)}
        if live.get("error_type"):
            setup_context["runtime_execution"] = {"error_type": live.get("error_type"), "error": live.get("error"), "model_a_exit_code": first_exit, "restore_exit_code": second_exit}
        elif live.get("process_diagnostics"):
            setup_context["runtime_startup"] = {
                stage: {"status": "PASS" if diagnostic.get("exit_code") == 0 else "FAIL", **diagnostic}
                for stage, diagnostic in live["process_diagnostics"].items()
            }
        if live.get("process_diagnostics"):
            _write(pair_root / "process-diagnostics.json", live["process_diagnostics"])
        if "task_id" in live:
            _write(pair_root / "task-before.json", {key: live[key] for key in ("task_id", "workspace_id", "session_id", "attempt_id_before_restart", "model_a")})
            _write(pair_root / "task-after.json", {key: live[key] for key in ("task_id", "workspace_id", "attempt_id_after_restart", "model_b", "final_result")})
            _write(pair_root / "tool-results.json", live["tool_results"])
            _write(pair_root / "provider-transition.json", {"provider": "A6api", "model_a": MODEL_A, "model_b": MODEL_B, "gateway": gateway})
            (pair_root / "events.ndjson").write_text("".join(json.dumps(redact_value(event), sort_keys=True, ensure_ascii=True) + "\n" for event in live["candidate_events"]), encoding="utf-8")
            action_events = [event for event in live["candidate_events"] if event.get("candidate_event_type") == "ActionEvent"]
            read_actions = [event for event in action_events if event.get("tool_name") == "read_fixture"]
            result_values = list(live["tool_results"].values())
            gates = {
                "model_a_process_exited_cleanly": first_exit == 0,
                "fresh_restore_process_succeeded": second_exit == 0,
                "new_attempt_id_explicit": live["attempt_id_after_restart"] != live["attempt_id_before_restart"],
                "same_task_id": live["task_id"] == live.get("task_id_after_restart", live["task_id"]),
                "same_workspace_id": live["workspace_id"] == live.get("workspace_id_after_restart", live["workspace_id"]),
                "same_session_id": live["session_id"] == live.get("session_id_after_restart", live["session_id"]),
                "model_transition": live["model_a"] == MODEL_A and live["model_b"] == MODEL_B,
                "native_read_fixture_action": len(read_actions) == 1,
                "tool_result_marker": len(result_values) == 1 and result_values[0].get("result") == "alpha\n",
                "tool_result_correlated": len(read_actions) == 1 and len(result_values) == 1 and result_values[0].get("tool_call_id") == read_actions[0].get("tool_call_id"),
                "checkpoint_persisted": bool(live.get("checkpoint_id")),
                "gateway_probe_passed": setup_context.get("gateway_probe", {}).get("status") == "PASS" and setup_context.get("gateway_probe", {}).get("selected_routes_present") is True,
                "successful_final_result": live.get("final_result", "").strip() == "alpha",
                "no_duplicate_tool_execution": len(read_actions) == 1,
            }
            live["gates"] = gates
            status = "PASS" if all(gates.values()) else "FAIL"
            classification = None if status == "PASS" else "COMPOSITION_SEMANTIC_FAILURE"
        else:
            status = "FAIL"
            classification = "SETUP_FAILURE"
        _write(pair_root / "process-exit.json", {"model_a_exit_code": first_exit, "restore_exit_code": second_exit, "fresh_process": True})
        _write(pair_root / "topology.json", {
            "runtime": "OpenHands Software Agent SDK 1.49.6",
            "runtime_base_url": internal_gateway_url,
            "host_gateway_url": gateway_url,
            "gateway_container": container,
            "gateway_network": network,
            "gateway": gateway,
            "gateway_upstream": "https://api.a6api.com",
            "provider": "A6api",
            "direct_provider_bypass": False,
            "runtime_provider_key": "NOT_PRESENT",
        })
        _write(pair_root / "setup.json", setup_context)
        if container:
            _write(pair_root / "gateway-log-tail.json", {"gateway": gateway, "logs": _tail_text(_docker_logs(container), 8000, root)})
        _write(pair_root / "gateway-provenance.json", {"source_ref": "docs/poc/candidate-lock.json", "artifact": BIFROST_ARTIFACT if gateway == "Bifrost" else "runtime image " + LITELLM_IMAGE, "artifact_sha256": "sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5" if gateway == "Bifrost" else "sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280", "source_tree_ref": "docs/poc/candidate-lock.json"})
        _write(pair_root / "runtime-provenance.json", {"source_ref": "tests/poc/evidence/phase-7/phase7-remediation-20261001T045000Z/provenance.json", "candidate": "OpenHands Software Agent SDK", "version": "1.49.6", "source_tree_hash": "sha256:e1258a81a1304726a1622943078907b689fccc524d733838fd57e10665ebd468", "python_image_digest": "sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4", "uv_image_digest": "sha256:733b4042187702f832f7fdecb3aff14a61b288c4ca37af188bb5715c1caebaf8", "runtime_image": runtime_image})
        _write(pair_root / "result.json", {"status": status, "classification": classification, "provider": "A6api", "model_a": MODEL_A, "model_b": MODEL_B, "expected_result": "alpha", "final_result": live.get("final_result"), "gateway": gateway, "runtime": "OpenHands"})
        _write(pair_root / "composition-manifest.json", {"schema_version": "1.0", "run_id": run_id, "pairing": f"{gateway} + OpenHands", "started_at_utc": started, "status": status, "classification": classification, "evidence_class": "LIVE_PROVIDER_EVIDENCE" if status != "BLOCKED" else "SETUP_FAILURE_EVIDENCE", "task_id": live.get("task_id"), "workspace_id": live.get("workspace_id"), "checkpoint_id": live.get("checkpoint_id"), "tool_call_ids": [event.get("tool_call_id") for event in live.get("candidate_events", []) if event.get("tool_call_id")], "provider_transition": {"model_a": MODEL_A, "model_b": MODEL_B}, "setup_diagnostic": "process-diagnostics.json" if (pair_root / "process-diagnostics.json").is_file() else "setup.json"})
        row = {"pairing": f"{gateway} + OpenHands", "status": status, "classification": classification, "evidence_root": str(pair_root.relative_to(root)).replace("\\", "/"), "task_id": live.get("task_id"), "workspace_id": live.get("workspace_id"), "checkpoint_id": live.get("checkpoint_id"), "final_result": live.get("final_result"), "tool_call_ids": [event.get("tool_call_id") for event in live.get("candidate_events", []) if event.get("tool_call_id")], "provider_transition_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{gateway}:A6api:{MODEL_A}:{MODEL_B}"))}
        _write(root / "poc/runs" / f"composition-{gateway.lower()}-openhands" / "manifest.json", {"schema_version": "1.0", "run_id": run_id, "pairing": row["pairing"], "status": status, "classification": classification, "evidence_root": row["evidence_root"], "task_id": row["task_id"], "workspace_id": row["workspace_id"], "checkpoint_id": row["checkpoint_id"], "tool_call_ids": row["tool_call_ids"], "provider_transition_id": row["provider_transition_id"], "commit": False, "push": False})
        return row
    except BaseException as error:
        diagnostic = {
            "error_type": type(error).__name__,
            "error": _tail_text(str(error), root=root),
            "setup_context": setup_context,
        }
        _write(pair_root / "setup.json", diagnostic)
        _write(pair_root / "result.json", {
            "status": "FAIL",
            "classification": "SETUP_FAILURE",
            "provider": "A6api",
            "model_a": MODEL_A,
            "model_b": MODEL_B,
            "expected_result": "alpha",
            "gateway": gateway,
            "runtime": "OpenHands",
        })
        provider_transition_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{gateway}:A6api:{MODEL_A}:{MODEL_B}"))
        row = {
            "pairing": f"{gateway} + OpenHands",
            "status": "FAIL",
            "classification": "SETUP_FAILURE",
            "evidence_root": str(pair_root.relative_to(root)).replace("\\", "/"),
            "task_id": None,
            "workspace_id": None,
            "checkpoint_id": None,
            "tool_call_ids": [],
            "provider_transition_id": provider_transition_id,
            "setup_diagnostic": "setup.json",
        }
        _write(root / "poc/runs" / f"composition-{gateway.lower()}-openhands" / "manifest.json", {
            "schema_version": "1.0",
            "run_id": run_id,
            "pairing": row["pairing"],
            "status": row["status"],
            "classification": row["classification"],
            "evidence_root": row["evidence_root"],
            "setup_diagnostic": row["setup_diagnostic"],
            "provider_transition_id": provider_transition_id,
            "commit": False,
            "push": False,
        })
        return row
    finally:
        cleanup = {"container_removed": False, "network_removed": False, "runtime_root_removed": not runtime_root.exists(), "runtime_image_removed": False, "temporary_root_removed": False}
        if gateway_obj is not None:
            try:
                gateway_obj.stop()
            except Exception:
                pass
        if container:
            _stop_container(container)
            cleanup["container_removed"] = _run(["docker", "inspect", container]).returncode != 0
        if network:
            _run(["docker", "network", "rm", network])
            cleanup["network_removed"] = _run(["docker", "network", "inspect", network]).returncode != 0
        if runtime_root.exists():
            shutil.rmtree(runtime_root, ignore_errors=True)
            cleanup["runtime_root_removed"] = not runtime_root.exists()
        if runtime_image:
            _run(["docker", "image", "rm", "--force", runtime_image])
            cleanup["runtime_image_removed"] = _run(["docker", "image", "inspect", runtime_image]).returncode != 0
        if temp_parent.exists():
            shutil.rmtree(temp_parent, ignore_errors=True)
            cleanup["temporary_root_removed"] = not temp_parent.exists()
        if setup_context.get("runtime_build") and not (pair_root / "setup.json").exists():
            _write(pair_root / "setup.json", setup_context)
        _write(pair_root / "cleanup.json", cleanup)


def _mastra_row(root: Path, evidence_root: Path, gateway: str, run_id: str) -> dict[str, Any]:
    pair = f"{gateway} + Mastra"
    pair_root = evidence_root / f"{gateway.lower()}-mastra"
    _write(pair_root / "blocker.json", {"status": "BLOCKED", "classification": "LICENSE_BOUNDARY_BLOCKER", "candidate": "Mastra", "phase8_evidence": "tests/poc/evidence/phase-8/phase8-closure-20261001T035711Z/closure-report.json", "reason": "Required durable Agent import closure reaches excluded EE-licensed auth modules; no OSS-only durable runtime path satisfies Phase 8 semantics.", "ee_source_used": False})
    _write(pair_root / "composition-manifest.json", {"schema_version": "1.0", "run_id": run_id, "pairing": pair, "status": "BLOCKED", "evidence_class": "BLOCKED_LICENSE_EVIDENCE", "live_provider_calls": 0})
    _write(pair_root / "cleanup.json", {"live_provider_calls": 0, "candidate_process_started": False})
    row = {"pairing": pair, "status": "BLOCKED", "classification": "LICENSE_BOUNDARY_BLOCKER", "evidence_root": str(pair_root.relative_to(root)).replace("\\", "/")}
    _write(root / "poc/runs" / f"composition-{gateway.lower()}-mastra" / "manifest.json", {"schema_version": "1.0", "run_id": run_id, "pairing": pair, "status": "BLOCKED", "classification": "LICENSE_BOUNDARY_BLOCKER", "evidence_root": row["evidence_root"], "commit": False, "push": False})
    return row


def run_phase11(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    _validate_live_inputs(root)
    evidence_root = root / "tests/poc/evidence/phase-11" / run_id
    evidence_root.mkdir(parents=True, exist_ok=False)
    rows = []
    for gateway in ("Bifrost", "LiteLLM"):
        rows.append(_pair(root, evidence_root, gateway, run_id))
        rows.append(_mastra_row(root, evidence_root, gateway, run_id))
    result = {"schema_version": "1.0", "phase": "phase_11", "run_id": run_id, "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "PARTIAL", "rows": rows, "provider": "A6api", "model_a": MODEL_A, "model_b": MODEL_B, "live_provider_key_presence": "PRESENT" if os.environ.get("A6API_KEY") else "MISSING"}
    _write(evidence_root / "phase-11-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", default=RUN_ID_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()
    result = run_phase11(args.root, args.run_id)
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "rows": result["rows"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
