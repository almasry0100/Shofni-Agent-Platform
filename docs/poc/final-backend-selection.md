# Final Backend Selection

**Decision: `NO_DECISION_YET`.** Neither Bifrost nor LiteLLM has complete mandatory candidate evidence for selection. No winner, tie-break, or equivalence claim is made.

The corrected R4/T12 ledger marks both candidates `NO_DECISION_YET`. Each of the three fixed Claude Code T03 runs per gateway ended with a client process failure and no emitted event. The route-list probe succeeded, but the T03 request itself was not correlated to a gateway response or outbound A6api request. The six client failures remain recorded; they are not attributed to either gateway. See [R2 attribution correction](../../tests/poc/evidence/resolution/20261001T180545Z/r2/attribution-correction.json) and the [corrected T12 report](../../tests/poc/evidence/resolution/20261001T180545Z/r4/t12-report-r2-attribution-corrected.json).

The R6 Bifrost + OpenHands and LiteLLM + OpenHands repetitions passed their semantic CLIENT and RUNTIME checks, but both compositions remain `PARTIAL`: direct outbound provider HTTP was not observed. That required composition evidence is incomplete.

The RelayRouter/OpenCode external block is excluded from candidate failure under Resolution v1.1. The single direct control timed out without a provider response; the timeout's external cause is unverified. Candidate T04 was skipped for both gateways.

No numeric scores were assigned. The lexicographic tie-break was not applied because the eligibility gate did not pass. The fixed repetitions are complete and will not be rerun in this Resolution run.

Level 2 ownership remains `CLIENT`. Candidate identities remain pinned to [candidate-lock.json](candidate-lock.json); all candidate source trees remain read-only.
