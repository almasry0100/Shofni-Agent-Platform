# 03 — Final Architecture Decisions

**Project:** Shofni Agent Platform  
**Document Type:** Architecture Decision Baseline  
**Status:** Approved baseline for execution planning  
**Date:** 2026-09-29  
**Purpose:** Freeze the current architectural decisions before creating the implementation plan and before selecting any final open-source backend.  
**Revision note:** Provider scope and observed provider/client compatibility updated to the verified 2026-09-29 operational baseline.

---

## 1. Why This Document Exists

The Level 2 / Level 3 architecture evolved significantly during research and discussion.

This document is the **current decision baseline**.

When this file conflicts with earlier exploratory notes, brainstorms, or preliminary recommendations, **this file takes precedence for architecture planning** unless a later explicit decision supersedes it.

This document does **not** select the final gateway backend or runtime backend.

Those choices must be validated through a technical proof of concept.

---

# 2. Product Direction

We are building:

> **Shofni Agent Platform**

It must be an independent, open-source-capable platform that can be published publicly on GitHub.

It must not be designed as:

- a LiteLLM fork
- a Bifrost fork
- an OpenHands fork
- a Mastra fork
- an OpenCode-only bridge
- a Codex-only proxy
- a Claude-only compatibility layer

External open-source projects may be used as replaceable infrastructure backends behind Shofni-owned interfaces.

Shofni must remain architecturally independent from any single provider, client, framework, gateway, runtime, or model vendor.

---

# 3. Core Architectural Principle

The platform is divided into two permanent operating planes.

```text
Shofni Agent Platform
│
├── Level 2 — Compatibility / Gateway Plane
│
└── Level 3 — Agent Runtime Plane
```

Level 3 does **not** replace Level 2.

Level 2 remains a permanent core of the platform and is reused by Level 3.

The platform must support both modes long term.

---

# 4. Level 2 — Permanent Compatibility / Gateway Plane

Level 2 keeps the original client as the agent.

Examples:

```text
Codex
Claude Code
OpenCode
Future Agent Clients
```

In Level 2:

```text
Client = Agent
Client = Tool Executor
Shofni = Compatibility / Routing / Repair Layer
```

Primary flow:

```text
User
  ↓
Codex / Claude Code / OpenCode
  ↓
Shofni Compatibility Layer
  ↓
Provider / Model
  ↓
Tool Call
  ↓
Shofni normalization / repair when needed
  ↓
Client
  ↓
Client executes tool locally
```

The Shofni Level 2 layer must not execute local shell/filesystem tools itself.

Execution remains owned by the connected client.

---

# 5. Required Level 2 Capabilities

Level 2 must be designed to support:

## Clients

- Codex
- Claude Code
- OpenCode
- future clients

## Client Protocols

- OpenAI Chat Completions
- OpenAI Responses
- Anthropic Messages
- Models endpoint where applicable
- future protocol adapters

## Providers

### Initial live providers

- A6api
- RelayRouter

### Future / optional provider adapter targets

- generic OpenAI-compatible providers
- generic Anthropic-compatible providers
- future/custom providers
- OpenRouter may be added later, but it is **out of the initial live provider scope**

The architecture must remain provider-extensible even though only A6api and RelayRouter are required for the initial live implementation and POC.

## Compatibility

- protocol translation
- provider normalization
- model routing
- multi-provider routing
- fallback
- retries
- streaming normalization
- unified errors
- provider/model capability metadata

## Tools

- native tool-call normalization
- tool schema normalization
- tool-result normalization
- sequential tool continuation
- parallel tool compatibility where supported

## Shofni-specific compatibility capabilities

These are considered strategic Shofni capabilities unless the POC proves a reusable implementation is sufficiently complete:

- chat-only model tool emulation
- structured synthetic tool calling
- text-to-tool-call parsing
- malformed JSON tool-call repair
- provider/model live capability probing
- compatibility diagnostics
- sequential tool reliability testing
- client/provider conformance testing

---

# 6. Native Capability First

Shofni must not downgrade a provider or client when a native path already works correctly.

Preferred behavior:

```text
Native capability available and reliable?
        │
        ├── YES → passthrough / minimal normalization
        │
        └── NO  → translation / emulation / repair
```

Examples:

- Native tools working correctly → use native tools.
- Native Responses support working correctly → use native Responses.
- Native Anthropic Messages support working correctly → use native Messages.
- Native streaming working correctly → preserve it.

Compatibility logic must be activated only when required.

---

# 7. Canonical Shofni Contracts

Shofni must own stable internal contracts.

No client adapter should directly depend on a specific provider adapter.

No provider adapter should contain client-specific logic.

Conceptual flow:

```text
Client Protocol
      ↓
Client Adapter
      ↓
Shofni Canonical Contract
      ↓
Provider / Gateway Backend
      ↓
Provider
```

The same principle applies in reverse.

Canonical contracts should cover at minimum:

```text
Messages
Model Requests
Model Responses
Tools
Tool Calls
Tool Results
Streaming Events
Errors
Capabilities
Routing Metadata
Usage Metadata
```

Provider-specific extensions must be preserved where possible rather than collapsing all providers into the lowest common denominator.

---

# 8. Level 3 — Shofni Agent Runtime Plane

Level 3 adds a Shofni-owned agent runtime on top of the Level 2 core.

In Level 3:

```text
Shofni Runtime = Agent
Shofni Runtime = Tool Executor
Model = Brain / Reasoning Backend
Client = UI / Consumer / Optional Worker
```

Conceptual flow:

```text
User / Client
     ↓
Shofni Agent Runtime
     ↓
Agent Loop
     ↓
Model Router
     ↓
Provider / Model
     ↓
Tool Request
     ↓
Runtime Tool Executor
     ↓
Real Local Workspace / APIs / MCP
     ↓
Tool Result
     ↓
Agent Loop continues
```

Level 3 must reuse the provider, protocol, routing, streaming, tool normalization, diagnostics, and compatibility capabilities created for Level 2.

---

# 9. Required Level 3 Capabilities

Level 3 adds:

- owned Agent Loop
- runtime Tool Executor
- Task State
- sessions
- attempts
- checkpoints
- resume
- recovery
- durable task state
- provider fallback while preserving task identity
- model fallback while preserving task identity
- workspace management
- Git awareness
- worktree awareness
- runtime-owned execution
- MCP integration
- browser/API/tool execution
- audit/evidence
- multi-model continuation
- failure recovery
- execution/result correlation
- duplicate side-effect prevention where possible

---

# 10. Execution Backend Abstraction

Tool execution must be abstracted.

Conceptually:

```text
ToolExecutionBackend
├── CLIENT
└── RUNTIME
```

Level 2:

```text
execution_backend = CLIENT
```

Level 3:

```text
execution_backend = RUNTIME
```

This abstraction is mandatory so Level 2 can evolve into Level 3 without rewriting the tool protocol.

---

# 11. Level 2 Is Not Disposable

This is a hard architectural requirement.

Do not create a temporary Level 2 architecture that will be thrown away when Level 3 begins.

The following Level 2 capabilities must remain reusable in Level 3:

- client protocol adapters
- canonical contracts
- provider adapters
- gateway backend abstraction
- routing
- fallback
- streaming normalization
- tool normalization
- tool emulation
- tool parsing
- tool repair
- capability probing
- diagnostics
- unified errors
- compatibility/conformance tests

Level 3 is an extension of this core.

---

# 12. Open-Source Reuse Strategy

Greenfield development is not the default.

We should reuse mature open-source infrastructure when it materially reduces complexity without creating unacceptable architectural lock-in.

However:

> Shofni owns the stable platform contracts and architecture.

External systems must remain replaceable.

Preferred structure:

```text
Shofni Agent Platform
        │
        ├── Shofni-owned interfaces
        ├── Shofni-owned compatibility features
        ├── Shofni-owned tests
        │
        └── Replaceable Backends
             ├── Gateway Backend
             └── Runtime Backend
```

---

# 13. Gateway Backend Candidates

The current POC candidates are:

```text
Bifrost
LiteLLM
```

No final gateway backend has been selected.

The implementation plan must not assume that either candidate has already won.

They must be evaluated using the same objective POC scenarios.

Possible future abstraction:

```text
GatewayBackend
├── BifrostBackend
├── LiteLLMBackend
└── FutureNativeBackend
```

A Shofni-native gateway may be implemented later if justified, but it is not the starting assumption.

---

# 14. Runtime Backend Candidates

The current POC candidates are:

```text
OpenHands SDK
Mastra
```

No final runtime backend has been selected.

Possible abstraction:

```text
RuntimeBackend
├── OpenHandsBackend
├── MastraBackend
└── FutureNativeRuntime
```

Additional projects such as:

- Pydantic AI
- LangGraph
- Temporal

are currently considered supporting/reference building blocks rather than default platform cores.

They should only be added if the POC proves they solve a real uncovered requirement.

Avoid unnecessary framework stacking.

---

# 15. No Fork Before POC

Do not fork Bifrost, LiteLLM, OpenHands, Mastra, or another candidate before the POC proves that a fork is necessary.

Preferred integration order:

```text
1. dependency / external service
2. adapter
3. extension
4. fork only if necessary
```

Forking is not the default.

---

# 16. No Backend Lock-In

Shofni public APIs and internal canonical contracts must not expose implementation-specific assumptions from:

- Bifrost
- LiteLLM
- OpenHands
- Mastra
- LangGraph
- Temporal
- any individual provider

The platform must be able to replace one backend without rewriting unrelated layers.

---

# 17. Execution Permission Policy

Shofni must not add an additional restrictive execution policy by default.

The requested default philosophy is:

```text
Provider/model restrictions
        +
Client/runtime restrictions
        +
Operating-system permissions
        +
External API/account permissions
        =
Effective execution permissions
```

Shofni should not impose additional:

- branch restrictions
- production restrictions
- tool allowlists
- tool denylists
- mandatory approval gates
- command filters

unless explicitly configured in the future.

Default Shofni execution mode:

```text
authorization.mode = unrestricted
```

This does **not** mean bypassing provider, client, operating-system, account, or external-service restrictions.

Those remain authoritative.

---

# 18. Reliability Is Not a Permission Restriction

The following are required even in unrestricted execution mode:

- schema validation
- protocol validation
- malformed-response detection
- error normalization
- retries
- state tracking
- checkpoints
- result correlation
- logging
- evidence
- duplicate-execution detection
- recovery
- diagnostics

These mechanisms improve correctness and reliability and are not intended to limit the actions available to the model.

---

# 19. Strategic Shofni-Owned Capabilities

The strongest current open-source research did not establish a complete off-the-shelf solution for all of the following.

Therefore these remain primary Shofni design areas:

## Universal Tool Compatibility

```text
Chat-only model
     ↓
Structured tool emulation
     ↓
Real agent/client tool call
```

## Tool Call Repair

```text
Textual tool syntax
Malformed JSON
Provider-specific broken formats
     ↓
Normalized valid tool request
```

## Capability Probing

Test the model/provider rather than trusting declared metadata.

Examples:

- accepts tools?
- emits native tool calls?
- accepts tool results?
- continues after tool result?
- sequential calls work?
- parallel calls work?
- streaming tool calls work?
- Responses protocol behaves correctly?
- Anthropic Messages behaves correctly?

## Compatibility Reports

Generate evidence-based compatibility profiles for:

```text
client × protocol × provider × model
```

## Reliable Continuation

Detect and handle cases such as:

```text
Tool call succeeds
Tool result succeeds
Model returns narration only
No next tool call
Task is not actually complete
```

## Cross-Provider Task Continuity

For Level 3:

```text
Provider / Model A
      ↓ failure
Provider / Model B
      ↓
same task
same workspace
same checkpoint lineage
no duplicated successful side effects
```

---

# 20. POC Is a Required Gate

No final backend selection should happen before the POC.

At minimum the POC must test:

```text
T01
Responses client
→ provider with native tools

T02
Responses client
→ chat-only provider

T03
Anthropic Messages client
→ OpenAI-compatible provider

T04
Chat-only model
→ emulated tool call

T05
Text tool_call
→ valid structured tool call

T06
Malformed tool JSON
→ repaired structured tool call

T07
Tool call #1
→ result
→ tool call #2
→ result
→ FINAL

T08
Streaming tool calls

T09
Provider failure
→ fallback

T10
Level 3 task
→ checkpoint
→ provider/model switch
→ resume

T11
Successful prior side effect
→ not duplicated after resume

T12
Compatibility report across:
Codex
Claude Code
OpenCode
```

Each test must have objective pass/fail criteria.

---

# 21. Provider Scope for Initial Planning

The initial **live** provider scope is:

```text
A6api
RelayRouter
```

OpenRouter is **not** part of the initial live implementation or mandatory POC provider set.

The architecture must still remain able to support:

```text
Generic OpenAI-Compatible Provider
Generic Anthropic-Compatible Provider
Future Custom Providers
```

OpenRouter, Direct OpenAI, Direct Anthropic, or other providers may be added later through those replaceable provider interfaces without changing Shofni's canonical contracts.

## Current Operational Provider Roles

### A6api — Primary Provider

A6api is the current primary operational provider.

Observed project baseline:

```text
Codex        ✅ supported
Claude Code  ✅ supported
OpenCode     ✅ supported

Chat         ✅ supported
Tools        ✅ supported
Agent use    ✅ supported
```

A6api is therefore the initial positive-control provider for client, protocol, tool, and agent-workflow POC testing.

A6api also provides provider-side routing across multiple underlying source/supplier routes for logical model IDs, including official-source options and smart source selection where available.

Shofni must treat these as two distinct fallback layers:

```text
Layer 1:
A6api internal source / supplier selection and failover

Layer 2:
Shofni provider / model routing and fallback
```

They must not be conflated in diagnostics, evidence, or task-continuity logic.

A model ID exposed through A6api should therefore be treated as a logical model route unless an underlying supplier/source is explicitly pinned.

### RelayRouter — OpenCode Chat-Only Compatibility Target

RelayRouter has a narrower observed role.

Current project baseline:

```text
OpenCode chat                 ✅ supported

OpenCode native usable tools  ❌ unsupported
OpenCode tool-dependent work  ❌ unsupported directly

Codex                         ❌ unsupported
Claude Code                   ❌ unsupported
```

RelayRouter must **not** be represented as a general direct provider for all three clients.

Its currently proven Level 2 direct-client role is:

```text
OpenCode
→ RelayRouter
→ chat only
```

Its strategic value is as a real chat-only compatibility target for Shofni capabilities such as:

```text
tool emulation
text-to-tool parsing
malformed tool-call repair
sequential continuation
capability probing
compatibility diagnostics
```

The target path is:

```text
OpenCode
↓
Shofni
↓
RelayRouter chat
↓
text / structured action intent
↓
Shofni parsing / emulation / repair
↓
valid OpenCode tool call
↓
OpenCode executes locally
```

There is currently no direct RelayRouter Level 2 path for Codex or Claude Code.

Protocol-level chat-only tests for Codex Responses or Claude Code Messages must use controlled synthetic provider fixtures/test doubles unless a future live provider path is separately proven.

## Provider Evidence Rule

Provider documentation and compatibility labels do not override reproducible runtime evidence.

Use this precedence:

```text
1. Reproducible live runtime test
2. Shofni capability probe
3. Provider documentation
4. Static model metadata
5. Compatibility / marketing labels
```

Therefore the current operational matrix is:

| Client | A6api | RelayRouter |
|---|---|---|
| Codex | ✅ Working | ❌ Unsupported |
| Claude Code | ✅ Working | ❌ Unsupported |
| OpenCode | ✅ Working with tools | ⚠️ Chat only |

The detailed provider capability source of truth is maintained in:

```text
04-provider-inventory.md
```

When this architecture file contains older exploratory provider assumptions, the newer verified provider inventory takes precedence for operational planning.

---

# 22. Client Scope for Initial Planning

Primary clients:

```text
Codex
Claude Code
OpenCode
```

The architecture must not hard-code assumptions that prevent future clients.

---

# 23. State Strategy

Level 2 should remain as stateless as practical.

Do not introduce a durable database merely to implement Level 2 unless an evidence-based requirement demands it.

Level 3 requires durable state.

The runtime state abstraction should not be tied permanently to one database.

Conceptually:

```text
StateStore
├── Memory / No-op for lightweight Level 2 needs
├── SQLite for local Level 3
└── PostgreSQL / distributed store later if required
```

Do not introduce distributed infrastructure before it is justified.

---

# 24. Public GitHub Requirement

The resulting Shofni Agent Platform is intended to be publishable publicly on GitHub.

Architecture and dependency choices must remain compatible with:

- public source distribution
- modification
- redistribution
- commercial use
- SaaS use
- future optional proprietary Shofni modules where legally permitted

Prefer permissive licenses when architecture quality is comparable.

Review enterprise/custom-license directories separately from the open-source core of any dependency.

---

# 25. Repository Independence

The Shofni repository must remain its own product.

Preferred structure:

```text
shofni-agent-platform/
├── apps/
├── packages/
├── docs/
├── tests/
├── examples/
└── ...
```

Do not vendor complete third-party repositories into the Shofni repository by default.

Open-source candidates should normally be consumed as:

- packages
- binaries
- services
- containers
- adapters
- external development references

unless the execution plan establishes a justified reason otherwise.

---

# 26. Architecture Evaluation Criteria

Backend decisions must be based on evidence, not popularity.

Evaluate:

- architecture fit
- protocol coverage
- client compatibility
- provider compatibility
- native tools
- chat-only tool support
- streaming correctness
- continuation reliability
- routing
- fallback
- extensibility
- runtime ownership
- durable state
- checkpoint/resume
- workspace support
- maintenance health
- security/supply-chain considerations
- license
- public GitHub compatibility
- upgrade risk
- integration complexity
- custom code avoided
- long-term Level 2 → Level 3 evolution

---

# 27. Decisions That Are Final for Planning

The following decisions are considered approved for the implementation-plan stage:

1. The project is **Shofni Agent Platform**.
2. Level 2 is a permanent Compatibility / Gateway Plane.
3. Level 3 is an Agent Runtime Plane built on the Level 2 core.
4. Level 3 does not replace Level 2.
5. Shofni owns the canonical contracts and stable platform interfaces.
6. External gateway/runtime implementations must remain replaceable.
7. Greenfield infrastructure development is not the default.
8. No fork is authorized before the POC justifies it.
9. Gateway POC candidates are Bifrost and LiteLLM.
10. Runtime POC candidates are OpenHands SDK and Mastra.
11. Tool emulation, repair, capability probing, and compatibility testing are strategic Shofni concerns.
12. Initial clients are Codex, Claude Code, and OpenCode.
13. Initial live providers are A6api and RelayRouter; OpenRouter is outside the initial live scope.
14. A6api is the primary provider and is currently observed working with Codex, Claude Code, and OpenCode, including usable tool/agent workflows.
15. RelayRouter is currently an OpenCode chat-only provider: native usable tools are unavailable, and direct Codex/Claude Code support is not part of the current operational baseline.
16. A6api provider-side source/supplier selection and failover is separate from Shofni provider/model fallback and must be diagnosed separately.
17. Level 2 tool execution is client-owned.
18. Level 3 tool execution is runtime-owned.
19. Default Shofni execution authorization is unrestricted.
20. Reliability validation remains mandatory even in unrestricted mode.
21. The project is intended for public GitHub distribution.
22. Backend selection is blocked on objective POC evidence.
23. The implementation plan must preserve a clean Level 2 → Level 3 evolution path.

---

# 28. Decisions Still Open

The following must **not** be treated as already decided:

```text
Bifrost vs LiteLLM
OpenHands vs Mastra
SQLite implementation details
final programming-language split
final monorepo tooling
final deployment model
final CLI/UI implementation
whether LangGraph is needed
whether Temporal is needed
whether Pydantic AI is needed
whether a native gateway/runtime should later replace OSS backends
```

These decisions belong to the POC and execution-plan process.

---

# 29. Planning Rule for Codex

Before proposing implementation work:

1. Read this file completely.
2. Read the original Level 2 / Level 3 architecture source.
3. Read the deep open-source research.
4. Inspect the current candidate projects where necessary.
5. Treat the POC as a required decision gate.
6. Do not silently choose a backend before evidence exists.
7. Do not redesign Level 2 as disposable.
8. Do not introduce unnecessary frameworks.
9. Keep Shofni-owned abstractions independent from third-party implementation details.
10. Optimize for the smallest amount of custom code that still preserves Shofni's strategic capabilities and long-term independence.

---

# 30. Target End State

```text
                         SHOFNI AGENT PLATFORM

                               Clients
                    ┌────────────┼────────────┐
                    ↓            ↓            ↓
                  Codex      Claude Code    OpenCode
                    │            │            │
                    └────────────┼────────────┘
                                 ↓
                         Client Adapters
                                 ↓
                      Shofni Canonical Core
                                 │
              ┌──────────────────┼──────────────────┐
              ↓                  ↓                  ↓
        Compatibility       Capability          Diagnostics
        / Tool Repair         Probing
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 ↓
                         Gateway Backend
                                 │
                    ┌────────────┴────────────┐
                    ↓                         ↓
                 Bifrost                  LiteLLM
                    │                         │
                    └────────────┬────────────┘
                                 ↓
                              Providers

══════════════════════════════ LEVEL 2 ══════════════════════════════

                                 │
                                 ↓
                         Shofni Agent Core
                                 │
                            Agent Loop
                                 │
               ┌─────────────────┼─────────────────┐
               ↓                 ↓                 ↓
          Task / State       Model Routing    Tool Executor
               │                                   │
          Checkpoints                         Local Workspace
               │                              APIs / MCP
          Resume / Recovery                   Browser / Git
               │
          Evidence / Audit
               │
               ↓
                        Runtime Backend Layer
                         ┌───────┴───────┐
                         ↓               ↓
                    OpenHands         Mastra

══════════════════════════════ LEVEL 3 ══════════════════════════════
```

---

## Final Principle

> **Reuse infrastructure. Own the contracts. Own the compatibility intelligence. Keep backends replaceable. Build Level 2 as a permanent core, then add Level 3 without rewriting it.**
