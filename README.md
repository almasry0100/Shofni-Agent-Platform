# Shofni Agent Platform

Shofni Agent Platform is an open-source-capable AI agent infrastructure project designed around two permanent operating planes:

- **Level 2 — Compatibility / Gateway Plane**
- **Level 3 — Agent Runtime Plane**

The project is currently in the **architecture-frozen / proof-of-concept stage**. The target architecture has been defined, provider behavior has been captured from live use, and an objective POC acceptance suite is ready. No final gateway or runtime backend has been selected yet.

## Project Goal

Shofni is intended to provide a stable compatibility and execution layer between AI coding clients, model providers, tools, and future agent runtimes without locking the platform to one provider, client, framework, or model vendor.

The core principle is:

> **Reuse infrastructure. Own the contracts. Own compatibility intelligence. Keep backends replaceable.**

Shofni owns the canonical platform contracts and compatibility behavior. External gateways and runtimes are treated as replaceable infrastructure behind Shofni-owned interfaces.

## Architecture

### Level 2 — Compatibility / Gateway Plane

Level 2 keeps the connected client as the agent and tool executor.

```text
User
  ↓
Codex / Claude Code / OpenCode
  ↓
Shofni Compatibility / Gateway Plane
  ↓
Provider / Model
  ↓
Tool Call
  ↓
Shofni normalization / repair when needed
  ↓
Client
  ↓
Client executes the tool locally
```

In Level 2:

```text
Client = Agent
Client = Tool Executor
Shofni = Compatibility / Routing / Repair Layer
ToolExecutionBackend = CLIENT
```

The Level 2 plane is intended to support:

- OpenAI Chat Completions
- OpenAI Responses
- Anthropic Messages
- model discovery where applicable
- provider normalization
- routing and fallback
- retries
- streaming normalization
- unified errors
- native tool-call normalization
- chat-only tool emulation
- textual tool-call parsing
- malformed JSON repair
- tool-result continuation
- sequential multi-tool reliability
- provider/model capability probing
- evidence-based compatibility reports

Level 2 is a permanent part of the platform. It is **not** a temporary bridge that will be discarded later.

### Level 3 — Agent Runtime Plane

Level 3 reuses the Level 2 compatibility/provider core and moves agent ownership into Shofni.

```text
User / Client UI
  ↓
Shofni Agent Runtime
  ↓
Shofni Agent Loop
  ↓
Provider / Model
  ↓
Runtime Tool Executor
  ↓
Workspace / Git / MCP / Browser / API Tools
  ↓
Durable Task State / Checkpoints / Evidence
```

In Level 3:

```text
Shofni Runtime = Agent
Shofni Runtime = Tool Executor
Model = Reasoning Backend
Client = UI / Consumer / Optional Worker
ToolExecutionBackend = RUNTIME
```

Level 3 adds:

- owned agent loop
- runtime tool execution
- task/session/attempt identity
- durable task state
- checkpoints
- resume and recovery
- provider/model fallback while preserving task state
- workspace lifecycle
- Git/worktree awareness
- MCP integration
- browser/API/tool execution
- audit and evidence records
- multi-model continuation
- duplicate-side-effect prevention where possible

## Initial Client Targets

The initial first-class clients are:

| Client | Target protocol | Level 2 role | Level 3 role |
|---|---|---|---|
| Codex | OpenAI Responses-compatible | Agent + Tool Executor | UI / Consumer / Optional Worker |
| Claude Code | Anthropic Messages-compatible | Agent + Tool Executor | UI / Consumer / Optional Worker |
| OpenCode | OpenAI-compatible / Chat Completions | Agent + Tool Executor | UI / Consumer / Optional Worker |

Protocol correctness, streaming behavior, and multi-tool continuation remain subject to the POC acceptance suite.

## Initial Live Providers

The initial live provider scope is intentionally limited to:

- **A6api**
- **RelayRouter**

OpenRouter and direct OpenAI/Anthropic providers are not required for the initial live POC. The architecture remains extensible through generic OpenAI-compatible and Anthropic-compatible adapters.

### A6api

Current project evidence classifies A6api as the **primary positive-control provider**.

Observed project behavior:

```text
Codex        ✅
Claude Code  ✅
OpenCode     ✅
Chat         ✅
Usable tools ✅
Agent flows  ✅
```

A6api can also expose multiple underlying source/supplier routes for one logical model ID. Provider-internal source selection must remain separate from Shofni's own provider/model fallback logic.

### RelayRouter

Current project evidence classifies RelayRouter as an **OpenCode chat-only compatibility target**.

Observed project behavior:

```text
OpenCode chat                 ✅
OpenCode usable native tools  ❌
Codex direct path             ❌
Claude Code direct path       ❌
```

RelayRouter is therefore useful as a real-world negative control for:

- chat-only compatibility
- tool emulation
- text-to-tool parsing
- malformed tool-call repair
- sequential continuation testing
- live capability probing

Provider documentation and observed runtime behavior are recorded separately. When they conflict, reproducible observed behavior takes precedence for Shofni's effective capability classification.

## POC Candidates

No final backend has been selected.

The same objective Level 2 suite will be run against:

```text
Bifrost
LiteLLM
```

The same objective Level 3 suite will be run against:

```text
OpenHands Software Agent SDK
Mastra
```

Supporting/reference projects currently include:

```text
Pydantic AI
LangGraph
Temporal
```

These are not automatic dependencies.

The POC decides what is reused, extended, wrapped, or rejected. No fork is authorized merely because a project is popular or feature-rich.

## POC Acceptance Philosophy

A candidate does not pass because:

```text
it starts
a normal chat request works
its README claims compatibility
one tool call succeeds once
```

A candidate must prove the required protocol, tool, streaming, continuation, fallback, state, recovery, and evidence behavior.

Examples of required scenarios include:

- Responses client → native-tool provider
- Responses client → controlled chat-only backend
- Anthropic Messages client → OpenAI-compatible provider
- chat-only provider → emulated tool call
- textual `tool_call` → structured tool call
- malformed tool JSON → bounded repair
- tool 1 → result → tool 2 → result → final
- streaming tool calls
- provider fallback before and after tool execution
- checkpoint → restart/switch → same Level 3 task and workspace
- duplicate-side-effect prevention
- compatibility report generation from evidence

See [`docs/06-poc-acceptance-scenarios.md`](docs/06-poc-acceptance-scenarios.md) for the full decision-grade acceptance specification.

## Evidence-Driven Compatibility

Shofni distinguishes:

```text
declared capability
observed capability
effective capability
```

Example:

```text
provider declares tools
+
reproducible tool request fails
=
effective capability: UNSUPPORTED
```

until later evidence proves otherwise.

The project includes sanitized reproduction artifacts for real provider behavior under [`docs/repro/`](docs/repro/).

## Repository Documentation

The current documentation set is organized as follows:

| Document | Purpose |
|---|---|
| [`docs/01-level-2-level-3-original.md`](docs/01-level-2-level-3-original.md) | Original problem framing and architecture evolution |
| [`docs/02-open-source-deep-research.md`](docs/02-open-source-deep-research.md) | Deep open-source landscape research |
| [`docs/03-final-architecture-decisions.md`](docs/03-final-architecture-decisions.md) | Approved architecture decision baseline |
| [`docs/04-provider-docs.md`](docs/04-provider-docs.md) | Captured provider documentation |
| [`docs/04-provider-inventory.md`](docs/04-provider-inventory.md) | Provider/model capability source of truth |
| [`docs/05-client-readiness.json`](docs/05-client-readiness.json) | Sanitized machine-readable workstation readiness snapshot |
| [`docs/05-client-targets.md`](docs/05-client-targets.md) | Client targets and local readiness baseline |
| [`docs/06-poc-acceptance-scenarios.md`](docs/06-poc-acceptance-scenarios.md) | POC acceptance specification |
| [`docs/repro/`](docs/repro/) | Sanitized provider reproduction and regression evidence |
| [`docs/research/licenses.md`](docs/research/licenses.md) | Lightweight OSS license baseline |

The model lists used during provider preparation are also retained in the repository as project research inputs.

## Local POC Prerequisites

The current development baseline includes:

- Windows 11
- Codex CLI
- Claude Code
- OpenCode
- Docker
- Git
- GitHub CLI
- Node.js / npm
- Python 3.12

The POC must still validate end-to-end compatibility even when all local tooling is installed successfully.

## Environment Configuration

Copy the public template:

```text
.env.example
```

Required live-provider variables for the initial POC:

```dotenv
A6API_KEY=
RELAYROUTER_API_KEY=
```

Do not commit the real `.env` file.

The test harness may validate that a credential is present, but it must never print or persist the secret value in evidence artifacts.

## Security and Evidence Rules

Never commit:

- API keys
- bearer tokens
- GitHub tokens
- cookies
- secret query parameters
- raw provider credentials
- raw evidence containing secrets or private local data

The repository `.gitignore` excludes local secret/state paths and raw POC evidence directories. Sanitized evidence may be committed separately.

## Open-Source Reuse Policy

Shofni should consume external projects as packages, services, binaries, containers, adapters, or development references by default.

Complete third-party repositories should not be vendored into this repository unless the POC provides a specific justification.

Current license screening includes:

- Bifrost — Apache-2.0
- LiteLLM — MIT outside its separately licensed `enterprise/` tree
- OpenHands Software Agent SDK — MIT
- Mastra — Apache-2.0 outside its separately licensed `ee/` tree
- Pydantic AI — MIT
- LangGraph — MIT
- Temporal — MIT

Exact licenses must be re-verified at the selected commit/tag before copying, modifying, vendoring, or redistributing third-party source.

## Current Project Status

```text
Architecture baseline          ✅ Frozen for execution planning
Provider baseline              ✅ Captured
Client/toolchain readiness     ✅ Captured
Provider failure evidence      ✅ Captured
POC acceptance specification   ✅ Ready
Gateway backend selection      ⏳ Pending POC
Runtime backend selection      ⏳ Pending POC
Production implementation      ⏳ Not started
```

The next major project step is to execute the documented POC and use its evidence to drive the final implementation plan and backend decisions.

## License

Shofni Agent Platform is licensed under the [MIT License](LICENSE).

Third-party dependencies and reused code remain subject to their own licenses.
