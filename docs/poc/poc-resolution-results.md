# Shofni POC Resolution Results

## Run and Baseline

- Run: `resolution-20261001T180545Z`
- Repository: nested checkout `Shofni Agent Platform`
- Starting branch: `main`
- Starting HEAD and `origin/main`: `3b59332e76abcae7c50f4374ff63e80b60296195`
- Baseline commit remains in history; no commit or push was made.
- Initial status contained only the authorized untracked plan. Nothing was staged; tracked files were clean. Initial `git diff --check` passed.
- Baseline command: `.\.venv\Scripts\python.exe -m pytest tests/poc`; 81 passed.
- Plan: `docs/poc/poc-resolution-plan-v1.1.md`, `UNTRACKED`.
- Starting plan SHA-256: `09844BA74273E7D63756B60CFDB468BD5E8B1BE5CD3DC37819F9B1C1A8071CB7`.

## R0 Policy

Resolution outcomes preserve pass, fail, blocked, ineligible, not-applicable, setup, provenance, observability, external-provider, and equivalence distinctions. Each execution result records candidate, provider, and client reach separately. Level 2 remains `CLIENT`; Level 3 remains `RUNTIME`. Candidate failure and compatibility readiness are separate decision surfaces.

## R1 OpenHands Provenance

Phase 7 had 187 distributions and Phase 11 had 232. Selection metadata was incomplete, so count equality was not used as provenance and no arbitrary reconstruction builds were attempted. Four repository-justified configurations were predeclared; the formal Baseline v2 path was used.

Baseline v2: OpenHands SDK `1.49.6`, tree hash `sha256:e1258a81a1304726a1622943078907b689fccc524d733838fd57e10665ebd468`, lock hash `sha256:58c8b04e867891f3d7671bb0c34e459d5de5fa61fb25e3c10f63ec57b1bdd02e`, `uv sync --locked --package openhands-sdk --no-dev --no-editable --python 3.12`, Python `3.12.10`, uv `0.11.7`, 126 installed distributions, normalized inventory hash `sha256:302931e4646e0367463da771be4ddc2405417b624b05a0b8b15e3717bc85a22c`, and Linux/amd64 image digest `sha256:e50309a5aa33a619636deed2c0361a89937860ef3a7fa1a957638b4839ee13e4`. One setup-only correction copied the locked source into a run-owned writable snapshot; no semantic retry was counted.

Lifecycle passed. T10 passed model A action, result persistence, checkpoint, process exit, fresh-process restore, same task/workspace, new attempt, model B continuation, and final `alpha`. T11 passed both crash boundaries; each preserved one logical ledger result and the same operation ID, with duplicate suppression after durable append.

## R2 Claude Code T03

Actual Claude Code `2.1.278` was run three times per gateway against configured A6api `gpt-5.4-mini` route. All six processes exited with client failure, with no tool or result event. The separate model-list probes passed. No request-level gateway status/log correlation or outbound provider request was observed.

An evidence correction records that the model-list probe does not prove the T03 request reached a candidate. The six client failures remain unchanged, `candidate_reached=false`, `provider_reached=false`, and client attribution is `EVIDENCE_OBSERVABILITY_FAILURE`. No live retry was performed.

## R3 OpenCode T04

OpenCode `1.18.33` performed exactly one direct RelayRouter control. It timed out after 240 seconds without an HTTP/provider response. The Resolution record is `BLOCKED / EXTERNAL_PROVIDER_BLOCKED`, `candidate_reached=false`; no Cloudflare code or provider response was observed, so the timeout's cause is unverified. Bifrost and LiteLLM T04 pairings were skipped. Earlier failed historical RelayRouter attempts remain preserved and are not candidate failures under the Resolution attribution rule.

## R4 Level 2 Reconciliation

The canonical ledger contains 26 T01-T09 rows, including 10 candidate-neutral fixture rows, plus two T12 report rows. Historical attempts are preserved. The corrected T12 report marks both gateway selections `NO_DECISION_YET`; Claude Code T03 is an unresolved observability blocker. RelayRouter/OpenCode T04/T07/T08 are `BLOCKED_EXTERNAL_PROVIDER`, `candidate_reached=false`. Current tuple readiness is A6api/Codex `READY`, A6api/OpenCode `READY`, A6api/Claude Code `PARTIAL`, and RelayRouter/OpenCode `BLOCKED_EXTERNAL_PROVIDER`.

## R5 Mastra

Historical status remains `BLOCKED / LICENSE_BOUNDARY_BLOCKER`. Current OSS runtime selection disposition is `INELIGIBLE_FOR_CURRENT_OSS_RUNTIME_SELECTION`. T10/T11 were not run because of ineligibility. No Mastra EE source or artifact was used; this is not a permanent rejection of a future candidate.

## R6 Authoritative Composition

For each gateway, three Level 2 `CLIENT` repetitions and three Level 3 `RUNTIME` repetitions completed. All semantic subcases passed. Level 2 used the gateway, with exactly one client execution and no candidate/runtime tool execution. Level 3 used OpenHands through the gateway, preserved one `read_fixture` result, task/workspace/checkpoint lineage, exited the model A process, restored in a fresh process under model B, and returned `alpha`; direct provider bypass was false.

Both composition records remain `PARTIAL`: outbound A6api HTTP telemetry was not observed. The fixed blocks were not restarted. One documented Windows bind-mount setup correction was applied before semantic repetitions for each gateway.

## R7-R8 Decisions

Gateway: `NO_DECISION_YET`. Runtime: `NO_DECISION_YET`. Composition: `NO_DECISION_YET`. Neither gateway reached eligibility, so the lexicographic tie-break was not applied and equivalence was not claimed. OpenHands cannot be selected until a required composition fully passes. The compatibility readiness matrix is in [final-compatibility-readiness.md](final-compatibility-readiness.md).

## R9 Artifacts and Implementation Planning

Created the canonical ledger and corrected T12 revision, Mastra disposition, gateway decision, and final readiness surfaces, plus this report. The earlier generated R4 ledger/T12 files remain preserved and are marked superseded by an evidence record. `docs/poc/implementation-plan.md` was not created because the selection gate did not pass.

## Tests and Provenance

- Baseline suite: 81 passed.
- Focused Resolution group: 7 passed.
- Final full suite: 88 passed (`.\.venv\Scripts\python.exe -m pytest tests/poc`). The focused Resolution group passed 7 tests.
- Candidate source trees were not modified. Final tree revalidation matched all four locked identities and artifact revalidation matched the recorded Bifrost binary and LiteLLM wheel hashes. The Mastra tree required the Windows extended-length path form because one snapshot descendant could not be traversed through the ordinary path form; its locked hash and file count still matched. The OpenHands Baseline v2 runtime image digest is recorded in the R1 manifest.
- Candidate/build identities: Bifrost tree `sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe`; Bifrost artifact `sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5`; LiteLLM tree `sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb`; LiteLLM artifact `sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280`; LiteLLM wheel `sha256:762b286fe81491f242040b14f28338da0ebf4f32fea50972b6969ee578011d52`; OpenHands tree `sha256:e1258a81a1304726a1622943078907b689fccc524d733838fd57e10665ebd468`; OpenHands runtime image `sha256:e50309a5aa33a619636deed2c0361a89937860ef3a7fa1a957638b4839ee13e4`; Mastra tree `sha256:2f31743b5591fe158903bc50c4cd6886153d754d01ffd8627906eb23ad605d05`.

## Security and Cleanup

Credential reporting is presence-only. Permanent evidence contains sanitized diagnostics and no persisted credential values or credential hashes. No OpenRouter route or provider was introduced. R2 temporary directories, all named run containers/networks/images, and recorded listeners were verified absent.

The execution-time cleanup attempt was `BLOCKED_BY_EXECUTION_POLICY`; that historical result remains preserved in the [R6 cleanup verification](../../tests/poc/evidence/resolution/20261001T180545Z/r6/cleanup-verification.json). The user subsequently removed the exact run-owned `poc/.runtime/resolution-20261001T180545Z` tree. Final ownership-scoped verification found no run-owned runtime root, raw evidence, temporary configuration, container, network, temporary image, or listener. Final cleanup is therefore `PASS_AFTER_USER_MANUAL_REMOVAL`. See the [R9 cleanup closure](../../tests/poc/evidence/resolution/20261001T180545Z/r9/cleanup-closure.json).

## Git and Plan Integrity

Final branch remains `main`; HEAD and `origin/main` remain the baseline commit. Nothing is staged. No commit or push was made. Resolution outputs and the protected untracked plan are expected working-tree changes. Final `git diff --check` passed. All 59 resolution JSON files parsed, all 4,390 `evidence_refs` entries resolved, the permanent-evidence redaction scan passed, and the protected plan hash matched its starting value.

The starting plan hash above is the integrity reference. The final hash is `09844BA74273E7D63756B60CFDB468BD5E8B1BE5CD3DC37819F9B1C1A8071CB7`; the plan remains `UNTRACKED` and unchanged.

## Confirmations

- Level 2 remains `CLIENT`; Level 3 remains `RUNTIME`.
- Historical evidence and failed repetitions were preserved.
- No candidate source was modified or silently upgraded.
- No Mastra EE, OpenRouter, new provider, production implementation, commit, or push was used.
- Retry and repetition budgets were respected; there was no retry-until-green.
- External blocks were not converted to candidate passes or failures.
- No architecture winner was forced; nothing was staged.
