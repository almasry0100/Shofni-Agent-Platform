# Level 2 Compatibility Matrix

Observed at: 2026-09-30T21:59:34.323512Z

This report uses the newest validated setup and Level 2 observations as the current state. Earlier BLOCKED and FAIL attempts remain listed in the evidence references and history fields. No gateway winner is selected.

| Gateway | Client | Provider | Protocol | Status | Failure | Artifact |
|---|---|---|---|---|---|---|
| Bifrost | Codex | A6api | Responses | PASS |  | sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5 |
| Bifrost | Claude Code | A6api | Anthropic Messages | FAIL | MIXED_FAILURES | sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5 |
| Bifrost | OpenCode | A6api | Chat Completions | PASS |  | sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5 |
| Bifrost | OpenCode | RelayRouter | Chat Completions | FAIL | GATEWAY_FAILURE | sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5 |
| LiteLLM | Codex | A6api | Responses | PASS |  | sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280 |
| LiteLLM | Claude Code | A6api | Anthropic Messages | FAIL | MIXED_FAILURES | sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280 |
| LiteLLM | OpenCode | A6api | Chat Completions | PASS |  | sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280 |
| LiteLLM | OpenCode | RelayRouter | Chat Completions | FAIL | MIXED_FAILURES | sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280 |
| Direct | Codex | RelayRouter | Direct client/provider pairing | NOT_APPLICABLE |  |  |
| Direct | Claude Code | RelayRouter | Direct client/provider pairing | NOT_APPLICABLE |  |  |

Current setup states: Bifrost `PASS`, LiteLLM `PASS`. Current Phase 5 status is `PARTIAL`. Synthetic controls remain separate from live candidate execution.

Historical setup attempts and all sealed Level 2 run matrices are retained in `historical_setup_attempts` and `historical_level2_runs`.
