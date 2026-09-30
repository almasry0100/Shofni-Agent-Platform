# Tool Loop Failure Reproduction — RelayRouter vs A6api Control

**Project:** Shofni Agent Platform  
**Evidence date:** 2026-09-30  
**Status:** Real live-provider reproduction  
**Primary POC mapping:** T04, T07, T12

---

## 1. Purpose

Record a controlled real-world contrast between:

```text
OpenCode → RelayRouter
```

and:

```text
OpenCode → A6api
```

for a simple local file-read task.

This document intentionally separates what the attached raw evidence proves from older/historical tool-loop symptoms.

---

## 2. Controlled Conditions

Both captured sessions used:

```text
Client: OpenCode
Client version: 1.18.32
Agent mode: build
Workspace class: <USERPROFILE>\Downloads\test
Task class: read local config.toml and report contents
```

The provider/model changed.

### Failure route

```text
Provider: RelayRouter
Model route: private/gpt-5.6-sol
```

### Positive control

```text
Provider: A6api
Model route: gpt-6-astra
```

This is not a same-model benchmark. It is a client/tool-path control comparison.

---

## 3. RelayRouter Failure Sequence

The user requested that OpenCode read:

```text
<USERPROFILE>\Downloads\test\config.toml
```

Observed:

```text
user requests file read
↓
assistant says it will open/read the file
↓
NO structured tool event
↓
assistant states local file access/tools are unavailable
↓
finish: stop
```

The user then explicitly requested execution again.

Observed:

```text
user: execute
↓
assistant again narrates the intended action
↓
NO structured tool event
↓
assistant suggests a manual PowerShell command
↓
finish: stop
```

The user requested execution a third time.

Observed:

```text
user: execute
↓
NO structured tool event
↓
assistant again states file tools are unavailable
↓
finish: stop
```

### Important raw-session fact

The RelayRouter session contains:

```text
structured tool events: 0
```

for this task sequence.

The route therefore behaved as chat-only for this OpenCode session.

---

## 4. A6api Positive Control

The same task class was run through A6api.

Observed:

```text
user requests file read
↓
assistant finish: tool-calls
↓
structured tool event:
  tool = read
  filePath = <USERPROFILE>\Downloads\test\config.toml
↓
tool state = completed
↓
tool output contains the file
↓
assistant returns the file contents
↓
finish: stop
```

This demonstrates that:

```text
OpenCode itself can execute the read tool
the local filesystem path is usable
the workspace is usable
the read tool is usable
```

in the positive-control route.

---

## 5. Current Evidence-Based Conclusion

The current raw pair supports this conclusion:

```text
A6api + OpenCode:
usable tool path observed

RelayRouter + OpenCode:
chat observed
usable tool path not observed
```

It does **not** prove the exact internal root cause.

Possible failure domains remain:

```text
RelayRouter route capability
provider protocol translation
tool-schema transport
model route behavior
provider/client adapter behavior
```

Shofni should classify the effective current capability, not guess the hidden cause:

```text
RelayRouter/OpenCode native tools = UNSUPPORTED_OBSERVED
```

---

## 6. Historical Premature-Continuation Variant

A separate historical symptom motivated the original `T07` acceptance test:

```text
tool #1 succeeds
↓
tool result succeeds
↓
assistant narrates the next action
↓
finish: stop
↓
no tool #2
```

The two raw files used for this document do **not** reproduce that exact post-tool-result sequence.

Therefore:

```text
Current raw pair
= direct no-tool / chat-only reproduction

Historical symptom
= post-tool-result premature continuation failure
```

They must remain separate evidence classes.

`T07` exists to reproduce the historical variant deterministically.

---

## 7. Regression Requirement

The Level 2 compatibility layer must eventually pass:

```text
tool #1
→ result #1
→ tool #2
→ result #2
→ FINAL
```

with:

```text
unique call IDs
correct result correlation
no dropped follow-up call
no narration-only continuation
no duplicate execution
```

---

## 8. Related Evidence

```text
docs/repro/relayrouter-opencode-failure.json
docs/repro/text-tool-call-example.md
docs/repro/provider-errors.md
docs/06-poc-acceptance-scenarios.md
```

Raw session exports should remain outside Git unless intentionally sanitized.
