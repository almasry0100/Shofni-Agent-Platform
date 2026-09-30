# Phase 0 Test Runner Decision

**Decision:** No established Shofni runner exists. Use exactly one Shofni-local POC runner: Python 3.12 with pytest.

## Evidence

The Shofni Git root contains documentation, `.env.example`, `.gitignore`, and `LICENSE`; it has no `pyproject.toml`, `package.json`, Python/JavaScript lockfile, pytest/Vitest/Jest configuration, Makefile, `scripts/`, `tests/`, or GitHub Actions workflow. No current test or build command is established. The candidate repositories' own runners do not count as a Shofni runner.

## Rationale and use

Python 3.12 is the declared baseline in the client readiness material and is currently installed. Pytest is a small, widely used runner for Phase 1 contract and redaction tests and Phase 2 deterministic fixtures. One runner can exercise schemas, normalization, subprocess adapters, and offline scenario suites without coupling Shofni's public contracts to a candidate framework.

Python candidate adapters can be imported or launched as child processes. TypeScript candidate adapters can run as child processes and exchange versioned JSON over stdin/stdout or local HTTP. Pytest owns the cross-language assertions and evidence checks; candidate repositories do not receive separate Shofni harnesses.

## Phase 1 bootstrap requirements

1. Create one Shofni-local virtual environment with the installed Python 3.12 runtime.
2. Add a Shofni POC `pyproject.toml`/lock or equivalent exact pytest pin and pytest configuration.
3. Install only the pinned test-runner dependency into the Shofni environment after the Phase 1 bootstrap is authorized; do not install it into candidate trees.
4. Use the invocation shape `py -3.12 -m pytest tests/poc` and record its exact version and exit code in the run manifest.
5. Keep Python and TypeScript candidate communication behind a subprocess or protocol boundary so both use the same scenarios and assertions.

No runner was installed, bootstrapped, or executed during Phase 0. No candidate-specific test harness was selected.
