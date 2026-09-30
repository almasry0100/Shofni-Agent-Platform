from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from poc.contracts.capability import (
    CapabilityObservation,
    CapabilityProbeResult,
    CapabilityState,
    CompatibilityReport,
)
from poc.contracts.checkpoint import Checkpoint
from poc.contracts.evidence import EvidenceRecordKind, EvidenceRecorder, RedactedEvidenceRecord
from poc.contracts.gateway import GatewayBackend
from poc.contracts.runtime import RuntimeBackend
from poc.contracts.task_state import TaskLifecycleStatus, TaskState
from poc.contracts.tool_execution import ToolExecutionBackend, ToolExecutionResult, ToolExecutionStatus
from poc.evidence.schema import (
    BehaviorMode,
    EvidenceEnvelope,
    EvidenceType,
    ProvenanceReference,
    ResultStatus,
    dumps_evidence_envelope,
    load_evidence_schema,
    loads_evidence_envelope,
)
from poc.evidence.taxonomy import FailureClass


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_SOURCE_ROOTS = (ROOT / "poc/contracts", ROOT / "poc/evidence")
CANDIDATE_ROOT_NAMES = {"bifrost", "litellm", "openhands", "mastra"}


class _GatewayStub:
    def start(self) -> None: pass
    def stop(self) -> None: pass
    def request(self, request): return request
    def stream(self, request): return iter([request])
    def list_models(self): return []
    def classify_error(self, error): return FailureClass.GATEWAY_FAILURE


class BifrostFutureGateway(_GatewayStub):
    pass


class LiteLLMFutureGateway(_GatewayStub):
    pass


class _RuntimeStub:
    def start(self) -> None: pass
    def stop(self) -> None: pass
    def create_task(self, task_spec): return _sample_task()
    def run(self, task_id): return _sample_task()
    def checkpoint(self, task_id): return _sample_checkpoint()
    def resume(self, checkpoint): return _sample_task()
    def interrupt(self, task_id): return _sample_task()
    def inspect(self, task_id): return _sample_task()


class OpenHandsFutureRuntime(_RuntimeStub):
    pass


class MastraFutureRuntime(_RuntimeStub):
    pass


class _ToolStub:
    def execute(self, call, tool_call_id, operation_id):
        return ToolExecutionResult(tool_call_id, operation_id, ToolExecutionStatus.SUCCEEDED, {"ok": True})
    def lookup(self, operation_id): return None
    def record(self, result): return None


class _EvidenceStub:
    def append(self, record): return None


def _sample_task() -> TaskState:
    return TaskState(
        task_id="task-1",
        session_id="session-1",
        attempt_id="attempt-2",
        workspace_id="workspace-1",
        selected_provider="provider-a",
        selected_model="model-a",
        lifecycle_status=TaskLifecycleStatus.RUNNING,
        last_committed_tool_call_id="call-3",
        last_committed_tool_result_id="result-3",
        candidate_runtime_ref="opaque-runtime-ref-7",
    )


def _sample_checkpoint() -> Checkpoint:
    return Checkpoint(
        checkpoint_id="checkpoint-4",
        schema_version="1.0",
        task_id="task-1",
        session_id="session-1",
        workspace_id="workspace-1",
        timestamp_utc=datetime(2026, 9, 30, 12, 30, tzinfo=timezone.utc),
        parent_checkpoint_id="checkpoint-3",
        portable_state={"turn": 4, "messages": [{"role": "assistant", "text": "ready"}]},
        candidate_snapshot_ref=None,
    )


def _sample_envelope(**overrides) -> EvidenceEnvelope:
    values = {
        "test_run_id": "phase-1-contracts",
        "timestamp_utc": datetime(2026, 9, 30, 12, 30, tzinfo=timezone.utc),
        "evidence_type": EvidenceType.SYNTHETIC_FIXTURE_EVIDENCE,
        "result_status": ResultStatus.PASS,
        "test_id": "P1-CONTRACTS",
        "candidate": None,
        "client": None,
        "client_version": None,
        "provider": None,
        "model_id": None,
        "protocol": None,
        "request_id": None,
        "task_id": None,
        "session_id": None,
        "attempt_id": None,
        "workspace_id": None,
        "checkpoint_id": None,
        "tool_call_id": None,
        "operation_id": None,
        "behavior_mode": BehaviorMode.UNVERIFIED,
        "failure_class": None,
        "provenance_references": (
            ProvenanceReference("test", "tests/poc/unit/test_contracts.py", None, None, None, "LOCAL"),
        ),
    }
    values.update(overrides)
    return EvidenceEnvelope(**values)


def test_public_contracts_import_without_candidate_packages() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import poc.contracts; import sys; "
            "assert not ({'bifrost', 'litellm', 'openhands', 'mastra'} & set(sys.modules))",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    for source_root in PUBLIC_SOURCE_ROOTS:
        for source in source_root.glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(tree):
                imported = []
                if isinstance(node, ast.Import):
                    imported.extend(alias.name.split(".", 1)[0].casefold() for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module.split(".", 1)[0].casefold())
                assert not (CANDIDATE_ROOT_NAMES & set(imported)), source


def test_gateway_families_share_the_shofni_contract() -> None:
    assert isinstance(BifrostFutureGateway(), GatewayBackend)
    assert isinstance(LiteLLMFutureGateway(), GatewayBackend)


def test_runtime_families_share_the_shofni_contract() -> None:
    assert isinstance(OpenHandsFutureRuntime(), RuntimeBackend)
    assert isinstance(MastraFutureRuntime(), RuntimeBackend)


def test_task_state_round_trip_preserves_authoritative_fields() -> None:
    state = _sample_task()
    restored = TaskState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restored == state
    assert restored.to_dict()["candidate_runtime_ref"] == "opaque-runtime-ref-7"


def test_checkpoint_round_trip_supports_portable_and_opaque_state() -> None:
    checkpoint = _sample_checkpoint()
    restored = Checkpoint.from_dict(json.loads(json.dumps(checkpoint.to_dict())))
    assert restored == checkpoint

    opaque = Checkpoint(
        checkpoint_id="checkpoint-5",
        schema_version="1.0",
        task_id="task-1",
        session_id="session-1",
        workspace_id="workspace-1",
        timestamp_utc=datetime(2026, 9, 30, 12, 31, tzinfo=timezone.utc),
        parent_checkpoint_id="checkpoint-4",
        portable_state=None,
        candidate_snapshot_ref="opaque-snapshot-ref",
    )
    assert Checkpoint.from_dict(opaque.to_dict()) == opaque
    with pytest.raises(ValueError):
        Checkpoint(
            checkpoint_id="checkpoint-invalid",
            schema_version="1.0",
            task_id="task-1",
            session_id="session-1",
            workspace_id="workspace-1",
            timestamp_utc=datetime(2026, 9, 30, 12, 31, tzinfo=timezone.utc),
            parent_checkpoint_id=None,
            portable_state=None,
            candidate_snapshot_ref=None,
        )


def test_evidence_envelope_round_trip_and_nullable_ids() -> None:
    envelope = _sample_envelope()
    serialized = dumps_evidence_envelope(envelope)
    restored = loads_evidence_envelope(serialized)
    assert restored == envelope
    payload = json.loads(serialized)
    assert payload["test_id"] is not None
    for name in (
        "candidate", "client", "client_version", "provider", "model_id", "protocol",
        "request_id", "task_id", "session_id", "attempt_id", "workspace_id",
        "checkpoint_id", "tool_call_id", "operation_id",
    ):
        assert payload[name] is None


def test_python_evidence_types_match_the_committed_schema() -> None:
    properties = load_evidence_schema()["properties"]
    assert {item.value for item in EvidenceType} == set(properties["evidence_type"]["enum"])
    assert {item.value for item in BehaviorMode} == {
        item for item in properties["behavior_mode"]["enum"] if item is not None
    }
    assert {item.value for item in ResultStatus} == set(properties["result_status"]["enum"])


def test_declared_probed_observed_and_effective_states_stay_separate() -> None:
    native = ProvenanceReference("probe", "probe-1", None, None, None, "OBSERVED")
    emulated = ProvenanceReference("adapter", "adapter-1", None, None, None, "SHOFNI_OWNED")
    result = CapabilityProbeResult(
        declared_metadata={"tools": CapabilityState.SUPPORTED},
        probed_state={"tools": CapabilityState.PARTIAL},
        observations=(CapabilityObservation("tools", CapabilityState.UNSUPPORTED, (native,)),),
        evidence_references=(native,),
    )
    report = CompatibilityReport(
        client="client-a",
        client_version="1.0",
        provider="provider-a",
        model="model-a",
        protocol="responses",
        declared_state=result.declared_metadata,
        probed_state=result.probed_state,
        observed_state={item.capability: item.observed_state for item in result.observations},
        effective_state={"tools": CapabilityState.EMULATED},
        provenance_references=(native, emulated),
    )
    assert len({
        report.declared_state["tools"],
        report.probed_state["tools"],
        report.observed_state["tools"],
        report.effective_state["tools"],
    }) == 4
    assert {ref.status for ref in report.provenance_references} == {"OBSERVED", "SHOFNI_OWNED"}
    native = dumps_evidence_envelope(_sample_envelope(behavior_mode=BehaviorMode.NATIVE))
    emulated = dumps_evidence_envelope(_sample_envelope(behavior_mode=BehaviorMode.EMULATED))
    assert native != emulated
    assert json.loads(native)["behavior_mode"] == "NATIVE"
    assert json.loads(emulated)["behavior_mode"] == "EMULATED"


def test_tool_execution_contract_carries_call_and_operation_ids() -> None:
    assert isinstance(_ToolStub(), ToolExecutionBackend)
    assert {"call", "tool_call_id", "operation_id"}.issubset(
        __import__("inspect").signature(ToolExecutionBackend.execute).parameters
    )
    assert "operation_id" in __import__("inspect").signature(ToolExecutionBackend.lookup).parameters


def test_evidence_recorder_accepts_typed_redacted_records() -> None:
    record = RedactedEvidenceRecord(EvidenceRecordKind.REQUEST, _sample_envelope(), {"body": "safe"})
    assert isinstance(_EvidenceStub(), EvidenceRecorder)
    assert record.kind is EvidenceRecordKind.REQUEST
    assert {item.value for item in EvidenceRecordKind} == {"request", "event", "tool", "state", "error"}
