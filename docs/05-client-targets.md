# 05 — Client Targets & Local Readiness

**Project:** Shofni Agent Platform  
**Document Type:** Client Target / Local Environment Readiness Baseline  
**Status:** READY FOR POC AUTHORING AND LOCAL EXECUTION SETUP  
**Date:** 2026-09-29  
**Architecture source of truth:** `03-final-architecture-decisions.md`

---

## 1. Purpose

This document freezes the initial client targets and records the verified local workstation readiness for the Shofni Agent Platform POC.

It separates:

1. **Architectural target**
2. **Observed local installation/readiness**
3. **Protocol behavior still requiring POC evidence**

Installation readiness does not itself prove end-to-end protocol compatibility.

---

## 2. Initial Client Priority

```text
1. Codex
2. Claude Code
3. OpenCode
```

All three remain first-class client targets.

---

## 3. Intended Client / Protocol Mapping

| Client | Primary target protocol | Level 2 role | Level 3 role | Protocol status |
|---|---|---|---|---|
| Codex | OpenAI Responses-compatible path | Agent + Tool Executor | UI / Consumer / Optional Worker | POC required |
| Claude Code | Anthropic Messages-compatible path | Agent + Tool Executor | UI / Consumer / Optional Worker | POC required |
| OpenCode | OpenAI-compatible / Chat Completions path | Agent + Tool Executor | UI / Consumer / Optional Worker | POC required |

Conceptual Level 2 routes:

```text
Codex
  → /v1/responses
  → Shofni Compatibility / Gateway Plane
  → Provider

Claude Code
  → /v1/messages
  → Shofni Compatibility / Gateway Plane
  → Provider

OpenCode
  → /v1/chat/completions
  → Shofni Compatibility / Gateway Plane
  → Provider
```

These are target routes, not claims of compatibility before the POC.

---

## 4. Workstation Baseline

```text
Operating system: Microsoft Windows 11 Enterprise
Windows version: 10.0.26200
Architecture: AMD64
PowerShell: 5.1.26100.9444
```

Primary local workspace:

```text
C:\Users\shofni\Desktop\Shofni Agent Platform
```

---

## 5. Codex

```text
Installed: YES
Command: codex
Version: codex-cli 0.159.0
Executable:
C:\Users\shofni\AppData\Roaming\npm\codex.ps1
```

Configuration detected:

```text
C:\Users\shofni\.codex\config.toml
C:\Users\shofni\.codex
```

Target:

```text
Codex
→ OpenAI Responses-compatible interface
→ Shofni
→ selected gateway/provider
```

Level 2:

```text
Codex = Agent
Codex = Tool Executor
Shofni = Compatibility / Routing / Repair
```

Level 3:

```text
Shofni Runtime = Agent
Shofni Runtime = Tool Executor
Codex = UI / Consumer / Optional Worker
```

**Local readiness: PASS**

Protocol, streaming, and sequential-tool behavior still require POC evidence.

---

## 6. Claude Code

```text
Installed: YES
Command: claude
Version: 2.1.278 (Claude Code)
Executable:
C:\Users\shofni\AppData\Roaming\npm\claude.ps1
```

Configuration detected:

```text
C:\Users\shofni\.claude
C:\Users\shofni\.claude\settings.json
```

Target:

```text
Claude Code
→ Anthropic Messages-compatible interface
→ Shofni
→ selected gateway/provider
```

**Local readiness: PASS**

Protocol, streaming, and sequential-tool behavior still require POC evidence.

---

## 7. OpenCode

Verified after installation cleanup:

```text
Installed: YES
Command: opencode
Version: 1.18.33
Executable:
C:\Users\shofni\AppData\Roaming\npm\opencode.ps1
```

Configuration directory detected:

```text
C:\Users\shofni\.config\opencode
```

The candidate file:

```text
C:\Users\shofni\.config\opencode\opencode.json
```

was not present during the last automated readiness scan.

This is not an installation blocker; the active configuration path should be inspected/configured during the POC setup phase.

Target:

```text
OpenCode
→ OpenAI-compatible / Chat Completions interface
→ Shofni
→ selected gateway/provider
```

**Local readiness: PASS**

Protocol and tool behavior still require POC evidence.

---

## 8. Docker

```text
Installed: YES
Docker CLI: Docker version 29.8.1, build 4a63305
Docker daemon: RUNNING
Docker server version: 29.8.1

Executable:
C:\Program Files\Docker\Docker\resources\bin\docker.exe
```

Docker is available for isolated POC services, gateway candidates, test providers, and controlled integration environments.

**Local readiness: PASS**

---

## 9. Git

```text
Installed: YES
Version: git version 2.55.0.windows.5
Executable:
C:\Program Files\Git\cmd\git.exe
```

Global identity:

```text
user.name: Youssef
user.email: configured
```

Git is ready for:

```text
repository awareness
branches
diffs
commits
worktrees
workspace identity
resume/recovery tests
```

**Local readiness: PASS**

---

## 10. GitHub CLI

```text
Installed: YES
Version: gh 2.101.0
Executable:
C:\Program Files\GitHub CLI\gh.exe
```

Authentication:

```text
GitHub.com: authenticated
Git protocol: HTTPS
Active account: YES
Required repository/workflow scopes: present
```

No token values are recorded in this document.

**Local readiness: PASS**

---

## 11. Node.js / npm

```text
Node: v24.19.0
Node executable:
C:\Program Files\nodejs\node.exe

npm: 11.17.0
npm executable:
C:\Program Files\nodejs\npm.ps1
```

**Local readiness: PASS**

---

## 12. Python

Two Python runtimes are installed.

Default Python:

```text
Python 3.14.7
```

POC baseline:

```text
Python 3.12.10
Executable:
C:\Users\shofni\AppData\Local\Programs\Python\Python312\python.exe

pip:
25.0.1
```

Verified commands:

```text
py -0p
py -3.12 --version
py -3.12 -m pip --version
py -3.12 -c "import sys; print(sys.executable)"
```

Python 3.12 is the intended POC baseline for Python-based gateway/runtime candidates that require or prefer 3.12.

Python 3.14 remains installed and does not need to be removed.

**Local readiness: PASS**

---

## 13. Provider Credential Snapshot

The readiness collector checked only variable presence and did not store secret values.

Last observed:

| Variable | Present |
|---|---:|
| `A6API_KEY` | YES |
| `RELAYROUTER_API_KEY` | NO |
| `OPENROUTER_API_KEY` | NO |
| `OPENAI_API_KEY` | NO |
| `ANTHROPIC_API_KEY` | NO |

Interpretation:

```text
A6api:
credential visible to collected environment

RelayRouter:
credential not visible in collected environment

OpenRouter:
credential not visible in collected environment

Direct OpenAI:
optional baseline, not configured

Direct Anthropic:
optional baseline, not configured
```

Provider credentials are a provider-specific execution prerequisite, not a client/tooling installation blocker.

No secrets belong in Git.

---

## 14. Final Local Readiness Matrix

| Component | Status |
|---|---|
| Codex CLI | ✅ READY |
| Claude Code | ✅ READY |
| OpenCode | ✅ READY |
| Docker CLI | ✅ READY |
| Docker daemon | ✅ READY |
| Git | ✅ READY |
| GitHub CLI | ✅ READY |
| GitHub authentication | ✅ READY |
| Node.js | ✅ READY |
| npm | ✅ READY |
| Python 3.12 | ✅ READY |
| Python pip | ✅ READY |
| A6api credential | ✅ PRESENT |
| RelayRouter credential | ⚠️ NOT VISIBLE |
| OpenRouter credential | ⚠️ NOT VISIBLE |
| Direct OpenAI credential | OPTIONAL |
| Direct Anthropic credential | OPTIONAL |

---

## 15. Readiness Decision

The local machine is now ready to proceed with:

```text
06-poc-acceptance-scenarios.md
```

and then with controlled local POC execution.

The previous environment blockers are closed:

```text
OpenCode   ✅
Git        ✅
GitHub CLI ✅
Python 3.12 ✅
```

Remaining credential gaps should be resolved only when the corresponding live provider scenario is about to run.

They do not block writing the POC specification.

---

## 16. POC Validation Still Required

Local installation readiness is not compatibility proof.

Each client must later be tested for:

```text
request protocol
model selection
streaming
tool schema transmission
tool-call receipt
tool-result continuation
sequential multi-tool flow
error propagation
provider fallback behavior
diagnostic evidence
```

For Level 2:

```text
ToolExecutionBackend = CLIENT
```

For Level 3:

```text
ToolExecutionBackend = RUNTIME
```

---

## 17. Evidence Rules

Do not mark compatibility PASS merely because:

```text
the CLI starts
a config file exists
a normal chat response succeeds
a provider claims OpenAI compatibility
native tool metadata exists
```

Compatibility requires the matching POC acceptance scenario.

Important distinctions:

```text
OpenAI-compatible ≠ automatically Responses-compatible

Native tools ≠ reliable sequential tool continuation

MCP support ≠ complete Agent Runtime
```

---

## 18. Next Artifact

Next required artifact:

```text
06-poc-acceptance-scenarios.md
```

Each test should define:

```text
Test ID
Purpose
Level
Client
Protocol
Provider
Model / route class
Preconditions
Input
Expected request
Expected events
Expected tool behavior
Expected state behavior
PASS criteria
FAIL criteria
Evidence to capture
Retry limits
Cleanup
```

The POC remains the mandatory decision gate before selecting:

```text
Gateway:
Bifrost vs LiteLLM

Runtime:
OpenHands SDK vs Mastra
```
