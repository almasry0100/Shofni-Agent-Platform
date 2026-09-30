# Open-Source License Baseline

**Project:** Shofni Agent Platform  
**Status:** Lightweight pre-POC license screen  
**Updated:** 2026-09-30  
**Shofni project license:** MIT

> This is an engineering license inventory, not legal advice. Re-check the exact license at the selected commit/tag before vendoring, forking, redistributing, or copying source code.

---

## 1. Why this file exists

The project is intended for public GitHub distribution.

Even if Shofni uses a permissive MIT license, third-party code keeps its own license.

Using a dependency does **not** relicense that dependency as MIT.

---

## 2. Current Candidates

| Project | Current research baseline | Important boundary |
|---|---|---|
| Bifrost | Apache-2.0 | Preserve required notices if code is redistributed/copied |
| LiteLLM | MIT outside `enterprise/` | `enterprise/` has separate licensing/terms; do not assume MIT applies there |
| OpenHands Software Agent SDK | MIT | Re-check selected revision and bundled third-party notices |
| Mastra | Apache-2.0 outside `ee/` | `ee/` has separate terms; do not assume Apache-2.0 applies there |
| Pydantic AI | MIT | Re-check selected revision |
| LangGraph | MIT | Re-check selected revision |
| Temporal | MIT | Re-check selected revision |

---

## 3. Initial Policy

Before the POC:

```text
use candidates as external packages/services/containers/reference code
do not vendor whole repositories into Shofni
do not fork unless evidence requires it
```

If the POC selects a backend:

```text
1. pin the exact commit/tag
2. verify the license at that revision
3. identify separately licensed directories
4. preserve required NOTICE / attribution files
5. record whether code is linked, copied, modified, or run as a service
```

---

## 4. Shofni License

Shofni Agent Platform uses:

```text
MIT
```

Reason for the initial choice:

```text
simple
permissive
widely understood
allows commercial use
allows modification
allows redistribution
minimal project-level friction
```

The root `LICENSE` file governs Shofni-owned code only.

---

## 5. Do Not Copy Restricted Trees Accidentally

Particular attention:

```text
LiteLLM:
enterprise/

Mastra:
ee/
```

Do not copy or vendor those directories under the assumption that the repository root license applies to them.

---

## 6. Pre-Release Check

Before the first public release containing third-party code:

```text
[ ] exact dependency versions pinned
[ ] exact license files reviewed
[ ] NOTICE/attribution requirements checked
[ ] separately licensed directories excluded or explicitly approved
[ ] copied/modified upstream code identified
[ ] third-party license notices included where required
```
