# Shofni Agent Platform — POC Resolution Plan v1.1

**Document status:** Authoritative Resolution Plan for the bounded POC resolution run  
**Repository:** `almasry0100/Shofni-Agent-Platform`  
**Expected branch:** `main`  
**Expected baseline HEAD:** `3b59332e76abcae7c50f4374ff63e80b60296195`  
**Expected baseline tests:** `81 passing`  
**Scope:** Evidence resolution, candidate selection, compatibility-readiness classification, and final POC closure only  
**Production implementation:** Out of scope  
**Git execution boundary:** The execution agent must not commit or push during the Resolution run

## Purpose

This is the standalone source-of-truth version of the approved Resolution Plan v1.1 that was previously embedded in the Codex execution prompt. It preserves the plan's architecture boundaries, evidence rules, retry budgets, selection logic, validation gates, and stop conditions. Future execution prompts should reference this file instead of embedding the whole plan inline.

============================================================
0. OBJECTIVE
============================================================

Resolve the remaining POC evidence gaps and produce a defensible final
architecture decision if candidate-controlled mandatory evidence permits it.

Do not force a winner.

Do not reinterpret old failures.

Do not erase historical evidence.

The final decision model is intentionally split into:

A. Architecture Selection
B. Compatibility Readiness

This Resolution Plan v1.1 is an explicit authorized refinement of the prior
POC decision policy.

============================================================
1. FIRST ACTION — VERIFY CURRENT STATE
============================================================

Locate the actual nested repository.

Verify:

- Git root
- branch
- HEAD
- origin/main
- clean working tree
- nothing staged
- latest commits

Expected:

branch = main
HEAD = 3b59332e76abcae7c50f4374ff63e80b60296195
origin/main = same
working tree = clean

Run:

.\.venv\Scripts\python.exe -m pytest tests/poc

Expected baseline:

81 passing

Run:

git diff --check

If HEAD is newer:

inspect and preserve legitimate newer work.

Never reset, clean Git history, overwrite evidence, or destroy newer work.

============================================================
2. READ AUTHORITATIVE MATERIAL
============================================================

Read completely:

docs/07-codex-execution-plan.md
docs/06-poc-acceptance-scenarios.md
docs/03-final-architecture-decisions.md
docs/poc/backend-decision.md
docs/poc/decision-evidence.md
docs/poc/composition-results.md
docs/poc/runtime-results.md
docs/poc/gateway-results.md
docs/poc/phase14-followup-results.md
docs/poc/post-poc-implementation-plan.md
docs/poc/candidate-lock.json

Read all relevant evidence for:

Phase 3-6
Phase 7
Phase 8
Phase 9
Phase 10
Phase 11
Phase 12
Phase 13
Phase 14
Phase 14 follow-up

Especially:

T01-T12
OpenHands provenance
T10
T11
T03
T04
RelayRouter provider/access failures
Mastra license closure
four composition rows

============================================================
3. FROZEN ARCHITECTURE
============================================================

Level 2:

ToolExecutionBackend = CLIENT

Level 3:

ToolExecutionBackend = RUNTIME

Level 2 remains the permanent compatibility/gateway plane.

Level 3 remains a separate runtime plane.

Candidates remain replaceable.

Shofni owns:

- canonical contracts
- provider/client normalization
- compatibility intelligence
- task identity
- workspace identity
- attempt identity
- checkpoints
- evidence
- side-effect protection
- error taxonomy
- selection policy

Do not collapse Level 2 and Level 3.

============================================================
4. CANDIDATE SAFETY
============================================================

Candidate source trees remain read-only:

Bifrost
LiteLLM
OpenHands
Mastra

Before execution, revalidate all candidate tree/file-count/manifest/lock
identities against:

docs/poc/candidate-lock.json

Do NOT:

- modify candidate source
- patch candidate imports
- use Mastra EE
- stub EE modules
- hide EE imports
- update candidate versions silently
- use OpenRouter
- invent a new candidate
- invent a new provider

============================================================
5. CREATE RESOLUTION RUN
============================================================

Create:

poc/runs/resolution-<run-id>/manifest.json

Permanent sanitized evidence:

tests/poc/evidence/resolution/<run-id>/

Record:

- starting HEAD
- candidate identities
- gateway artifact identities
- runtime artifact identity
- client executable identities
- provider/model routes
- R0-R9 status
- repetition counters
- setup corrections
- task/workspace/attempt/checkpoint IDs
- tool-call IDs
- provider correlation IDs where available
- external-block classifications
- architecture decision
- compatibility readiness
- cleanup
- commit=false
- push=false

Never persist secret values.

============================================================
============================================================
R0 — RESOLUTION POLICY AND TAXONOMY FREEZE
============================================================
============================================================

Before any live execution, implement Resolution-only policy/schema.

Do NOT rewrite historical evidence.

Introduce explicit Resolution classifications including:

PASS
FAIL
BLOCKED
NOT_APPLICABLE
INELIGIBLE
EXTERNAL_PROVIDER_BLOCKED
SETUP_FAILURE
PROVENANCE_MISMATCH
EVIDENCE_OBSERVABILITY_FAILURE
EQUIVALENT_FOR_CURRENT_REQUIREMENTS

Every result must also record:

candidate_reached = true/false
provider_reached = true/false
client_reached = true/false

Separate:

A. Candidate Hard Gates

- protocol correctness attributable to candidate
- tool correlation
- tool execution semantics
- state/recovery
- duplicate-side-effect handling
- candidate provenance
- composition correctness
- OSS/license eligibility
- canonical-contract independence

B. Compatibility Readiness Gates

- provider reachability
- account/access availability
- Cloudflare/provider outage
- external client availability
- provider/client specific compatibility

============================================================
6. EXPLICIT T04 RESOLUTION POLICY AMENDMENT
============================================================

The original T04 remains:

OpenCode
→ Shofni
→ Gateway Candidate
→ RelayRouter chat
→ Shofni tool emulator
→ OpenCode executes tool

T04 is STILL mandatory for declaring:

FULL RelayRouter/OpenCode COMPATIBILITY READINESS.

However, Resolution Plan v1.1 explicitly changes architecture-selection
attribution:

If a fresh direct RelayRouter/OpenCode control proves failure BEFORE any
gateway candidate is reached due to:

- provider outage
- Cloudflare
- authentication/account
- provider routing
- provider access

then record:

status = BLOCKED
classification = EXTERNAL_PROVIDER_BLOCKED
candidate_reached = false

This does NOT make T04 PASS.

It means:

RelayRouter/OpenCode Compatibility Readiness = BLOCKED

but T04 does NOT count as a candidate-specific hard failure for Bifrost or
LiteLLM architecture selection.

If direct control succeeds and candidate-specific T04 subsequently fails:

candidate_reached = true

and that candidate receives a real mandatory T04 FAIL.

This policy amendment is explicit and Resolution-only.

Historical POC records remain unchanged.

============================================================
7. ENTRY GATES
============================================================

Record before live work:

Claude Code executable path/version
OpenCode executable path/version
Codex version if used by residual rows
Docker Desktop version/status
Docker Linux architecture
Windows host architecture
Python = 3.12.10
uv = 0.11.7 for locked OpenHands reconstruction
gateway artifact identities
ports allocated
A6api route availability
RelayRouter access readiness
credential presence only

A6API_KEY:

presence only.

Never print/hash/store the value.

Provider credentials remain gateway-side whenever architecture permits.

Docker environment forwarding:

--env A6API_KEY

Never inline the value into process command text.

============================================================
============================================================
R1 — OPENHANDS PROVENANCE RESOLUTION
============================================================
============================================================

Known evidence:

Phase 7 installed package inventory:
187 distributions

Phase 11:
232 distributions

Phase 7 is a strict subset of Phase 11 with 45 additions.

Source tree, Python, uv and lock identities match.

Historical Phase 7 selection metadata is incomplete.

------------------------------------------------------------
R1-A — FORENSIC RECONSTRUCTION
------------------------------------------------------------

Do NOT search arbitrarily until 187 appears.

Before building any environment:

derive and predeclare at most FOUR repository-justified configurations.

Each configuration must differ only on evidence-supported dimensions such as:

- workspace root vs project selection
- default groups
- explicit no-dev or group behavior
- workspace package selection
- extras supported by pyproject metadata

For every configuration record:

- exact cwd
- exact uv command
- exact environment variables
- project selection
- groups
- extras
- Python identity
- uv identity
- candidate tree
- lock hash
- complete installed name/version inventory
- package count
- normalized package inventory SHA-256
- runtime artifact/environment identity

A configuration may be classified:

RECONSTRUCTION_MATCH

only if the complete normalized package name/version set exactly matches the
historical 187 inventory.

Count equality alone is invalid.

IMPORTANT:

Even an exact 187 inventory match does NOT prove the missing historical
selection command.

Do not claim historical byte-identical provenance.

If exact reconstruction match occurs:

use it as a strong reconstruction candidate, but still create a fully
documented authoritative Resolution runtime identity before selection.

------------------------------------------------------------
R1-B — FORMAL OPENHANDS BASELINE V2
------------------------------------------------------------

If historical execution selection cannot be proven:

preserve Phase 7 as valid historical evidence but insufficiently reproducible.

Create:

OpenHands Resolution Baseline v2

from the SAME locked OpenHands candidate source.

Derive the minimum justified runtime surface from actual Shofni runtime imports,
workspace dependencies and lock graph.

Do not invent an SDK-only closure if repository dependencies require more.

Capture completely:

- source tree hash
- lock hash
- selected projects
- groups
- extras
- cwd
- exact sync/install command
- Python version/image digest
- uv version/image digest
- full installed inventory
- normalized inventory hash
- runtime image/artifact digest
- architecture
- environment variables excluding values
- dependency closure rationale

One build plus one setup-only correction allowed.

Then validate Baseline v2 with:

1. OpenHands lifecycle
2. T10
3. T11 crash-before side effect
4. T11 crash-after-side-effect-before-checkpoint

T10 must prove:

model A
→ real OpenHands action
→ persisted tool result
→ checkpoint
→ process exits
→ genuinely fresh process
→ same task
→ same workspace
→ new attempt
→ model B
→ final result

T11 must preserve the same operation_id across recovery and prove no duplicate
ledger side effect.

Normal deterministic regression coverage must remain offline.

Baseline v2 becomes authoritative only after all required runtime gates pass.

============================================================
8. LIVE STABILITY RULE
============================================================

Any live route whose PASS contributes directly to architecture selection must
use THREE fixed independent successful repetitions.

This is NOT retry-until-green.

The repetition count is predetermined.

A setup-only correction may occur once before the semantic repetition block.

If semantic repetition fails:

preserve the failure.

Do not restart the 3-run block to erase it.

One-shot evidence may be recorded but cannot establish stable selection PASS.

Deterministic local/fixture behavior used as stability evidence should have a
10/10 clean regression block where practical and relevant.

============================================================
============================================================
R2 — ACTUAL CLAUDE CODE T03
============================================================
============================================================

Authoritative path:

Claude Code
→ Anthropic Messages
→ Shofni canonical translation
→ Gateway Candidate
→ A6api OpenAI-compatible route
→ canonical response
→ Messages response
→ Claude Code

Required pairings:

Claude Code → Bifrost → A6api
Claude Code → LiteLLM → A6api

Do NOT use a raw HTTP harness as the authoritative T03 result.

The actual Claude Code executable must run.

Use identical:

- Claude Code version
- prompt
- tool schema
- fixture
- model
- timeout
- retry policy

Prefer validated A6api route:

gpt-5.4-mini

unless current route availability proves it unavailable.

If changed, create a new explicit route decision before execution.

PASS requires:

- actual Claude Code process started
- client identity recorded
- Messages request correlated
- Shofni canonical translation correlated
- gateway candidate correlated
- actual configured A6api OpenAI-compatible route correlated
- sanitized upstream provider-boundary observation
- provider/model identity observed
- valid tool schema
- one tool call
- stable tool-call ID
- tool executes exactly once
- tool result maps back
- Claude Code accepts returned event/schema
- valid stop semantics
- final response
- no invalid OpenAI fields leak into Claude events
- client never receives provider credential

Upstream observability must distinguish:

configured route

from:

observed outbound provider request

Gateway HTTP 200 alone is insufficient.

Do not persist authorization headers or secret-bearing wire captures.

Run THREE fixed semantic repetitions per gateway.

One setup-only correction may occur before repetitions.

============================================================
============================================================
R3 — ORIGINAL T04
============================================================
============================================================

Do NOT redefine T04.

Authoritative T04 remains:

OpenCode
→ Shofni
→ Gateway Candidate
→ RelayRouter chat
→ Shofni tool emulation
→ valid OpenCode tool call
→ OpenCode executes
→ result returns
→ final answer

------------------------------------------------------------
R3-A — DIRECT EXTERNAL CONTROL
------------------------------------------------------------

Perform exactly ONE fresh direct reachability/control attempt sufficient to
determine whether RelayRouter/OpenCode can currently reach the chat route.

No candidate attribution.

If blocked before a candidate exists:

record:

BLOCKED / EXTERNAL_PROVIDER_BLOCKED
candidate_reached=false

Preserve:

HTTP/provider/access classification
Cloudflare code if present
OpenCode version
provider route identity
timestamp
sanitized diagnostics

Do not expose credentials.

If R3-A is externally blocked:

DO NOT run Bifrost or LiteLLM T04.

Record both candidate T04 architecture-attribution rows as:

BLOCKED
EXTERNAL_PROVIDER_BLOCKED
candidate_reached=false

Compatibility readiness remains BLOCKED.

Candidate hard-gate selection does not treat this as candidate FAIL.

If R3-A succeeds:

continue to R3-B.

------------------------------------------------------------
R3-B — CANDIDATE T04
------------------------------------------------------------

Run:

OpenCode → Bifrost → RelayRouter
OpenCode → LiteLLM → RelayRouter

RelayRouter is chat-only.

Do not send an assumed native-tool contract.

Shofni owns emulation.

PASS requires:

- RelayRouter chat reached
- tool availability represented through emulation
- expected action selected
- Shofni parses action intent
- valid OpenCode tool call produced
- OpenCode executes exactly once
- tool result reinjected
- final answer
- no manual correction
- no duplicate execution

Run THREE fixed independent repetitions per gateway.

One setup-only correction allowed before the repetition block.

============================================================
============================================================
R4 — RESIDUAL LEVEL 2 RECONCILIATION
============================================================
============================================================

This phase is mandatory.

Build a canonical ledger for every applicable gateway row:

T01
T02
T03
T04
T05
T06
T07
T08
T09-A
T09-B
T12

for:

Bifrost
LiteLLM

For every row determine:

- current effective result
- historical attempts
- evidence path
- provider/client
- live vs fixture
- candidate_reached
- unresolved reason
- whether candidate-controlled
- whether externally blocked
- whether rerun is required

Do not rerun rows already deterministically settled unless the new authoritative
baseline/policy makes the old evidence unusable.

For residual candidate-controlled mandatory failures or missing evidence:

run only the minimum required targeted scenario.

For provider-specific RelayRouter rows:

apply the same external attribution rule established in R0/R3.

Do not convert external blocking into PASS.

After all rows are reconciled:

regenerate T12.

T12 must clearly separate:

Architecture Candidate Eligibility

from:

Compatibility Readiness

and expose:

native tools
emulated tools
streaming
sequential continuation
fallback
effective capability
provider/client readiness
candidate attribution
evidence
timestamp

============================================================
============================================================
R5 — MASTRA FINAL OSS DISPOSITION
============================================================
============================================================

Do NOT rerun Mastra.

Do NOT use EE code.

Historical record remains:

BLOCKED / LICENSE_BOUNDARY_BLOCKER

Resolution-only eligibility disposition becomes:

INELIGIBLE_FOR_CURRENT_OSS_RUNTIME_SELECTION

because the exact pinned durable Agent closure requires separately licensed EE
source and no permitted OSS path satisfied the required semantics.

Do not rewrite historical Phase 8 evidence.

Record T10/T11 for Mastra in Resolution selection view as:

NOT_RUN_DUE_TO_INELIGIBILITY

not PASS
not semantic FAIL

Mastra as a project is NOT permanently rejected.

A future version/new candidate is a separate future POC.

Mastra ineligibility does not itself make OpenHands PASS.

============================================================
============================================================
R6 — AUTHORITATIVE COMPOSITION
============================================================
============================================================

Run only after OpenHands authoritative Baseline v2 is valid.

Required candidate pairs:

Bifrost + OpenHands
LiteLLM + OpenHands

Each composition must contain TWO clearly separate subcases.

------------------------------------------------------------
R6-A — NATIVE LEVEL 2 CLIENT-OWNED SUBCASE
------------------------------------------------------------

Prove:

ToolExecutionBackend = CLIENT

Flow:

client request
→ Shofni Level 2
→ selected gateway
→ A6api
→ structured native tool request
→ client-side executor
→ result
→ gateway/provider continuation

Assertions:

- actual gateway path
- no direct provider bypass
- gateway does NOT execute the local tool
- runtime backend does NOT execute the Level 2 client-owned tool
- stable correlation
- exactly one client execution
- final response

------------------------------------------------------------
R6-B — LEVEL 3 RUNTIME-OWNED CONTINUATION
------------------------------------------------------------

Prove:

ToolExecutionBackend = RUNTIME

Flow:

OpenHands
→ selected gateway
→ A6api model A
→ real structured read_fixture action
→ RuntimeBackend executes once
→ exact result
→ result through gateway/provider
→ checkpoint
→ runtime exits
→ process exit proven
→ fresh runtime process
→ same Shofni task_id
→ same workspace_id
→ explicit new attempt_id
→ prior result preserved
→ same gateway
→ model B
→ final result

Assertions:

- Baseline v2 identity
- gateway identity
- provider/model route
- no OpenHands → A6api bypass
- runtime owns Level 3 tool execution
- gateway owns no local tool execution
- exactly one execution
- stable tool-call correlation
- checkpoint lineage
- fresh-process proof
- task continuity
- workspace continuity
- model A → B transition
- final expected marker
- zero duplicate side effect

Capture sanitized provider-boundary observability.

Windows Docker:

use explicit:

--mount type=bind,source=...,target=...

Use gateway DNS/internal ports inside Docker networks.

One diagnostics-captured setup correction is allowed before semantic repetitions.

Run THREE fixed independent successful semantic repetitions per gateway
composition.

Do not restart the repetition block to erase failures.

============================================================
============================================================
R7 — GATEWAY SELECTION
============================================================
============================================================

A gateway is architecture-eligible only if:

- provenance valid
- every candidate-controlled mandatory applicable Level 2 row is deterministic
- no unexplained critical protocol corruption
- no undetected repeated completed side effect
- canonical Shofni contracts remain backend-independent
- license/distribution viable
- required custom Shofni code understood
- required composition evidence passes

External provider blocks with:

candidate_reached=false

remain Compatibility Readiness blockers but are not candidate FAIL.

If only one candidate is eligible:

select it.

If both are eligible:

apply evidence-backed lexicographic tie-break:

1. less candidate-specific Shofni adapter code
2. fewer compatibility workarounds
3. simpler build/runtime dependency chain
4. simpler startup/configuration
5. easier failure diagnosis
6. cleaner Windows developer workflow
7. smaller operational footprint
8. licensing simplicity
9. easier candidate replacement
10. maintenance evidence already captured

Do NOT invent numeric scores.

For every criterion:

candidate A advantage
candidate B advantage
or TIE

with evidence.

If all meaningful criteria remain tied:

Resolution v1.1 explicitly authorizes:

EQUIVALENT_FOR_CURRENT_REQUIREMENTS

This is NOT a forced winner.

Do not arbitrarily choose one.

If later implementation requires one concrete default despite equivalence,
record a reversible implementation preference separately from architecture
eligibility.

============================================================
============================================================
R8 — FINAL DECISION SURFACES
============================================================
============================================================

Produce:

A. Architecture Selection

Gateway:
SELECTED / EQUIVALENT_FOR_CURRENT_REQUIREMENTS / NO_DECISION_YET

Runtime:
SELECTED / NO_DECISION_YET

Composition:
SELECTED / EQUIVALENT_FOR_CURRENT_REQUIREMENTS / NO_DECISION_YET

B. Compatibility Readiness

Classify independently:

A6api
RelayRouter
Codex
Claude Code
OpenCode

Use tuple-level detail where needed:

provider
client
protocol
route
capability

Possible readiness statuses:

READY
PARTIAL
BLOCKED_EXTERNAL_PROVIDER
UNSUPPORTED
FAILED_COMPATIBILITY
UNVERIFIED

Do not call an externally blocked route READY.

Do not convert compatibility failure into candidate PASS.

============================================================
9. RUNTIME SELECTION RULE
============================================================

Mastra is currently:

INELIGIBLE_FOR_CURRENT_OSS_RUNTIME_SELECTION

OpenHands may be selected only if:

- authoritative Baseline v2 exists
- lifecycle passes
- T10 passes
- T11 passes
- required composition passes
- evidence/provenance is valid

Mastra's ineligibility is not itself proof that OpenHands succeeds.

============================================================
============================================================
R9 — FINAL EVIDENCE AND CLOSURE
============================================================
============================================================

Create/update:

docs/poc/poc-resolution-results.md
docs/poc/final-backend-selection.md
docs/poc/final-runtime-selection.md
docs/poc/final-compatibility-readiness.md

Machine evidence:

tests/poc/evidence/resolution/<run-id>/

Run manifest:

poc/runs/resolution-<run-id>/manifest.json

If Architecture Selection reaches an accepted selection/equivalence state:

create:

docs/poc/implementation-plan.md

PLANNING ONLY.

Do not start Production implementation.

============================================================
10. EVIDENCE VALIDATION
============================================================

Validate:

- all JSON
- all NDJSON
- all references
- run IDs
- candidate identities
- artifact identities
- provider/client correlations
- task/workspace/attempt/checkpoint lineage
- tool-call correlation
- repetition counts
- setup corrections
- external-block attribution
- skipped/ineligible taxonomy
- final decision inputs

No broken mandatory evidence references.

============================================================
11. SECURITY
============================================================

Permanent evidence must contain:

zero API key values
zero credential hashes
zero Authorization headers
zero cookies
zero private absolute user paths
zero raw secret-bearing provider captures

Raw transient evidence only under:

poc/.runtime/raw-evidence/

Delete after sanitized canonical evidence exists.

Credential presence only.

============================================================
12. FINAL TESTING
============================================================

Run full:

.\.venv\Scripts\python.exe -m pytest tests/poc

Normal suite must remain offline.

Add minimal regression tests for:

Resolution taxonomy
external provider attribution
candidate_reached semantics
tie rule
Baseline v2 manifest validation
upstream observability redaction
Level 2 CLIENT ownership
Level 3 RUNTIME ownership
composition topology enforcement
T12 architecture/readiness split

Where deterministic fixture stability is claimed:

run a fixed 10/10 block.

============================================================
13. PROVENANCE REVALIDATION
============================================================

At end verify all four original candidate tree identities still match Phase 0.

No candidate source mutation.

Verify all built disposable artifacts have recorded hashes/digests.

============================================================
14. CLEANUP
============================================================

Remove only Resolution-created transient:

containers
networks
ports/listeners
temporary provider configs
runtime roots
raw evidence

Do not remove historical committed evidence.

Do not delete pre-existing unrelated runtime state.

============================================================
15. GIT BOUNDARY
============================================================

At end:

git diff --check must pass

nothing staged

DO NOT commit.
DO NOT push.

Expected repository HEAD remains:

3b59332e76abcae7c50f4374ff63e80b60296195

unless legitimate newer work already existed before starting.

============================================================
16. FINAL DECISION RULE
============================================================

Architecture may end as:

SELECTED
EQUIVALENT_FOR_CURRENT_REQUIREMENTS
NO_DECISION_YET

NO_DECISION_YET is allowed only if candidate-controlled mandatory architecture
evidence remains unresolved or failed, or the authorized selection policy still
cannot distinguish eligible candidates.

A provider outage occurring before candidate execution is NOT by itself enough
to force architecture NO_DECISION_YET under Resolution v1.1.

It remains a Compatibility Readiness blocker.

============================================================
17. FINAL REPORT
============================================================

Report:

1. Starting repository state.

2. R0 taxonomy/policy.

3. R1:
   forensic configurations
   reconstruction result
   Baseline v2 identity
   lifecycle
   T10
   T11

4. R2:
   actual Claude Code identity
   Bifrost T03 repetitions
   LiteLLM T03 repetitions
   provider-route evidence
   client acceptance

5. R3:
   RelayRouter direct control
   external attribution
   Bifrost T04 if executed
   LiteLLM T04 if executed

6. R4:
   full T01-T09/T12 reconciliation
   residual reruns
   regenerated T12

7. R5:
   Mastra historical status
   Resolution eligibility status

8. R6:
   Bifrost + OpenHands
   LiteLLM + OpenHands
   native Level 2 CLIENT subcase
   Level 3 RUNTIME subcase
   repetition results

9. R7:
   gateway eligibility
   tie-break evidence
   selection/equivalence/no-decision

10. R8:
    Gateway Architecture Selection
    Runtime Architecture Selection
    Composition Selection
    A6api readiness
    RelayRouter readiness
    Codex readiness
    Claude Code readiness
    OpenCode readiness

11. R9:
    final artifacts
    implementation-plan status

12. Tests and deterministic repetitions.

13. Candidate/artifact provenance.

14. Security/redaction.

15. Cleanup.

16. Git state.

17. Explicit confirmations:

- Level 2 remains CLIENT
- Level 3 remains RUNTIME
- historical evidence preserved
- no candidate source modified
- no Mastra EE used
- no OpenRouter
- no retry-until-green
- external provider blocks not misattributed to candidates
- no forced winner
- no Production implementation
- no commit
- no push

STOP after Resolution closure.
