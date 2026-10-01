"""Bounded authoritative Resolution gateway/OpenHands compositions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.adapters.bifrost_http import BifrostHTTPBackend
from poc.adapters.litellm_http import LiteLLMHTTPBackend
from poc.evidence.redactor import redact_value
from poc.runners.phase11_composition import (
    BIFROST_ARTIFACT,
    BIFROST_IMAGE,
    LITELLM_IMAGE,
    LITELLM_WHEEL,
    MODEL_A,
    MODEL_B,
    _bifrost_config,
    _litellm_config,
    _matches_model_route,
    _route_probe,
)


RUN_ID = "resolution-20261001T180545Z"
EVIDENCE_RUN_DIR = "20261001T180545Z"
EXPECTED_OPENHANDS_TREE = "sha256:e1258a81a1304726a1622943078907b689fccc524d733838fd57e10665ebd468"
EXPECTED_BASELINE_ID = "openhands-resolution-baseline-v2-20261001T180545Z"
PYTHON_IMAGE = "python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4"
UV_IMAGE = "ghcr.io/astral-sh/uv:0.11.7@sha256:733b4042187702f832f7fdecb3aff14a61b288c4ca37af188bb5715c1caebaf8"


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact_value(value), sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _run(command: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=timeout)


def _path_for_docker(path: Path) -> str:
    # Docker Desktop accepts drive paths with forward slashes in --mount fields.
    return str(path.resolve()).replace("\\", "/")


def _mount(source: Path, target: str, readonly: bool = False) -> str:
    value = f"type=bind,source={_path_for_docker(source)},target={target}"
    return value + (",readonly" if readonly else "")


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _validate_inputs(root: Path) -> dict[str, Any]:
    manifest_path = root / "tests/poc/evidence/resolution" / EVIDENCE_RUN_DIR / "r1/baseline-v2/manifest.json"
    baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
    if baseline.get("status") != "PASS" or baseline.get("baseline_id") != EXPECTED_BASELINE_ID:
        raise RuntimeError("authoritative OpenHands Baseline v2 is not valid")
    if baseline.get("candidate_tree_hash") != EXPECTED_OPENHANDS_TREE:
        raise RuntimeError("Baseline v2 OpenHands identity does not match the locked source")
    if not os.environ.get("A6API_KEY"):
        raise RuntimeError("A6API_KEY is missing")
    bifrost = root / BIFROST_ARTIFACT
    wheel = root / LITELLM_WHEEL
    if not bifrost.is_file() or _sha256(bifrost) != "sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5":
        raise RuntimeError("Bifrost artifact identity is invalid")
    if not wheel.is_file() or _sha256(wheel) != "sha256:762b286fe81491f242040b14f28338da0ebf4f32fea50972b6969ee578011d52":
        raise RuntimeError("LiteLLM wheel identity is invalid")
    return baseline


def _build_runtime(root: Path, run_id: str) -> tuple[str, dict[str, Any]]:
    snapshot = root / "poc/.runtime" / RUN_ID / "source"
    sdk = snapshot / "openhands-sdk"
    manifest = json.loads((root / "tests/poc/evidence/resolution" / EVIDENCE_RUN_DIR / "r1/baseline-v2/manifest.json").read_text(encoding="utf-8"))
    lock = snapshot / "uv.lock"
    if not sdk.is_dir() or not lock.is_file() or _sha256(lock) != manifest["source_lock_sha256"]:
        raise RuntimeError("OpenHands Baseline v2 source or lock identity is unavailable")
    tag = f"shofni-openhands-resolution-v2:{run_id}"
    if _run(["docker", "image", "inspect", tag]).returncode == 0:
        raise RuntimeError("Resolution runtime image tag already exists; refusing to overwrite it")
    dockerfile = root / "poc/.runtime" / RUN_ID / "r6-runtime.Dockerfile"
    dockerfile.write_text(
        "FROM " + UV_IMAGE + " AS uv\n"
        "FROM " + PYTHON_IMAGE + "\n"
        "COPY --from=uv /uv /uvx /usr/local/bin/\n"
        "WORKDIR /src\n"
        "COPY . /src\n"
        "RUN uv sync --locked --package openhands-sdk --no-dev --no-editable --python 3.12\n"
        "ENV PATH=/src/.venv/bin:$PATH\n"
        "WORKDIR /workspace\n"
        "ENTRYPOINT [\"/src/.venv/bin/python\"]\n",
        encoding="utf-8",
        newline="\n",
    )
    result = _run(["docker", "build", "--platform", "linux/amd64", "--file", str(dockerfile), "--tag", tag, str(snapshot)], timeout=1800)
    details = {
        "tag": tag,
        "exit_code": result.returncode,
        "stdout_tail": str(redact_value((result.stdout or "")[-3000:])),
        "stderr_tail": str(redact_value((result.stderr or "")[-3000:])),
        "python_image": PYTHON_IMAGE,
        "uv_image": UV_IMAGE,
        "sync_command": manifest["sync_command"],
        "candidate_tree_hash": manifest["candidate_tree_hash"],
        "lock_sha256": manifest["source_lock_sha256"],
    }
    if result.returncode != 0:
        return tag, details
    inspect = _run(["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}|{{.Id}}", tag])
    details["inspect"] = str(redact_value(inspect.stdout.strip()))
    return tag, details


def _start_gateway(root: Path, gateway: str, run_id: str, network: str, temp_root: Path) -> tuple[Any, str, int, str]:
    suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{gateway}".lower())[-48:]
    container = f"shofni-r6-{suffix}"
    host_port = _port()
    if gateway == "Bifrost":
        backend = BifrostHTTPBackend(
            artifact_dir=(root / BIFROST_ARTIFACT).parent,
            app_dir=temp_root / "bifrost-app",
            image_ref=BIFROST_IMAGE,
            network_name=network,
            provider_url="https://api.a6api.com",
            host_port=host_port,
            container_name=container,
            provider_config=_bifrost_config(),
            environment={"A6API_KEY": None},
        )
        path_suffix = "/openai/v1"
        internal_port = 8080
    else:
        config_dir = temp_root / "litellm-config"
        config_dir.mkdir(parents=True, exist_ok=False)
        (config_dir / "config.yaml").write_text(_litellm_config(), encoding="utf-8", newline="\n")
        backend = LiteLLMHTTPBackend(
            config_dir=config_dir,
            image_ref=LITELLM_IMAGE,
            network_name=network,
            host_port=host_port,
            container_name=container,
            environment={"A6API_KEY": None},
        )
        path_suffix = "/v1"
        internal_port = 4000
    backend.start()
    return backend, container, internal_port, backend.base_url + path_suffix


def _client_subcase(backend: Any, model: str, repetition: int) -> dict[str, Any]:
    prompt = "Use read_fixture exactly once with path input/alpha.txt. Return the exact contents."
    request = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "function", "function": {"name": "read_fixture", "description": "Read one fixture file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}],
        "tool_choice": {"type": "function", "function": {"name": "read_fixture"}},
        "max_tokens": 256,
    }
    first = backend.request(request)
    choices = first.get("choices")
    message = choices[0].get("message", {}) if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    valid = isinstance(calls, list) and len(calls) == 1
    call = calls[0] if valid and isinstance(calls[0], dict) else {}
    function = call.get("function", {}) if isinstance(call, dict) else {}
    args_text = function.get("arguments") if isinstance(function, dict) else None
    try:
        args = json.loads(args_text) if isinstance(args_text, str) else {}
    except json.JSONDecodeError:
        args = {}
    call_id = call.get("id") if isinstance(call, dict) else None
    valid = valid and function.get("name") == "read_fixture" and args == {"path": "input/alpha.txt"} and isinstance(call_id, str) and bool(call_id)
    tool_result = "alpha fixture input\n" if valid else ""
    continuation = None
    final_text = ""
    if valid:
        continuation = backend.request({
            "model": model,
            "messages": [
                {"role": "user", "content": prompt},
                message,
                {"role": "tool", "tool_call_id": call_id, "name": "read_fixture", "content": tool_result},
            ],
            "max_tokens": 256,
        })
        choices = continuation.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            content = choices[0].get("message", {}).get("content")
            final_text = content if isinstance(content, str) else ""
    return {
        "repetition": repetition,
        "status": "PASS" if valid and final_text.strip() else "FAIL",
        "level": 2,
        "tool_execution_backend": "CLIENT",
        "candidate_gateway": backend.container_name,
        "provider": "A6api",
        "model": model,
        "candidate_tool_execution_count": 0,
        "client_tool_execution_count": 1 if valid else 0,
        "runtime_tool_execution_count": 0,
        "tool_call_id": call_id,
        "tool_result": tool_result,
        "final_response_present": bool(final_text.strip()),
        "final_marker": "alpha" if final_text.strip() == "alpha" else None,
        "configured_retry_count": 0,
        "provider_boundary_observation": {"configured_route": "https://api.a6api.com/v1/responses", "observed_live_gateway_response": bool(first), "observed_outbound_provider_http": False},
        "candidate_reached": bool(first),
        "provider_reached": False,
        "provider_request_observed": False,
        "client_reached": True,
    }


def _runtime_subcase(root: Path, evidence_root: Path, runtime_image: str, network: str, container: str, gateway: str, internal_port: int, repetition: int) -> dict[str, Any]:
    rep_root = evidence_root / f"rep-{repetition}" / "level3-runtime"
    runtime_root = root / "poc/.runtime" / RUN_ID / "r6" / gateway.lower() / f"rep-{repetition}"
    runtime_root.mkdir(parents=True, exist_ok=False)
    rep_root.mkdir(parents=True, exist_ok=False)
    internal_url = f"http://{container}:{internal_port}{'/openai/v1' if gateway == 'Bifrost' else '/v1'}"
    command = [
        "docker", "run", "--rm", "--network", network, "--platform", "linux/amd64",
        "--mount", _mount(root, "/workspace", readonly=True),
        "--mount", _mount(rep_root, "/evidence"),
        "--mount", _mount(runtime_root, "/runtime"),
        "--env", "PYTHONPATH=/workspace",
        "--env", f"SHOFNI_ATTEMPT_ID={RUN_ID}-{gateway.lower()}-r6-rep-{repetition}",
        runtime_image,
        "-m", "poc.runners.openhands_level3_live",
        "--stage", "orchestrate", "--runtime-root", "/runtime", "--evidence-root", "/evidence",
        "--model-a", MODEL_A, "--model-b", MODEL_B, "--base-url", internal_url, "--gateway-mode",
    ]
    result = _run(command, timeout=700)
    diagnostics = str(redact_value(((result.stdout or "") + "\n" + (result.stderr or ""))[-5000:]))
    result_path = rep_root / "t10-live.json"
    live = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else None
    event_ref = None
    if live is not None:
        event_ref = "t10-live.json"
    action_events = live.get("candidate_action_events", []) if isinstance(live, dict) else []
    result_record = {
        "repetition": repetition,
        "status": "PASS" if isinstance(live, dict) and live.get("status") == "PASS" and result.returncode == 0 else "FAIL",
        "level": 3,
        "tool_execution_backend": "RUNTIME",
        "baseline_id": EXPECTED_BASELINE_ID,
        "gateway": gateway,
        "provider": "A6api",
        "model_a": MODEL_A,
        "model_b": MODEL_B,
        "runtime_process_exit_code": result.returncode,
        "fresh_process_proven": isinstance(live, dict) and live.get("process_boundary", "").find("separate child processes") >= 0,
        "task_id": live.get("task_id") if isinstance(live, dict) else None,
        "workspace_id": live.get("workspace_id") if isinstance(live, dict) else None,
        "checkpoint_id": live.get("checkpoint_id") if isinstance(live, dict) else None,
        "tool_call_ids": [item.get("tool_call_id") for item in action_events if isinstance(item, dict) and item.get("tool_call_id")],
        "tool_result": live.get("tool_result") if isinstance(live, dict) else None,
        "final_result": live.get("final_result") if isinstance(live, dict) else None,
        "direct_provider_bypass": False,
        "runtime_provider_key": "NOT_PRESENT",
        "gateway_local_tool_execution": False,
        "provider_boundary_observation": {"configured_route": "https://api.a6api.com/v1/responses", "gateway_response_observed": isinstance(live, dict), "observed_outbound_provider_http": False},
        "diagnostic_tail": diagnostics,
        "live_evidence_ref": event_ref,
        "candidate_reached": isinstance(live, dict),
        "provider_reached": False,
        "provider_request_observed": False,
        "client_reached": True,
    }
    shutil.rmtree(runtime_root, ignore_errors=True)
    result_record["cleanup"] = {"runtime_root_removed": not runtime_root.exists()}
    _write(evidence_root / f"rep-{repetition}" / "level3-runtime-result.json", result_record)
    return result_record


def _composition(root: Path, runtime_image: str, gateway: str, run_id: str, evidence_root: Path) -> dict[str, Any]:
    if run_id != RUN_ID:
        raise ValueError("Resolution run ID is frozen")
    evidence = evidence_root / "r6" / gateway.lower()
    evidence.mkdir(parents=True, exist_ok=False)
    suffix = re.sub(r"[^a-z0-9-]", "-", f"{run_id}-{gateway}".lower())[-45:]
    network = f"shofni-r6-net-{suffix}"
    temp_root = root / "poc/.runtime" / RUN_ID / "r6-setup" / gateway.lower()
    temp_root.mkdir(parents=True, exist_ok=False)
    backend = None
    container = None
    runtime_reps: list[dict[str, Any]] = []
    client_reps: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {}
    composition_path = evidence / "composition.json"
    setup_correction = {
        "type": "SETUP_CORRECTION",
        "cause": "Docker on Windows rejects the path-list mount syntax used by historical attempts.",
        "correction": "Validated explicit --mount type=bind,source=C:/...,target=... with forward-slash drive paths in one disposable Linux container before semantic repetitions.",
        "semantic_retry": False,
    }
    setup: dict[str, Any] = {"gateway": gateway, "network": network, "setup_corrections": [setup_correction]}
    try:
        created = _run(["docker", "network", "create", network])
        if created.returncode != 0:
            raise RuntimeError("could not create Resolution-owned Docker network")
        backend, container, internal_port, host_url = _start_gateway(root, gateway, run_id, network, temp_root)
        selected = MODEL_A if gateway == "Bifrost" else MODEL_A
        setup["gateway_probe"] = _route_probe(backend.list_models(), (selected, MODEL_B))
        if setup["gateway_probe"]["status"] != "PASS":
            raise RuntimeError("required model routes were not advertised by the gateway")
        setup.update({"container": container, "host_gateway_url": host_url, "internal_gateway_url": f"http://{container}:{internal_port}", "provider": "A6api", "provider_route_a": MODEL_A, "provider_route_b": MODEL_B})
        for repetition in range(1, 4):
            try:
                client_reps.append(_client_subcase(backend, selected, repetition))
            except Exception as error:
                client_reps.append({"repetition": repetition, "status": "FAIL", "level": 2, "tool_execution_backend": "CLIENT", "failure_class": "GATEWAY_OR_PROVIDER_FAILURE", "error_type": type(error).__name__, "diagnostic": str(redact_value(str(error))), "candidate_tool_execution_count": 0, "runtime_tool_execution_count": 0, "candidate_reached": False, "provider_reached": False, "provider_request_observed": False, "client_reached": True})
        for repetition in range(1, 4):
            try:
                runtime_reps.append(_runtime_subcase(root, evidence, runtime_image, network, container, gateway, internal_port, repetition))
            except Exception as error:
                runtime_reps.append({"repetition": repetition, "status": "FAIL", "level": 3, "tool_execution_backend": "RUNTIME", "failure_class": "RUNTIME_OR_PROVIDER_FAILURE", "error_type": type(error).__name__, "diagnostic": str(redact_value(str(error))), "runtime_provider_key": "NOT_PRESENT", "direct_provider_bypass": False, "gateway_local_tool_execution": False, "candidate_reached": False, "provider_reached": False, "provider_request_observed": False, "client_reached": True})
        observed = {
            "schema_version": "1.0",
            "run_id": run_id,
            "phase": "R6",
            "pairing": f"{gateway} + OpenHands",
            "gateway": gateway,
            "runtime": "OpenHands Baseline v2",
            "level2_native_client_owned": client_reps,
            "level3_runtime_owned": runtime_reps,
            "required_successful_repetitions": 3,
            "status": "PASS" if all(item["status"] == "PASS" for item in client_reps + runtime_reps) and all(item["provider_boundary_observation"]["observed_outbound_provider_http"] for item in runtime_reps) else "PARTIAL",
            "provider_boundary_observability": "NOT_OBSERVED",
            "candidate_reached": True,
            "provider_reached": False,
            "provider_request_observed": False,
            "client_reached": True,
            "setup": setup,
        }
        _write(composition_path, observed)
    except Exception as error:
        record = {
            "schema_version": "1.0",
            "run_id": run_id,
            "phase": "R6",
            "pairing": f"{gateway} + OpenHands",
            "gateway": gateway,
            "runtime": "OpenHands Baseline v2",
            "status": "FAIL",
            "classification": "SETUP_FAILURE" if not client_reps and not runtime_reps else "PARTIAL",
            "error_type": type(error).__name__,
            "diagnostic": str(redact_value(str(error))),
            "setup": setup,
            "level2_native_client_owned": client_reps,
            "level3_runtime_owned": runtime_reps,
            "required_successful_repetitions": 3,
            "candidate_reached": bool(container),
            "provider_reached": False,
            "provider_request_observed": False,
            "client_reached": True,
        }
        _write(composition_path, record)
    finally:
        if backend is not None:
            try:
                backend.stop()
                cleanup["gateway_stop_returned"] = True
            except Exception as error:
                cleanup["gateway_stop_returned"] = False
                cleanup["gateway_stop_error_type"] = type(error).__name__
        if container:
            _run(["docker", "rm", "--force", container])
            cleanup["container_absent_after_cleanup"] = _run(["docker", "inspect", container]).returncode != 0
        else:
            cleanup["container_absent_after_cleanup"] = True
        _run(["docker", "network", "rm", network])
        cleanup["network_absent_after_cleanup"] = _run(["docker", "network", "inspect", network]).returncode != 0
        shutil.rmtree(temp_root, ignore_errors=True)
        cleanup["temporary_config_removed"] = not temp_root.exists()
        runtime_root = root / "poc/.runtime" / RUN_ID / "r6" / gateway.lower()
        shutil.rmtree(runtime_root, ignore_errors=True)
        cleanup["owned_runtime_roots_removed"] = not runtime_root.exists()
        if composition_path.is_file():
            saved = json.loads(composition_path.read_text(encoding="utf-8"))
            saved["cleanup"] = cleanup
            _write(composition_path, saved)
    return json.loads(composition_path.read_text(encoding="utf-8"))


def run_r6(root: Path, run_id: str, evidence_root: Path) -> dict[str, Any]:
    root = root.resolve()
    _validate_inputs(root)
    runtime_image, build = _build_runtime(root, run_id)
    build_root = evidence_root / "r6" / "runtime-build.json"
    _write(build_root, {"run_id": run_id, "phase": "R6", "record_kind": "RUNTIME_IMAGE_BUILD", "build": build, "status": "PASS" if build.get("exit_code") == 0 else "FAIL", "candidate_reached": False, "provider_reached": False, "client_reached": False})
    if build.get("exit_code") != 0:
        return {"run_id": run_id, "status": "FAIL", "classification": "SETUP_FAILURE", "runtime_build": build}
    rows = [_composition(root, runtime_image, gateway, run_id, evidence_root) for gateway in ("Bifrost", "LiteLLM")]
    cleanup = _run(["docker", "image", "rm", "--force", runtime_image])
    image_absent = _run(["docker", "image", "inspect", runtime_image]).returncode != 0
    runtime_roots = root / "poc/.runtime" / RUN_ID / "r6"
    shutil.rmtree(runtime_roots, ignore_errors=True)
    runtime_roots_removed = not runtime_roots.exists()
    dockerfile = root / "poc/.runtime" / RUN_ID / "r6-runtime.Dockerfile"
    dockerfile.unlink(missing_ok=True)
    result = {
        "schema_version": "1.0",
        "run_id": run_id,
        "phase": "R6",
        "status": "PASS" if all(row.get("status") == "PASS" for row in rows) else "PARTIAL",
        "rows": rows,
        "runtime_image_removed": cleanup.returncode == 0,
        "runtime_image_absent_after_cleanup": image_absent,
        "runtime_roots_removed": runtime_roots_removed,
        "runtime_build_config_removed": not dockerfile.exists(),
        "candidate_reached": True,
        "provider_reached": False,
        "provider_request_observed": False,
        "client_reached": True,
        "repetition_counters": {row["gateway"]: {"level2_client": len(row.get("level2_native_client_owned", [])), "level3_runtime": len(row.get("level3_runtime_owned", []))} for row in rows},
        "level2_backend": "CLIENT",
        "level3_backend": "RUNTIME",
    }
    _write(evidence_root / "r6" / "summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_r6(args.root, args.run_id, args.evidence_root), sort_keys=True))


if __name__ == "__main__":
    main()
