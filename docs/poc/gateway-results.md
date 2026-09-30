# Gateway Results

This report records candidate-specific evidence independently and does not rank candidates or select a winner.

## Bifrost

- Current setup: **PASS**; current artifact: `sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5`.
- Source identity: `sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe` (5172 included files).
- Artifact identity: `{"artifact_sha256": "sha256:22e3f48c7e9dcaff1ae68c18f5281cc0e771c000bf99e54f8d9c28c62e4adac5", "candidate_tree_hash": "sha256:df94a64815001fc9af685dd4f7f06b0609a7eff57a092b10dcd61ed0b1e38efe", "go_toolchain_image": "docker.io/library/golang:1.27.0-bookworm@sha256:ba5ef6614ca131b80a635fc6a7b715d9ee8a7f333debdbb81afb68259c7d48d4"}`.
- Historical setup attempts: phase3-20260930T150128Z=BLOCKED, phase3-remediation-20260930T172952Z=BLOCKED, phase3-remediation-20260930T173130Z=BLOCKED, phase3-remediation-20260930T174700Z=BLOCKED, phase3-remediation-20260930T180300Z=FAIL, phase3-remediation-20260930T180800Z=PASS.
- Current live Phase 5 observations: see `level2-remediation-20260930T225100Z`; current report status is `PARTIAL`.
- License boundary: Apache-2.0; LICENSE

## LiteLLM

- Current setup: **PASS**; current artifact: `sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280`.
- Source identity: `sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb` (12075 included files).
- Artifact identity: `{"candidate_tree_hash": "sha256:3493d676d2c162b05d4962939eb7183648a277ecadd9f58613964c6881616ffb", "python_base_image": "docker.io/library/python:3.13.7-slim-bookworm@sha256:781449467ffb6f04218f09b1ecdcdc7d22b289ee5da9ec498b024e24ad7a6db7", "runtime_image_digest": "sha256:36fd553758eb8a79c858d1be08a43dabe390e8e003dcb71f3e98ba9a605da280", "rust_build_image": "docker.io/library/rust:1.88.0-bookworm@sha256:4727898c104ecd2e22d780925832502faee9fe4e70581b8572af081370b315a0", "uv_image": "ghcr.io/astral-sh/uv:0.11.7@sha256:733b4042187702f832f7fdecb3aff14a61b288c4ca37af188bb5715c1caebaf8", "wheel_sha256": "sha256:762b286fe81491f242040b14f28338da0ebf4f32fea50972b6969ee578011d52"}`.
- Historical setup attempts: phase4-20260930T150128Z=BLOCKED, phase4-remediation-20260930T190000Z=BLOCKED, phase4-remediation-20260930T190500Z=BLOCKED, phase4-remediation-20260930T191000Z=FAIL, phase4-remediation-20260930T191500Z=FAIL, phase4-remediation-20260930T192000Z=PASS.
- Current live Phase 5 observations: see `level2-remediation-20260930T225100Z`; current report status is `PARTIAL`.
- License boundary: MIT outside enterprise/; root LICENSE

## Operational observations

The current run used three repetitions per authorized live pairing. Cleanup evidence records container removal, network removal, port release, and temporary configuration removal. No secret values are persisted.

Phase 2 synthetic fixture controls are reported separately and do not establish gateway support.
