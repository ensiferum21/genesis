# Genesis revision 16 — signed partial-run and identity scope hardening

**Classification:** DEV_ONLY_NOT_PROMOTED. **Batch 1:** FAILED_REPAIR_REQUIRED. **Completed batches:** 0. **Independent external re-audit:** PENDING. **External sealed evaluator/key:** ABSENT. **External Lean:** NOT RUN. **New sealed jobs:** 0. **Historical sealed jobs:** 11/20 raw records missing; not rerun or reused.

## GEN-AUD-025 — HIGH: signed aggregate can describe a different/partial evaluation

On the exact REV15 source, a synthetic two-task pool was evaluated under a local test signing key. A locally re-signed result was then modified to report only one task per arm, a different campaign ID and a different custodian ID, while preserving the pinned pool, candidate, preregistration and evaluator hashes. `verify_bundle` returned `signature_valid=true` and `bundle_hashes_valid=true`. This is a **false scope/coverage acknowledgement**, not a demonstrated false mathematical theorem and not evidence of malicious external signer behavior. The test key is not an independent custodian key.

**Patch:** `custody_reference/evaluator.py:verify_bundle` now requires externally expected task count, campaign ID, custodian ID, and preregistered per-arm budget as mandatory arguments. It rejects a signed partial run, unexpected campaign or custodian, invalid expectation types, and too-small budgets. The pre-existing exact-arm, arithmetic, signature, hash and canonical-serialization checks remain. All internal call sites and the synthetic smoke were updated. Six adversarial tests added in `tests/test_gen_aud_025.py`.

**Negative reproduction:** `audit/REV16_GEN_AUD_025_BEFORE.json` records REV15 accepting the forged partial/identity-swapped aggregate. `audit/REV16_GEN_AUD_025_AFTER.json` records REV16 rejecting it with `ValueError`. Reproducer scripts and complete test attempt ledger retained in `audit/`. **A valid signature does not prove the signer actually evaluated every task**; even a correct expected count is self-reported by a signer unless raw outcomes are independently audited. No external custody or independent signer was provisioned.

## Execution evidence

- REV16 integrated source suite: **252 tests run, 251 passed, 1 skipped, 0 failed**, exit 0; full stdout/stderr in `audit/REV16_REGRESSION.*`. Command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest discover -s tests -q`.
- Targeted tests: `tests.test_custody_reference tests.test_gen_aud_021`: 18/18 passed; `tests.test_gen_aud_025`: 6/6 passed.
- Synthetic reference custody smoke: `SYNTHETIC_DEV_SMOKE_PASS`, repeat reservation blocked, NOT independent custody.
- The first foreground full-suite attempt ended in a tool timeout without a final exit receipt; the subsequent separately launched run completed successfully. Both attempts are recorded, without treating the timed-out attempt as a pass.
- Evidence-manifest cache-negative check rejected locally generated `__pycache__/*.pyc`; those ephemeral files were removed before building the source-only manifest. No protected sealed payloads were observed.

## Hard blockers (unchanged)

Accepted base `/gap-engine-v2-incremental-checkpoint.zip` unchanged. Latest genuinely independent read-only audit remains REV11 (`GENESIS_INDEPENDENT_AUDIT_20261008T190009Z.json`) with six critical blockers and `BLOCK_PROMOTION`. All integrated REV12–REV16 fixes await independent release acceptance. GEN-AUD-002 genuine separately controlled sealed evaluator, signing key and isolation audit absent. GEN-AUD-003 old 11/20 raw sealed jobs missing; never rerun/reuse them. No pinned independent Lean theorem/axiom audit, no 300 genuinely diverse independently verified fresh theorem statements, no externally frozen NEW prereg or matched prospective D/U/V2n/V2p sealed outcomes. Maintain alpha 0.05 and full cost/attempt/retry accounting. No scientific gain, theorem discovery or multi-generation improvement established.

**Next:** independent red-team re-audit of integrated proof/evaluator code, genuine separate operational custody and immutable prereg anchor, independently pinned Lean kernel/axiom audit, and genuinely fresh semantically screened theorem pool before any new sealed evaluation.
