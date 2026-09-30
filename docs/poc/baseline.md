# Phase 0 Baseline / Guardrails

**Captured:** 2026-09-30 (UTC)
**Execution boundary:** Phase 0 only
**Status:** PARTIAL; Bifrost local-source-equivalent startup is BLOCKED.

## Shofni repository baseline

- Actual Git root: `<WORKSPACE_PARENT>/Shofni Agent Platform`
- Branch: `main`
- HEAD: `dffb376b44c806995669acd57a76a5a5fd572230`
- Starting `git status --short --branch`: `## main` (clean)
- The opened `<WORKSPACE_PARENT>` directory is a container, not the Git root.
- No user changes were present at the start. Candidate and reference source trees were inspected read-only.

## Current host toolchain

Refreshed from the restarted Codex process on 2026-09-30 (UTC). Where this
snapshot differs from the initial Phase 0 capture, the earlier result describes
the prior Codex process environment; current availability is based only on this
process.

| Component | Availability / version |
|---|---|
| OS | Microsoft Windows 11 Enterprise, 10.0.26200, AMD64 |
| PowerShell | 7.6.5 (current shell) |
| Python | `python` is Python 3.12.10; `py -3.12` is Python 3.12.10 |
| pip | `pip` and `py -3.12 -m pip` are available; both report pip 25.0.1 for Python 3.12 |
| uv | Unavailable |
| Node.js | v24.19.0 |
| npm | 11.17.0 |
| pnpm | 11.25.0 |
| Go | Unavailable |
| Docker CLI | 29.8.1, build 4a63305 |
| Docker daemon | Available; server 29.8.1 |
| Git | 2.55.0.windows.5 |
| GitHub CLI (`gh`) | 2.101.0 (2026-09-15) |
| Codex CLI | 0.159.0 |
| Claude Code | 2.1.278 |
| OpenCode | 1.18.33 |

No missing tool was installed. The older sanitized readiness snapshot in `docs/05-client-readiness.json` is historical; this table records the current checks for this Phase 0 run.

## Local ports

Read-only listener inspection found port 3000 in use by Windows/Docker relay processes. The candidate-relevant default ports checked were free: Bifrost 8080, LiteLLM 4000, Mastra test port 4111, and 3001, 8000, 8081, 8787, 9000, 5432, and 6379. OpenHands uses an in-process SDK/local workspace for the minimum planned surface; Mastra's POC server port remains configurable and must be checked again when a concrete launch shape is chosen. Do not assume 3000 is available.

## Credentials

Only environment-variable presence was tested; values were not read, printed, copied, or persisted. Process and readable User scope were checked separately in the restarted Codex process.

| Variable | Process scope | User scope |
|---|---|---|
| `A6API_KEY` | PRESENT | PRESENT |
| `RELAYROUTER_API_KEY` | PRESENT | PRESENT |

The initial Phase 0 capture recorded `RELAYROUTER_API_KEY` as missing in the prior Codex process. It is present in both Process and readable User scope in this restarted process, so that prior environment-absence blocker no longer applies here. Presence alone does not verify credential validity. No credential remediation was attempted.

## Candidate roots and provenance

All four primary roots and the three reference roots exist as sibling extracted trees. None of the four primary candidates has `.git` metadata. No commit SHA is assigned to an extracted tree. See `candidate-lock.json` for tree hashes, manifests, license boundaries, artifact identities, and per-candidate provenance status.

| Candidate | Root | `.git` | Phase 0 provenance |
|---|---|---:|---|
| Bifrost | `<WORKSPACE_PARENT>/bifrost-dev` | No | BLOCKED for execution of the inspected local core/plugin source; the checked-in transport build resolves published modules |
| LiteLLM | `<WORKSPACE_PARENT>/litellm-main` | No | PARTIAL; source/package version and locks identified; built package digest not selected |
| OpenHands Software Agent SDK | `<WORKSPACE_PARENT>/software-agent-sdk-main` | No | PARTIAL; source/package version and UV lock identified; built package digest not selected |
| Mastra | `<WORKSPACE_PARENT>/mastra-main` | No | PARTIAL; core/workspace/lock identity identified; built package digest not selected |

Reference-only roots `pydantic-ai-main`, `langgraph-main`, and `temporal-main` were not modified. No candidate was installed, built, or started.

### Bifrost source versus execution

The Bifrost root has neither `go.mod` nor `go.work`. `transports/go.mod` exists and has no `replace` directives. It requires published `github.com/maximhq/bifrost/core v1.10.2`, `framework v1.7.4`, and versioned plugin modules; its `go.sum` records module checksums. Local `core/go.mod` and `framework/go.mod` exist as separate modules but are not wired into the transport module. `transports/Dockerfile` copies and builds the transport module and downloads its declared modules; it does not copy the sibling local core/framework/plugin source into the Go build. `transports/bifrost-http/main.go` describes the HTTP server and default port 8080.

Therefore path A (local transport plus published core/framework/plugins) is distinct from path B (execution using the inspected local core/plugin source). A is not evidence for B. No external Go workspace/configuration has been validated, and Go is unavailable on this host. **`BIFROST_EXECUTION_PROVENANCE = BLOCKED`** until a reproducible local-source-equivalent build path is established without editing Bifrost, or the POC explicitly selects and pins a different source/artifact identity. The candidate must not be silently substituted with the published dependency graph.

### LiteLLM source and artifact

The inspected `pyproject.toml` declares LiteLLM 1.104.0, Python `>=3.10,<3.15`, and a Maturin build backend for its Rust/Python extension. Relevant locks are `uv.lock` and `litellm-rust/Cargo.lock`; both are hashed in `candidate-lock.json`. The open-source license boundary is MIT outside `enterprise/`; the enterprise tree and `litellm/proxy/enterprise/` remain excluded. The source lock and local tree identify this extracted source, but no wheel/image digest has been selected. Before Phase 4 startup, pin the source tree/revision and exact built wheel or image digest and verify its provenance; do not use a floating PyPI version. The historical PyPI incident involving 1.82.7/1.82.8 does not establish that this inspected 1.104.0 source is compromised.

### Runtime source and minimum surface

- OpenHands declares `openhands-sdk` 1.49.6 and Python `>=3.12` in its UV workspace. The minimum likely RuntimeBackend surface is `openhands-sdk` plus `openhands-workspace` for controlled local workspace operations; add `openhands-tools` only if the chosen fixture requires its bundled tools. Pin the built artifact(s) before startup.
- Mastra's root workspace version is 0.1.11; the relevant `@mastra/core` package declares 1.72.0-alpha.8. The repository is a pnpm/Turbo workspace with pnpm lockfile version 9. The minimum likely surface is `@mastra/core` plus the internal workspace packages required by its dependency graph and filesystem storage. Exclude `ee/`. The workspace package manager declaration is pnpm 11.21.0 with an integrity-qualified version; the host currently has pnpm 11.25.0. Pin the exact source/workspace and produced package/artifact before startup.

## Test runner

No existing Shofni test/build runner or tests were found. The sole POC-local strategy is Python 3.12 with pytest; see `test-runner.md`. Phase 0 did not install or bootstrap it.

## Evidence and redaction baseline

- Permanent sanitized evidence: `tests/poc/evidence/`.
- Raw/debug evidence: `poc/.runtime/raw-evidence/`; transient, gitignored, never committed, and deleted after sanitized evidence validation.
- The raw-evidence ignore rule is present in the repository `.gitignore`. No raw directory or provider capture was created.
- Redact header names/values for Authorization, bearer tokens, and `x-api-key`; provider API keys and credential-like environment values; cookies; secret query parameters; GitHub tokens; and private user paths. Record credential presence only.
- No live or synthetic evidence was generated in Phase 0. `poc/evidence/schema.json` is a schema definition only.

## Phase boundary and blockers

Phase 0 outputs and validation are the only work in scope. Phase 1 implementation has not started. Before any candidate startup, require an exact executable/package/image/module pin and digest. Bifrost's local-source-equivalent execution is blocked as stated above. RelayRouter live subcases may proceed past the prior missing-variable condition only if the relevant later-phase checks confirm the credential is valid. Missing Go and uv are host constraints, not install requests; GitHub CLI is available in the restarted process. The POC runner is not to be bootstrapped until Phase 1.

Confirmed for this run: no dependency installs/upgrades, no live provider calls, no candidate/reference writes, no candidate startup, no credential values read/printed/persisted, no commit/push/history rewrite, and no Phase 1 code.
