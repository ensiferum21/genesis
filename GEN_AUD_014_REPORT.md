# Genesis Batch 1 — GEN-AUD-014 freshness gate repair (DEV only)

Timestamp (UTC): 2026-10-08T17:38:17.016271+00:00.

## Critical finding

The previous `scripts/screen_fresh_pool.py` returned `READY_FOR_PREREG` solely from a count of 300 structurally distinct strings, even when none parsed as an equation and none had a checked proof. A reproducible local adversarial input of `nonsense_0` through `nonsense_299` produced `READY_FOR_PREREG`, `fresh_count=300` in the original rev9 integrated checkpoint. This was a misleading readiness signal, not a completed preregistration or a sealed evaluation.

## Integrated DEV repair

* Reject malformed, ill-sorted, reflexive and function-free candidate equations before structural freshness screening. Reject non-string task records and invalid screening parameters.
* Report `invalid_or_trivial_rejected` explicitly. Retain old exact/shingle and alpha-renaming/instance checks.
* Even if 300 structurally fresh, well-typed statements survive, classify only `DEV_FRESHNESS_THRESHOLD_MET_UNVERIFIED`. Set `preregistration_allowed=false`, `promotion_allowed=false`, `proofs_independently_replayed=false`, `semantic_family_independence_proven=false`. Proof correctness, actual theorem truth, semantic family diversity and independent custody remain unproven.
* `screen_fresh_pool.py` CLI exits nonzero until a separate authenticated preregistration gate exists; generator callers still receive DEV diagnostics.

## Local evidence

* Before (rev9): 300 unparseable strings -> `READY_FOR_PREREG`, fresh_count=300.
* After (rev10): same 300 strings -> `INSUFFICIENT_FRESH_TASKS`, fresh_count=0, invalid_or_trivial_rejected=300.
* A syntactically valid but false statement `plus Z Z = S Z` can count as syntactically fresh in a one-task DEV screen, but now never becomes prereg-ready; this is intentionally not a truth checker.
* Regression suite: 207 tests run, 206 passed, 1 skipped (rev9: 203 tests run, 202 passed, 1 skipped). No real Lean, external custodian or new sealed experiment.

## Status

`GEN-AUD-014`: DEV mitigation locally tested; **independent re-audit pending**. Other critical blockers GEN-AUD-013/012/011/009/008/001 await independent acceptance. GEN-AUD-002 external sealed custody absent; GEN-AUD-003 11 of 20 historical raw sealed jobs missing and must not be rerun/reused. Batch 1 remains `FAILED_REPAIR_REQUIRED`; no accepted base change and no promotion. Next: independently red-team the integrated proof/evaluator paths, build actual separately controlled custody and trusted Lean theorem/axiom audit, then construct >=300 semantically diverse proven fresh tasks before NEW preregistration and matched baselines.

This report is from a local adversarial review, **not an independent external audit**.
