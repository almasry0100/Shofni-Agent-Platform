"""Candidate-neutral, deterministic POC fixtures."""

FIXTURE_VERSION = "1.0.0"

from .fallback import FailAfterToolFixture, FailBeforeToolFixture, NarrationOnlyAfterToolFixture
from .ledger import LedgerAppendResult, LedgerFixture, LedgerRecord
from .provider_server import LocalProviderServer, probe_local_provider
from .providers import (
    ChatOnlyProviderFixture,
    MalformedToolJsonFixture,
    NativeToolProviderFixture,
    TextualToolCallFixture,
    make_structured_tool_call,
    parse_textual_tool_call,
    repair_tool_json,
)
from .streaming import StreamingToolFixture, assemble_stream
from .workspace import DisposableWorkspace, WorkspaceError

__all__ = [
    "FIXTURE_VERSION",
    "ChatOnlyProviderFixture",
    "DisposableWorkspace",
    "FailAfterToolFixture",
    "FailBeforeToolFixture",
    "LedgerAppendResult",
    "LedgerFixture",
    "LedgerRecord",
    "LocalProviderServer",
    "MalformedToolJsonFixture",
    "NarrationOnlyAfterToolFixture",
    "NativeToolProviderFixture",
    "StreamingToolFixture",
    "TextualToolCallFixture",
    "WorkspaceError",
    "assemble_stream",
    "make_structured_tool_call",
    "parse_textual_tool_call",
    "probe_local_provider",
    "repair_tool_json",
]
