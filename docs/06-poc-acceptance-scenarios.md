# 06 — POC Acceptance Scenarios

**Project:** Shofni Agent Platform  
**Document Type:** Proof-of-Concept Acceptance Specification  
**Status:** READY FOR POC IMPLEMENTATION  
**Date:** 2026-09-29  
**Decision Gate:** Mandatory before final gateway/runtime backend selection

---

## 1. Purpose

This document converts the architectural POC requirement into an objective, reproducible acceptance suite.

The POC must determine whether the shortlisted open-source infrastructure can support the Shofni Agent Platform architecture without forcing Shofni into backend lock-in or requiring a rewrite between Level 2 and Level 3.

The POC is not a demo.

A candidate does not pass because:

```text
it starts
a normal chat request works
its README claims compatibility
a single tool call succeeds once
```

A candidate passes only when the required scenarios produce the expected protocol, tool, state, continuation, fallback, and evidence behavior.

---

## 2. Source Precedence

Use the following precedence when the project documents conflict:

```text
1. Latest explicit project decisions
2. 04-provider-inventory.md
3. 03-final-architecture-decisions.md
4. 02-open-source-deep-research.md
5. 01-level-2-level-3-original.md
```

The provider decisions in `04-provider-inventory.md` supersede the older provider-scope statements in `03-final-architecture-decisions.md`.

Current live provider scope is:

```text
A6api
RelayRouter
```

OpenRouter is not part of the required initial live POC.

---

## 3. Architecture Under Test

### Level 2

```text
Client = Agent
Client = Tool Executor
Shofni = Compatibility / Routing / Repair Layer
```

Execution backend:

```text
ToolExecutionBackend = CLIENT
```

The Level 2 gateway must not execute the client's local shell/filesystem tools.

### Level 3

```text
Shofni Runtime = Agent
Shofni Runtime = Tool Executor
Model = Brain / Reasoning Backend
Client = UI / Consumer / Optional Worker
```

Execution backend:

```text
ToolExecutionBackend = RUNTIME
```

Level 3 must reuse the Level 2 protocol/provider/tool compatibility core.

---

## 4. POC Candidates

### Gateway candidates

Run the same Level 2 acceptance suite against:

```text
Bifrost
LiteLLM
```

No winner is selected by this document.

### Runtime candidates

Run the same Level 3 acceptance suite against:

```text
OpenHands Software Agent SDK
Mastra
```

No winner is selected by this document.

### Reference / supporting projects

These may be inspected or used only where justified by evidence:

```text
Pydantic AI
LangGraph
Temporal
```

They are not automatic mandatory dependencies.

---

## 5. Provider Reality

### A6api

Current observed project classification:

```text
Codex        ✅ supported
Claude Code  ✅ supported
OpenCode     ✅ supported

Chat         ✅
Tools        ✅
Agent use    ✅
```

A6api is the real **positive-control provider**.

A6api may route one logical model ID through multiple internal sources/suppliers.

Provider-internal source failover must remain conceptually separate from Shofni provider/model fallback.

### RelayRouter

Current observed project classification:

```text
OpenCode chat                 ✅
OpenCode native usable tools  ❌
Codex                         ❌ unsupported
Claude Code                   ❌ unsupported
```

RelayRouter is the real **OpenCode-only chat negative control / compatibility target**.

It must not be represented as a direct Codex or Claude Code provider in the initial POC.

---

## 6. Real Live Client × Provider Matrix

The initial live matrix is:

| Client | A6api | RelayRouter |
|---|---|---|
| Codex | ✅ Live supported path | ❌ Unsupported |
| Claude Code | ✅ Live supported path | ❌ Unsupported |
| OpenCode | ✅ Live supported path | ✅ Chat only |

Therefore:

```text
Codex × RelayRouter
Claude Code × RelayRouter
```

must not be repeatedly retried or misclassified as ordinary transient failures.

They are known unsupported direct-client pairings in the current baseline.

---

## 7. Synthetic Provider Fixtures Are Mandatory

Some protocol scenarios cannot be tested correctly with RelayRouter because RelayRouter does not directly support Codex or Claude Code.

The POC must include deterministic local provider fixtures/test doubles.

Required fixture classes:

```text
NativeToolProviderFixture
ChatOnlyProviderFixture
TextualToolCallFixture
MalformedToolJsonFixture
StreamingToolFixture
FailBeforeToolFixture
FailAfterToolFixture
NarrationOnlyAfterToolFixture
```

These fixtures are not substitutes for real-provider tests.

They exist to isolate protocol and compatibility behavior deterministically.

A report must always distinguish:

```text
LIVE_PROVIDER_EVIDENCE
vs
SYNTHETIC_FIXTURE_EVIDENCE
```

Never present a synthetic fixture result as proof that RelayRouter supports Codex or Claude Code.

---

## 8. Controlled Workspace

All POC scenarios must run against a disposable controlled workspace.

Recommended structure:

```text
tests/poc/workspace/
├── input/
│   ├── alpha.txt
│   └── beta.json
├── output/
├── state/
└── evidence/
```

Do not test against important personal files or production repositories.

---

## 9. Standard Safe Test Tools

Use deterministic harmless tools.

Minimum tool set:

```text
read_fixture(path)
write_marker(path, value)
read_marker(path)
append_ledger(operation_id, value)
get_ledger(operation_id)
```

Optional:

```text
list_fixture_dir(path)
calculate(a, b)
git_status_fixture()
```

Side-effect tests must operate only inside the controlled POC workspace.

---

## 10. Correlation IDs

Every request/test run must record:

```text
run_id
test_id
candidate_id
client_id
provider_id
model_id
protocol
request_id
task_id          # Level 3
session_id       # where applicable
attempt_id       # where applicable
tool_call_id
operation_id     # side-effect tests
workspace_id
checkpoint_id    # Level 3
```

Where an upstream provider does not expose an ID, Shofni should generate its own correlation ID.

---

## 11. Evidence Bundle

Every test run must produce a machine-readable evidence bundle.

Recommended:

```text
tests/poc/evidence/<candidate>/<test-id>/<run-id>/
├── metadata.json
├── request.normalized.json
├── provider.request.redacted.json
├── provider.response.redacted.json
├── stream.ndjson
├── tool-calls.json
├── tool-results.json
├── errors.json
├── state-before.json
├── state-after.json
└── result.json
```

Not every file is required for every scenario, but `metadata.json` and `result.json` are mandatory.

Secrets must be redacted.

---

## 12. Standard Result Schema

Each scenario should return:

```json
{
  "test_id": "T01",
  "candidate": "bifrost",
  "status": "PASS",
  "evidence_type": "LIVE_PROVIDER_EVIDENCE",
  "client": "codex",
  "provider": "a6api",
  "model": "configured-model-id",
  "protocol": "responses",
  "assertions": [],
  "failures": [],
  "artifacts": []
}
```

Allowed final statuses:

```text
PASS
FAIL
BLOCKED
NOT_APPLICABLE
```

`NOT_APPLICABLE` must be used for an intentionally unsupported matrix cell.

Example:

```text
Codex × RelayRouter direct
=
NOT_APPLICABLE / known unsupported direct path
```

Do not mark this as a gateway candidate failure.

---

## 13. Capability States

Compatibility reporting should use:

```text
SUPPORTED
UNSUPPORTED
PARTIAL
BROKEN
EMULATED
UNVERIFIED
TRANSIENT_FAILURE
```

Keep separate:

```text
declared
observed
effective
```

Example:

```json
{
  "provider": "relayrouter",
  "client": "opencode",
  "tools": {
    "declared": true,
    "observed": false,
    "effective": "UNSUPPORTED"
  }
}
```

---

# T01 — Responses Client → Native-Tool Provider

## 14. Objective

Prove that a Responses-style client can use a real provider with working tools through the gateway candidate without losing protocol semantics.

### Level

```text
Level 2
```

### Live path

```text
Codex
→ Shofni
→ Gateway Candidate
→ A6api
→ native/usable tool call
→ Shofni
→ Codex executes
→ tool result
→ provider
→ final
```

### Required gateway runs

```text
Bifrost
LiteLLM
```

### Provider

```text
A6api
```

### Model

Use one currently available A6api model that has already demonstrated normal agent/tool capability.

Do not hard-code one permanent model into the architecture.

Model ID must be recorded in evidence.

### Input task

Example:

```text
Read input/alpha.txt using the provided tool and return the exact marker contained in it.
```

### Required assertions

PASS only if all are true:

```text
1. Codex request is accepted.
2. Responses semantics are preserved or correctly translated.
3. Tool schema reaches the effective model path.
4. Exactly one valid tool call is returned for the requested action.
5. Tool call has a stable correlation ID.
6. Client executes exactly once.
7. Tool result is correlated to the correct call.
8. Provider/model continues after the tool result.
9. Final response contains the expected fixture result.
10. No duplicate tool execution occurs.
11. No tool call is exposed only as narration/text.
12. No protocol-invalid event is emitted.
```

### FAIL examples

```text
tool schema dropped
tool call malformed
tool call appears only as text
tool result rejected
model stops before final
duplicate execution
invalid Responses event sequence
```

---

# T02 — Responses Client → Chat-Only Provider

## 15. Objective

Prove that Shofni can preserve the Responses client contract even when the backend has no native tools.

### Important provider rule

Do **not** use RelayRouter as the mandatory live backend for this test.

RelayRouter is not a supported direct Codex provider.

### Required backend

```text
ChatOnlyProviderFixture
```

Optionally add another future real provider only if it genuinely supports Codex transport but lacks native tools.

### Level

```text
Level 2
```

### Path

```text
Codex / Responses
→ Shofni
→ Gateway Candidate
→ deterministic chat-only backend
→ model-style structured/text action
→ Shofni emulation
→ valid Responses tool call
→ Codex executes
```

### PASS criteria

```text
1. Codex can remain a Responses client.
2. Backend receives a chat-only compatible request.
3. Native tools are not falsely assumed.
4. Shofni injects/uses the emulation contract.
5. Backend output is converted into one valid client tool call.
6. Codex executes exactly once.
7. Tool result is reintroduced correctly.
8. The conversation reaches FINAL.
9. Synthetic evidence is clearly labelled synthetic.
```

### FAIL criteria

```text
Shofni requires backend-native tools
Codex receives plain action text instead of a tool event
provider-specific format leaks into the client contract
tool result cannot continue
```

---

# T03 — Anthropic Messages Client → OpenAI-Compatible Provider

## 16. Objective

Prove genuine cross-protocol translation.

### Level

```text
Level 2
```

### Client

```text
Claude Code
```

### Client protocol

```text
Anthropic Messages
```

### Live provider

```text
A6api
```

### Critical test condition

The provider side must be deliberately forced through an **OpenAI-compatible provider interface** for this test.

Do not simply pass Claude Code directly to A6api `/messages`, because that would test native Messages passthrough rather than Messages → canonical → OpenAI-compatible translation.

### Path

```text
Claude Code / Messages
→ Shofni Messages adapter
→ Shofni canonical contract
→ Gateway Candidate
→ A6api OpenAI-compatible route
→ canonical response
→ Messages response
→ Claude Code
```

### Tool phase

Use one harmless tool.

### PASS criteria

```text
1. Claude request semantics are preserved.
2. system/user/assistant roles remain correct.
3. tool schema translates correctly.
4. tool call ID survives round trip.
5. tool result maps back correctly.
6. stop/finish semantics are valid for Claude Code.
7. final response succeeds without client-side schema errors.
8. provider-specific OpenAI fields do not leak into invalid Claude events.
```

---

# T04 — Chat-Only Model → Emulated Tool Call

## 17. Objective

Prove the core Shofni Level 2 differentiator against a real chat-only route.

### Level

```text
Level 2
```

### Real path

```text
OpenCode
→ Shofni
→ Gateway Candidate
→ RelayRouter chat
→ action intent
→ Shofni tool emulator
→ valid OpenCode tool call
→ OpenCode executes
```

### Provider

```text
RelayRouter
```

### Client

```text
OpenCode
```

### PASS criteria

```text
1. Chat request reaches RelayRouter successfully.
2. RelayRouter is not sent a falsely assumed native-tool contract.
3. Shofni exposes available tools through the emulation contract.
4. Model response selects the expected tool.
5. Shofni returns a valid OpenCode tool call.
6. OpenCode executes exactly once.
7. Tool result returns through Shofni.
8. Model produces a final answer.
9. No manual user correction is required to force the tool call.
```

### Failure of the real provider to follow the emulation prompt

Record as evidence.

Do not hide the failure with an unlimited retry loop.

Bounded repair/retry only.

---

# T05 — Textual `tool_call` → Valid Structured Tool Call

## 18. Objective

Prove deterministic parsing of tool syntax emitted as text.

### Mandatory fixture

```text
TextualToolCallFixture
```

Example backend output:

```text
I need to use a tool.

tool_call:
{"name":"read_fixture","arguments":{"path":"input/alpha.txt"}}
```

The exact test corpus should include several textual wrappers.

### Optional real evidence

If RelayRouter naturally emits textual tool syntax through OpenCode, record it as additional live evidence.

### PASS criteria

```text
1. Text tool intent is detected.
2. Exactly one unambiguous tool call is extracted.
3. Tool name exists in the supplied tool registry.
4. Arguments validate against the tool schema.
5. A real structured client tool event is generated.
6. Narrative wrapper text is not mistaken for final completion.
7. No tool is executed before schema validation.
```

### Negative corpus

Must include ordinary prose containing words like:

```text
tool
tool_call
function
```

that is not actually a requested action.

PASS only if false-positive tool execution does not occur.

---

# T06 — Malformed Tool JSON → Repaired Valid Call

## 19. Objective

Prove bounded repair of recoverable malformed tool JSON.

### Mandatory fixture

```text
MalformedToolJsonFixture
```

### Test corpus

Include at least:

```text
trailing comma
single recoverable quoting error
JSON fenced in Markdown
arguments serialized as a JSON string
extra harmless wrapper field
```

Also include at least one ambiguous/unrecoverable payload.

### Required behavior

```text
recoverable
→ normalize/repair
→ schema validate
→ tool call

unrecoverable or ambiguous
→ no tool execution
→ bounded retry or explicit normalized error
```

### Retry limit

The implementation must use a bounded retry count.

Recommended POC maximum:

```text
2 repair attempts
```

### PASS criteria

```text
1. Recoverable payloads become schema-valid calls.
2. Repaired arguments preserve intended values.
3. Ambiguous payload does not execute a tool.
4. Repair loop terminates.
5. Error is normalized when repair cannot succeed.
6. Evidence records original and repaired redacted payloads.
```

---

# T07 — Sequential Multi-Tool Continuation

## 20. Objective

Prove the exact reliability issue that motivated the platform:

```text
tool #1
→ result #1
→ tool #2
→ result #2
→ FINAL
```

### Native positive-control matrix

Run through A6api using:

```text
Codex
Claude Code
OpenCode
```

for each gateway candidate.

### Emulated real-world matrix

Also run:

```text
OpenCode
→ RelayRouter
→ Shofni emulation
```

when T04 is functioning.

### Task

Example:

```text
1. Read input/alpha.txt.
2. Write its marker to output/result.txt.
3. Read output/result.txt.
4. Return FINAL with the marker.
```

Depending on client tool vocabulary, normalize this into exactly two core logical tool operations for the assertion run.

### Hard PASS criteria

```text
- exactly 2 expected logical tool calls
- exactly 2 successful tool executions
- tool call IDs are unique
- each result correlates to the correct call
- call #2 occurs only after result #1
- FINAL occurs only after result #2
- no dropped follow-up call
- no narration-only "I will continue" termination
- no duplicate call
- no duplicated side effect
```

### Explicit regression assertion

The following is a FAIL:

```text
tool #1 succeeds
tool result #1 succeeds
assistant says "I'll continue"
finish = stop
no tool #2
```

---

# T08 — Streaming Tool Calls

## 21. Objective

Prove streaming correctness across supported client protocols.

### Live positive-control matrix

```text
Codex       → A6api
Claude Code → A6api
OpenCode    → A6api
```

Run through each gateway candidate.

### OpenCode RelayRouter stream

Test RelayRouter streaming as chat behavior separately.

Do not classify RelayRouter as native-tool capable.

### Synthetic emulated stream

Use `StreamingToolFixture` to test a tool call arriving in fragments.

### PASS criteria

```text
1. stream starts validly
2. content/tool deltas remain ordered
3. tool-call arguments reassemble exactly
4. one stable tool ID is produced
5. completion event is emitted
6. finish reason is valid for the client protocol
7. no duplicate terminal event
8. no partial tool execution before arguments are complete and valid
```

Capture:

```text
stream.ndjson
```

for every streaming test.

---

# T09 — Provider/Route Failure → Fallback

## 22. Objective

Prove routing/fallback without corrupting the conversation or duplicating completed work.

This test has multiple subcases.

---

## T09-A — Failure Before Tool Execution

Primary route fails before any tool side effect.

### All-client deterministic test

Use:

```text
FailBeforeToolFixture
→ fallback route
```

### Live A6api route test

Where practical, simulate or configure:

```text
A6api model/route A
→ controlled failure
→ A6api model/route B
```

This tests Shofni routing without pretending that A6api's internal supplier failover is Shofni fallback.

### Additional OpenCode cross-provider test

When T04 is functional:

```text
OpenCode
→ A6api primary
→ controlled primary failure
→ RelayRouter chat + Shofni emulation
```

This is the only required Level 2 direct cross-provider live fallback involving RelayRouter.

### PASS

```text
same conversation intent
fallback is recorded
no tool execution before fallback
task reaches expected result
client receives valid protocol output
```

---

## T09-B — Failure After a Completed Tool Call

Sequence:

```text
tool executes successfully
tool result is recorded
provider/route fails afterward
fallback occurs
```

### PASS

```text
completed tool result remains in history
fallback receives the existing result
completed tool is not requested/executed again
continuation reaches FINAL
```

This is a Level 2 continuation assertion.

The stronger crash/resume exactly-once-ish runtime assertion is T11.

---

## 23. Invalid Fallback Paths

Do not configure these as real Level 2 fallback targets:

```text
Codex → RelayRouter
Claude Code → RelayRouter
```

They are unsupported direct pairings.

For Codex/Claude fallback testing use:

```text
another valid A6api route/model
or
synthetic provider fixtures
```

---

# T10 — Level 3 Checkpoint → Model/Provider Switch → Resume

## 24. Objective

Prove that Level 3 owns durable task identity and can resume from a checkpoint with another reasoning backend.

### Runtime candidates

Run separately against:

```text
OpenHands Software Agent SDK
Mastra
```

### Execution backend

```text
RUNTIME
```

### Minimum sequence

```text
create task
↓
execute first tool successfully
↓
persist result
↓
create checkpoint
↓
terminate/restart runtime or attempt
↓
change model or provider route
↓
resume same task
↓
continue from checkpoint
↓
FINAL
```

### Required identity assertions

Must remain stable:

```text
task_id
workspace_id
checkpoint lineage
prior successful tool result
logical task objective
```

A new:

```text
attempt_id
```

is allowed and expected after restart/fallback.

### Required provider/model switch

At minimum:

```text
A6api model A
→ A6api model B
```

must be supported for the deterministic POC.

Optional/advanced:

```text
A6api
→ RelayRouter
```

may be tested inside Level 3 if the runtime provider adapter can use RelayRouter's chat API.

In Level 3, RelayRouter's lack of direct Codex/Claude support is irrelevant because the Shofni Runtime owns the model loop.

### PASS criteria

```text
1. same task_id
2. same workspace_id
3. checkpoint restored
4. prior result available
5. new model/provider can continue
6. previous successful work is not discarded
7. final result is correct
8. audit sequence clearly records the transition
9. task does not restart from the beginning
```

---

# T11 — No Duplicate Successful Side Effect After Resume

## 25. Objective

Prove exactly-once-ish side-effect safety across Level 3 recovery.

Perfect distributed exactly-once semantics are not assumed.

The POC must prove that Shofni can prevent or detect duplicate successful operations in the controlled runtime.

### Controlled side-effect tool

Use:

```text
append_ledger(operation_id, value)
```

Behavior:

```text
operation_id is unique
first call inserts one record
repeated call with same operation_id must not create a second logical effect
```

A local SQLite or deterministic ledger file is sufficient for the POC.

Do not introduce distributed infrastructure.

### Sequence

```text
task starts
↓
append_ledger succeeds
↓
success is durably recorded
↓
runtime is interrupted
↓
resume from checkpoint
↓
model/runtime attempts to continue
```

### Hard PASS criteria

```text
ledger count for operation_id = 1
successful result remains visible
resume reaches FINAL
no second logical side effect
audit trail shows whether duplicate attempt was suppressed/detected
```

### FAIL

```text
ledger count > 1
successful effect repeated silently
runtime cannot determine whether prior operation succeeded
resume restarts entire task
```

Run against both runtime candidates.

---

# T12 — Capability Compatibility Report

## 26. Objective

Prove that Shofni can generate an evidence-based compatibility profile instead of trusting provider/model metadata.

### Required real matrix

At minimum report:

```text
Codex × A6api
Claude Code × A6api
OpenCode × A6api
OpenCode × RelayRouter
```

Also explicitly report known unsupported direct paths:

```text
Codex × RelayRouter
Claude Code × RelayRouter
```

### Required dimensions

For each valid live pairing:

```text
chat
streaming
native tools
emulated tools
tool result
sequential continuation
parallel tools if tested
Responses compatibility
Anthropic Messages compatibility
Chat Completions compatibility
error normalization
fallback eligibility
```

### Required metadata

```text
client
client_version
protocol
provider
model_id
gateway_candidate
observed_at
evidence_refs
declared_state
observed_state
effective_state
```

### Example

```json
{
  "client": "opencode",
  "provider": "relayrouter",
  "chat": {
    "observed": true,
    "effective": "SUPPORTED"
  },
  "native_tools": {
    "declared": true,
    "observed": false,
    "effective": "UNSUPPORTED"
  },
  "tool_emulation": {
    "effective": "EMULATED",
    "evidence_ref": "..."
  }
}
```

### PASS criteria

```text
1. report is generated from test evidence
2. live and synthetic evidence are distinguished
3. known unsupported pairs are explicit
4. no untested capability is silently labelled supported
5. each supported/unsupported conclusion references evidence
6. report can be regenerated
```

---

# 27. Gateway POC Execution Matrix

Run each gateway candidate through the same relevant tests.

| Test | Bifrost | LiteLLM |
|---|---:|---:|
| T01 Responses → native tools | Required | Required |
| T02 Responses → chat-only fixture | Required | Required |
| T03 Messages → OpenAI-compatible provider | Required | Required |
| T04 OpenCode + RelayRouter tool emulation | Required | Required |
| T05 textual tool parsing | Required | Required |
| T06 malformed JSON repair | Required | Required |
| T07 sequential tools | Required | Required |
| T08 streaming | Required | Required |
| T09 fallback | Required | Required |
| T12 capability report contribution | Required | Required |

A candidate is not excused merely because a feature must be implemented in the Shofni-owned compatibility layer.

Instead record:

```text
what the backend provides
what Shofni must add
how much custom integration surface is required
```

---

# 28. Runtime POC Execution Matrix

| Test | OpenHands SDK | Mastra |
|---|---:|---:|
| T10 checkpoint/resume/switch | Required | Required |
| T11 duplicate side-effect prevention | Required | Required |
| Runtime evidence/audit integration | Required | Required |
| Workspace identity preservation | Required | Required |
| Level 2 contract reuse | Required | Required |

Runtime evaluation must not replace Shofni's canonical contracts with runtime-specific public interfaces.

---

## 29. Backend Independence Test

For both gateway candidates, the Shofni-facing test harness should call the same conceptual interface.

Example:

```text
GatewayBackend
├── BifrostBackend
└── LiteLLMBackend
```

For both runtime candidates:

```text
RuntimeBackend
├── OpenHandsRuntimeBackend
└── MastraRuntimeBackend
```

A backend is architecturally problematic if swapping it requires rewriting:

```text
client adapters
canonical tool schema
provider capability registry
compatibility report format
public Shofni task identity
```

---

## 30. Do Not Pair Candidates Too Early

Do not make the entire POC only:

```text
Bifrost + OpenHands
vs
LiteLLM + Mastra
```

because that can hide which layer caused a result.

First evaluate independently:

```text
Gateway plane:
Bifrost vs LiteLLM

Runtime plane:
OpenHands SDK vs Mastra
```

Then perform composition smoke tests.

Suggested composition smoke tests:

```text
Bifrost + OpenHands SDK
Bifrost + Mastra
LiteLLM + OpenHands SDK
LiteLLM + Mastra
```

Only after the independent layer tests pass.

---

# 31. Mandatory Candidate Evaluation Dimensions

In addition to PASS/FAIL, record:

```text
architecture fit
protocol coverage
client compatibility
provider compatibility
native tools
chat-only tool support
streaming correctness
continuation reliability
routing
fallback
extensibility
runtime ownership
durable state
checkpoint/resume
workspace support
maintenance health
security/supply-chain concerns
license
public GitHub compatibility
upgrade risk
integration complexity
custom Shofni code required
long-term Level 2 → Level 3 fit
```

Do not convert these measurements into a final winner until the full evidence set exists.

---

## 32. Quantitative Measurements

Record where practical:

```text
startup time
request latency overhead
stream first-event latency
tool-call round trips
retry count
fallback time
checkpoint write time
resume time
memory footprint
container/process count
number of Shofni adapter modules required
number of backend-specific escape hatches required
```

Performance numbers are comparative evidence, not the only decision criterion.

---

## 33. Repeatability

Each mandatory scenario should be repeatable.

Recommended:

```text
deterministic fixture tests:
10/10 clean passes

live provider tests:
minimum 3 successful repetitions per selected route
```

A flaky result must not be averaged into a simple PASS.

Record:

```text
PASS_STABLE
PASS_FLAKY
FAIL
```

in supplementary metrics if useful, while preserving the final scenario status.

---

## 34. Retry Rules

Retries must not hide correctness failures.

Permitted:

```text
bounded network retry
bounded malformed-output repair
controlled fallback
```

Not permitted:

```text
retry forever until one attempt works
discard failed evidence
manually prompt the model to "please use the tool" during an automated acceptance run
```

If the test requires manual intervention to make the expected tool call occur, the run fails.

---

## 35. Streaming Validation

Streaming tests must validate event semantics, not merely concatenate text.

Check:

```text
event order
event type
role
tool call ID
argument delta assembly
completion event
finish reason
error event
```

For Responses and Messages paths, validate against the expected client-facing event model.

---

## 36. Error Normalization

At least the following must be representable in the evidence/error layer:

```text
CLIENT_ERROR
PROTOCOL_ADAPTER_ERROR
SHOFNI_NORMALIZATION_ERROR
MODEL_BEHAVIOR
PROVIDER_ROUTE_ERROR
PROVIDER_CAPABILITY_MISSING
UPSTREAM_SOURCE_ERROR
RATE_LIMIT
AUTH_ERROR
BILLING_ERROR
STREAM_ERROR
TOOL_CONTINUATION_ERROR
CHECKPOINT_ERROR
DUPLICATE_SIDE_EFFECT
```

A6api diagnostics should distinguish, when evidence permits:

```text
A6API gateway problem
vs
A6API underlying source problem
```

---

## 37. Security / Secret Rules

Never include secret values in POC artifacts.

Redact:

```text
Authorization
x-api-key
API tokens
cookies
secret query parameters
provider credentials
GitHub tokens
```

Expected local variables:

```text
A6API_KEY
RELAYROUTER_API_KEY
```

The test harness may validate presence, never print values.

---

## 38. Execution Authorization

Default Shofni execution mode remains:

```text
authorization.mode = unrestricted
```

The POC must not add arbitrary Shofni-only:

```text
branch restrictions
tool allowlists
tool denylists
mandatory approval gates
command filters
```

Reliability validation remains mandatory.

Underlying client, provider, operating system, account, and API restrictions remain authoritative.

---

# 39. POC Entry Gate

Before live execution begins, verify:

```text
[ ] Codex installed and starts
[ ] Claude Code installed and starts
[ ] OpenCode installed and starts
[ ] Docker daemon available
[ ] Git available
[ ] GitHub CLI authenticated
[ ] Python 3.12 available
[ ] Node/npm available
[ ] A6API_KEY available
[ ] RELAYROUTER_API_KEY available for RelayRouter live tests
[ ] disposable POC workspace created
[ ] secrets excluded from Git
[ ] gateway candidate locations recorded
[ ] runtime candidate locations recorded
```

Current workstation evidence already establishes readiness for the client/toolchain components.

A6api credential was present in the latest readiness snapshot.

RelayRouter credential was not visible in that snapshot, so RelayRouter live tests remain blocked until that variable is configured in the execution environment.

---

# 40. Current Local OSS Candidate Inventory

The project preparation currently includes local copies of:

```text
Bifrost
LiteLLM
OpenHands Software Agent SDK
Mastra
Pydantic AI
LangGraph
Temporal
```

These copies are research/POC inputs.

They must not be vendored wholesale into the Shofni repository by default.

Preferred use remains:

```text
package
external service
container
adapter
development reference
```

with a fork only if the POC later justifies it.

---

# 41. POC Output Artifacts

The completed POC must produce at minimum:

```text
docs/poc/
├── gateway-results.md
├── runtime-results.md
├── compatibility-matrix.md
├── decision-evidence.md
└── evidence/
```

Machine-readable output should also be retained under:

```text
tests/poc/evidence/
```

---

## 42. Gateway Result Document

`gateway-results.md` must compare Bifrost and LiteLLM using the same tests.

It must answer:

```text
Which required capabilities are native?
Which require Shofni code?
Which are broken?
Which are unverified?
What protocol transformations are required?
How much backend-specific integration is required?
```

No popularity-based conclusion.

---

## 43. Runtime Result Document

`runtime-results.md` must compare OpenHands SDK and Mastra using the same Level 3 contract.

It must answer:

```text
Can Shofni own task identity?
Can workspace identity survive resume?
Can checkpoints be restored?
Can the model/provider change?
Can successful side effects avoid duplication?
How much runtime-specific code leaks into Shofni?
```

---

## 44. Compatibility Matrix Output

The final matrix must include:

```text
client
protocol
provider
model
gateway backend
native tools
emulated tools
streaming
sequential continuation
fallback
effective capability
evidence
timestamp
```

Known invalid RelayRouter client pairs must remain explicit.

---

# 45. POC Completion Gate

The POC is complete only when:

```text
[ ] T01 executed against Bifrost and LiteLLM
[ ] T02 executed against Bifrost and LiteLLM
[ ] T03 executed against Bifrost and LiteLLM
[ ] T04 executed against Bifrost and LiteLLM
[ ] T05 executed against Bifrost and LiteLLM
[ ] T06 executed against Bifrost and LiteLLM
[ ] T07 executed against Bifrost and LiteLLM
[ ] T08 executed against Bifrost and LiteLLM
[ ] T09 executed against Bifrost and LiteLLM
[ ] T10 executed against OpenHands SDK and Mastra
[ ] T11 executed against OpenHands SDK and Mastra
[ ] T12 compatibility report generated
[ ] all failures have evidence
[ ] all secrets are redacted
[ ] live vs synthetic evidence is distinguishable
[ ] backend-specific custom code is documented
[ ] licenses are reviewed
```

---

# 46. Eligibility Gate

A backend may proceed to final architecture selection only if:

```text
1. Every mandatory scenario for its layer has a deterministic result.
2. No critical protocol corruption remains unexplained.
3. No repeated completed side effect remains undetected.
4. The Shofni canonical contract can remain backend-independent.
5. Public GitHub distribution remains legally/operationally viable.
6. Required custom Shofni code is understood and documented.
```

A backend can still be evaluated if one test is intentionally `NOT_APPLICABLE`, but only when the reason is an architecture-level matrix restriction rather than an implementation failure.

---

# 47. POC Non-Goals

The POC does not authorize:

```text
forking Bifrost
forking LiteLLM
forking OpenHands
forking Mastra
Production deployment
distributed database infrastructure
final UI
final CLI
final monorepo tooling
final gateway selection
final runtime selection
```

---

# 48. After the POC

Only after the evidence bundle is complete should the project create the final implementation plan.

That plan may then decide:

```text
gateway backend
runtime backend
language split
package boundaries
state-store implementation
deployment model
repository structure
release phases
```

while preserving:

```text
Shofni-owned canonical contracts
Level 2 permanent core
Level 3 reuse of Level 2
backend replaceability
native-capability-first behavior
unrestricted default execution policy
evidence-based compatibility truth
```

---

# 49. Final Acceptance Principle

The POC must answer one question objectively:

> Can Shofni provide a stable compatibility/runtime contract across real clients and imperfect providers while keeping external gateway/runtime backends replaceable?

A successful result is not:

```text
"the model answered"
```

A successful result is:

```text
the protocol remained valid
the correct tool was called
the result was correlated
the loop continued
streaming remained valid
fallback preserved state
resume preserved task/workspace identity
successful side effects were not duplicated
and the evidence proves it
```
