# 04 — Provider Inventory & Observed Capability Baseline

**Project:** Shofni Agent Platform  
**Document Type:** Provider / Model / Capability Source of Truth  
**Status:** Approved operational baseline for POC planning  
**Date:** 2026-09-29  
**Current live-provider scope:** **A6api + RelayRouter only**

---

## 1. Purpose

This file records the provider reality that Shofni must support.

It combines:

1. **Observed runtime behavior** from real use with Codex, Claude Code, and OpenCode.
2. **Captured provider documentation**.
3. **Current project model inventories**.

When documentation and real runtime behavior conflict, **observed runtime behavior wins for Shofni capability classification**.

That rule exists because Shofni Level 2 is intended to discover what a provider/model route actually supports rather than trusting labels such as “OpenAI-compatible”, “tool-capable”, or “agent-ready”.

---

## 2. Current Provider Decision

The initial live provider set is:

```text
1. A6api
2. RelayRouter
```

The project is **not** depending on OpenRouter for the initial implementation/POC.

Generic OpenAI-compatible and Anthropic-compatible adapters remain part of the architecture so future providers can be added without changing Shofni's canonical contracts.

---

## 3. Provider Roles

### A6api

```text
Role:
PRIMARY PROVIDER

Project assessment:
Strongest current operational provider for this Shofni use case

Primary uses:
- normal coding-agent operation
- native/usable tool workflows
- Codex
- Claude Code
- OpenCode
- positive-control provider for POC tests
- broad multi-model access
- provider-side source redundancy
```

### RelayRouter

```text
Role:
SECONDARY / CHAT-ONLY PROVIDER

Primary uses:
- normal chat inference
- chat-only compatibility target
- negative-control provider for tool tests
- Shofni tool-emulation target
- tool parsing / repair / continuation testing
- cross-provider comparison
```

RelayRouter is **not** currently classified as a native tool-capable coding-agent provider.

---

## 4. Capability Evidence Priority

Shofni will use this precedence:

```text
1. Reproducible live runtime test
2. Shofni live capability probe
3. Provider documentation
4. Static model metadata
5. Marketing / compatibility labels
```

Therefore:

```text
provider declares tools
+
real tool request fails
=
effective Shofni capability: UNSUPPORTED
```

until later evidence proves otherwise.

---

# A6api

## 5. A6api Base URL

```text
https://api.a6api.com
```

Captured documentation also states that the old `/v1` entry point remains compatible.

---

## 6. A6api Authentication

Project variable:

```text
A6API_KEY
```

OpenAI-compatible requests:

```text
Authorization: Bearer $A6API_KEY
```

Anthropic-native requests use the same A6api token with protocol-specific headers.

Never store secret values in Git or documentation.

---

## 7. A6api Protocol Surface

Captured provider documentation exposes at least:

```text
POST /chat/completions
POST /responses
POST /messages
POST /v1beta/models/{model}:generateContent
POST /completions

GET  /models
GET  /models/{model}

POST /images/generations
POST /images/edits
POST /embeddings
POST /rerank
POST /audio/transcriptions
POST /audio/speech

WS   /realtime
```

Initial Shofni-relevant paths:

```text
/chat/completions
/responses
/messages
/models
```

---

## 8. A6api Observed Client Compatibility

Current project observation:

| Client | Observed status | Intended protocol path |
|---|---|---|
| Codex | ✅ Working | Responses / OpenAI-compatible |
| Claude Code | ✅ Working | Anthropic Messages-compatible |
| OpenCode | ✅ Working | OpenAI-compatible / Chat Completions |

Operational conclusion:

```text
client.codex = SUPPORTED
client.claude_code = SUPPORTED
client.opencode = SUPPORTED
```

The formal POC will still capture protocol traces and exact conformance evidence.

---

## 9. A6api Tool / Agent Capability

Observed project behavior:

```text
normal chat                    ✅
tool-dependent workflows       ✅
coding-agent workflows         ✅
multi-step agent usage         ✅
```

Current effective classification:

```text
native_or_usable_tools = SUPPORTED
tool_result_continuation = SUPPORTED
direct_coding_agent_use = SUPPORTED
```

This does not mean Shofni should permanently assume every future A6api route behaves the same way. Live probing still remains required.

---

## 10. A6api Multi-Source Model Routing

A key A6api advantage for this project is that the same logical model ID can be backed by multiple underlying sources/channels.

Conceptually:

```text
Client requests one model ID
        ↓
A6api logical model
        ↓
Source / merchant A
Source / merchant B
Official source
Other available source
```

The captured documentation distinguishes:

```text
Fixed Merchant / Supplier
vs
Smart Selection
```

and states that Smart Selection can bypass abnormal channels.

This gives A6api provider-side resilience without requiring Shofni to change the model ID.

---

## 11. A6api Official and Alternative Sources

Current project understanding:

```text
same model ID
→ multiple supplier/source routes may exist
→ official-source routes may be available
→ alternative routes may be available
```

If one route/source fails or degrades, A6api can select another route depending on its marketplace/smart-selection behavior.

This capability is one of the main reasons A6api is the primary provider.

---

## 12. Two Separate Fallback Layers

A6api's internal source fallback and Shofni's provider fallback are different.

```text
Layer 1:
A6api internal source/channel selection

Layer 2:
Shofni provider/model routing and fallback
```

Shofni diagnostics must never merge these into one concept.

Example:

```text
requested_provider = a6api
requested_model = gpt-5.6-sol

Shofni provider did not change
but
A6api upstream source may have changed
```

when upstream source metadata is observable.

---

## 13. Why A6api Is the Primary Provider

Within this project, A6api is currently treated as the strongest provider because it combines:

```text
Codex compatibility
Claude Code compatibility
OpenCode compatibility

OpenAI-compatible API
Responses API
Anthropic Messages
Models API

working tool/agent paths

large model catalog

multiple underlying sources
official-source options
smart source selection
provider-side source failover/redundancy
```

This is a **Shofni project assessment**, not a universal statement that A6api is objectively best for every workload.

---

## 14. A6api POC Role

A6api is the **positive-control provider**.

It gives the POC a working path where tools are expected to function.

Example:

```text
Codex
→ Shofni
→ A6api
→ model
→ native/usable tool call
→ Shofni normalization
→ Codex executes tool
```

This helps isolate failures:

```text
client problem?
Shofni adapter problem?
provider problem?
model behavior?
tool-execution problem?
```

---

## 15. A6api Current OpenAI/Codex Candidate IDs

The current project shortlist contains **18** IDs:

```text
gpt-4o
gpt-4o-mini
gpt-5.2
gpt-5.2-2025-12-11
gpt-5.2-chat-latest
gpt-5.3-codex
gpt-5.3-codex-spark
gpt-5.4
gpt-5.4-mini
gpt-5.5
gpt-5.6
gpt-5.6-luna
gpt-5.6-sol
gpt-5.6-terra
gpt-6-astra
gpt-6-luna
gpt-6-sol
codex-auto-review
```

Important:

This is the current **OpenAI/Codex-oriented candidate subset**, not the full A6api marketplace.

The complete marketplace is dynamic and should ultimately be discovered from:

```text
GET /models
```

plus live capability probes.

---

## 16. A6api Model ID Semantics

A Shofni model ID must be treated as a **logical route** unless a supplier is explicitly pinned.

Do not infer:

```text
same model ID
=
same physical upstream source every time
```

This distinction matters for:

```text
reproducibility
latency
tool reliability
benchmarking
failure diagnosis
cost
compatibility reports
```

---

## 17. A6api Capability Baseline

| Capability | Current status |
|---|---|
| Chat Completions | ✅ Supported |
| Responses | ✅ Supported |
| Anthropic Messages | ✅ Supported |
| Models endpoint | ✅ Supported |
| Streaming | ✅ Documented; conformance still to be captured |
| Tool/agent workflows | ✅ Observed working |
| Codex | ✅ Observed working |
| Claude Code | ✅ Observed working |
| OpenCode | ✅ Observed working |
| Multiple sources per model route | ✅ Core operational behavior |
| Smart source selection | ✅ Documented |
| Official source options | ✅ Project-observed/known behavior |
| Provider-side source fallback | ✅ Project-observed/known behavior |
| Shofni live probing | ⏳ To build |
| Per-route compatibility reports | ⏳ POC |

---

# RelayRouter

## 18. RelayRouter Base URL

```text
https://api.relayrouter.org/v1
```

---

## 19. RelayRouter Authentication

Project-standard variable:

```text
RELAYROUTER_API_KEY
```

Authorization:

```text
Authorization: Bearer $RELAYROUTER_API_KEY
```

Captured RelayRouter examples use the variable name `RELAY_API_KEY`, but Shofni standardizes its own environment naming as `RELAYROUTER_API_KEY`.

---

## 20. RelayRouter Documented Surface

The captured docs explicitly describe:

```text
/v1/chat/completions
/v1/messages
SSE streaming
OpenAI SDK compatibility
```

The docs also claim translation of:

```text
Anthropic Messages
function calls
tool results
```

However, current real-world Shofni project testing does **not** support treating RelayRouter tools as usable.

---

## 21. RelayRouter Observed Runtime Reality

Actual behavior established by project use is more restrictive than previously recorded.

### OpenCode

```text
normal chat request
→ works

tool-dependent request
→ fails

coding-agent task requiring tools/execution
→ fails because usable tool support is not available
```

### Codex

```text
RelayRouter is not operationally supported with Codex.

Direct Codex use:
→ unsupported / non-working for this project
```

### Claude Code

```text
RelayRouter is not operationally supported with Claude Code.

Direct Claude Code use:
→ unsupported / non-working for this project
```

Therefore the observed compatibility boundary is:

```text
RelayRouter + OpenCode + chat
= WORKING

RelayRouter + OpenCode + tools
= NOT WORKING

RelayRouter + Codex
= NOT SUPPORTED

RelayRouter + Claude Code
= NOT SUPPORTED
```

This observed behavior is the effective baseline for Shofni planning.


## 22. RelayRouter Effective Capability Classification

```text
client.opencode.chat = SUPPORTED
client.opencode.tools = UNSUPPORTED

client.codex = UNSUPPORTED
client.claude_code = UNSUPPORTED

native_usable_tools = UNSUPPORTED
tool_execution_path = UNSUPPORTED
tool_result_continuation = UNSUPPORTED
direct_tool_dependent_coding_agent = UNSUPPORTED
```

Important:

```text
RelayRouter is NOT a general chat provider for all three clients.

Its currently proven direct-client role is:
OpenCode chat only.
```

This classification overrides provider claims until a reproducible future probe proves otherwise.


## 23. Documentation vs Observed Behavior

Recorded discrepancy:

```text
RelayRouter documentation:
- OpenAI-compatible surface
- /v1/messages
- function calls
- tool results

Observed project behavior:
- OpenCode chat works
- OpenCode tool-dependent tasks fail
- Codex is not supported
- Claude Code is not supported
```

Shofni must preserve both declared and observed state.

For tools:

```text
declared_tools = true
observed_tools = false
effective_tools = UNSUPPORTED
```

For clients:

```text
declared_openai_compatibility = true
observed_codex_compatibility = false

declared_anthropic_messages = true
observed_claude_code_compatibility = false

observed_opencode_chat = true
```

This is a primary example of why protocol labels alone are insufficient and why live capability probing is a core Level 2 feature.


## 24. RelayRouter Strategic Value

RelayRouter remains strategically useful because it gives the project a **real OpenCode-only chat path with no usable tools**.

Its proven direct path is:

```text
OpenCode
   ↓
Shofni
   ↓
RelayRouter chat
   ↓
model text / action intent
```

This makes RelayRouter a strong real-world target for:

```text
OpenCode chat-only compatibility
tool emulation
text-to-tool parsing
malformed tool-call repair
sequential continuation after emulated tools
capability probing
provider-vs-model diagnosis
```

The target Level 2 path is:

```text
OpenCode
   ↓
Shofni
   ↓
RelayRouter chat-only model
   ↓
synthetic/text action intent
   ↓
Shofni parser / emulator / repair
   ↓
valid OpenCode tool call
   ↓
OpenCode executes the real tool
```

RelayRouter must **not** be presented as a direct Codex or Claude Code provider in the current baseline.


## 25. RelayRouter POC Role

RelayRouter is the **real-world negative-control provider for OpenCode only**.

Without Shofni tool emulation:

```text
OpenCode
→ RelayRouter
→ chat succeeds
→ tool-dependent task fails
```

With Shofni Level 2, the target becomes:

```text
OpenCode
↓
Shofni
↓
RelayRouter chat
↓
model expresses action intent
↓
Shofni parses/emulates tool call
↓
OpenCode receives a valid tool request
↓
OpenCode executes
↓
tool result returns through Shofni
↓
workflow continues
```

RelayRouter is therefore appropriate for real tests such as:

```text
OpenCode → RelayRouter chat
OpenCode → RelayRouter → emulated tool call
textual tool_call → structured OpenCode tool call
malformed tool JSON → repair
tool #1 → result → tool #2 → result → final
```

It is **not** the live provider for:

```text
Codex / Responses → chat-only provider
Claude Code / Anthropic Messages → chat-only provider
```

because RelayRouter is not currently supported with Codex or Claude Code.

Those protocol-level negative tests must use:

```text
controlled synthetic provider fixtures
or
a dedicated Shofni test double
```

so that the protocol behavior can be tested independently from RelayRouter's client incompatibility.


## 26. RelayRouter Direct Client Classification

### Codex

```text
direct compatibility:
UNSUPPORTED

chat:
NOT OPERATIONALLY SUPPORTED

tools:
NOT SUPPORTED
```

RelayRouter must not be used as a direct Codex provider in the current POC baseline.

### Claude Code

```text
direct compatibility:
UNSUPPORTED

chat:
NOT OPERATIONALLY SUPPORTED

tools:
NOT SUPPORTED
```

RelayRouter must not be used as a direct Claude Code provider in the current POC baseline.

### OpenCode

```text
direct compatibility:
SUPPORTED FOR CHAT

chat:
WORKS

tool-dependent coding task:
FAILS without Shofni compatibility/emulation
```

Therefore:

```text
RelayRouter direct role
=
OpenCode CHAT-ONLY

RelayRouter via Shofni Level 2
=
OpenCode TOOL-EMULATION TARGET
```


## 27. RelayRouter Current OpenAI-Related Route IDs

Current project inventory contains **52** OpenAI-related RelayRouter route IDs:

```text
1/gpt-5.6-luna
openai/gpt-5-6-luna
private/gpt-5.5
private/gpt-5.6-luna
private/gpt-5.6-sol
private/gpt-5.6-terra
stealth/openai/gpt-3.5-turbo
stealth/openai/gpt-3.5-turbo-0613
stealth/openai/gpt-3.5-turbo-16k
stealth/openai/gpt-3.5-turbo-instruct
stealth/openai/gpt-4.1
stealth/openai/gpt-4.1-mini
stealth/openai/gpt-4.1-nano
stealth/openai/gpt-4o
stealth/openai/gpt-4o-2024-05-13
stealth/openai/gpt-4o-2024-08-06
stealth/openai/gpt-4o-2024-11-20
stealth/openai/gpt-4o-mini
stealth/openai/gpt-4o-mini-2024-07-18
stealth/openai/gpt-5
stealth/openai/gpt-5-mini
stealth/openai/gpt-5-nano
stealth/openai/gpt-5.1
stealth/openai/gpt-5.1-codex
stealth/openai/gpt-5.1-codex-max
stealth/openai/gpt-5.1-codex-mini
stealth/openai/gpt-5.2
stealth/openai/gpt-5.2-codex
stealth/openai/gpt-5.3-codex
stealth/openai/gpt-5.4
stealth/openai/gpt-5.4-mini
stealth/openai/gpt-5.4-nano
stealth/openai/gpt-5.6-luna
stealth/openai/gpt-5.6-luna-pro
stealth/openai/gpt-5.6-sol
stealth/openai/gpt-5.6-sol-pro
stealth/openai/gpt-5.6-terra
stealth/openai/gpt-5.6-terra-pro
stealth/openai/gpt-6-luna
stealth/openai/gpt-6-luna-pro
stealth/openai/gpt-6-sol
stealth/openai/gpt-6-sol-pro
stealth/openai/gpt-oss-120b
stealth/openai/gpt-oss-20b
stealth/openai/gpt-oss-safeguard-20b
stealth/openai/o3-mini-high
stealth/openai/o4-mini-high
stealth/~openai/gpt-luna-latest
stealth/~openai/gpt-mini-latest
stealth/~openai/gpt-sol-latest
stealth/~openai/gpt-terra-latest
video-stealth/openai/sora-2-pro
```

These are **RelayRouter route IDs**, not automatically official OpenAI API model IDs.

Namespaces currently represented include:

```text
1/
openai/
private/
stealth/openai/
stealth/~openai/
video-stealth/openai/
```

---

## 28. RelayRouter Capability Baseline

| Capability | Current status |
|---|---|
| OpenCode normal chat | ✅ Observed working |
| OpenCode Chat Completions path | ✅ Observed working |
| OpenCode native usable tools | ❌ Observed unavailable |
| Codex direct compatibility | ❌ Unsupported / non-working |
| Responses API for Codex | ❌ Not an operational project path |
| Claude Code direct compatibility | ❌ Unsupported / non-working |
| Anthropic Messages for Claude Code | ❌ Not an operational project path despite documentation claims |
| Streaming | ✅ Documented; verify specifically on the working OpenCode path |
| Tool-result continuation | ❌ Native workflow unavailable |
| Direct coding-agent execution | ❌ Tool-dependent tasks unusable |
| Shofni synthetic tool emulation for OpenCode | ⏳ To build/test |
| Text-to-tool parsing | ⏳ To build/test |
| Malformed JSON repair | ⏳ To build/test |
| Capability probing | ⏳ To build/test |

The key baseline is:

```text
RelayRouter direct client support:
OpenCode chat only.
```


## 29. Provider Comparison

| Capability | A6api | RelayRouter |
|---|---:|---:|
| Project role | **Primary** | **OpenCode chat-only compatibility target** |
| Codex | ✅ Working | ❌ Unsupported |
| Claude Code | ✅ Working | ❌ Unsupported |
| OpenCode | ✅ Working with tools | ⚠️ Chat only |
| Normal chat | ✅ all target clients | ✅ OpenCode only |
| Responses / Codex path | ✅ | ❌ Not operational |
| Anthropic Messages / Claude Code path | ✅ | ❌ Not operational |
| OpenCode Chat Completions path | ✅ | ✅ Chat only |
| Native/usable tools | ✅ | ❌ |
| Tool-result continuation | ✅ | ❌ native path |
| Coding-agent workflows | ✅ | ❌ direct path |
| Multi-source same-model routing | ✅ | Not relied upon |
| Smart source selection | ✅ | Not relied upon |
| Official-source options | ✅ | Not relied upon |
| Provider-side source redundancy | ✅ | Not relied upon |
| Best POC role | Positive control across all clients | OpenCode-only negative control / emulation target |


## 30. Initial Routing Policy

Default provider:

```text
A6api
```

Use A6api for:

```text
Codex
Claude Code
OpenCode
native tool workflows
normal coding-agent work
positive-control tests
```

Use RelayRouter only for the currently proven path:

```text
OpenCode chat
OpenCode chat-only capability probing
OpenCode tool-emulation tests
OpenCode tool parsing/repair tests
OpenCode sequential continuation tests
cross-provider OpenCode comparison
```

Do not route Codex or Claude Code to RelayRouter in the current baseline.

Do not use RelayRouter as the expected native-tool success path.


## 31. Positive and Negative Controls

### Positive control — all target clients

```text
Codex / Claude Code / OpenCode
+
A6api
+
tool-capable model route

Expected:
native/usable agent and tool path succeeds
```

### Real-world negative control — OpenCode only

```text
OpenCode
+
RelayRouter
+
chat-capable model route

Expected without Shofni emulation:
chat succeeds
tools fail
```

Then:

```text
OpenCode
+
Shofni Level 2
+
RelayRouter

Target:
Shofni converts RelayRouter chat/model intent
into valid OpenCode tool calls.
```

### Codex and Claude negative-control tests

RelayRouter must not be used for these because the client/provider pairing itself is unsupported.

Use controlled fixtures/test doubles for:

```text
Codex Responses → synthetic chat-only backend
Claude Code Messages → synthetic chat-only/backend-translation fixture
```

This separates:

```text
protocol compatibility testing
```

from:

```text
RelayRouter-specific client incompatibility
```


## 32. Same-Family Cross-Provider Testing

Cross-provider comparisons involving RelayRouter should use **OpenCode as the common client**, because OpenCode is the only currently supported direct RelayRouter client.

Example:

```text
OpenCode
→ A6api
→ gpt-5.6-sol
```

versus:

```text
OpenCode
→ RelayRouter
→ stealth/openai/gpt-5.6-sol
```

Do **not** assume these routes are identical implementations.

Purpose:

```text
same client
similar model family
different provider path
different tool behavior
```

This helps isolate:

```text
provider translation
provider capability
model behavior
Shofni normalization
tool emulation
```

Codex and Claude Code cross-provider tests should not include RelayRouter until a future probe establishes those client/provider pairings as functional.


## 33. Live Capability Probe Requirements

The compatibility matrix is **not** assumed to be a full Cartesian product.

Known valid live paths begin as:

```text
Codex × A6api
Claude Code × A6api
OpenCode × A6api
OpenCode × RelayRouter
```

Known invalid / unsupported paths begin as:

```text
Codex × RelayRouter
Claude Code × RelayRouter
```

Each relevant valid route should be probed for:

```text
chat succeeds?
streaming succeeds?
tools accepted?
native tool call emitted?
tool-call ID valid?
tool result accepted?
continues after tool result?
second sequential tool call emitted?
parallel tool calls work?
textual pseudo-tool call emitted?
malformed JSON emitted?
protocol events valid?
```

Unsupported client/provider pairs should be recorded explicitly rather than repeatedly treated as generic transient failures.


## 34. Capability States

Recommended states:

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
declared capability
observed capability
effective capability
```

RelayRouter example:

```json
{
  "provider": "relayrouter",
  "native_tools": {
    "declared": true,
    "observed": false,
    "effective": "UNSUPPORTED"
  }
}
```

A6api example:

```json
{
  "provider": "a6api",
  "native_tools": {
    "declared": true,
    "observed": true,
    "effective": "SUPPORTED"
  }
}
```

---

## 35. Failure-Domain Classification

Diagnostics should distinguish:

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
```

For A6api, distinguish when possible:

```text
A6API_GATEWAY_FAILURE
vs
A6API_UPSTREAM_SOURCE_FAILURE
```

---

## 36. Native Capability First

A6api:

```text
native/usable tools available
↓
use native path
```

RelayRouter:

```text
usable native tools unavailable
↓
activate Shofni compatibility/emulation path
```

Rule:

```text
native first
emulation only when needed
```

---

## 37. Credential Variables

Required for the two live providers:

```text
A6API_KEY
RELAYROUTER_API_KEY
```

Never commit or log their values.

POC evidence must redact:

```text
Authorization
x-api-key
cookies
secret query parameters
provider tokens
```

---

## 38. Explicitly Out of Initial Live Scope

Not required for the first provider implementation:

```text
OpenRouter
Direct OpenAI
Direct Anthropic
```

Their protocol families can still be represented by Shofni adapters.

This keeps:

```text
protocol support
```

separate from:

```text
mandatory live provider dependency
```

---

## 39. Level 2 Implication

A6api validates the native path for all three initial clients:

```text
Codex / Claude Code / OpenCode
↓
Shofni
↓
A6api
↓
native/usable tool call
↓
Shofni normalization
↓
Client executes
```

RelayRouter validates a different compatibility path, specifically through OpenCode:

```text
OpenCode
↓
Shofni
↓
RelayRouter chat
↓
synthetic/text action intent
↓
Shofni parser/emulator/repair
↓
valid OpenCode tool call
↓
OpenCode executes
```

There is currently **no direct RelayRouter Level 2 path for Codex or Claude Code**.

If Shofni later chooses to expose RelayRouter-derived model reasoning to Codex or Claude Code, that would be a new compatibility feature implemented by Shofni, not an existing RelayRouter client capability.


## 40. Level 3 Implication

Level 3 reuses the same provider knowledge but changes who owns execution.

A6api remains the primary model backend.

RelayRouter can become more broadly useful inside Level 3 even though it does not directly support Codex or Claude Code, because Shofni Runtime itself becomes the agent and tool executor.

Conceptually:

```text
User / Client UI
↓
Shofni Runtime
↓
RelayRouter chat/model reasoning
↓
Shofni Runtime interprets tool intent
↓
Runtime Tool Executor
↓
Tool result
↓
Shofni Agent Loop continues
```

In Level 3, direct RelayRouter compatibility with Codex or Claude Code is no longer required for RelayRouter to act as a model backend, because the Shofni Runtime owns the model loop and execution contract.

This is different from Level 2, where the external client remains the agent.


## 41. POC Provider Baseline

Start with:

```text
Provider A:
A6api
classification = native-tool positive control

Live clients:
- Codex
- Claude Code
- OpenCode
```

and:

```text
Provider B:
RelayRouter
classification = OpenCode-only chat negative control / emulation target

Live client:
- OpenCode only
```

For protocol-level chat-only scenarios involving Codex or Claude Code, use controlled synthetic fixtures/test doubles rather than falsely treating RelayRouter as a supported direct provider.

A third live provider is unnecessary before the compatibility core is proven.


## 42. Final Decision Summary

```text
A6api
=
PRIMARY

Codex                         ✅
Claude Code                   ✅
OpenCode                      ✅
Chat                          ✅
Tools                         ✅
Agent workflows               ✅
Multiple source routes        ✅
Official-source options       ✅
Smart source selection        ✅
Provider-side redundancy      ✅
```

```text
RelayRouter
=
SECONDARY / OPENCODE CHAT-ONLY / COMPATIBILITY TARGET

OpenCode chat                 ✅
OpenCode native tools         ❌
OpenCode tool-dependent work  ❌ direct path

Codex                         ❌ unsupported
Claude Code                   ❌ unsupported

Strategic use:
- OpenCode chat-only negative control
- OpenCode tool emulation
- tool parsing/repair
- capability probing
- cross-provider OpenCode comparison
```

This client restriction is part of the operational baseline and must be reflected in all later POC scenarios.


## 43. Final Rule

Never classify a provider/model by model name or marketing label alone.

Shofni must eventually answer:

```text
Does THIS model
through THIS provider
through THIS protocol
for THIS client
actually support THIS capability
right now?
```

That evidence-based capability truth is a core Level 2 responsibility and remains reusable in Level 3.
