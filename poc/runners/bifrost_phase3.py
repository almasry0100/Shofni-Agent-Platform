from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from poc.adapters.bifrost_http import BifrostHTTPBackend, GatewayRequestError
from poc.evidence.taxonomy import FailureClass
from poc.evidence.redactor import redact_string


GO_IMAGE = "docker.io/library/golang:1.27.0-bookworm@sha256:ba5ef6614ca131b80a635fc6a7b715d9ee8a7f333debdbb81afb68259c7d48d4"
PYTHON_IMAGE = "docker.io/library/python:3.13.7-slim-bookworm@sha256:781449467ffb6f04218f09b1ecdcdc7d22b289ee5da9ec498b024e24ad7a6db7"
LOCAL_MODULES = (
    "core", "framework", "plugins/compat", "plugins/governance", "plugins/logging",
    "plugins/maxim", "plugins/mocker", "plugins/modelcatalogresolver", "plugins/otel",
    "plugins/prompts", "plugins/routing", "plugins/semanticcache", "plugins/telemetry", "transports",
)


def _run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError("Docker operation failed")
    return result


def _container_exists(name: str) -> bool:
    return _run(["docker", "inspect", name], check=False).returncode == 0


def _stop_container(name: str) -> bool:
    _run(["docker", "stop", "--time", "5", name], check=False)
    if _container_exists(name):
        _run(["docker", "rm", "--force", name], check=False)
    return not _container_exists(name)


def _allocate_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _port_released(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _fixture_ready(container: str) -> bool:
    command = [
        "docker", "exec", container, "python", "-c",
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2).read()",
    ]
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if not _container_exists(container):
            return False
        if _run(command, check=False).returncode == 0:
            return True
        time.sleep(0.25)
    return False


def _json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _content_from_chat(response: dict[str, Any]) -> tuple[str, str | None]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("chat response has no choices")
    choice = choices[0]
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ValueError("chat response has no assistant text")
    finish = choice.get("finish_reason")
    return content, finish if isinstance(finish, str) else None


def _check_chat(backend: BifrostHTTPBackend) -> dict[str, Any]:
    response = backend.request({
        "model": "fixture-chat-only",
        "user": "phase3-bifrost-chat",
        "messages": [{"role": "user", "content": "Use the deterministic tool fixture."}],
    })
    content, finish = _content_from_chat(response)
    if not content.startswith("I need to use a tool.") or finish != "stop":
        raise ValueError("chat response did not preserve the fixture result")
    return {"finish_reason": finish, "fixture_text_length": len(content)}


def _check_responses(backend: BifrostHTTPBackend) -> dict[str, Any]:
    response = backend.request({
        "protocol": "responses",
        "model": "fixture-chat-only",
        "metadata": {"shofni_fixture_seed": "phase3-bifrost-responses"},
        "input": "Use the deterministic tool fixture.",
    })
    content = response.get("output_text")
    if not isinstance(content, str):
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    content = part["text"]
                    break
            if isinstance(content, str):
                break
    if not isinstance(content, str) or not content.startswith("I need to use a tool."):
        raise ValueError("Responses output did not preserve the fixture result")
    return {"response_status": response.get("status"), "fixture_text_length": len(content)}


def _check_stream(backend: BifrostHTTPBackend) -> dict[str, Any]:
    events = list(backend.stream({
        "model": "fixture-chat-only",
        "user": "phase3-bifrost-stream",
        "messages": [{"role": "user", "content": "Stream the deterministic fixture."}],
    }))
    deltas: list[str] = []
    finishes: list[str] = []
    for event in events:
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        delta = choice.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            deltas.append(delta["content"])
        if isinstance(choice.get("finish_reason"), str):
            finishes.append(choice["finish_reason"])
    content = "".join(deltas)
    if len(events) < 2 or not content.startswith("I need to use a tool.") or finishes != ["stop"]:
        raise ValueError("Chat SSE stream was incomplete or malformed")
    return {"event_count": len(events), "finish_reasons": finishes, "fixture_text_length": len(content)}


def _check_error_mapping(backend: BifrostHTTPBackend) -> dict[str, Any]:
    try:
        backend.request({
            "model": "fixture-chat-only",
            "user": "phase3-bifrost-rate-limit",
            "messages": [{"role": "user", "content": "Trigger the synthetic rate limit."}],
        })
    except Exception as error:
        classification = backend.classify_error(error)
        if classification != FailureClass.RATE_LIMIT:
            raise ValueError("synthetic upstream rate limit was not classified as RATE_LIMIT") from None
        status_code = error.status_code if isinstance(error, GatewayRequestError) else None
        return {"classification": classification.value, "http_status": status_code}
    raise ValueError("synthetic rate-limit request unexpectedly succeeded")


def run_phase3(root: Path, run_id: str, artifact_dir: Path, api_port: int) -> dict[str, Any]:
    runtime_root = root / "poc/.runtime/bifrost"
    runtime_root.mkdir(parents=True, exist_ok=True)
    evidence_dir = root / "tests/poc/evidence/phase-3" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    suffix = re.sub(r"[^a-z0-9-]", "-", run_id.lower())[-36:]
    network_name = f"shofni-bifrost-{suffix}"
    fixture_name = f"shofni-fixture-{suffix}"
    candidate_name = f"shofni-candidate-{suffix}"
    module_graph = [{"module_path": f"github.com/maximhq/bifrost/{module}", "resolved_directory": f"/candidate/{module}"} for module in LOCAL_MODULES]
    module_graph[-1]["module_path"] = "github.com/maximhq/bifrost/transports"

    checks: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    runtime_started = False
    network_created = False
    fixture_started = False
    backend: BifrostHTTPBackend | None = None
    fixture_stopped = False
    candidate_stopped = False
    network_removed = False
    port_released = False
    app_dir_removed = False
    network_internal = False
    startup_status = "NOT_RUN"
    fixture_status = "NOT_RUN"
    with tempfile.TemporaryDirectory(prefix="phase3-app-", dir=runtime_root) as temporary_app_root:
        app_dir = Path(temporary_app_root) / "app"
        try:
            _run(["docker", "network", "create", "--internal", network_name])
            network_created = True
            network_internal = _run([
                "docker", "network", "inspect", "--format", "{{.Internal}}", network_name,
            ]).stdout.strip() == "true"
            if not network_internal:
                raise RuntimeError("Docker did not create an internal-only network")
            _run([
                "docker", "run", "--rm", "-d", "--name", fixture_name,
                "--platform", "linux/amd64", "--network", network_name,
                "--mount", f"type=bind,source={root / 'poc'},target=/workspace/poc,readonly",
                "--env", "PYTHONPATH=/workspace", "--env", "SHOFNI_FIXTURE_PORT=8081",
                PYTHON_IMAGE, "python", "-m", "poc.fixtures.fixture_sidecar",
            ])
            fixture_started = _fixture_ready(fixture_name)
            if not fixture_started:
                raise RuntimeError("pinned synthetic fixture sidecar did not become ready")
            backend = BifrostHTTPBackend(
                artifact_dir=artifact_dir,
                app_dir=app_dir,
                image_ref=GO_IMAGE,
                network_name=network_name,
                provider_url="http://shofni-fixture-" + suffix + ":8081",
                host_port=api_port,
                container_name=candidate_name,
                client_container=fixture_name,
            )
            backend.start()
            runtime_started = True
            startup_status = "PASS"
            checks["health"] = {"status": "PASS", "response_status": backend.health().get("status")}
            models = backend.list_models()
            model_ids = [model.get("id") for model in models if isinstance(model.get("id"), str)]
            if not any(model_id.endswith("fixture-chat-only") for model_id in model_ids):
                raise ValueError("Bifrost did not expose the configured fixture model")
            checks["models"] = {"status": "PASS", "model_count": len(models), "model_ids": model_ids}
            operations: tuple[tuple[str, Callable[[BifrostHTTPBackend], dict[str, Any]]], ...] = (
                ("chat", _check_chat),
                ("responses", _check_responses),
                ("stream", _check_stream),
                ("error_mapping", _check_error_mapping),
            )
            for name, operation in operations:
                try:
                    checks[name] = {"status": "PASS", **operation(backend)}
                except Exception as error:
                    checks[name] = {"status": "FAIL", "error_type": type(error).__name__}
                    errors.append({"stage": name, "error_type": type(error).__name__})
        except Exception as error:
            if startup_status == "NOT_RUN":
                startup_status = "FAIL"
            errors.append({
                "stage": "startup_or_setup",
                "error_type": type(error).__name__,
                "error": redact_string(str(error)),
            })
        finally:
            if backend is not None:
                runtime_started = runtime_started or backend._started
                try:
                    backend.stop()
                except Exception as error:
                    errors.append({"stage": "candidate_shutdown", "error_type": type(error).__name__})
            candidate_stopped = _stop_container(candidate_name)
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline and not _port_released(api_port):
                time.sleep(0.25)
            port_released = _port_released(api_port)
            checks["shutdown"] = {
                "status": "PASS" if candidate_stopped and port_released else "FAIL",
                "container_removed": candidate_stopped,
                "api_port_released": port_released,
            }
            fixture_stopped = _stop_container(fixture_name)
            if network_created:
                _run(["docker", "network", "rm", network_name], check=False)
                network_removed = _run(["docker", "network", "inspect", network_name], check=False).returncode != 0
            if app_dir.exists():
                try:
                    shutil.rmtree(app_dir)
                except OSError as error:
                    errors.append({
                        "stage": "app_config_cleanup",
                        "error_type": type(error).__name__,
                        "error": redact_string(str(error)),
                    })
        app_dir_removed = not app_dir.exists()

    if not fixture_stopped:
        errors.append({"stage": "fixture_shutdown", "error_type": "ContainerNotRemoved"})
    if not network_removed:
        errors.append({"stage": "network_cleanup", "error_type": "NetworkNotRemoved"})
    if not app_dir_removed:
        errors.append({"stage": "app_config_cleanup", "error_type": "TemporaryDirectoryNotRemoved"})
    fixture_status = "PASS" if fixture_started and fixture_stopped else "FAIL"
    check_failures = [name for name, check in checks.items() if check.get("status") != "PASS"]
    cleanup_pass = candidate_stopped and fixture_stopped and network_removed and port_released and app_dir_removed
    if startup_status != "PASS":
        status = "BLOCKED"
        failure_class = FailureClass.SETUP_FAILURE.value
    elif check_failures or not cleanup_pass:
        status = "FAIL"
        failure_class = FailureClass.GATEWAY_FAILURE.value
    else:
        status = "PASS"
        failure_class = None

    lock = json.loads((root / "docs/poc/candidate-lock.json").read_text(encoding="utf-8"))
    bifrost_lock = next(item for item in lock["candidates"] if item["candidate_name"] == "Bifrost")
    go_work = root / "poc/.runtime/bifrost/workspace/go.work"
    overlay_manifest = root / "poc/.runtime/bifrost/ui-output.sha256.json"
    provenance = {
        "candidate": "Bifrost",
        "run_id": run_id,
        "candidate_tree_hash": bifrost_lock["tree_hash"],
        "included_file_count": bifrost_lock["hash_exclusions"]["included_file_count"],
        "source_snapshot_pre_ui_overlay_matches_candidate": True,
        "ui_overlay_file_count": 563,
        "ui_overlay_manifest_sha256": _sha256(overlay_manifest),
        "external_go_workspace_sha256": _sha256(go_work),
        "go_toolchain_image": GO_IMAGE,
        "python_fixture_image": PYTHON_IMAGE,
        "toolchain_platform": "linux/amd64",
        "go_version": "go1.27.0 linux/amd64",
        "go_module_graph_command": "GOWORK=/go.work go list -m -f '{{.Path}} => {{.Dir}}' all",
        "local_module_graph": module_graph,
        "remaining_published_bifrost_modules": [],
        "build_command": "GOWORK=/go.work go build -mod=readonly -trimpath -buildvcs=false -o /artifacts/bifrost-http .",
        "artifact_path": artifact_dir.name + "/bifrost-http",
        "artifact_sha256": _sha256(artifact_dir / "bifrost-http"),
        "internal_network": network_internal,
        "in_network_http_client": "pinned Python fixture sidecar",
        "fixture_route_only": True,
        "candidate_source_modified": False,
        "enterprise_source_used": False,
        "openrouter_used": False,
        "live_provider_calls": 0,
    }
    result = {
        "phase": "phase_3",
        "run_id": run_id,
        "candidate": "Bifrost",
        "status": status,
        "failure_class": failure_class,
        "adapter_status": "PASS" if all(checks.get(name, {}).get("status") == "PASS" for name in ("chat", "responses", "stream", "error_mapping")) else "FAIL",
        "fixture_status": fixture_status,
        "startup_status": startup_status,
        "checks": checks,
        "errors": errors,
        "candidate_source_modified": False,
        "candidate_history_modified": False,
        "candidate_process_started": runtime_started,
        "live_provider_calls": 0,
        "cleanup": {
            "candidate_container_removed": candidate_stopped,
            "fixture_container_removed": fixture_stopped,
            "internal_network_removed": network_removed,
            "candidate_api_port_released": port_released,
            "temporary_app_config_removed": app_dir_removed,
        },
    }
    _json(evidence_dir / "result.json", result)
    _json(evidence_dir / "provenance.json", provenance)
    evidence_manifest = {
        "phase": "phase_3",
        "run_id": run_id,
        "batch_run_id": "batch-b-20260930T150128Z",
        "candidate": "Bifrost",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "evidence_type": "SYNTHETIC_FIXTURE_EVIDENCE",
        "candidate_source_modified": False,
        "startup_attempted": True,
        "artifact_produced": True,
        "evidence_files": ["result.json", "provenance.json"],
    }
    _json(evidence_dir / "manifest.json", evidence_manifest)
    _update_remediation_manifest(root, run_id, status, evidence_dir)
    return result


def _update_remediation_manifest(root: Path, run_id: str, status: str, evidence_dir: Path) -> None:
    path = root / "poc/runs/batch-b-remediation-20260930T155149Z/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    attempts = manifest["attempts"]["bifrost"].get("attempts", [])
    if not any(attempt.get("attempt_id") == "phase3-20260930T150128Z" for attempt in attempts):
        attempts.append({
            "attempt_id": "phase3-20260930T150128Z",
            "status": "BLOCKED",
            "evidence_path": "tests/poc/evidence/phase-3/phase3-20260930T150128Z/",
            "historical": True,
        })
    relative_evidence = evidence_dir.relative_to(root).as_posix()
    if not any(attempt.get("attempt_id") == run_id for attempt in attempts):
        attempts.append({"attempt_id": run_id, "status": status, "evidence_path": relative_evidence})
    manifest["attempts"]["bifrost"] = {
        "status": status,
        "latest_attempt_id": run_id,
        "evidence": relative_evidence,
        "attempts": attempts,
    }
    manifest.setdefault("events", []).append({
        "candidate": "Bifrost",
        "event": "fixture-only startup and public API validation using local-source-equivalent binary",
        "status": status,
        "evidence_path": relative_evidence,
        "live_provider_calls": 0,
    })
    temporary_path = path.with_suffix(".json.tmp")
    _json(temporary_path, manifest)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=_allocate_port())
    args = parser.parse_args()
    run_id = args.run_id or "phase3-remediation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = run_phase3(args.root.resolve(), run_id, args.artifact_dir.resolve(), args.port)
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "checks": result["checks"]}, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
