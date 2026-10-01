# Final Compatibility Readiness

Readiness is reported by provider/client tuple. A tuple result does not make a gateway architecture eligible by itself.

| Provider | Client | Protocol and route | Readiness | Evidence boundary |
| --- | --- | --- | --- | --- |
| A6api | Codex | Responses, `gpt-5.4-mini` | `READY` | Historical repeated live rows pass for both gateways. |
| A6api | Claude Code | Anthropic Messages to A6api OpenAI-compatible Responses, `gpt-5.4-mini` | `PARTIAL` | Three client failures per gateway; model-list probe passed, but the T03 request and provider-bound request were not observed. Root cause is unverified. |
| A6api | OpenCode | Chat Completions, `gpt-5.4-mini` | `READY` | Historical repeated live T04/T07/T08 rows pass for both gateways. |
| RelayRouter | OpenCode | Chat Completions with Shofni tool emulation, `stealth/openai/gpt-5.6-sol` | `BLOCKED_EXTERNAL_PROVIDER` | One direct control timed out at 240 seconds without a provider response and before a gateway candidate. The underlying cause is unverified. Candidate T04 was skipped. |
| RelayRouter | Claude Code | Out of scope for this POC | `UNSUPPORTED` | No pairing was run. |
| RelayRouter | Codex | Out of scope for this POC | `UNSUPPORTED` | No pairing was run. |

Aggregate summaries: A6api `PARTIAL`; RelayRouter `BLOCKED_EXTERNAL_PROVIDER`; Codex `READY` for the A6api tuple; Claude Code `PARTIAL`; OpenCode `PARTIAL` across A6api and RelayRouter. These summaries preserve the route-level differences. The generated T12 report is authoritative for its per-candidate rows and records the same provider aggregates.

The RelayRouter result is not a candidate pass or fail. The Claude Code result is not attributed to either gateway because request-level candidate and provider reach were not observed.
