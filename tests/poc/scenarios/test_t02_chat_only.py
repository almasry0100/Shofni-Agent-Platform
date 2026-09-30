from __future__ import annotations

from poc.fixtures.providers import ChatOnlyProviderFixture, parse_textual_tool_call
from poc.fixtures.scenarios import run_scenario


def test_chat_only_provider_is_offline_control_with_deterministic_emulation() -> None:
    seed = "t02-fixed-seed"
    request = {"path": "input/alpha.txt", "tool_emulation": True}
    fixture = ChatOnlyProviderFixture()

    first = fixture.respond(request, seed)
    second = fixture.respond(request, seed)
    parsed = parse_textual_tool_call(first["content"], seed)
    record = run_scenario("t02_chat_only", seed)

    assert first == second
    assert first["tool_calls"] == []
    assert record["normalized_response"]["provider_response"]["tool_calls"] == []
    assert record["normalized_response"]["tool_execution_count"] == 1
    assert record["behavior_mode"] == "EMULATED"
    assert record["result_status"] == "PASS"
    assert parsed.tool_calls == tuple(record["normalized_response"]["canonical_tool_calls"])
    assert record["test_id"] == "T02_CHAT_ONLY"
    assert record["normalized_response"]["canonical_tool_calls"][0]["id"].startswith("call_")
