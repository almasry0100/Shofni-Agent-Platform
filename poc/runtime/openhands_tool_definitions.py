"""Stable OpenHands tool types used only by the lazy candidate adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, ClassVar, Self

from pydantic import Field

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolDefinition, ToolExecutor, register_tool


FixtureReader = Callable[[str], str]
LedgerAppender = Callable[[dict[str, Any]], dict[str, Any]]

_fixture_reader: FixtureReader | None = None
_ledger_appender: LedgerAppender | None = None


class ReadFixtureAction(Action):
    path: str = Field(description="Fixture-relative input path")


class ReadFixtureObservation(Observation):
    pass


class ReadFixtureExecutor(ToolExecutor):
    def __call__(self, action: ReadFixtureAction, conversation=None) -> ReadFixtureObservation:
        if _fixture_reader is None:
            raise RuntimeError("read_fixture tool is not configured")
        return ReadFixtureObservation.from_text(_fixture_reader(action.path))


class ReadFixtureTool(ToolDefinition[ReadFixtureAction, ReadFixtureObservation]):
    name = "read_fixture"

    @classmethod
    def create(cls, conv_state=None, **params) -> Sequence[Self]:
        return [
            cls(
                description="Read the controlled alpha fixture file.",
                action_type=ReadFixtureAction,
                observation_type=ReadFixtureObservation,
                executor=ReadFixtureExecutor(),
            )
        ]


class AppendLedgerAction(Action):
    value: dict[str, Any] = Field(description="JSON value to append")


class AppendLedgerObservation(Observation):
    pass


class AppendLedgerExecutor(ToolExecutor):
    def __call__(self, action: AppendLedgerAction, conversation=None) -> AppendLedgerObservation:
        if _ledger_appender is None:
            raise RuntimeError("append_ledger tool is not configured")
        result = _ledger_appender(action.value)
        return AppendLedgerObservation.from_text(json.dumps(result, sort_keys=True))


class AppendLedgerTool(ToolDefinition[AppendLedgerAction, AppendLedgerObservation]):
    name = "append_ledger"

    @classmethod
    def create(cls, conv_state=None, **params) -> Sequence[Self]:
        return [
            cls(
                description="Append one idempotent operation to the controlled ledger.",
                action_type=AppendLedgerAction,
                observation_type=AppendLedgerObservation,
                executor=AppendLedgerExecutor(),
            )
        ]


def configure_tools(fixture_reader: FixtureReader, ledger_appender: LedgerAppender) -> None:
    global _fixture_reader, _ledger_appender
    _fixture_reader = fixture_reader
    _ledger_appender = ledger_appender
    register_tool(ReadFixtureTool.name, ReadFixtureTool)
    register_tool(AppendLedgerTool.name, AppendLedgerTool)
