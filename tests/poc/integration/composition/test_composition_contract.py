from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from poc.contracts._serialization import JSONMapping
from poc.contracts.gateway import GatewayBackend
from poc.contracts.runtime import RuntimeBackend
from poc.evidence.taxonomy import FailureClass, FailureTaxonomyClass
from poc.runners.phase11_composition import _mastra_row
from poc.runtime.openhands_backend import OpenHandsRuntimeBackend
from tests.poc.support.fake_candidate import (
    ActionEvent,
    FakeAction,
    MessageEvent,
    ObservationEvent,
)


GATEWAY_BASE_URL = "http://127.0.0.1:18765/v1"
GATEWAY_ROUTE = f"{GATEWAY_BASE_URL}/chat/completions"
PROVIDER = "A6api"
MODEL_A = "gpt-5.4-mini"
MODEL_B = "gpt-5.5"
MARKER = "alpha fixture marker\n"


class RecordingGateway:
    """Offline GatewayBackend double that rejects any non-gateway route."""

    def __init__(self) -> None:
        self.started = False
        self.requests: list[JSONMapping] = []
        self.direct_provider_calls = 0

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def request(self, request: JSONMapping) -> JSONMapping:
        if not self.started:
            raise RuntimeError("gateway must be started before a request")
        self.requests.append(dict(request))
        if request.get("gateway_route") != GATEWAY_ROUTE:
            self.direct_provider_calls += 1
            raise AssertionError("runtime attempted to bypass the Shofni gateway")
        if request.get("provider") != PROVIDER:
            raise AssertionError("composition changed the selected provider")

        model = request.get("model")
        if request.get("tool_calls"):
            raise AssertionError("tool calls must originate from the gateway response")
        if request.get("phase") == "initial":
            if model != MODEL_A:
                raise AssertionError("the initial composition request must use model A")
            return {
                "tool_calls": [
                    {
                        "id": "gateway-call-1",
                        "name": "read_fixture",
                        "arguments": {"path": "input/alpha.txt"},
                    }
                ],
                "candidate_conversation_id": "gateway-conversation-1",
            }
        if request.get("phase") == "tool-continuation":
            result = request.get("tool_result")
            if not isinstance(result, Mapping) or result.get("tool_call_id") != "gateway-call-1":
                raise AssertionError("tool continuation lost the gateway tool-call correlation")
            if result.get("result") != MARKER:
                raise AssertionError("gateway received the wrong fixture result")
            return {"content": MARKER.strip(), "continuation": "accepted"}
        if request.get("phase") == "resume":
            if model != MODEL_B:
                raise AssertionError("the resumed composition request must use model B")
            saved = request.get("saved_tool_results")
            if not isinstance(saved, list) or len(saved) != 1:
                raise AssertionError("resume lost the persisted tool result")
            if saved[0].get("tool_call_id") != "gateway-call-1":
                raise AssertionError("resume changed the persisted tool-call identity")
            return {"content": MARKER.strip(), "continuation": "resumed"}
        raise AssertionError(f"unexpected gateway phase: {request.get('phase')!r}")

    def stream(self, request: JSONMapping) -> Iterator[JSONMapping]:
        yield self.request(request)

    def list_models(self) -> list[JSONMapping]:
        return [{"id": MODEL_A}, {"id": MODEL_B}]

    def classify_error(self, error: object) -> FailureTaxonomyClass:
        return FailureClass.GATEWAY_FAILURE


class GatewayConversation:
    """Candidate conversation whose only provider transport is RecordingGateway."""

    def __init__(
        self,
        record: JSONMapping,
        _persistence: Path,
        _resume: bool,
        event_callback,
        fixture_reader,
        _ledger_appender,
        gateway: RecordingGateway,
    ) -> None:
        self._record = record
        self._emit = event_callback
        self._read = fixture_reader
        self._gateway = gateway
        self._model = str(record["model"])
        self._events: list[object] = []
        self.messages: list[str] = []

    @property
    def conversation_id(self) -> str:
        return str(self._record["conversation_id"])

    def send_message(self, message: str) -> None:
        self.messages.append(message)

    def run(self) -> None:
        if self._record.get("tool_results"):
            saved = list(self._record["tool_results"].values())
            response = self._gateway.request(
                {
                    "gateway_route": GATEWAY_ROUTE,
                    "provider": PROVIDER,
                    "model": self._model,
                    "phase": "resume",
                    "saved_tool_results": saved,
                    "messages": list(self.messages),
                }
            )
            self._emit_message(str(response["content"]))
            return

        response = self._gateway.request(
            {
                "gateway_route": GATEWAY_ROUTE,
                "provider": PROVIDER,
                "model": self._model,
                "phase": "initial",
                "messages": list(self.messages),
                "tools": [{"name": "read_fixture", "parameters": {"path": "string"}}],
            }
        )
        tool_call = response["tool_calls"][0]
        self._emit_action(tool_call["name"], tool_call["id"], tool_call["arguments"])
        result = self._read(tool_call["arguments"]["path"])
        self._emit_observation(tool_call["name"], tool_call["id"])
        continuation = self._gateway.request(
            {
                "gateway_route": GATEWAY_ROUTE,
                "provider": PROVIDER,
                "model": self._model,
                "phase": "tool-continuation",
                "tool_result": {"tool_call_id": tool_call["id"], "result": result},
            }
        )
        self._emit_message(str(continuation["content"]))

    def switch_model(self, model: str, _api_key: str, base_url: str) -> None:
        if base_url != GATEWAY_BASE_URL:
            raise AssertionError("runtime model switch was not configured for the Shofni gateway")
        self._model = model

    def event_projection(self) -> list[JSONMapping]:
        projected: list[JSONMapping] = []
        for event in self._events:
            item: JSONMapping = {
                "candidate_event_type": type(event).__name__,
                "candidate_event_id": str(event.id),
            }
            if event.tool_name:
                item["tool_name"] = event.tool_name
            if event.tool_call_id:
                item["tool_call_id"] = event.tool_call_id
            if event.action is not None:
                item["action"] = event.action.model_dump()
            if event.llm_message is not None:
                item["role"] = event.llm_message.role
                item["content"] = event.llm_message.content
            projected.append(item)
        return projected

    def record_recovered_tool_result(
        self, tool_name: str, tool_call_id: str, action_id: str, result: JSONMapping
    ) -> None:
        del action_id, result
        self._emit_observation(tool_name, tool_call_id)

    def close(self) -> None:
        return None

    def _emit_action(self, tool_name: str, call_id: str, arguments: JSONMapping) -> None:
        event = ActionEvent(
            f"action-{call_id}",
            tool_name=tool_name,
            tool_call_id=call_id,
            action=FakeAction(tool_name, dict(arguments)),
        )
        self._events.append(event)
        self._emit(event)

    def _emit_observation(self, tool_name: str, call_id: str) -> None:
        event = ObservationEvent(
            f"observation-{call_id}-{len(self._events)}",
            tool_name=tool_name,
            tool_call_id=call_id,
        )
        self._events.append(event)
        self._emit(event)

    def _emit_message(self, content: str) -> None:
        event = MessageEvent(
            f"message-{len(self._events)}",
            role="assistant",
            content=content,
        )
        self._events.append(event)
        self._emit(event)


def _factory_for(gateway: RecordingGateway):
    def factory(*args: Any):
        return GatewayConversation(*args, gateway)

    return factory


def test_runtime_gateway_composition_preserves_tool_checkpoint_and_model_transition(tmp_path) -> None:
    gateway = RecordingGateway()
    assert isinstance(gateway, GatewayBackend)
    gateway.start()
    root = tmp_path / "runtime"
    first = OpenHandsRuntimeBackend(
        root,
        conversation_factory=_factory_for(gateway),
        api_key="",
        base_url=GATEWAY_BASE_URL,
    )
    assert isinstance(first, RuntimeBackend)
    first.start()
    created = first.create_task(
        {
            "provider": PROVIDER,
            "model": MODEL_A,
            "prompt": "Read input/alpha.txt through the gateway tool.",
            "fixture_marker": MARKER,
        }
    )
    first.run(created.task_id)
    before = first.inspect(created.task_id)
    checkpoint = first.checkpoint(created.task_id)
    first.stop()

    resumed_backend = OpenHandsRuntimeBackend(
        root,
        conversation_factory=_factory_for(gateway),
        api_key="",
        base_url=GATEWAY_BASE_URL,
    )
    resumed_backend.start()
    resumed = resumed_backend.resume(checkpoint)
    resumed_backend.switch_model(created.task_id, MODEL_B)
    resumed_backend.send_message(created.task_id, "Resume with the saved fixture result.")
    resumed_backend.run(created.task_id)
    after = resumed_backend.inspect(created.task_id)
    record = resumed_backend._load(resumed_backend._paths(created.task_id))
    gateway.stop()

    assert resumed.task_id == created.task_id
    assert after.task_id == created.task_id
    assert after.session_id == created.session_id
    assert after.workspace_id == created.workspace_id
    assert after.attempt_id != before.attempt_id
    assert after.selected_provider == PROVIDER
    assert after.selected_model == MODEL_B
    assert after.last_committed_tool_call_id == "gateway-call-1"
    assert after.last_committed_tool_result_id == before.last_committed_tool_result_id
    assert record["final_result"] == MARKER.strip()
    assert checkpoint.task_id == created.task_id
    assert checkpoint.workspace_id == created.workspace_id
    assert checkpoint.portable_state["tool_results"]
    assert checkpoint.portable_state["candidate_conversation_id"] == created.candidate_runtime_ref

    assert [request["phase"] for request in gateway.requests] == [
        "initial",
        "tool-continuation",
        "resume",
    ]
    assert [request["model"] for request in gateway.requests] == [MODEL_A, MODEL_A, MODEL_B]
    assert all(request["gateway_route"] == GATEWAY_ROUTE for request in gateway.requests)
    assert all(request["provider"] == PROVIDER for request in gateway.requests)
    assert gateway.direct_provider_calls == 0
    assert len(record["tool_results"]) == 1
    action_events = [event for event in record["events"] if event.get("candidate_event_type") == "ActionEvent"]
    assert len(action_events) == 1
    assert action_events[0]["tool_call_id"] == "gateway-call-1"
    assert next(iter(record["tool_results"].values()))["result"] == MARKER


def test_mastra_runtime_block_is_propagated_to_each_composition_row(tmp_path) -> None:
    closure_path = Path(__file__).resolve().parents[4] / "tests/poc/evidence/phase-8/phase8-closure-20261001T035711Z/closure-report.json"
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    assert closure["effective_phase_8_status"] == "BLOCKED"
    assert closure["failure_class"] == "LICENSE_BOUNDARY_BLOCKER"
    assert closure["ee_source_used"] is False

    evidence_root = tmp_path / "phase-11"
    rows = [
        _mastra_row(tmp_path, evidence_root, gateway, "composition-test-run")
        for gateway in ("Bifrost", "LiteLLM")
    ]
    assert {(row["pairing"], row["status"]) for row in rows} == {
        ("Bifrost + Mastra", "BLOCKED"),
        ("LiteLLM + Mastra", "BLOCKED"),
    }
    assert all(row["classification"] == "LICENSE_BOUNDARY_BLOCKER" for row in rows)
    assert all((evidence_root / f"{row['pairing'].split()[0].lower()}-mastra/blocker.json").is_file() for row in rows)

