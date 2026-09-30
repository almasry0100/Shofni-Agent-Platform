from __future__ import annotations

from typing import Any

from poc.evidence.taxonomy import FailureClass

from .providers import NativeToolProviderFixture


class FailBeforeToolFixture:
    fixture_name = "FailBeforeToolFixture"

    def primary(self, seed: str) -> dict[str, Any]:
        return {
            "status": "FAILED",
            "failure_class": FailureClass.PROVIDER_FAILURE.value,
            "failure_stage": "BEFORE_TOOL_EFFECT",
            "tool_effect_occurred": False,
            "attempt_id": f"attempt_primary_{seed}",
        }

    def fallback(self, seed: str) -> dict[str, Any]:
        return NativeToolProviderFixture().respond(
            {"tool_name": "read_fixture", "arguments": {"path": "input/alpha.txt"}},
            seed,
        )


class FailAfterToolFixture:
    fixture_name = "FailAfterToolFixture"

    def primary_tool_request(self, seed: str) -> dict[str, Any]:
        return NativeToolProviderFixture().respond(
            {"tool_name": "read_fixture", "arguments": {"path": "input/alpha.txt"}},
            seed,
        )

    def fail_after_result(self, seed: str) -> dict[str, Any]:
        return {
            "status": "FAILED",
            "failure_class": FailureClass.PROVIDER_FAILURE.value,
            "failure_stage": "AFTER_TOOL_RESULT",
            "tool_effect_occurred": True,
            "attempt_id": f"attempt_primary_{seed}",
        }

    def fallback(self, seed: str, existing_tool_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": f"Completed from the recorded result: {existing_tool_result['result']['text']}",
            "tool_calls": [],
            "finish_reason": "stop",
            "received_tool_results": [existing_tool_result],
            "attempt_id": f"attempt_fallback_{seed}",
        }


class NarrationOnlyAfterToolFixture:
    fixture_name = "NarrationOnlyAfterToolFixture"

    def respond(self, seed: str) -> dict[str, Any]:
        return {
            "content": "I will read the next file.",
            "tool_calls": [],
            "finish_reason": "stop",
            "attempt_id": f"attempt_narration_{seed}",
        }
