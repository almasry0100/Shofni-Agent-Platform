# Final Runtime Selection

**Decision: `NO_DECISION_YET`.** OpenHands is not selected because its required Level 2 + Level 3 composition remains partial. Mastra is ineligible for the current OSS runtime selection under the exact pinned source and license boundary.

OpenHands Resolution Baseline v2 passed lifecycle, T10, and both T11 crash-boundary cases. T10 preserved task and workspace identity across a genuinely fresh process, changed from model A `gpt-5.4-mini` to model B `gpt-5.5`, and returned the expected `alpha` marker. T11 preserved one logical operation across crash-before-append and crash-after-append-before-checkpoint boundaries.

R6 ran three fixed Level 2 `CLIENT` and three fixed Level 3 `RUNTIME` repetitions for each gateway. All 12 semantic subcases passed, including gateway routing, one client/runtime tool execution, persisted result, checkpoint lineage, fresh-process restore, task/workspace continuity, model A-to-B continuation, and final result. Direct outbound provider HTTP telemetry was absent for both pairings, so R6 does not satisfy the complete composition gate.

Mastra's historical result remains `BLOCKED / LICENSE_BOUNDARY_BLOCKER`. The Resolution disposition is `INELIGIBLE_FOR_CURRENT_OSS_RUNTIME_SELECTION`; T10 and T11 are `NOT_RUN_DUE_TO_INELIGIBILITY`. No EE source, patched or stubbed import, or prebuilt artifact containing the EE closure was used. This is not a permanent rejection of a future Mastra version or candidate.

The Level 3 ownership boundary remains `RUNTIME`. No implementation plan was created because the architecture selection gate did not produce a selection or equivalence result.
