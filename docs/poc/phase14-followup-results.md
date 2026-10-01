# Phase 14 Follow-Up Results

Run `20261001T130018Z` started from `main` at `2889e86d472d23693c76a46460c09ed2b651d27e`, with a clean worktree and 71 passing baseline POC tests. The committed follow-up plan was `tests/poc/evidence/phase-14/batch-d-phase14-20261001T121200Z/plan.json`.

## D-F1: OpenHands Compositions

**BLOCKED: `PROVENANCE_MISMATCH`.** Phase 7 recorded 187 installed distributions; Phase 11 recorded 232, with 45 additional distributions. Python 3.12.10, uv 0.11.7, frozen-lock requests, and the OpenHands tree hash match, but Phase 7 does not record project/group/extra selection. The difference is not proven to be a counting-only difference, so execution stopped before either composition or any provider call.

The planned topologies were OpenHands RuntimeBackend -> Bifrost -> A6api and OpenHands RuntimeBackend -> LiteLLM -> A6api, using model A `gpt-5.4-mini` and model B `gpt-5.5`. Neither topology, task, workspace, checkpoint, tool action, or runtime restart was executed. The harness now uses explicit Windows bind mounts, gateway DNS/internal ports, route fail-fast normalization, UTF-8-safe subprocess capture, and bounded sanitized startup/runtime diagnostics; those controls were checked offline. Gateway startup diagnostics were not exercised live. Evidence: `tests/poc/evidence/phase-14-followup/D-F1/20261001T130018Z/provenance-review.json`.

## D-F2: Level 2

**PARTIAL.** One raw-protocol-equivalent T03 attempt ran for each locked gateway. Both route probes passed, and each gateway returned a valid Anthropic Messages assistant response with one `read_fixture` tool call, a correlated tool result of `alpha fixture input\n`, and a final `end_turn` response with no repeated tool call. Each pairing made two gateway HTTP requests, both status 200, and each container, network, temporary config, and host port was cleaned up.

| Gateway | Candidate tree | Messages endpoint | Tool-call ID | Result |
|---|---|---|---|---|
| Bifrost | `sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe` | `/anthropic/v1/messages` | `call_mDRIbTNNn8AlSYNllQQNFDrH` | `PASS_RAW_PROTOCOL_EQUIVALENT` |
| LiteLLM | `sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb` | `/v1/messages` | `call_2poyA2jdAAxbefa5OHEJiDuG` | `PASS_RAW_PROTOCOL_EQUIVALENT` |

Both rows used the `read_fixture` tool schema with required string field `path`, configured A6api's OpenAI Responses route `/v1/responses` with `gpt-5.4-mini`, and set gateway retries to zero. The gateway HTTP client did not expose upstream A6api HTTP statuses. The runner did not invoke the Claude Code executable; the rows validate the Messages gateway boundary and continuation flow, not Claude Code's own parser or client-side schema handling. Detailed evidence is in `tests/poc/evidence/phase-14-followup/D-F2/20261001T130018Z/`.

T04 is **BLOCKED: `EVIDENCE_DESIGN_CONFLICT`** for both gateways. The Phase 14 follow-up requires A6api with Codex/Claude Code matrix clients, while the authoritative T04 contract requires OpenCode, RelayRouter, and Shofni tool emulation. No provider call or candidate process was used for T04, and RelayRouter was not substituted. Evidence: `tests/poc/evidence/phase-14-followup/D-F2/20261001T130018Z/t04-design-conflict.json`.

## D-F3: Mastra License Review

**BLOCKED: `LICENSE_BOUNDARY_BLOCKER`.** The exact pinned `@mastra/core` 1.72.0-alpha.8 durable Agent closure reaches the public Agent's imports from `packages/core/src/auth/ee`, durable types that import `ee/fga-check`, and `ee/LICENSE`, which identifies the EE source as non-OSS. No EE code, stubs, aliases, patches, or prebuilt artifacts were used. There were no execution reruns or provider calls. Evidence: `tests/poc/evidence/phase-14-followup/D-F3/20261001T130018Z/license-decision.json`.

## Decision Delta

| Plane | Decision | Basis |
|---|---|---|
| Gateway | **NO_DECISION_YET** | Both T03 raw protocol probes passed, but T04 is unresolved and prior mandatory Level 2 failures remain. |
| Runtime | **NO_DECISION_YET** | OpenHands D-F1 is blocked on provenance; Mastra remains license-blocked. |
| Composition | **NO_DECISION_YET** | Neither D-F1 composition was executed or proven. |

No candidate is selected. Level 2 remains `CLIENT`; Level 3 remains `RUNTIME`.

All four candidate source tree hashes and file counts match `docs/poc/candidate-lock.json`: Bifrost 5,172; LiteLLM 12,075; OpenHands 1,796; Mastra 18,938. Historical evidence remains preserved. `A6API_KEY` was reported as present only; no value or hash, Authorization header, cookie, or raw evidence was persisted. Follow-up containers, networks, temporary configs, runtime roots, and ports were removed or released; pinned images were pre-existing and retained.

Machine-readable decision delta: `tests/poc/evidence/phase-14-followup/20261001T130018Z/summary.json`. No commit or push was made.

## Scope And Boundary

All three rerun budgets were respected: D-F1 started no runtime or provider request, D-F2 used one T03 attempt per gateway and no T04 attempt, and D-F3 performed zero execution reruns. No candidate source tree was modified, no Mastra EE code was used, no OpenRouter call or RelayRouter substitution occurred, and no production implementation began. No winner was forced.

Validation passed: the baseline was 71 tests, the full offline POC suite passed 81 tests, and the requested focused groups passed 24 tests, including 10 follow-up regression tests.
