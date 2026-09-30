# Textual Tool Call → Structured Tool Call Regression Fixture

**Project:** Shofni Agent Platform  
**Status:** Synthetic regression fixture + historical-observation specification  
**Primary POC mapping:** T05, T06, T07

---

## 1. Evidence Status

The current 2026-09-30 A6api and RelayRouter raw session pair does **not** contain a literal textual `tool_call` block.

Therefore this file must not be represented as a direct extraction from those two raw sessions.

A previous observed session pattern included cases where textual tool-call syntax appeared in assistant text while a structured tool event was also present.

The exact source of that duplication was not established.

Possible sources include:

```text
model output
provider translation
gateway/adapter translation
client serialization
```

This fixture exists to make that historical class testable without inventing claims about the current raw pair.

---

## 2. Canonical Synthetic Fixture A — Text Only

Provider/model output:

```text
I need to read the requested file.

tool_call:
{"name":"read_fixture","arguments":{"path":"input/alpha.txt"}}
```

Expected Shofni normalization:

```json
{
  "type": "tool_call",
  "name": "read_fixture",
  "arguments": {
    "path": "input/alpha.txt"
  }
}
```

Expected execution count:

```text
1
```

---

## 3. Canonical Synthetic Fixture B — Fenced JSON

Provider/model output:

````text
I will inspect the fixture.

```tool_call
{
  "name": "read_fixture",
  "arguments": {
    "path": "input/alpha.txt"
  }
}
```
````

Expected:

```text
one structured canonical tool call
no final completion before tool result
```

---

## 4. Duplicate Representation Fixture

Input consists of both:

```text
assistant textual content:
tool_call: {"name":"read_fixture","arguments":{"path":"input/alpha.txt"}}
```

and a native structured event:

```json
{
  "type": "tool_call",
  "id": "call_001",
  "name": "read_fixture",
  "arguments": {
    "path": "input/alpha.txt"
  }
}
```

Expected Shofni behavior:

```text
prefer native structured event
detect textual semantic duplicate
execute exactly once
preserve both original representations in evidence
never emit two logical calls
```

---

## 5. False-Positive Corpus

These must **not** execute a tool:

```text
"The provider supports tool_call syntax."

"Example: tool_call is a field used by some APIs."

"Do not issue a tool call yet."

"The previous tool_call failed."
```

The parser must require an unambiguous actionable structure.

---

## 6. Validation Rules

Before converting text into a real tool call:

```text
1. tool name must exist in the supplied tool registry
2. arguments must parse
3. arguments must validate against tool schema
4. payload must be unambiguous
5. native structured duplicate must be detected
6. execution must not occur before validation
```

---

## 7. Failure Handling

Recoverable syntax:

```text
→ bounded repair
→ validate
→ structured tool call
```

Ambiguous/unrecoverable syntax:

```text
→ do not execute
→ bounded retry or normalized error
```

No infinite repair loop.

---

## 8. PASS Criteria

PASS only if:

```text
textual actionable syntax is converted correctly
ordinary prose is not executed
native + textual duplicates execute once
call/result correlation remains intact
follow-up tool continuation still works
```

---

## 9. Evidence Label

Results produced from this file must be marked:

```text
SYNTHETIC_FIXTURE_EVIDENCE
```

not:

```text
LIVE_PROVIDER_EVIDENCE
```
