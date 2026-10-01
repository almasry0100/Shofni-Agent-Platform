from __future__ import annotations

import json
import os
import threading
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from poc.contracts._serialization import JSONMapping
from poc.contracts.checkpoint import Checkpoint
from poc.contracts.runtime import RuntimeBackend
from poc.contracts.task_state import TaskLifecycleStatus, TaskState


class CandidateConversation(Protocol):
    @property
    def conversation_id(self) -> str: ...

    def send_message(self, message: str) -> None: ...

    def run(self) -> None: ...

    def switch_model(self, model: str, api_key: str, base_url: str) -> None: ...

    def event_projection(self) -> list[JSONMapping]: ...

    def record_recovered_tool_result(
        self, tool_name: str, tool_call_id: str, action_id: str, result: JSONMapping
    ) -> None: ...

    def close(self) -> None: ...


ConversationFactory = Callable[
    [
        JSONMapping,
        Path,
        bool,
        Callable[[object], None],
        Callable[[str], str],
        Callable[[str, JSONMapping], JSONMapping],
    ],
    CandidateConversation,
]


@dataclass(frozen=True)
class RuntimePaths:
    task_file: Path
    workspace: Path
    candidate_persistence: Path


class OpenHandsRuntimeBackend(RuntimeBackend):
    """Shofni identity/checkpoint adapter over OpenHands LocalConversation."""

    def __init__(
        self,
        persistence_root: str | Path,
        *,
        conversation_factory: ConversationFactory | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        crash_hook: Callable[[int], None] | None = None,
    ) -> None:
        self._root = Path(persistence_root).resolve()
        self._tasks = self._root / "tasks"
        self._factory = conversation_factory or self._create_openhands_conversation
        self._api_key = api_key if api_key is not None else os.environ.get("A6API_KEY", "")
        self._base_url = base_url or os.environ.get("A6API_BASE_URL", "https://api.a6api.com")
        self._crash_hook = crash_hook
        self._active: dict[str, CandidateConversation] = {}
        self._action_ids: deque[str] = deque()
        self._append_action_ids: deque[str] = deque()
        self._lock = threading.RLock()
        self._started = False

    def start(self) -> None:
        self._tasks.mkdir(parents=True, exist_ok=True)
        self._started = True

    def stop(self) -> None:
        for task_id in list(self._active):
            self._close_conversation(task_id)
        self._started = False

    def create_task(self, task_spec: JSONMapping) -> TaskState:
        self._require_started()
        model = _text(task_spec.get("model", "gpt-5.4-mini"), "model")
        provider = _text(task_spec.get("provider", "A6api"), "provider")
        prompt = _text(task_spec.get("prompt", ""), "prompt")
        task_id, session_id, attempt_id, workspace_id = (str(uuid.uuid4()) for _ in range(4))
        conversation_id = str(uuid.uuid4())
        state = TaskState(
            task_id=task_id,
            session_id=session_id,
            attempt_id=attempt_id,
            workspace_id=workspace_id,
            selected_provider=provider,
            selected_model=model,
            lifecycle_status=TaskLifecycleStatus.CREATED,
            last_committed_tool_call_id=None,
            last_committed_tool_result_id=None,
            candidate_runtime_ref=conversation_id,
        )
        paths = self._paths(task_id)
        paths.workspace.mkdir(parents=True, exist_ok=True)
        (paths.workspace / "input").mkdir(exist_ok=True)
        marker = _text(task_spec.get("fixture_marker", "alpha fixture marker\n"), "fixture_marker")
        (paths.workspace / "input" / "alpha.txt").write_text(marker, encoding="utf-8")
        (paths.workspace / "state").mkdir(exist_ok=True)
        record: JSONMapping = {
            "task_id": task_id,
            "task_state": state.to_dict(),
            "conversation_id": conversation_id,
            "workspace_path": str(paths.workspace),
            "prompt": prompt,
            "tool_mode": task_spec.get("tool_mode", "read"),
            "model": model,
            "provider": provider,
            "workspace_id": workspace_id,
            "tool_results": {},
            "events": [],
            "pending_operations": {},
            "crash_boundary": task_spec.get("crash_boundary"),
            "ledger_value": task_spec.get("ledger_value", {"marker": marker.strip()}),
            "checkpoint_ids": [],
            "final_result": None,
            "prompt_sent": False,
        }
        self._save(paths, record)
        return state

    def run(self, task_id: str) -> TaskState:
        self._require_started()
        paths = self._paths(task_id)
        record = self._load(paths)
        state = TaskState.from_dict(record["task_state"])
        conversation = self._active.get(task_id) or self._get_conversation(
            task_id, record, paths, resume=bool(record["prompt_sent"])
        )
        if not record["prompt_sent"]:
            conversation.send_message(str(record["prompt"]))
            record["prompt_sent"] = True
        state = _replace_state(state, lifecycle_status=TaskLifecycleStatus.RUNNING)
        record["task_state"] = state.to_dict()
        self._save(paths, record)
        conversation.run()
        record = self._load(paths)
        self._sync_events(paths, record, conversation)
        record = self._load(paths)
        result = _last_assistant_text(record["events"])
        state = _replace_state(
            TaskState.from_dict(record["task_state"]),
            lifecycle_status=TaskLifecycleStatus.COMPLETED,
        )
        record["task_state"] = state.to_dict()
        record["final_result"] = result
        self._save(paths, record)
        return state

    def checkpoint(self, task_id: str) -> Checkpoint:
        self._require_started()
        paths = self._paths(task_id)
        record = self._load(paths)
        state = TaskState.from_dict(record["task_state"])
        active = self._active.get(task_id)
        if active is not None:
            record = self._load(paths)
            self._sync_events(paths, record, active)
            record = self._load(paths)
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            schema_version="1.0",
            task_id=state.task_id,
            session_id=state.session_id,
            workspace_id=state.workspace_id,
            timestamp_utc=datetime.now(timezone.utc),
            parent_checkpoint_id=record["checkpoint_ids"][-1] if record["checkpoint_ids"] else None,
            portable_state={
                "attempt_id": state.attempt_id,
                "candidate_conversation_id": record["conversation_id"],
                "event_count": len(record["events"]),
                "tool_results": record["tool_results"],
                "pending_operations": record["pending_operations"],
            },
            candidate_snapshot_ref=None,
        )
        (self._root / "checkpoints").mkdir(exist_ok=True)
        _atomic_json(self._root / "checkpoints" / f"{checkpoint_id}.json", checkpoint.to_dict())
        record["checkpoint_ids"].append(checkpoint_id)
        self._save(paths, record)
        return checkpoint

    def resume(self, checkpoint: Checkpoint) -> TaskState:
        self._require_started()
        paths = self._paths(checkpoint.task_id)
        record = self._load(paths)
        state = TaskState.from_dict(record["task_state"])
        if state.task_id != checkpoint.task_id or state.workspace_id != checkpoint.workspace_id:
            raise ValueError("checkpoint identity does not match persisted task")
        self._close_conversation(state.task_id)
        state = _replace_state(state, attempt_id=str(uuid.uuid4()), lifecycle_status=TaskLifecycleStatus.RUNNING)
        record["task_state"] = state.to_dict()
        self._save(paths, record)
        conversation = self._get_conversation(state.task_id, record, paths, resume=True)
        self._recover_pending_operations(state.task_id, record, paths, conversation)
        record = self._load(paths)
        self._sync_events(paths, record, conversation)
        return TaskState.from_dict(record["task_state"])

    def interrupt(self, task_id: str) -> TaskState:
        paths = self._paths(task_id)
        record = self._load(paths)
        state = _replace_state(TaskState.from_dict(record["task_state"]), lifecycle_status=TaskLifecycleStatus.INTERRUPTED)
        record["task_state"] = state.to_dict()
        self._save(paths, record)
        return state

    def inspect(self, task_id: str) -> TaskState:
        return TaskState.from_dict(self._load(self._paths(task_id))["task_state"])

    def switch_model(self, task_id: str, model: str) -> None:
        model = _text(model, "model")
        conversation = self._active.get(task_id)
        if conversation is None:
            raise RuntimeError("conversation must be restored before changing model")
        conversation.switch_model(model, self._api_key, self._base_url)
        paths = self._paths(task_id)
        record = self._load(paths)
        state = _replace_state(TaskState.from_dict(record["task_state"]), selected_model=model)
        record["task_state"] = state.to_dict()
        record["model"] = model
        self._save(paths, record)

    def send_message(self, task_id: str, message: str) -> None:
        conversation = self._active.get(task_id)
        if conversation is None:
            raise RuntimeError("conversation must be restored before sending a message")
        conversation.send_message(_text(message, "message"))

    def read_fixture(self, task_id: str, relative_path: str) -> str:
        if relative_path != "input/alpha.txt":
            raise ValueError("fixture read is outside the allowed input")
        if task_id not in self._active:
            raise RuntimeError("no active task for fixture read")
        paths = self._paths(task_id)
        result = (paths.workspace / relative_path).read_text(encoding="utf-8")
        with self._lock:
            record = self._load(paths)
            if not self._action_ids:
                raise RuntimeError("OpenHands did not emit a correlated tool action")
            call_id = self._action_ids.popleft()
            operation_id = f"{record['conversation_id']}:{call_id}"
            result_id = str(uuid.uuid5(uuid.NAMESPACE_URL, operation_id))
            record["tool_results"][operation_id] = {
                "tool_call_id": call_id,
                "result_id": result_id,
                "result": result,
            }
            record["pending_operations"].pop(operation_id, None)
            state = _replace_state(
                TaskState.from_dict(record["task_state"]),
                last_committed_tool_call_id=call_id,
                last_committed_tool_result_id=result_id,
            )
            record["task_state"] = state.to_dict()
            self._save(paths, record)
        return result

    def _get_conversation(
        self, task_id: str, record: JSONMapping, paths: RuntimePaths, *, resume: bool
    ) -> CandidateConversation:
        conversation = self._factory(
            record,
            paths.candidate_persistence,
            resume,
            lambda event: self._record_candidate_event(task_id, event),
            lambda relative_path: self.read_fixture(task_id, relative_path),
            lambda value: self.append_ledger(task_id, value),
        )
        if conversation.conversation_id != record["conversation_id"]:
            raise RuntimeError("OpenHands conversation identity changed")
        self._active[task_id] = conversation
        return conversation

    def _record_candidate_event(self, task_id: str, event: object) -> None:
        event_type = type(event).__name__
        event_id = getattr(event, "id", None)
        projection: JSONMapping = {"candidate_event_type": event_type, "candidate_event_id": str(event_id)}
        tool_name = getattr(event, "tool_name", None)
        if tool_name:
            projection["tool_name"] = str(tool_name)
        call_id = getattr(event, "tool_call_id", None)
        if call_id:
            projection["tool_call_id"] = str(call_id)
        action = getattr(event, "action", None)
        if action is not None:
            projection["action"] = action.model_dump(mode="json", exclude_none=True)
        message = getattr(event, "llm_message", None)
        if message is not None:
            projection["role"] = str(getattr(message, "role", ""))
            content = getattr(message, "content", "")
            projection["content"] = (
                "".join(str(getattr(part, "text", part)) for part in content)
                if isinstance(content, (list, tuple))
                else str(content)
            )
        with self._lock:
            if event_type == "ActionEvent" and tool_name == "read_fixture" and call_id:
                self._action_ids.append(str(call_id))
            if event_type == "ActionEvent" and tool_name == "append_ledger" and call_id:
                self._append_action_ids.append(str(call_id))
            paths = self._paths(task_id)
            record = self._load(paths)
            record["events"].append(projection)
            if event_type == "ActionEvent" and tool_name == "append_ledger" and call_id:
                operation_id = f"{record['conversation_id']}:{call_id}"
                record["pending_operations"][operation_id] = {
                    "operation_id": operation_id,
                    "tool_call_id": str(call_id),
                    "action_event_id": str(event_id),
                    "action": action.model_dump(mode="json", exclude_none=True) if action else {},
                }
            self._save(paths, record)

    def _sync_events(self, paths: RuntimePaths, record: JSONMapping, conversation: CandidateConversation) -> None:
        projected = conversation.event_projection()
        known = {event.get("candidate_event_id"): event for event in record["events"]}
        for event in projected:
            candidate_id = event.get("candidate_event_id")
            if candidate_id in known:
                known[candidate_id].update(event)
            else:
                record["events"].append(event)
        self._save(paths, record)

    def append_ledger(self, task_id: str, value: JSONMapping) -> JSONMapping:
        paths = self._paths(task_id)
        record = self._load(paths)
        if not self._append_action_ids:
            raise RuntimeError("OpenHands did not emit a correlated append action")
        tool_call_id = self._append_action_ids.popleft()
        operation_id = f"{record['conversation_id']}:{_text(tool_call_id, 'tool_call_id')}"
        pending = record["pending_operations"].get(operation_id)
        if pending is None:
            raise RuntimeError("OpenHands append action was not durably prepared")
        ledger = _ledger(paths.workspace)
        try:
            boundary = record.get("crash_boundary")
            if boundary == "before_append" and not pending.get("recovery_started"):
                self._crash(71)
            append_result = ledger.append_ledger(operation_id, value)
            if boundary == "after_append_before_checkpoint" and not pending.get("recovery_started"):
                self._crash(73)
            result = {
                "operation_id": operation_id,
                "result": append_result.result,
                "duplicate_suppressed": append_result.duplicate_suppressed,
                "ledger_rows": ledger.count(operation_id),
            }
        finally:
            ledger.close()
        result_id = str(uuid.uuid5(uuid.NAMESPACE_URL, operation_id))
        record["tool_results"][operation_id] = {
            "tool_call_id": tool_call_id,
            "result_id": result_id,
            **result,
        }
        record["pending_operations"].pop(operation_id, None)
        state = _replace_state(
            TaskState.from_dict(record["task_state"]),
            last_committed_tool_call_id=tool_call_id,
            last_committed_tool_result_id=result_id,
        )
        record["task_state"] = state.to_dict()
        self._save(paths, record)
        return result

    def _crash(self, code: int) -> None:
        if self._crash_hook is not None:
            self._crash_hook(code)
            return
        os._exit(code)

    def _recover_pending_operations(
        self,
        task_id: str,
        record: JSONMapping,
        paths: RuntimePaths,
        conversation: CandidateConversation,
    ) -> None:
        for operation_id, pending in list(record["pending_operations"].items()):
            pending["recovery_started"] = True
            record["pending_operations"][operation_id] = pending
            self._save(paths, record)
            recovered = self._append_ledger_replay(
                task_id,
                operation_id,
                pending["tool_call_id"],
                pending["action"].get("value", {}),
            )
            conversation.record_recovered_tool_result(
                "append_ledger",
                pending["tool_call_id"],
                pending["action_event_id"],
                recovered,
            )
            record = self._load(paths)

    def _append_ledger_replay(
        self, task_id: str, operation_id: str, tool_call_id: str, value: JSONMapping
    ) -> JSONMapping:
        paths = self._paths(task_id)
        record = self._load(paths)
        ledger = _ledger(paths.workspace)
        try:
            appended = ledger.append_ledger(operation_id, value)
            result: JSONMapping = {
                "operation_id": operation_id,
                "result": appended.result,
                "duplicate_suppressed": appended.duplicate_suppressed,
                "ledger_rows": ledger.count(operation_id),
            }
        finally:
            ledger.close()
        result_id = str(uuid.uuid5(uuid.NAMESPACE_URL, operation_id))
        record["tool_results"][operation_id] = {
            "tool_call_id": tool_call_id,
            "result_id": result_id,
            **result,
        }
        record["pending_operations"].pop(operation_id, None)
        state = _replace_state(
            TaskState.from_dict(record["task_state"]),
            last_committed_tool_call_id=tool_call_id,
            last_committed_tool_result_id=result_id,
            lifecycle_status=TaskLifecycleStatus.COMPLETED,
        )
        record["task_state"] = state.to_dict()
        self._save(paths, record)
        return result

    def _close_conversation(self, task_id: str) -> None:
        conversation = self._active.pop(task_id, None)
        if conversation is not None:
            conversation.close()

    def _paths(self, task_id: str) -> RuntimePaths:
        base = self._tasks / _text(task_id, "task_id")
        return RuntimePaths(
            task_file=base / "state.json",
            workspace=base / "workspace",
            candidate_persistence=base / "openhands",
        )

    def _load(self, paths: RuntimePaths) -> JSONMapping:
        return json.loads(paths.task_file.read_text(encoding="utf-8"))

    def _save(self, paths: RuntimePaths, record: JSONMapping) -> None:
        _atomic_json(paths.task_file, record)

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("runtime backend is not started")

    def _create_openhands_conversation(
        self,
        record: JSONMapping,
        persistence: Path,
        resume: bool,
        event_callback: Callable[[object], None],
        fixture_reader: Callable[[str], str],
        ledger_appender: Callable[[JSONMapping], JSONMapping],
    ) -> CandidateConversation:
        try:
            from pydantic import SecretStr
            from openhands.sdk import Agent, Conversation, LLM, Tool
            from poc.runtime.openhands_tool_definitions import configure_tools
        except ImportError as exc:
            raise RuntimeError("OpenHands SDK dependencies are not installed in this runtime") from exc

        configure_tools(fixture_reader, ledger_appender)
        callback = event_callback
        conversation_id = uuid.UUID(str(record["conversation_id"]))
        if resume:
                conv = Conversation(
                agent=None,
                workspace=Path(record["workspace_path"]),
                persistence_dir=persistence,
                conversation_id=conversation_id,
                callbacks=[callback],
                visualizer=None,
                delete_on_close=False,
                max_iteration_per_run=1,
            )
        else:
            llm = LLM(
                model=f"openai/{record['model']}",
                api_key=SecretStr(self._api_key),
                base_url=self._base_url,
                usage_id="shofni-runtime",
            )
            tool_names = ["append_ledger"] if record.get("crash_boundary") else ["read_fixture"]
            agent = Agent(llm=llm, tools=[Tool(name=name) for name in tool_names])
            conv = Conversation(
                agent=agent,
                workspace=Path(record["workspace_path"]),
                persistence_dir=persistence,
                conversation_id=conversation_id,
                callbacks=[callback],
                visualizer=None,
                delete_on_close=False,
                max_iteration_per_run=1,
            )
        return _OpenHandsConversation(conv, event_callback)


class _OpenHandsConversation:
    def __init__(self, conversation: object, event_callback: Callable[[object], None]) -> None:
        self._conversation = conversation
        self._event_callback = event_callback

    @property
    def conversation_id(self) -> str:
        return str(self._conversation.id)

    def send_message(self, message: str) -> None:
        self._conversation.send_message(message)

    def run(self) -> None:
        self._conversation.run()

    def switch_model(self, model: str, api_key: str, base_url: str) -> None:
        from pydantic import SecretStr
        from openhands.sdk import LLM

        self._conversation.switch_llm(
            LLM(
                model=f"openai/{model}",
                api_key=SecretStr(api_key),
                base_url=base_url,
                usage_id=f"shofni-runtime:{model}",
            )
        )

    def event_projection(self) -> list[JSONMapping]:
        from openhands.sdk.event import ActionEvent

        output: list[JSONMapping] = []
        for event in self._conversation.state.events:
            item: JSONMapping = {
                "candidate_event_type": type(event).__name__,
                "candidate_event_id": str(event.id),
            }
            for name in ("tool_name", "tool_call_id"):
                value = getattr(event, name, None)
                if value is not None:
                    item[name] = str(value)
            if isinstance(event, ActionEvent) and event.action is not None:
                item["action"] = event.action.model_dump(mode="json", exclude_none=True)
            output.append(item)
        return output

    def record_recovered_tool_result(
        self, tool_name: str, tool_call_id: str, action_id: str, result: JSONMapping
    ) -> None:
        from openhands.sdk.event import ObservationEvent
        from poc.runtime.openhands_tool_definitions import (
            AppendLedgerObservation,
            ReadFixtureObservation,
        )

        observation_type = {
            "append_ledger": AppendLedgerObservation,
            "read_fixture": ReadFixtureObservation,
        }.get(tool_name)
        if observation_type is None:
            raise ValueError(f"unsupported recovered tool: {tool_name}")
        observation = observation_type.from_text(json.dumps(result, sort_keys=True))
        event = ObservationEvent(
            source="environment",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            observation=observation,
            action_id=action_id,
        )
        on_event = getattr(self._conversation, "_on_event_with_state_lock", None)
        if on_event is None:
            raise RuntimeError("OpenHands conversation cannot record a recovered observation")
        on_event(event)

    def close(self) -> None:
        self._conversation.close()


def _last_assistant_text(events: list[JSONMapping]) -> str | None:
    for event in reversed(events):
        if event.get("candidate_event_type") == "MessageEvent":
            message = event.get("llm_message")
            if isinstance(message, dict) and message.get("role") == "assistant":
                return str(message.get("content", ""))
            if event.get("role") == "assistant" and event.get("content") is not None:
                return str(event["content"])
    return None


def _replace_state(state: TaskState, **changes: Any) -> TaskState:
    values = state.to_dict()
    values.update(changes)
    return TaskState.from_dict(values)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty text")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(temporary, path)


class _LedgerWorkspace:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        (self._root / "state").mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_path: str) -> Path:
        candidate = (self._root / relative_path).resolve()
        if self._root not in candidate.parents and candidate != self._root:
            raise ValueError("ledger path escaped runtime workspace")
        return candidate


def _ledger(workspace: Path):
    from poc.fixtures.ledger import LedgerFixture

    return LedgerFixture(_LedgerWorkspace(workspace))
