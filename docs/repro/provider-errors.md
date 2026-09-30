# Provider Errors & Compatibility Evidence Catalog

**Project:** Shofni Agent Platform  
**Status:** Initial evidence baseline  
**Updated:** 2026-09-30

---

## 1. Purpose

Maintain a compact provider failure catalog that distinguishes:

```text
OBSERVED
DOCUMENTED
UNVERIFIED
```

Do not convert provider documentation into an observed capability.

---

# RelayRouter

## RR-001 — OpenCode chat works, usable native tools absent

**Evidence:** OBSERVED  
**Client:** OpenCode 1.18.32  
**Provider:** RelayRouter  
**Model route:** `private/gpt-5.6-sol`

Observed:

```text
chat response works
file-read task requested
no structured tool event emitted
assistant says file tools are unavailable
finish: stop
```

Repeated execution requests did not produce a tool call.

Effective classification:

```text
chat = SUPPORTED
native usable tools = UNSUPPORTED_OBSERVED
```

POC mapping:

```text
T04
T07
T12
```

---

## RR-002 — Narration instead of action

**Evidence:** OBSERVED

Pattern:

```text
assistant says it will read/check the file
↓
no tool event
↓
assistant tells user to execute manually
↓
finish: stop
```

This is not equivalent to a successful agent/tool turn.

Classification:

```text
PROVIDER_CAPABILITY_MISSING_OR_TRANSLATION_PATH
root cause = UNVERIFIED
```

---

## RR-003 — Usage metadata anomaly

**Evidence:** OBSERVED

The failure session reports:

```text
input tokens = 0
reasoning tokens = 0
```

despite real user/assistant exchanges.

Impact:

```text
diagnostics / accounting metadata may be unreliable on this route
```

Causal relationship to missing tools:

```text
UNVERIFIED
```

Do not treat this as the proven cause of the tool failure.

---

## RR-004 — Codex direct compatibility

**Evidence:** CURRENT PROJECT BASELINE

```text
Codex × RelayRouter = UNSUPPORTED
```

Do not configure it as a normal Level 2 fallback route.

---

## RR-005 — Claude Code direct compatibility

**Evidence:** CURRENT PROJECT BASELINE

```text
Claude Code × RelayRouter = UNSUPPORTED
```

Do not configure it as a normal Level 2 fallback route.

---

# A6api

## A6-CTRL-001 — OpenCode native tool positive control

**Evidence:** OBSERVED  
**Client:** OpenCode 1.18.32  
**Provider:** A6api  
**Model:** `gpt-6-astra`

Observed:

```text
file-read task requested
↓
assistant finish = tool-calls
↓
structured tool = read
↓
tool status = completed
↓
tool result returned
↓
assistant returns file contents
```

Effective classification for this tested route:

```text
tool call = SUPPORTED_OBSERVED
tool execution = SUPPORTED_OBSERVED
tool-result continuation = SUPPORTED_OBSERVED
```

POC mapping:

```text
T01
T07
T12
```

---

## A6-002 — Multi-source logical route diagnostics

**Evidence:** PROVIDER/PROJECT BASELINE

A6api may serve one logical model ID through multiple underlying source/supplier routes.

Shofni must distinguish:

```text
A6api internal source failover
```

from:

```text
Shofni provider/model fallback
```

When upstream source metadata is unavailable, report it as unknown rather than guessing.

---

# Cross-Provider A/B Evidence

## CP-001 — Same client/workspace class, different provider result

Controlled properties:

```text
OpenCode 1.18.32
build agent
same local workspace class
same task class: read config.toml
```

A6api:

```text
structured read tool emitted
tool completed
final answer produced
```

RelayRouter:

```text
zero structured tool events
assistant reports tools unavailable
repeated stop
```

Important limitation:

```text
different model IDs were used
```

Therefore the evidence establishes provider-route behavior for these tested paths, not model-independent universal behavior.

---

# Historical Regression Class

## HIST-001 — Successful tool result followed by premature stop

**Evidence:** HISTORICALLY OBSERVED; NOT REPRODUCED BY THE CURRENT RAW PAIR

Pattern:

```text
tool #1 succeeds
result #1 succeeds
assistant narrates next action
finish: stop
no tool #2
```

This remains a mandatory `T07` acceptance scenario.

Do not merge HIST-001 with RR-001.

RR-001 is:

```text
no usable tool call emitted
```

HIST-001 is:

```text
tool path exists but continuation breaks
```

---

# Error Classification Vocabulary

Use:

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

---

# Evidence Rules

Never say:

```text
provider supports tools
```

because documentation says so.

Record separately:

```text
declared
observed
effective
```

Never commit raw provider tokens, API keys, Authorization headers, cookies, or credentials.
