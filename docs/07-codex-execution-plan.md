# 07 - Codex Execution Plan

**Project:** Shofni Agent Platform
**Status:** Source-driven execution plan; POC not started
**Evidence date:** 2026-09-30
**Decision rule:** no gateway or runtime winner is selected here.

## 1. Executive Scope

This plan converts the frozen Shofni architecture into an implementation-ready Level 2 plus Level 3 POC. Level 2 keeps the client as Agent and Tool Executor (ToolExecutionBackend = CLIENT). Level 3 moves the Agent Loop, Tool Executor, and durable task state into Shofni (ToolExecutionBackend = RUNTIME).

Evaluate layers independently, then run all four compositions:

1. Bifrost + OpenHands SDK
2. Bifrost + Mastra
3. LiteLLM + OpenHands SDK
4. LiteLLM + Mastra

Live scope is A6api and RelayRouter only. A6api is the observed positive control for Codex, Claude Code, and OpenCode. RelayRouter is OpenCode chat-only/emulation evidence. Codex x RelayRouter and Claude Code x RelayRouter are known unsupported direct pairings. T02 must use a deterministic chat-only fixture and never RelayRouter as a Codex path. OpenRouter is outside this POC.

The governing principle is: reuse infrastructure, own contracts and compatibility intelligence, keep backends replaceable, build Level 2 as permanent core, then add Level 3 without rewriting it.

## 2. Verified Repository Baseline

The actual Shofni Git root is:

~~~text
<USERPROFILE>\Desktop\Shofni Agent Platform\Shofni Agent Platform
~~~

The opened parent directory is only a container. The baseline before this artifact was branch main with clean status. Recheck status before and after writing. Candidate trees were not modified; they are extracted copies without local Git directories, so the future POC must pin exact package versions, commits, or image digests.

Inspected trees:

- bifrost-dev
- litellm-main
- software-agent-sdk-main
- mastra-main
- pydantic-ai-main
- langgraph-main
- temporal-main

Authoritative Shofni inputs read:

~~~text
README.md
docs/01-level-2-level-3-original.md
docs/02-open-source-deep-research.md
docs/03-final-architecture-decisions.md
docs/04-provider-docs.md
docs/04-provider-inventory.md
docs/05-client-readiness.json
docs/05-client-targets.md
docs/06-poc-acceptance-scenarios.md
docs/repro/*
docs/research/licenses.md
~~~

## 3. Source Inspection Method

Repository archaeology used rg file enumeration, targeted symbol search, direct source reads, and nearby tests. A README or feature name is not treated as implementation proof. Each claim is classified as declared, observed, effective, or POC_REQUIRED. No candidate code was executed, installed, edited, or committed; no credential value was read or printed.

## 4. Level 2 Source Findings

### Bifrost

- core/schemas/provider.go defines Provider, ProviderConfig, CustomProviderConfig, AllowedRequests, NetworkConfig, normalized provider errors, base URLs, request-path overrides, retry/backoff, stream idle limits, and redaction helpers. The provider interface includes list models, Chat, Responses, and streaming.
- core/bifrost.go owns ListModelsRequest/ListAllModels, ChatCompletionRequest, ResponsesRequest, stream handling, plugin pipeline, shouldTryFallbacks, prepareFallbackRequest, provider dispatch, lifecycle operations, and per-attempt fallback identity.
- The provider interface comment in `core/schemas/provider.go` explicitly says non-OpenAI Responses calls use Chat internally; treat that as a translation path, not proof of native upstream Responses semantics. Bifrost also has MCP execution features, but those do not replace the initial Level 2 CLIENT-owned tool executor or Shofni Level 3 runtime.
- transports/bifrost-http/integrations/openai.go creates OpenAI Chat, Responses, stream, lifecycle, and /models routes and wire converters. integrations/anthropic.go handles Anthropic Messages; integrations/router.go selects protocol integrations.
- core/schemas/modelcapabilities.go stores declared per-model/provider metadata: tool limits, namespace and async tools, parameter drops, reasoning shape, beta headers, and request paths.
- plugins/logging, telemetry, routing, compat, and jsonparser provide hooks, routing, telemetry, compatibility processing, and parsing inputs.
- Tests read: transports/bifrost-http/integrations/router_test.go, router_listmodels_test.go, anthropic_test.go, openai_test.go, openai_stream_framing_test.go, core/providers/openai/responses_test.go, core/providers/anthropic/responses_test.go, core/schemas/responses_test.go, and responsestoolunmarshal_test.go. They prove transport and serialization behavior, not Shofni emulation or exactly-once semantics.
- transports/bifrost-http/main.go and Docker examples provide the HTTP operational surface. LICENSE is Apache-2.0. README-described enterprise features must not be assumed to exist in the open-source tree.

Reuse directly: provider dispatch/configuration, protocol routes, model listing, stream framing, retries/fallback primitives, metadata, and hooks. Add a thin Shofni adapter for canonical requests/events and evidence. Shofni must own effective capability truth, chat-only emulation, textual parsing, bounded repair, duplicate suppression, post-tool fallback policy, and compatibility reports. Exact Codex Responses events, A6api OpenAI-route translation, fragmented tools, and post-tool fallback remain POC questions.

### LiteLLM

- litellm/router.py defines Router, model groups, routing strategies, retries, cooldowns, deployment selection, and fallback configuration.
- litellm/proxy/proxy_server.py contains OpenAI Chat/Responses routes and /v1/models; Router and shared stream modules provide route fallback, streaming, and cancellation behavior.
- litellm/proxy/anthropic_endpoints/endpoints.py contains Anthropic Messages endpoint/bridge handling.
- litellm/llms/openai_like/chat/transformation.py, messages/transformation.py, and responses/transformation.py implement OpenAI-compatible provider transformations; custom endpoint config is resolved through OpenAI-like provider modules.
- litellm/litellm_core_utils/fallback_utils.py and streaming_handler.py implement fallback normalization and stream handling; router/proxy modules add route-level fallback, SSE, and disconnect behavior.
- Tests read: `tests/unit/responses/`, `tests/llm_responses_api_testing/`, `tests/router_unit_tests/`, `tests/integration/messages_endpoint/responses_bridge/`, `tests/integration/providers/`, `tests/unit/litellm_core_utils/test_fallback_utils.py`, `tests/unit/litellm_core_utils/test_streaming_handler.py`, and `tests/unit/llms/openai_like/`. They cover endpoint/transform behavior, not Shofni parser/emulation or side-effect policy.
- pyproject.toml identifies LiteLLM 1.104.0, Python 3.10-3.14, proxy extras, and a broad dependency surface. LICENSE states MIT outside enterprise/; enterprise/ is separately licensed.

Reuse directly: proxy startup, Chat/Responses/Messages translation, /models, OpenAI-like providers, router/fallback/retry, streaming, and hooks. Add the same Shofni adapter surface as Bifrost. Windows startup, A6api OpenAI-route Messages translation, fragmented tool events, and post-tool fallback remain POC questions.

### Level 2 conclusion

Both candidates provide substantial gateway infrastructure. Neither implements the complete Shofni contract. Compare adapter effort and measured behavior, not feature names or popularity.

### Source-derived refinements to prior research

- The earlier deep-research note said incoming Bifrost Anthropic Messages support had not been established. The inspected tree contains `transports/bifrost-http/integrations/anthropic.go`, route selection in `integrations/router.go`, and `integrations/anthropic_test.go`; this confirms an inbound endpoint and tested mapping surface. It does **not** prove T03 with Claude Code through the specific A6api OpenAI-compatible route, which remains a POC test.
- Bifrost's `plugins/jsonparser` accumulates streamed response content and closes partial JSON into parseable JSON. That is distinct from identifying a textual tool call, validating its registered tool schema, or bounded repair with an ambiguity no-execute rule. Do not treat it as Shofni's T05/T06 behavior.
- LiteLLM's inspected `pyproject.toml` declares version 1.104.0; prior research records the PyPI compromise at 1.82.7 and 1.82.8. This does not label the inspected source compromised. Before POC, pin the exact source revision and package artifact hashes/provenance instead of selecting an unverified PyPI artifact by version range.
- Both gateways have routing/retry machinery, but neither receives Shofni's external tool commit state as a general fallback invariant. The POC must test the state boundary explicitly rather than infer side-effect safety from a fallback unit test.
- OpenHands duplicate event-ID rejection concerns the event log; it does not deduplicate an external tool effect. Mastra's provider-executed commit gate prevents duplicate internal result commitment on that execution path; it does not establish exactly-once behavior for arbitrary Shofni tools.
- Candidate-declared capability metadata remains input to the compatibility report, not proof of effective capability for a given client/provider/model tuple. Only observed T01-T12 evidence changes the effective state.

## 5. Level 2 Capability Gap Matrix

### Detailed Level 2 ownership matrix

Status key: **Yes** means an implementation exists for the named behavior; **Partial** means infrastructure exists but does not establish Shofni semantics; **No** means no qualifying implementation was found in inspected source; **POC** means source inspection cannot establish effective behavior for the exact client/provider/model pair. Tests prove only their asserted cases.

| Capability | Bifrost | LiteLLM | Evidence | Reusable as-is? | Thin adapter required? | Shofni-owned implementation required? | POC validation required? | Txx |
|---|---|---|---|---|---|---|---|---|
| Chat Completions | Yes: `core/bifrost.go`, `transports/bifrost-http/integrations/openai.go` | Yes: `litellm/proxy/proxy_server.py`, `litellm/router.py` | Bifrost OpenAI integration tests; LiteLLM `tests/unit/llms/openai_like/chat/test_openai_like_chat_transformation.py` | Transport/provider dispatch | Canonical request/response map | Canonical contract and client policy | Exact client/provider route | T03/T04/T07 |
| Responses API | Yes: core/provider interface and OpenAI integration | Yes: proxy and OpenAI-like Responses transformation | Bifrost `core/providers/openai/responses_test.go`, `transports/bifrost-http/integrations/openai_stream_framing_test.go`; LiteLLM `litellm/llms/openai_like/responses/transformation.py`, `tests/unit/responses/`, `tests/unit/llms/openai_like/responses/test_openai_like_responses.py` | Partial; event semantics need mapping | Event and error map | Responses/client semantics | Codex event sequence and tool continuation | T01/T02/T08 |
| Anthropic Messages | Yes: `transports/bifrost-http/integrations/anthropic.go` | Yes: `litellm/proxy/anthropic_endpoints/endpoints.py` and bridge | Bifrost `transports/bifrost-http/integrations/anthropic_test.go`; LiteLLM `tests/integration/messages_endpoint/responses_bridge/`, `tests/unit/llms/openai_like/messages/test_openai_like_anthropic_messages_transformation.py` | Partial | Role/tool/result adapter | Canonical semantics and route policy | A6api OpenAI-compatible route | T03 |
| `/models` | Yes: `ListModelsRequest`/`ListAllModels` | Yes: proxy list and Router registry | Bifrost `core/bifrost.go`, `transports/bifrost-http/integrations/router_listmodels_test.go`; LiteLLM `litellm/proxy/proxy_server.py`, `tests/router_unit_tests/test_get_model_list_alias_optimization.py` | Yes for raw listing | Metadata projection | Effective capability state | Live visibility and aliases | T12 |
| Protocol translation | Yes: OpenAI/Anthropic integrations | Yes: protocol transformation modules | Bifrost `transports/bifrost-http/integrations/*.go`; LiteLLM `litellm/llms/openai_like/{chat,messages,responses}/transformation.py` | Partial | Canonical envelope | Loss/compatibility rules | Field-by-field client tests | T01-T04 |
| Provider normalization/custom base URL | Yes: `core/schemas/provider.go` custom config/path | Yes: `litellm/llms/openai_like/`, dynamic config | Bifrost `CustomProviderConfig`; LiteLLM OpenAI-like tests and `dynamic_config.py` | Mostly | Provider identity/config adapter | Secret isolation and effective capability | A6api route shapes | T01/T03 |
| Custom OpenAI-compatible and Anthropic-compatible endpoints | Custom provider selects a base provider type and per-operation paths; compatibility details are protocol-specific | OpenAI-like Chat/Responses/Messages transforms and Anthropic Messages bridge provide reusable pieces | Bifrost `core/schemas/provider.go` (`CustomProviderConfig`, `BaseProviderType`, `RequestPathOverrides`), `transports/bifrost-http/integrations/anthropic.go`; LiteLLM `litellm/llms/openai_like/chat/transformation.py`, `messages/transformation.py`, `responses/transformation.py`, `litellm/proxy/anthropic_endpoints/endpoints.py` | Partial; don't assume arbitrary endpoint interchangeability | Provider/protocol path adapter | Endpoint declaration and compatibility validation | Verify exact A6api endpoints and OpenAI vs Messages route | T03 |
| Streaming/SSE normalization | Yes: stream interfaces/framing | Yes: iterators/SSE/fallback stream handling | Bifrost `transports/bifrost-http/integrations/openai_stream_framing_test.go`; LiteLLM `litellm/litellm_core_utils/streaming_handler.py`, `tests/unit/litellm_core_utils/test_streaming_handler.py`, `tests/unit/responses/test_responses_streaming_iterator.py` | Transport primitives | Canonical event adapter | Event lifecycle and provenance | Fragmented calls and partial failures | T08 |
| Native tool schemas/calls/results | Yes: request schemas and provider conversion | Yes: transformations and Responses bridge | Bifrost Responses/provider tests; LiteLLM `tests/unit/responses/`, `tests/integration/messages_endpoint/responses_bridge/` | Partial | Preserve call/result IDs | Correlation and continuation policy | Native A6api workflows | T01/T03/T07 |
| `tool_choice` / required-tool semantics | Request fields and provider mappings exist; cross-provider behavior varies | Request fields and provider transforms exist; cross-provider behavior varies | Bifrost `core/schemas/` request types/provider tests; LiteLLM Responses and OpenAI-like Chat transformation tests | Partial | Normalize mode and names | Client contract and unsupported-mode reporting | Required/auto/none against selected route | T01/T03 |
| Native tool-call forwarding | Yes: typed chat/Responses tool fields and provider conversion | Yes: protocol transforms and bridge | Bifrost `core/schemas/responses.go`, `core/providers/openai/responses_test.go`; LiteLLM `tests/unit/responses/test_custom_tool_call.py`, `tests/integration/messages_endpoint/responses_bridge/` | Partial; provider quirks remain | Normalize IDs/arguments | Native-first dispatch decision | Exact call ID/name/arguments across live route | T01/T03 |
| Tool-result forwarding | Yes: request schema/provider conversion | Yes: message/Responses bridge conversion | Bifrost Responses schema/provider tests; LiteLLM `tests/unit/responses/` and `tests/integration/messages_endpoint/responses_bridge/` | Partial | Map result/call correlation | Continuation/result semantics | Result returns on same protocol with matching ID | T01/T03/T07 |
| Sequential tools | Wire support only; gateway does not own client loop | Wire support only; gateway does not own client loop | Candidate protocol tests; Shofni T07 controls continuation | No | Turn/result adapter | Ordering and no-premature-stop policy | Two-tool client workflow | T07 |
| Parallel tools | Schemas can carry multiple calls; no Shofni execution policy | Same | Candidate schemas/tests; no exactly-once evidence | Partial | Correlation/order adapter | Concurrency and side-effect policy | Fragmented/parallel fixture | T08/T11 |
| Chat-only emulation | No complete Shofni contract | No complete Shofni contract | Source inspection; Shofni `docs/repro/` | No | Emulation boundary | Synthetic calls, safety, mode labels | Fixture and OpenCode/RelayRouter | T02/T04 |
| Synthetic structured tool calls | No Shofni synthesis contract | No Shofni synthesis contract | Bifrost JSON parser only normalizes accumulated JSON; LiteLLM transforms existing tool structures; Shofni T02/T04 requirements | No | Adapter insertion point | Generate validated structured call only after safe classification | Synthetic fixture and real OpenCode/RelayRouter chat | T02/T04 |
| Textual call parsing | `plugins/jsonparser/` is input parsing, not Shofni recognition | No equivalent end-to-end contract found | Bifrost `plugins/jsonparser/main.go`, `utils.go`; Shofni `docs/repro/text-tool-call-example.md` | No | Parser adapter | False-positive refusal and schema validation | Corpus and narration-only case | T05 |
| Malformed JSON repair | Streaming JSON completion is distinct from tool-argument repair | Stream/output recovery is not bounded repair | Bifrost `plugins/jsonparser/main.go`, `plugins/jsonparser/utils.go`; LiteLLM `tests/integration/providers/test_responses_bridge_incomplete.py`, `tests/unit/responses/test_sse_output_recovery.py` | No | Repair hook | Maximum two attempts; ambiguous no-execute | Deterministic malformed corpus | T06 |
| Capability metadata/probing/report | Declared model/provider metadata and list APIs | Router/model metadata and health/cooldown pieces | Bifrost `core/schemas/modelcapabilities.go`; LiteLLM `litellm/router.py`; neither supplies Shofni effective report | Metadata only | Probe/report adapter | Declared/probed/observed/effective registry | Regenerated report | T12 |
| Compatibility reporting | Candidate has compatibility/config metadata, not Shofni pair report | Candidate has model/route metadata, not Shofni pair report | Bifrost `core/schemas/modelcapabilities.go`, `plugins/compat/`; LiteLLM Router/model-list endpoints; Shofni T12 schema | No complete report | Report input adapter | Client/provider/model protocol matrix and provenance | Regenerate from captured evidence | T12 |
| Provider/model routing | Routing plugin and provider/model selection | Router strategies, deployment selection, aliases | Bifrost `plugins/routing/`, `core/bifrost.go`; LiteLLM `litellm/router.py`, `litellm/types/router.py` | Yes for configured routing | Pass route intent/identity | Shofni route decision and compatibility gate | Assert exact provider/model selected | T09/T12 |
| Fallback/retry | `shouldTryFallbacks`/`prepareFallbackRequest`, provider retry settings | Router retries/fallback utility and streaming fallback logic | Bifrost `core/bifrost.go`, `core/schemas/provider.go`; LiteLLM `litellm/router.py`, `litellm/litellm_core_utils/fallback_utils.py`, `tests/unit/litellm_core_utils/test_fallback_utils.py` | Partial | Attempt/event adapter | Common retry budget and provenance | Injected route failures | T09 |
| Fail-before-tool handling | Provider failure fallback primitive | Router fallback primitive | Candidate fallback implementations; fixture establishes tool not yet committed | Partial | Attempt status propagation | Permit configured switch before any committed tool effect | Fail-before fixture should switch once | T09 |
| Fail-after-successful-tool handling | No tool-commit awareness in gateway fallback | No tool-commit awareness in gateway fallback | Gateway fallback sources do not receive Shofni external tool commit state | No | Propagate commit marker | Stop semantic retry or resume with saved result | Crash/failure after successful tool | T09/T11 |
| Duplicate-side-effect risk | Gateway does not own client tools or an operation ledger | Same | Candidate gateway ownership boundary; Shofni T09/T11 | No | Carry operation ID where available | Deduplication or duplicate detection policy | Controlled ledger only; no general claim | T09/T11 |
| Error normalization/cancellation | Typed provider errors, stream/lifecycle controls | Exception/fallback metadata, disconnect cleanup | Bifrost `core/schemas/provider.go`; LiteLLM `litellm/litellm_core_utils/streaming_handler.py`, `tests/test_litellm/proxy/pass_through_endpoints/test_streaming_handler_interrupt.py` | Partial | Error/event adapter | Shofni taxonomy and attempt state | Layer attribution | All |
| Timeout behavior | Provider network config includes request timeout, retry/backoff and stream idle timeout | Proxy/router and provider request configuration offer timeout handling | Bifrost `core/schemas/provider.go` (`NetworkConfig`, `CheckAndSetDefaults`); LiteLLM `litellm/router.py`, `litellm/proxy/proxy_server.py` | Transport/config primitives | Map common timeout budget and cancellation | Per-attempt deadline semantics | Same timeout budget and timeout class across candidate runs | T08/T09 |
| Custom adapters/hooks/evidence | Provider interface plus logging/telemetry/compat plugins | Provider registry plus callbacks/logging | Bifrost `plugins/{logging,telemetry,compat}/`; LiteLLM proxy callback/logging modules | Extension points | Recorder bridge | Redaction and evidence schema | Secret scan and IDs | All |
| Fail-after-tool and duplicate side effects | Outside gateway ownership | Outside gateway ownership | Candidate source boundaries; Shofni T09/T11 ledger requirement | No | Propagate attempt/operation IDs | Idempotency ledger and suppression | Controlled failure fixtures | T09/T11 |

### Qualitative Level 2 comparison

These are implementation-planning estimates, not rankings. Measure adapter lines, startup, memory, latency, dependency size, and failure diagnosis during the POC.

| Candidate | Integration complexity / Shofni adapter | Shofni-owned gaps | Operational and Windows-local complexity | Debugging / testability | Production implication |
|---|---|---|---|---|---|
| Bifrost | Moderate. Explicit Go provider and transport interfaces make the adapter boundary clear; canonical event mapping and plugin configuration remain required. | Effective capability report, chat-only emulation, textual parsing/repair, side-effect-aware fallback, evidence and canonical errors. | Go service/binary is a plausible single local process; verify build/runtime, config paths, plugin packaging, ports, and cleanup on Windows. | Nearby Go integration tests are focused; instrument core/plugin transitions because tests do not prove Shofni client/provider pairs. | Apache-2.0 core is permissive; audit plugin/transitive notices and keep Shofni independent of Bifrost structs. |
| LiteLLM | Moderate to high. Broad Python proxy/provider surface reduces translation code but adds configuration, callback, and dependency choices. | Same Shofni gaps; router fallback does not know committed external tool effects and bridge behavior needs exact evidence. | Direct Python proxy startup is convenient, but dependency footprint and optional extras are broad; use the smallest checked-out core and validate Windows startup/process cleanup. | Large unit/integration surface aids diagnosis but increases route/provider permutations; use identical fixtures and redacted traces. | MIT applies outside `enterprise/`; exclude enterprise modules, pin revision, and audit selected dependencies/configuration. |

## 6. Level 3 Source Findings

### OpenHands Software Agent SDK

- openhands-sdk/openhands/sdk/agent/agent.py defines Agent.step and execution.
- conversation/impl/local_conversation.py owns LocalConversation.run, lifecycle, workspace, persistence directory, callbacks, client tools, switch_llm, and LLM registry.
- conversation/state.py defines ConversationState.create for open/resume and stores conversation ID, workspace, status, agent_state, leaf event, and statistics.
- conversation/event_store.py implements a file-backed EventLog with locks, event IDs, parent/branch traversal, stale-index recovery, and duplicate event-ID rejection.
- agent/acp_agent.py is an ACP subprocess/MCP boundary with tool-call correlation IDs.
- openhands-workspace/openhands/workspace and openhands-tools/openhands/tools provide local/Docker/API/cloud workspaces and file/editor/grep/shell/browser-style tools. Git/worktree behavior is adapter-specific.
- Tests read: `tests/sdk/conversation/local/test_conversation_core.py`, `tests/sdk/conversation/local/test_client_tools_persistence.py`, `tests/sdk/conversation/test_event_store.py`, `tests/sdk/conversation/test_event_tree.py`, `tests/cross/test_conversation_restore_behavior.py`, `tests/cross/test_agent_loading.py`, `tests/sdk/conversation/test_switch_model.py`, `tests/sdk/conversation/test_local_conversation_mcp.py`, and `tests/workspace/test_workspace_pause_resume.py`.
- Root pyproject.toml is a UV workspace and the SDK LICENSE is MIT.

Reuse: agent loop, conversation/event persistence, local workspace/tools, LLM switching, callbacks, MCP/ACP points. Shofni must add task/session/attempt/workspace/checkpoint envelopes and operation-id policy. Fresh-process restore, tool-success interruption, worktree identity, and ledger behavior require T10/T11 evidence.

### Mastra

- packages/core/src/agent/agent.ts owns generation/streaming, model invocation, tools, tool choice, and step limits.
- packages/core/src/agent/durable/create-durable-agent.ts, durable-agent.ts, and durable/workflows/create-durable-agentic-workflow.ts provide durable workflow input, run IDs, snapshots, recovery, model resolution, and workflow topology.
- durable-agent.ts carries runId, optional threadId/resourceId, recovery leases, resume/recover, model-list restoration, message lists, and recovery events.
- packages/core/src/storage/factory-storage.ts and filesystem-db.ts provide pluggable storage, atomic temp-file writes, and path traversal checks.
- Tests read: `packages/core/src/agent/durable/__tests__/durable-agent-crash-recovery.test.ts`, `durable-agent-model-fallback.test.ts`, `durable-agent-tools.test.ts`, `packages/core/src/agent/durable/__tests__/recover-active-runs.test.ts`, `packages/core/src/agent/durable/workflows/steps/tool-call-provider-executed.test.ts`, `tool-call-provider-fallback.test.ts`, `packages/core/src/agent/durable/run-registry.test.ts`, and `packages/core/src/mastra/recover-all-durable-agents.test.ts`. These prove recovery, model fallback, tool registration, provider-executed commit guards, and tool resolution, not arbitrary side-effect exactly-once.
- LICENSE.md is Apache-2.0 for the open-source tree; `ee/LICENSE` is separate. The repository is a pnpm/Turbo TypeScript monorepo; use only the minimum open-source core.

Reuse: durable loop/workflow, snapshots, run IDs, storage, recovery leases, model fallback, tool registry, events/tracing. Shofni must define public task identity, checkpoint schema, workspace identity, provider switch history, and ledger safety. Windows process recovery and storage behavior require POC evidence.

### Level 3 conclusion

OpenHands supplies event-backed conversations/workspaces; Mastra supplies explicit durable workflow/run recovery. Both can be wrapped behind a Shofni runtime contract. Neither earns an exactly-once claim from source inspection.

## 7. Level 3 Capability Gap Matrix

### Detailed Level 3 ownership matrix

Status key: **Yes** means source implements the named mechanism; **Partial** means candidate internals exist but do not meet the portable Shofni contract by themselves; **No** means no qualifying behavior was found in inspected source. A green source test is evidence only for its asserted conditions.

| Capability | OpenHands SDK | Mastra | Evidence | Reusable as-is? | Thin adapter required? | Shofni-owned implementation required? | POC validation required? | Txx |
|---|---|---|---|---|---|---|---|---|
| Agent loop/model invocation/tool executor | `Agent.step`, LocalConversation event loop | Agent generation and durable agent workflow | OpenHands `openhands-sdk/openhands/sdk/agent/agent.py`, `conversation/impl/local_conversation.py`; Mastra `packages/core/src/agent/agent.ts`, `durable/workflows/durable-loop-builder.ts` | Loop mostly | RuntimeBackend mapping | Stable RuntimeBackend contract | Tool success/result continuation | T10 |
| Task identity | Conversation ID is candidate identity | runId plus optional thread/resource | OpenHands `conversation/state.py`, `conversation/event_store.py`; Mastra `agent/durable/durable-agent.ts`, `run-registry.ts` | Candidate IDs only | Map and persist correlation | Shofni task_id | Identity across restart/switch | T10 |
| Session/run/attempt identity | Conversation ID and event IDs; attempt distinction is not Shofni schema | runId/threadId/resourceId and workflow attempts/events | Same state/runtime files; Mastra run-registry and durable tests | Partial | Identity projection | session_id and attempt_id lineage | Resume creates correct new attempt under same task | T10 |
| Durable state/checkpoint | File-backed EventLog and ConversationState | Workflow snapshots and storage abstraction | OpenHands `conversation/event_store.py`, `conversation/state.py`; Mastra `agent/durable/durable-agent.ts`, storage modules | Partial | State/checkpoint bridge | Portable versioned Checkpoint contract | Compare checkpoint before/after | T10 |
| Resume/restart recovery | `ConversationState.create`/restore and event-store reconstruction | durable `resume`/`recover`, recovery leases | OpenHands `tests/cross/test_conversation_restore_behavior.py`, `tests/sdk/conversation/test_event_store.py`; Mastra `packages/core/src/agent/durable/__tests__/durable-agent-crash-recovery.test.ts`, `packages/core/src/agent/durable/__tests__/recover-active-runs.test.ts` | Mechanism yes, same-process/path assumptions differ | Restart adapter | Stable Shofni identity and recovery semantics | Fresh process, not just object reuse | T10 |
| Workspace identity/state | Workspace object and local/Docker/API backends | Workspace can be composed through integrations; no universal worktree identity | OpenHands `openhands-workspace/openhands/workspace/`; Mastra `packages/core/src/agent/agent.ts` workspace-tool wiring and durable workflow input | Partial | Workspace adapter | workspace_id, root, lifecycle and checkpoint relation | Same workspace after restart | T10 |
| Git/worktree support | Shell/tools can call Git; worktree lifecycle is not a portable SDK contract | Requires workspace integration/tooling | OpenHands `openhands-tools/openhands/tools/` and workspace tree; Mastra core tool registry | No portable contract | Workspace-specific adapter | Worktree identity and cleanup | Preserve repo root/branch/worktree state | T10 |
| MCP/tools/custom tools | MCP/ACP and custom tool wiring | Tool registry/processors | OpenHands `openhands-sdk/openhands/sdk/agent/acp_agent.py`, `tests/sdk/conversation/test_local_conversation_mcp.py`; Mastra `packages/core/src/agent/durable/__tests__/durable-agent-tools.test.ts` | Partial | Tool descriptor/correlation adapter | Stable tool contract and trust boundary | Same fixture tool semantics | T10/T11 |
| Filesystem, shell, browser/API tools | Workspace and tool packages expose selectable local/remote tools; exact boundary depends on workspace backend | Core can wire workspace tools and custom tools, but there is no universal Shofni workspace/shell/browser contract in the inspected core surface | OpenHands `openhands-workspace/openhands/workspace/`, `openhands-tools/openhands/tools/`; Mastra `packages/core/src/agent/agent.ts` workspace-tool wiring | Reuse only the minimal controlled workspace/tool | Workspace/tool adapter | Path, permission, process and evidence policy | T10 with controlled filesystem; browser/API are explicitly optional follow-up | T10 |
| Model/provider switch | `switch_llm` and tests | Model fallback/restoration in durable workflow | OpenHands `conversation/impl/local_conversation.py`, `tests/sdk/conversation/test_switch_model.py`; Mastra `packages/core/src/agent/durable/__tests__/durable-agent-model-fallback.test.ts` | Partial | Provider identity/switch bridge | Provider transition history and compatibility policy | Switch while preserving task state | T10 |
| Task identity preserved after switch | Conversation identity can remain while LLM changes | Durable run ID can remain through model fallback | Same switch/fallback sources | No Shofni guarantee | Map candidate IDs to Shofni IDs | Enforce stable task/workspace lineage | Assert before/after IDs | T10 |
| Audit events/traces/state history | EventLog, callbacks, event tree | Workflow events, run registry, tracing | OpenHands `openhands-sdk/openhands/sdk/conversation/event_store.py`; Mastra `packages/core/src/agent/durable/durable-agent.ts`, `packages/core/src/agent/durable/run-registry.test.ts` | Partial | Evidence event adapter | Common evidence schema and redaction | Event completeness/correlation | T10/T12 |
| Retry/failure boundary | Agent/tool failures and event lifecycle; external effect boundary is caller-defined | durable workflow retry/recovery and provider fallback | OpenHands agent/conversation tests; Mastra durable crash/fallback tests | Partial | Error/attempt mapping | Retry classes and commit boundary policy | Crash at each boundary | T09/T10/T11 |
| Duplicate side-effect protection | Event ID uniqueness does not deduplicate external tool effect | Recovery lease/provider-executed guard is mechanism-specific | OpenHands `openhands-sdk/openhands/sdk/conversation/event_store.py`; Mastra `packages/core/src/agent/durable/workflows/steps/tool-call-provider-executed.test.ts`, `tool-call-provider-fallback.test.ts` | No general guarantee | Operation context bridge | `operation_id` ledger/idempotency contract | Interrupt after successful effect | T11 |
| Exactly-once-ish controlled operation | Not supplied | Not supplied generally; guard semantics are provider-execution path-specific | Candidate source/tests above; Shofni T11 is controlled `append_ledger` | No | Ledger tool adapter | Atomic lookup/append and replay decision | One logical effect only for test fixture | T11 |
| External persistence/state store | Local EventLog/store abstractions and alternative backends | Factory storage and filesystem database; other adapters exist | OpenHands `conversation/event_store.py`; Mastra `packages/core/src/storage/factory-storage.ts`, `filesystem-db.ts` | Backend mechanisms | Storage adapter | Versioned Shofni state envelope | Restart and corruption handling | T10 |
| Extensibility/interceptors | Callbacks, hooks, custom tools, workspace/LLM registry | Custom tools, storage, workflow/event processors | OpenHands `conversation/impl/local_conversation.py`, hooks; Mastra durable workflow/storage APIs | Extension points | Lifecycle adapter | Stable replaceable public contracts | Run same suite on both runtimes | All |

### Qualitative Level 3 comparison

These are source-derived planning estimates, not ratings or a winner decision. The same T10/T11 contract applies to both runtime adapters.

| Candidate | Integration complexity / adapter | Shofni-owned gaps | Operational and Windows-local complexity | Debugging / testability | Production implication |
|---|---|---|---|---|---|
| OpenHands SDK | Moderate. Agent, conversation, workspace, event callbacks, interruption and LLM switching are explicit; adapter must translate event lineage and restore semantics into stable Shofni TaskState/Checkpoint. | Shofni task/session/attempt IDs, portable checkpoints, provider transition audit, workspace/worktree identity, operation ledger and cross-runtime evidence. | UV workspace has optional backend breadth; start with SDK + LocalWorkspace and validate Python/Windows filesystem locks, shell tools, paths, and fresh-process restore. | EventStore, conversation restore, tool persistence, model switch, MCP, interruption and workspace tests provide direct probes. Debug by comparing event IDs and Shofni lineage. | MIT SDK; workspace/shell tools are a security boundary. Pin only used packages and do not treat file persistence as a distributed side-effect transaction. |
| Mastra | Moderate. Durable run/snapshot/recovery interfaces are explicit, while task/workspace mapping and provider transitions require adapter code. Use only the open-source core. | Same Shofni public identity/checkpoint/workspace/ledger/evidence contracts; candidate recovery IDs cannot become the public API. | pnpm/Turbo monorepo is broad; consume minimum `@mastra/core` and filesystem storage in POC. Validate Node/pnpm and cross-process recovery on Windows. | Focused crash-recovery, fallback, tool, run-registry, and recovery tests support diagnosis; snapshot/lease events should be captured alongside Shofni IDs. | Core Apache-2.0; `ee/` has separate source-available license and must be excluded. Recheck exact selected package boundary and storage support before production. |

## 8. Reference Findings

- Pydantic AI: pydantic_ai_slim/pydantic_ai/tools.py provides typed Tool, ToolDefinition, JSON schemas, RunContext, and tool retry limits. _agent_graph.py defines tool-call/result parts, output retry accounting, suspended requests, incomplete tool-call detection, and graceful/exhaustive continuation. Use as a schema/retry reference only.
- LangGraph: libs/checkpoint/langgraph/checkpoint/base/__init__.py defines Checkpoint, metadata with step/parents/run_id, CheckpointTuple, and BaseCheckpointSaver; langgraph/types.py defines interrupt/resume vocabulary. Use as checkpoint reference only.
- Temporal: service/worker/workerdeployment/util.go shows ActivityOptions and RetryPolicy; workflow source/tests use WorkflowID/RunID, non-retryable errors, and idempotent operations. The full server is not a POC candidate or mandatory dependency.

## 9. Shofni-Owned Strategic Capabilities

Shofni owns the canonical request/response and stream contracts; Responses/Chat/Messages/client adapters; declared/probed/observed/effective capability registry; native-first tool pass-through; chat-only emulation; textual parsing and duplicate detection; bounded two-attempt JSON repair; fail-before versus fail-after fallback policy; task/session/attempt/workspace/checkpoint identity; operation-id ledger semantics; evidence/redaction; normalized errors; compatibility reports; and backend-independent public interfaces.

## 10. POC Harness Architecture

Create only during the future POC:

~~~text
poc/contracts/
poc/fixtures/
poc/gateway/
poc/runtime/
poc/providers/
poc/evidence/
poc/.runtime/                 # gitignored transient runtime state
poc/.runtime/raw-evidence/    # gitignored raw captures; never committed
tests/poc/unit/
tests/poc/integration/
tests/poc/scenarios/
tests/poc/workspace/
tests/poc/evidence/           # sanitized, committable evidence only
docs/poc/
~~~

The signatures below describe responsibilities, not a prescribed implementation language. `TaskState` should contain `task_id`, `session_id`, `attempt_id`, `workspace_id`, selected provider/model, lifecycle status, last committed tool-call/result IDs, and an opaque candidate runtime reference. `Checkpoint` should carry `checkpoint_id`, schema version, task/session/workspace identity, timestamp, parent checkpoint ID, and either portable state or an opaque candidate snapshot reference. `ToolExecutionBackend.execute` must accept `tool_call_id` and `operation_id`; before replaying a side effect it must query `lookup(operation_id)`. Capability probing must return observations plus evidence IDs, and reports must keep declared, probed, observed, and effective values separate.

Contracts:

~~~text
GatewayBackend: start, stop, request, stream, list_models, classify_error
RuntimeBackend: start, stop, create_task, run, checkpoint, resume, interrupt, inspect
ProviderAdapter: declared_capabilities, probe, invoke, normalize_response, normalize_stream
ClientProtocolAdapter: decode_request, encode_response, encode_stream, validate_wire_event
ToolExecutionBackend: execute(call, tool_call_id, operation_id), lookup(operation_id), record(result)
CapabilityProbe: declared_metadata + probe -> observed capability + evidence reference
CompatibilityReport: client/provider/model/protocol state and provenance
EvidenceRecorder: append redacted request/event/tool/state/error records with run IDs
TaskState: task_id, session_id, attempt_id, workspace_id, provider/model, status, committed results
Checkpoint: checkpoint_id, schema_version, task/session/workspace IDs, parent, timestamp, state/snapshot reference
~~~

Fixtures: NativeToolProviderFixture, ChatOnlyProviderFixture, TextualToolCallFixture, MalformedToolJsonFixture, StreamingToolFixture, FailBeforeToolFixture, FailAfterToolFixture, NarrationOnlyAfterToolFixture. Use a disposable workspace with input/alpha.txt, input/beta.json, output/, state/, and a local ledger.

## 11. Evidence and Redaction Model

Every run records test_run_id, test_id, candidate, client, client_version, provider, model_id, protocol, request_id, task_id, session_id, attempt_id, workspace_id, checkpoint_id, tool_call_id, operation_id, and timestamp_utc.

Raw and sanitized evidence are separate by construction:

~~~text
poc/.runtime/raw-evidence/<candidate>/<test-id>/<run-id>/
  # transient raw/debug captures only; gitignored; never committed

tests/poc/evidence/<candidate>/<test-id>/<run-id>/
  metadata.json
  request.normalized.json
  provider.request.redacted.json
  provider.response.redacted.json
  stream.ndjson
  tool-calls.json
  tool-results.json
  errors.json
  state-before.json
  state-after.json
  result.json
~~~

Prefer redaction at capture time. If a raw capture is temporarily required for diagnosis, write it only under the gitignored `poc/.runtime/raw-evidence/` tree, never reference it as permanent evidence, and delete it after the corresponding sanitized bundle has been validated. Only `tests/poc/evidence/` and `docs/poc/` artifacts may be committed.

Redact Authorization, x-api-key, bearer tokens, cookies, secret query parameters, provider credentials, GitHub tokens, and private paths. Record credential presence only. Every result labels LIVE_PROVIDER_EVIDENCE or SYNTHETIC_FIXTURE_EVIDENCE and NATIVE, EMULATED, REPAIRED, UNSUPPORTED, or UNVERIFIED. Known unsupported direct pairs are NOT_APPLICABLE, not gateway failures.

## 12. Failure Taxonomy

Primary classes:

~~~text
SETUP_FAILURE, UNSUPPORTED_FEATURE, PROTOCOL_TRANSLATION_FAILURE,
PROVIDER_FAILURE, MODEL_BEHAVIOR_FAILURE, GATEWAY_FAILURE,
RUNTIME_FAILURE, CLIENT_FAILURE, TOOL_SCHEMA_FAILURE,
MALFORMED_RESPONSE, CONTINUATION_FAILURE, STREAMING_FAILURE,
FALLBACK_FAILURE, DUPLICATE_SIDE_EFFECT_FAILURE,
EVIDENCE_OBSERVABILITY_FAILURE, AUTH_ERROR, RATE_LIMIT,
BILLING_ERROR, CHECKPOINT_ERROR, WORKSPACE_ERROR
~~~

Preserve secondary vocabulary where possible: CLIENT_ERROR, PROTOCOL_ADAPTER_ERROR, SHOFNI_NORMALIZATION_ERROR, PROVIDER_ROUTE_ERROR, PROVIDER_CAPABILITY_MISSING, UPSTREAM_SOURCE_ERROR, STREAM_ERROR, TOOL_CONTINUATION_ERROR, DUPLICATE_SIDE_EFFECT.

## 13. T01-T12 Mapping

| Test | Path and provider/client | Assertions | Evidence |
|---|---|---|---|
| T01 | Codex Responses -> A6api through both gateways | schema reaches model; one call/result/final; no duplicate | Live wire events and IDs |
| T02 | Codex Responses -> ChatOnlyProviderFixture | Shofni emulates a valid Responses call and continues | Synthetic; never RelayRouter |
| T03 | Claude Messages -> A6api OpenAI-compatible route | roles/schema/IDs/results/stop semantics survive translation | Live; route forced to OpenAI |
| T04 | OpenCode -> RelayRouter chat -> Shofni emulation | no native assumption; bounded emulation; one execution; final | Live chat plus emulated mode |
| T05 | TextualToolCallFixture | registry/schema validation; one structured call; no false positive | Synthetic corpus and duplicate case |
| T06 | MalformedToolJsonFixture | max two repairs; ambiguous payload never executes | Original/repaired redacted payloads |
| T07 | A6api with Codex/Claude/OpenCode; optional RelayRouter/OpenCode emulation | call1/result1/call2/result2/final; unique IDs; no narration stop | Live/emulated; historical premature-stop separate |
| T08 | A6api streams, RelayRouter chat stream, fragmented fixture | ordered events; exact args; stable ID; one terminal event | stream.ndjson |
| T09 | T09-A and T09-B fixtures across applicable clients; optional controlled A6api route A -> B; when T04 works, OpenCode A6api -> RelayRouter chat + Shofni emulation | before-tool fallback may switch once; after-successful-tool fallback reuses the completed result, does not execute that tool again, and reaches FINAL | Attempts, route transitions, tool/result IDs, and side-effect boundary |
| T10 | OpenHands and Mastra; required A6api model A -> model B | same task/workspace/checkpoint and prior result after fresh-process restart and model switch; final | State before/after and lineage |
| T11 | Both runtimes, append_ledger(operation_id,value) | one ledger effect after interruption/resume | Ledger and operation evidence |
| T12 | Report generator over live matrix plus fixtures | regenerated report with explicit states and unsupported pairs; include chat, streaming, native/emulated tools, tool result, sequential continuation, parallel tools when tested, Responses, Anthropic Messages, Chat Completions, error normalization, and fallback eligibility | JSON and Markdown report with client version, observation time, and evidence refs |

Native controls: Codex x A6api, Claude Code x A6api, OpenCode x A6api. Real RelayRouter pairing: OpenCode x RelayRouter. Unsupported direct pairings remain explicit.

For T09, preserve the acceptance specification's two distinct boundaries. T09-A runs `FailBeforeToolFixture` across the applicable clients and may exercise a controlled A6api route/model A -> B. Once T04 works, also run the OpenCode-only live cross-provider route A6api -> RelayRouter chat plus Shofni emulation; this is the only Level 2 direct cross-provider live fallback involving RelayRouter. T09-B starts with a successful tool execution and recorded result, then fails the provider/route; fallback must receive the existing result, retain it in history, avoid requesting or executing that completed tool again, and reach FINAL. Codex/Claude Code may only fall back to another valid A6api route/model or a synthetic fixture.

T10 requires a real A6api model A -> model B switch for each runtime when the configured live path is available. Deterministic provider fixtures remain a separate recovery-isolation control; fixture-only success does not satisfy the required live switch. If the A6api route becomes unavailable, preserve the fixture result and mark the required live subcase BLOCKED rather than PASS.

T12's generated compatibility record must include the full required dimensions and metadata in `docs/06-poc-acceptance-scenarios.md`: `client`, `client_version`, protocol, provider, `model_id`, gateway candidate, `observed_at`, evidence references, and declared/observed/effective states. Capability dimensions are chat, streaming, native tools, emulated tools, tool result, sequential continuation, parallel tools when actually tested, Responses, Anthropic Messages, Chat Completions, error normalization, and fallback eligibility. Untested capabilities must remain unverified; a source declaration alone is not an observed pass.

## 14. Fair Candidate Execution

Bifrost and LiteLLM receive identical canonical requests, fixtures, timeout/retry budgets, clients, tools, and assertions. Native behavior is passed through first; Shofni emulation/repair is at the same boundary for both. Record adapter modules, escape hatches, startup/process count, latency, memory, dependency footprint, Windows difficulty, and license/enterprise boundaries.

OpenHands and Mastra receive identical TaskSpec, model/provider switch, workspace, checkpoint trigger, interruption point, ledger tool, and assertions. Candidate snapshots/events remain internal; Shofni TaskState, Checkpoint, and evidence are identical. Independent results precede composition.

## 15. Phase-by-Phase Sequence

Phase records below name the planned Shofni paths, not files already created. Phase 0 must first determine whether the Shofni repository already has an established test runner. If one exists, the POC reuses it. If none exists, Phase 0 records one minimal Shofni-local POC runner choice and its rationale in `docs/poc/test-runner.md`; Phase 1 then bootstraps only that runner before any contract tests. Do not create parallel harnesses per candidate. Commands shown are command shapes and must be reconciled with the selected pinned package/runtime in that phase. Every phase records a manifest with phase/run IDs, candidate revision, commands, exit code, and evidence path. A phase may not turn an unresolved behavior into PASS by lowering assertions.

### Phase 0 - Baseline / guardrails

**Objective/dependencies:** Freeze the source-derived test environment before any POC artifact; depends on the completed source plan and existing provider/client documents.

**Expected files:** Add `docs/poc/baseline.md`, `docs/poc/candidate-lock.json`, `docs/poc/test-runner.md`, and `poc/evidence/schema.json`. Do not edit candidate/reference trees.

**Reuse/Shofni work:** Reuse installed Python/Node/Go/Docker only if already available; Shofni records versions, paths, configured port availability, license boundaries, redaction rules, and credential-presence booleans only. Never inspect credential values. `candidate-lock.json` is a hard provenance gate for candidate startup: for each primary candidate record the sanitized local path, upstream/source reference when known, declared version/tag when discoverable, a deterministic local tree hash or equivalent content hash, relevant lock/module manifest hashes, license boundary, and the exact package/image/module digest selected for execution. Because the extracted candidate trees have no local `.git`, never invent a commit SHA. If provenance cannot be established strongly enough to know what code will execute, mark that candidate startup BLOCKED rather than guessing.

**Tests/commands:** `git -C <shofni-root> rev-parse --show-toplevel`; `git -C <shofni-root> status --short`; `python --version`; `node --version`; `go version`; `docker version`; `Test-Path` for candidate roots; inspect listening ports with a read-only OS command; inspect Shofni build/test metadata (`pyproject.toml`, `package.json`, lockfiles, test configuration, or equivalents) to determine whether a repository test runner already exists. Commands unavailable on this host become explicit constraints, not install requests. If no repository runner exists, record exactly one minimal POC-runner decision in `docs/poc/test-runner.md`; do not install or bootstrap it until Phase 1.

**Evidence/PASS:** Baseline manifest, candidate roots resolve, required provider credential names are present without reading values, redaction test vectors are defined, the test-runner decision is recorded, and every primary candidate has a provenance entry sufficient to identify the code/artifact that would actually execute. Compare Shofni status against the captured starting status and whitelist this planning artifact; do not demand a globally clean status if user changes are present. This session began clean before `docs/07-codex-execution-plan.md` was created.

**FAIL/retry:** Missing candidate/path/runtime is `SETUP_FAILURE`; capture command and environment, permit one bounded correction using already installed tools, then stop dependent phases if still unavailable. Missing or ambiguous candidate provenance blocks startup for that candidate until the executable source/artifact can be pinned; do not substitute a floating package or unrelated image. Credential absence is not fixed by changing credentials; it blocks only affected live tests. A dirty Shofni status is compared with the baseline and preserved, not treated as failure or reverted.

**Cleanup/exit/forbidden:** No generated live configs or processes exist. Exit when exact baseline is recorded. No installs, candidate edits, live calls, credential reads, broad source copies, destructive Git commands, POC execution, or winner decision.

### Phase 1 - Contracts / harness skeleton

**Objective/dependencies:** Create disposable Shofni-owned boundary types from this plan; depends on Phase 0 lock and Shofni architecture docs.

**Expected files:** `poc/contracts/{gateway,runtime,provider,client_protocol,tool_execution,capability,evidence,task_state,checkpoint}.py` or the repo-native language equivalent; `poc/evidence/{schema,redactor,taxonomy}.py`; `tests/poc/unit/test_contracts.*`, `test_redaction.*`, `test_error_taxonomy.*`.

**Reuse/Shofni work:** Reuse no candidate types at public boundaries. Shofni owns `GatewayBackend`, `RuntimeBackend`, `ProviderAdapter`, `ClientProtocolAdapter`, `ToolExecutionBackend`, `CapabilityProbe`, `CompatibilityReport`, `EvidenceRecorder`, `TaskState`, and `Checkpoint`; candidate-specific private adapters may wrap native types.

**Tests/commands:** Run only focused contract/redactor/taxonomy tests using the repository's established runner. Test schema round trips, optional IDs, native/emulated provenance, and removal of authorization, API key, cookie, secret query, Git token, and private path values.

**Evidence/PASS:** Contract test report, JSON schema version, redaction corpus results. PASS when both gateway families and both runtime families can be represented without importing candidate types into Shofni contracts and secrets are removed from all serialized evidence.

**FAIL/retry:** A schema/type failure is `SETUP_FAILURE` or `EVIDENCE_OBSERVABILITY_FAILURE`; fix contract once and rerun focused unit tests. No candidate package startup retry applies.

**Cleanup/exit/forbidden:** Keep only Shofni harness files. Exit when interfaces have contract tests. Do not implement production platform code, capability logic beyond schema, or live integrations.

### Phase 2 - Synthetic fixtures

**Objective/dependencies:** Establish deterministic behavior for compatibility edge cases without model variance; depends on Phase 1 contracts.

**Expected files:** `poc/fixtures/{provider_server,scenarios,workspace,ledger}.*`; `tests/poc/scenarios/{t02_chat_only,t05_text_call,t06_malformed_json,t09_fallback,t11_ledger}.*`; disposable fixture configuration under `poc/fixtures/config/`.

**Reuse/Shofni work:** Reuse no candidate implementation for behavior under test. Shofni owns deterministic request/response fixtures and controlled `append_ledger(operation_id, value)`. Include a native tool fixture, chat-only fixture, textual-call fixture, malformed JSON fixture, fragmented streaming fixture, fail-before-tool and fail-after-tool fixtures, and narration-only response fixture.

**Tests/commands:** Run fixture unit/integration tests 10 consecutive times with seeded inputs; assert byte-stable normalized output and IDs except per-run IDs. Provide the ChatOnlyProviderFixture, TextualToolCallFixture, MalformedToolJsonFixture, StreamingToolFixture, FailBeforeToolFixture, FailAfterToolFixture, and NarrationOnlyAfterToolFixture contracts named in `docs/06-poc-acceptance-scenarios.md`. T02/T05/T06/T09 must execute offline. Assert at most two repair attempts and zero tool executions for ambiguous payloads.

**Evidence/PASS:** Synthetic evidence bundle per test with fixture version/hash, request/response, parser/repair decisions, tool ledger, and result. PASS if all repeated runs agree and no live provider is contacted.

**FAIL/retry:** Fixture server startup allows one bounded setup retry after redacted logs. A nondeterministic semantic failure is not retried into PASS; classify and fix fixture/harness, then rerun the full deterministic set. T06 ambiguous input always returns no-execute.

**Cleanup/exit/forbidden:** Stop fixture server and delete only generated workspace/output state after evidence is sanitized. Do not use RelayRouter as a fixture or begin live-provider requests.

### Phase 3 - Bifrost adapter/setup

**Objective/dependencies:** Wrap the pinned Bifrost open-source runtime behind GatewayBackend; depends on Phases 0-2.

**Expected files:** `poc/gateway/bifrost_backend.*`, `poc/config/bifrost.template.*`, generated ignored `poc/.runtime/bifrost.*` only if needed, `tests/poc/integration/gateway/test_bifrost_health.*` and `test_bifrost_fixture.*`.

**Reuse/Shofni work:** Reuse `core/schemas/provider.go`, `core/bifrost.go`, HTTP integrations, and selected open-source plugins as external package/runtime behavior. Shofni owns process lifecycle, config rendering with environment references (never values in artifacts), request/event mapping, health checks, redacted logs, and GatewayBackend adapter.

**Tests/commands:** Use only a launch path verified against the pinned Bifrost revision; verify `/health` if available, `/models`, Chat/Responses fixture round trips and error mapping. `transports/go.mod` is a Go module and `transports/bifrost-http/main.go` documents `go run main.go` from that module; however, `transports/go.mod` requires released `core`, `framework`, and plugin modules and has no local `replace` directives. The checked-out source also has no root `go.mod` or checked-in `go.work`. Therefore distinguish a transport build against released dependencies from a build that exercises the inspected local core/plugins. Phase 0 must record which exact, reproducible path is selected; if local-source composition is needed, use only an external temporary workspace/configuration and do not create or edit candidate-repository files. The checked-in `transports/Dockerfile` is another build path, but it also builds from `transports/go.mod`. Capture candidate source revision/hash and every resolved module/image digest before startup.

**Evidence/PASS:** Startup manifest, exact candidate pin, `/models` response, fixture request/result, redacted logs and process/port observations. PASS when GatewayBackend lifecycle and health/list/request work with no Shofni contract importing Bifrost types.

**FAIL/retry:** Startup failure is `SETUP_FAILURE`; capture logs and allow one restart after an identified transient cause. Protocol mismatch is not a setup retry. On second failure mark Bifrost setup blocked and preserve later independent LiteLLM work.

**Cleanup/exit/forbidden:** Stop process/container, release port, remove generated credential-bearing config after redaction. Do not edit Bifrost source, add enterprise-only features, contact live providers, or conclude candidacy from startup alone.

### Phase 4 - LiteLLM adapter/setup

**Objective/dependencies:** Wrap LiteLLM's pinned open-source proxy/runtime behind the same GatewayBackend; depends on Phases 0-2 and uses the same fixture contract as Phase 3.

**Expected files:** `poc/gateway/litellm_backend.py`, `poc/config/litellm.template.yaml`, generated ignored `poc/.runtime/litellm.*` only if needed, `tests/poc/integration/gateway/test_litellm_health.py`, `test_litellm_fixture.py`.

**Reuse/Shofni work:** Reuse the open-source proxy, Router, provider transforms, streaming/fallback primitives. Shofni owns lifecycle/config generation, canonical mapping, redacted callbacks/log capture, and GatewayBackend adapter. Exclude `enterprise/` and enterprise extras.

**Tests/commands:** Use the pinned revision's proxy command and Python runtime confirmed in Phase 0; verify health, `/models`, Chat/Responses fixture round trips, callback behavior and error mapping. Record package/environment metadata and artifact hashes, never config secrets. Do not resolve floating version constraints or accept a package without provenance verification.

**Evidence/PASS:** Same evidence fields and fixture corpus as Bifrost. PASS when LiteLLM satisfies the identical adapter contract and generated config has no credential values.

**FAIL/retry:** Setup failure gets one bounded restart after log capture. Protocol/semantic failures remain visible and do not consume setup retry. Failure does not block Bifrost suite.

**Cleanup/exit/forbidden:** Stop proxy, release port, remove generated secret-bearing config, exclude enterprise tree/features. No source edits, package installation in candidate tree, provider calls, or candidate comparison based on setup only.

### Phase 5 - Shared Level 2 suite

**Objective/dependencies:** Run the identical gateway contract and applicable T01-T09 suite independently against each candidate; depends on both adapters and synthetic fixtures.

**Expected files:** `tests/poc/scenarios/level2/` with candidate-neutral scenario definitions; `poc/runs/<run-id>/manifest.json`; no candidate source changes.

**Reuse/Shofni work:** Reuse both gateways only through adapters. Shofni owns the exact same request corpus, route definitions, assertion functions, native-first forwarding, and emulation/repair boundary for each candidate.

**Tests/commands:** One command shape: `<repo-test-runner> tests/poc/scenarios/level2 --candidate <bifrost|litellm> --evidence-root tests/poc/evidence`. Run T01-T09 and applicable T12 input collection against each candidate using the same scenarios and assertion version. Apply Codex x A6api, Claude Code x A6api, OpenCode x A6api controls; real RelayRouter pairing only OpenCode x RelayRouter. T02 uses ChatOnlyProviderFixture. Repeat live paths three times where provider availability permits; keep candidate timeout/retry budgets identical.

**Evidence/PASS:** Per-test protocol, normalized events, tool call/result IDs, route/model, native/emulated label, timing, errors and candidate version. Every applicable T01-T09 row must have PASS/FAIL/BLOCKED plus evidence; T12 consumes those records in Phase 6. Unsupported client/provider direct pairings are `NOT_APPLICABLE`, not failures.

**FAIL/retry:** Classify by layer; allow transport retry only before any tool effect and within common budget. A semantic failure, partial stream failure, or post-effect failure is retained and not hidden by rerun. Provider outage can be rerun as a separate run after evidence, never overwrite the original.

**Cleanup/exit/forbidden:** Preserve all evidence; stop gateway processes at suite boundary. Do not route RelayRouter through Codex/Claude, add OpenRouter, change fixtures per candidate, or remove a failed candidate result.

### Phase 6 - Level 2 report

**Objective/dependencies:** Produce T12 from sealed Level 2 evidence; depends on Phase 5 result manifests.

**Expected files:** `poc/reports/build_compatibility_report.*`, `docs/poc/gateway-results.md`, `docs/poc/compatibility-matrix.json`, `docs/poc/compatibility-matrix.md`.

**Reuse/Shofni work:** Reuse source declared metadata only as `declared`; Shofni owns report schema, status aggregation, provider/client pair keys, and provenance labels.

**Tests/commands:** `<repo-test-runner> tests/poc/scenarios/t12_report`; run generator twice and compare canonical JSON/Markdown content hashes. Validate schema and all references to evidence files.

**Evidence/PASS:** Generated report plus deterministic hash and source run IDs. PASS requires explicit LIVE/SYNTHETIC, NATIVE/EMULATED/REPAIRED/UNSUPPORTED/UNVERIFIED states and no unsupported pairing accidentally marked PASS.

**FAIL/retry:** Missing/invalid evidence is `EVIDENCE_OBSERVABILITY_FAILURE`; fix report generation and rerun. Do not retry provider calls just to fill a reporting hole unless Phase 5 calls are separately scheduled as new runs.

**Cleanup/exit/forbidden:** Keep sanitized report/evidence. Do not choose a gateway winner or backfill undocumented capability claims.

### Phase 7 - OpenHands adapter/setup

**Objective/dependencies:** Expose OpenHands SDK via RuntimeBackend with Shofni task identity; depends on Phases 0-2 and completed independent Level 2 evaluation is preferred before runtime composition.

**Expected files:** `poc/runtime/openhands_backend.py`, `poc/config/openhands.*`, `tests/poc/integration/runtime/test_openhands_lifecycle.py`, `test_openhands_restore.py`.

**Reuse/Shofni work:** Reuse Agent, LocalConversation, LocalWorkspace, EventLog, callbacks and `switch_llm`; Shofni owns RuntimeBackend, TaskState/Checkpoint projection, attempt IDs, workspace identity and evidence capture.

**Tests/commands:** Use already-available UV/Python environment only; run focused adapter tests for create/run/inspect, event capture, local file read/write, model switch and reconstruction from a new process using the same persistence directory. Never install dependencies during this planning phase; during POC, any install must follow the separately approved pinned setup plan.

**Evidence/PASS:** Candidate version, conversation/event lineage, Shofni task/session/attempt/workspace IDs, sanitized state snapshots and restore output. PASS when restart test can map the restored conversation to the same Shofni task/workspace.

**FAIL/retry:** Environment/start failure gets one bounded setup retry. State/identity mismatch is retained as a runtime failure; no fresh-task substitution.

**Cleanup/exit/forbidden:** Stop child processes, preserve sanitized event evidence, remove disposable workspace after Phase 11. Do not claim exactly-once or switch the runtime winner based on setup tests.

### Phase 8 - Mastra adapter/setup

**Objective/dependencies:** Expose Mastra open-source core via the same RuntimeBackend; depends on Phases 0-2 and uses the exact TaskSpec and tool fixture as Phase 7.

**Expected files:** `poc/runtime/mastra_backend.ts`, `poc/config/mastra.*`, `tests/poc/integration/runtime/test_mastra_lifecycle.ts`, `test_mastra_restore.ts`.

**Reuse/Shofni work:** Reuse Agent, durable agent/workflow, run registry, filesystem storage, recovery and model fallback in open-source core. Shofni owns public identity/checkpoint/workspace projections, process lifecycle and evidence. Exclude `ee/`.

**Tests/commands:** Use available Node/pnpm tooling and the minimum pinned core path identified in Phase 0; run create/run/inspect, tool result persistence, durable snapshot, fresh-process recovery and model switch. Record lockfile/revision and dependency tree without modifying the candidate repository.

**Evidence/PASS:** Same evidence envelope as OpenHands plus run registry ID, workflow snapshot version and recovery lease/event data. PASS when fresh-process recovery resumes same Shofni task/workspace and honors the saved tool result.

**FAIL/retry:** Environment/start failure gets one bounded setup retry; recovery semantic failures are preserved without resetting the task to pass.

**Cleanup/exit/forbidden:** Stop Node processes, preserve sanitized snapshots, remove disposable storage after T11. Do not import enterprise files, install into candidate tree, or state a runtime winner.

### Phase 9 - Runtime T10

**Objective/dependencies:** Compare portable checkpoint/restart/provider-switch behavior across both runtimes; depends on Phases 7 and 8.

**Expected files:** `tests/poc/scenarios/level3/t10_checkpoint_switch_resume.*`, `poc/runtime/provider_switch.*`, run manifests.

**Reuse/Shofni work:** Candidate snapshots/event logs remain opaque candidate internals. Shofni owns TaskState, checkpoint metadata/version, provider/model transition event, and common assertions.

**Tests/commands:** Run the same scenario: A6api model A executes a deterministic read/tool; persist result and checkpoint; terminate process; start a fresh process; switch to A6api model B; resume; reach final. This live model A -> model B switch is required by T10. Also run a separate deterministic provider-fixture case to isolate runtime recovery from provider/model variance; do not substitute that result for the required live switch. If the live A6api subcase cannot run, record it BLOCKED with the cause.

**Evidence/PASS:** State before/after, task/session/attempt/workspace/checkpoint IDs, candidate run IDs, tool result and transition history. PASS requires same task/workspace and prior result, valid checkpoint lineage and successful final output; new attempt ID is expected.

**FAIL/retry:** Setup-only process error may be repeated once as a new run. Any lost state, changed task/workspace, or repeated side effect is retained and classified; no semantic retry overwrites it.

**Cleanup/exit/forbidden:** Save evidence; retain workspace until T11/composition. Do not equate candidate runId with Shofni task_id or claim provider-independent success without evidence.

### Phase 10 - Runtime T11

**Objective/dependencies:** Verify controlled duplicate prevention after a successful external side effect; depends on both runtime adapters and T10 checkpoint mechanism.

**Expected files:** `poc/fixtures/ledger.*`, `tests/poc/scenarios/level3/t11_append_ledger.*`, sanitized `ledger.jsonl` under run evidence.

**Reuse/Shofni work:** Candidate tool dispatch/recovery only. Shofni owns `append_ledger(operation_id, value)`, uniqueness constraint, lookup/record contract, and decision to suppress or surface duplicate replay.

**Tests/commands:** For each runtime, execute append once, durably record tool result, interrupt/crash at the defined boundary, resume, and inspect ledger and tool events. Exercise crash before append and after append/before checkpoint as separate fixtures. The ledger's unique `operation_id` insert must be atomic (for example, a SQLite uniqueness constraint); on replay, return the already-recorded result or explicitly suppress/detect the duplicate. A lookup followed by an unguarded append is insufficient.

**Evidence/PASS:** One logical ledger record for one operation ID, one persisted result, final completion or explicit duplicate suppression, with complete event ordering. PASS is scoped to this controlled fixture only.

**FAIL/retry:** Never automatically retry an ambiguous successful side effect. Preserve failed run; manually start a new isolated run ID only after evidence capture and an empty ledger/workspace. A duplicate append is `DUPLICATE_SIDE_EFFECT_FAILURE`.

**Cleanup/exit/forbidden:** Preserve ledger and sanitized event sequence. Delete only disposable ledger after validation. Do not claim general exactly-once or apply the fixture result to production tools.

### Phase 11 - Four composition smoke tests

**Objective/dependencies:** Check composition interfaces after independent Level 2 and Level 3 results are sealed; depends on Phases 5-10.

**Expected files:** `tests/poc/scenarios/composition/`, four `poc/runs/composition-<gateway>-<runtime>/manifest.json` files, `docs/poc/composition-results.md`.

**Reuse/Shofni work:** Reuse selected gateway/runtime adapters without new candidate-specific scenario changes. Shofni owns composition lifecycle, correlation IDs and evidence links.

**Tests/commands:** Run the same one native Level 2 request and one T10-style checkpoint continuation for Bifrost+OpenHands SDK, Bifrost+Mastra, LiteLLM+OpenHands SDK, LiteLLM+Mastra. Use identical fixture/provider/model/tool and timeouts where applicable.

**Evidence/PASS:** Per-pair result links to independent candidate suites, records gateway/runtime revisions and end-to-end IDs. PASS only indicates composition compatibility for those requests; it does not amend independent results.

**FAIL/retry:** One setup-only rerun is allowed after logs are captured. A candidate semantic failure remains failed; composition cannot mask or relabel it.

**Cleanup/exit/forbidden:** Stop both components, preserve evidence, release ports. Do not skip a pairing because another combination passed or revise independent gates retroactively.

### Phase 12 - Evidence consolidation

**Objective/dependencies:** Consolidate reproducible, redacted records; depends on all mandatory scenario runs including compositions.

**Expected files:** `docs/poc/{gateway-results,runtime-results,compatibility-matrix,composition-results,decision-evidence}.md`; canonical JSON/NDJSON under `tests/poc/evidence/`.

**Reuse/Shofni work:** Reuse candidate logs only after redaction. Raw/debug captures, when unavoidable, remain only under gitignored `poc/.runtime/raw-evidence/`; sanitized canonical evidence lives under `tests/poc/evidence/`. Shofni owns final evidence schema, cross-layer correlation and evidence completeness validation.

**Tests/commands:** Run schema validator, evidence-link checker, JSON/NDJSON parser and secret-pattern scan over generated artifacts and configs. Regenerate each report twice and compare canonical output.

**Evidence/PASS:** Consolidation manifest lists all T01-T12 results, four composition records, skipped/blocked/unsupported reasons, redaction scan version and source run IDs. Every failed case has raw-protocol-equivalent sanitized diagnostic evidence.

**FAIL/retry:** Evidence gap is `EVIDENCE_OBSERVABILITY_FAILURE`; correct recorder/report, rerun only missing scenario as a new run when necessary, and preserve prior evidence.

**Cleanup/exit/forbidden:** After the sanitized evidence bundle is validated and its references resolve, delete the corresponding raw/transient capture from `poc/.runtime/raw-evidence/` and remove generated secret-bearing configs. Never move raw captures into `tests/poc/evidence/` or `docs/poc/`. Never store auth headers, API keys, cookies, or raw secret values in the repository.

### Phase 13 - Final decision gate

**Objective/dependencies:** Make evidence-backed gateway and runtime decisions independently; depends on Phase 12 and all mandatory pass/fail records.

**Expected files:** `docs/poc/decision-evidence.md`, `docs/poc/backend-decision.md`, decision table with links to evidence and license review.

**Reuse/Shofni work:** Reuse measured adapter diffs, test outcomes, environment/dependency manifests and license findings. Shofni owners apply the same decision rubric and record dissent/unknowns.

**Tests/commands:** No new provider calls. Validate completeness against T01-T12 and four combinations; compare correctness first, then adapter/custom code, missing Shofni code, operations, failure diagnosis, Windows feasibility, dependency footprint, maintenance and license boundaries.

**Evidence/PASS:** Independent candidate eligibility conclusions with evidence references and explicit residual risks. Winner may be selected only if mandatory gates pass and measured tradeoffs are acceptable; otherwise output is “no decision yet” plus bounded follow-up.

**FAIL/retry:** Missing mandatory evidence prevents winner selection. Schedule only targeted missing POC scenarios as new runs; never reinterpret unsupported pairings as failures or composition success as candidate-suite success.

**Cleanup/exit/forbidden:** Keep raw result lineage. No code migration or production rollout begins within the POC decision gate.

### Phase 14 - Post-POC boundary

**Objective/dependencies:** Translate accepted POC evidence into a production implementation backlog; depends on an actual Phase 13 decision, not source inspection alone.

**Expected files:** `docs/poc/post-poc-implementation-plan.md`, issue/task breakdown, pinned dependency and license inventory. Production code is outside this plan.

**Reuse/Shofni work:** Level 2 canonical contracts and compatibility intelligence remain permanent platform core; Level 3 is added behind `ToolExecutionBackend=RUNTIME` and must preserve `CLIENT` behavior. Candidate backends stay replaceable.

**Tests/commands:** Backlog review against architecture decisions, POC acceptance criteria, source pins and license requirements; no implementation command in this phase.

**Evidence/PASS:** Each production task links to a POC record or is labelled unverified; contract migration and rollback boundaries are explicit.

**FAIL/retry:** If decision or license evidence is incomplete, carry the unresolved item forward and keep implementations unstarted.

**Cleanup/exit/forbidden:** Remove/disable disposable POC runtime artifacts only according to Section 16. Do not change Level 2 into throwaway code, rewrite it to adopt Level 3, deploy, or start production implementation as part of this session.

## 16. Gates, Cleanup, and Rollback

Gateway eligibility requires complete T01-T09/T12 results, valid event semantics, explicit unsupported pairings, fallback before/after distinction, failure classification, and measured adapter/custom-code cost. Runtime eligibility requires T10/T11 evidence, stable identity, fresh-process recovery, model/provider transition records, and ledger behavior. Global completion requires all T01-T12, four composition records, redaction scan, license review, and source/evidence links.

Cleanup stops processes/containers, removes generated secret-bearing configs, deletes controlled workspaces after sanitized evidence, and leaves candidate trees, credentials, accounts, locks, and Git history unchanged. Rollback only disables/removes disposable Shofni POC artifacts; it never hides a failure or uses destructive Git commands.

## 17. Risks and Open Questions

- Exact Codex Responses event compatibility and fragmented tool behavior remain unverified.
- Source tree and runnable package provenance are separate questions: Bifrost has `transports/go.mod` but no root module/workspace, and the transport module resolves core/framework/plugins as released modules rather than local sibling source. Record which source is actually under test and pin every dependency/image; if inspected local core/plugin code cannot be composed reproducibly without editing the candidate tree, record that limitation and defer the setup decision to Phase 0. LiteLLM source declares 1.104.0, while the known PyPI incident involved 1.82.7/1.82.8; verify exact artifact provenance before installing any pinned build.
- T03 must force A6api OpenAI-compatible routing; native Messages passthrough is a different test.
- RelayRouter emulation may fail; bounded failure is valid evidence and remains visible.
- Generic JSON parsing is not proof against false positives or ambiguous execution.
- Streaming fallback and partial-stream failure require T08 evidence.
- OpenHands EventLog and Mastra snapshots are not arbitrary external side-effect guarantees.
- A6api model A -> model B is required; A6api -> RelayRouter is optional in Level 3 only.
- Extracted candidate trees have no local Git status; Phase 0 must establish executable provenance with a deterministic tree/content hash plus an upstream/package/image/module reference when available. Never invent a commit SHA for an archive-only tree.
- The current Shofni repository may not yet have a test runner. Phase 0 must record either the existing runner or one minimal POC-local runner choice before Phase 1; candidate-specific harnesses are not allowed.
- Raw/debug evidence is transient and gitignored under `poc/.runtime/raw-evidence/`; only sanitized evidence under `tests/poc/evidence/` and `docs/poc/` is committable.
- Recheck Bifrost Apache-2.0, LiteLLM MIT outside enterprise/, OpenHands MIT, Mastra Apache-2.0 outside ee/, and reference licenses at selected revisions.
- Record Windows startup, latency, memory, process count, dependency footprint, and cleanup empirically.

## 18. Source Evidence Index

### Shofni

README.md; docs/01-level-2-level-3-original.md; docs/02-open-source-deep-research.md; docs/03-final-architecture-decisions.md; docs/04-provider-docs.md; docs/04-provider-inventory.md; docs/05-client-readiness.json; docs/05-client-targets.md; docs/06-poc-acceptance-scenarios.md; docs/repro/; docs/repro/tool-loop-premature-stop.md; docs/repro/text-tool-call-example.md; docs/repro/relayrouter-opencode-failure.json; docs/repro/provider-errors.md; docs/research/licenses.md.

### Bifrost

core/go.mod; core/schemas/provider.go; core/schemas/modelcapabilities.go; core/schemas/responses.go; core/schemas/responsestoolunmarshal_test.go; core/bifrost.go; transports/go.mod; transports/Dockerfile; transports/bifrost-http/main.go; transports/bifrost-http/integrations/openai.go; transports/bifrost-http/integrations/anthropic.go; transports/bifrost-http/integrations/router.go; transports/bifrost-http/integrations/router_test.go; transports/bifrost-http/integrations/router_listmodels_test.go; transports/bifrost-http/integrations/anthropic_test.go; transports/bifrost-http/integrations/openai_stream_framing_test.go; core/providers/openai/responses_test.go; core/providers/anthropic/responses_test.go; plugins/logging/; plugins/telemetry/; plugins/routing/; plugins/compat/; plugins/jsonparser/; LICENSE; transports/config.schema.json.

### LiteLLM

litellm/router.py; litellm/proxy/proxy_server.py; litellm/proxy/route_llm_request.py; litellm/proxy/anthropic_endpoints/endpoints.py; litellm/litellm_core_utils/fallback_utils.py; litellm/litellm_core_utils/streaming_handler.py; litellm/llms/openai_like/chat/transformation.py; litellm/llms/openai_like/messages/transformation.py; litellm/llms/openai_like/responses/transformation.py; tests/unit/responses/; tests/unit/responses/test_custom_tool_call.py; tests/unit/responses/test_streaming_iterator.py; tests/unit/responses/test_responses_streaming_iterator.py; tests/unit/responses/test_sse_output_recovery.py; tests/llm_responses_api_testing/; tests/router_unit_tests/; tests/router_unit_tests/test_router_aresponses_streaming_fallback.py; tests/integration/messages_endpoint/responses_bridge/; tests/integration/providers/test_responses_bridge_incomplete.py; tests/unit/litellm_core_utils/test_fallback_utils.py; tests/unit/litellm_core_utils/test_streaming_handler.py; tests/test_litellm/proxy/pass_through_endpoints/test_streaming_handler_interrupt.py; tests/unit/llms/openai_like/; LICENSE; pyproject.toml; enterprise/.

### OpenHands SDK

openhands-sdk/openhands/sdk/agent/agent.py; openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py; openhands-sdk/openhands/sdk/conversation/state.py; openhands-sdk/openhands/sdk/conversation/event_store.py; openhands-sdk/openhands/sdk/conversation/cancellation.py; openhands-sdk/openhands/sdk/agent/acp_agent.py; openhands-workspace/openhands/workspace/; openhands-tools/openhands/tools/; tests/sdk/conversation/local/test_conversation_core.py; tests/sdk/conversation/local/test_client_tools_persistence.py; tests/sdk/conversation/test_event_store.py; tests/sdk/conversation/test_event_tree.py; tests/cross/test_conversation_restore_behavior.py; tests/cross/test_agent_loading.py; tests/sdk/conversation/test_switch_model.py; tests/sdk/conversation/test_interrupt.py; tests/sdk/conversation/test_local_conversation_mcp.py; tests/workspace/test_workspace_pause_resume.py; pyproject.toml; LICENSE.

### Mastra

packages/core/src/agent/agent.ts; packages/core/src/agent/durable/create-durable-agent.ts; packages/core/src/agent/durable/durable-agent.ts; packages/core/src/agent/durable/workflows/create-durable-agentic-workflow.ts; packages/core/src/agent/durable/workflows/durable-loop-builder.ts; packages/core/src/storage/factory-storage.ts; packages/core/src/storage/filesystem-db.ts; packages/core/src/agent/durable/__tests__/durable-agent-crash-recovery.test.ts; packages/core/src/agent/durable/__tests__/durable-agent-model-fallback.test.ts; packages/core/src/agent/durable/__tests__/durable-agent-tools.test.ts; packages/core/src/agent/durable/__tests__/recover-active-runs.test.ts; packages/core/src/agent/durable/workflows/steps/tool-call-provider-executed.test.ts; packages/core/src/agent/durable/workflows/steps/tool-call-provider-fallback.test.ts; packages/core/src/agent/durable/run-registry.test.ts; packages/core/src/mastra/recover-all-durable-agents.test.ts; package.json; packages/core/package.json; LICENSE.md; ee/LICENSE.

### References

pydantic-ai-main/pydantic_ai_slim/pydantic_ai/tools.py; pydantic-ai-main/pydantic_ai_slim/pydantic_ai/_agent_graph.py; langgraph-main/libs/checkpoint/langgraph/checkpoint/base/__init__.py; langgraph-main/libs/langgraph/langgraph/types.py; temporal-main/service/worker/workerdeployment/util.go; temporal-main/service/worker/workerdeployment/workflow.go; temporal-main/service/worker/workerdeployment/workflow_test.go.

This index is an evidence map, not a claim that every listed component is reusable without POC validation.
