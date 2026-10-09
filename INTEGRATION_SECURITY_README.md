# Genesis integrated DEV security checkpoint — 9 October 2026

This is a **source-only, unaccepted development artifact**. It integrates the
previous source-only cache safety fix and the later Lean evidence/canary modules.

CRITICAL regression GEN-AUD-013: a later component archive reintroduced the
GEN-AUD-012 error: `Lean exit_code=0` was interpreted as `proof_replayed=True`.
The integrated package rejects that inference. `proof_replayed` remains false
and successful local process execution is marked `DEV_LEAN_EXIT_ZERO_UNTRUSTED`.
The evidence and canary verifiers reject legacy unsafe receipts.

Run `PYTHONPATH=src:. python -m unittest discover -s tests -q` from this root.
The complete regression run in the builder's environment: 203 tests,
202 passed, 1 skipped. This is not independent external replication.

The external evaluator, independent Lean theorem/axiom audit, 300 genuinely
fresh tasks, preregistration and fresh sealed evaluation remain outstanding.
Do not use this checkpoint for scientific promotion. Historical sealed jobs
must never be rerun or recycled. Use the newest separately persisted
`/GenesisCampaign/CAMPAIGN_STATE_REV*_*.json` for campaign status.

## GEN-AUD-014 (DEV, independent re-audit pending)
Freshness screening never confers prereg readiness; malformed or unproved candidate statements cannot be called ready. See `GEN_AUD_014_REPORT.md`.

## GEN-AUD-015/016 (DEV, independent re-audit pending)
A locally consistent or self-signed preflight package cannot authorize promotion;
`promotion_allowed_by_this_preflight` is always false. Evidence manifests
reject untracked symlinks and symlinked manifests. See `GEN_AUD_015_016_REPORT.md`.

REV12: Legacy `SealedStore.judge` and `judge_sealed` now block in-process callbacks unless explicitly marked `unsafe_dev`. Any such outcomes are untrusted DEV evidence. For trusted sealed comparisons use a genuinely separate custodian and externally anchored preregistration. See REV12_REPORT.md.

## Revision 13 additional fail-closed boundaries

GEN-AUD-020: `promotion_custody_preflight` requires all six externally expected hashes and a pinned custodian identity. A caller's `isolation_audit_approved=True` is **not** independent evidence; the function always blocks promotion/custody admission.

GEN-AUD-021: `custody_reference.verify_bundle` rejects impossible per-arm scores, budget mismatches, incomplete arm sets, malformed schemas and false custody/export flags even when signed by the local reference key. These are DEV internal-consistency checks only, not verification of outcomes or external key custody.

REV14: GEN-AUD-022 found joint public proof+digest substitution could return a false proof acknowledgement for an originally true theorem. Admission-time private proof digests and full registry checks now block it. In-process only, independent re-audit pending. See REV14_REPORT.md.

## REV16 — GEN-AUD-025 (DEV-only signed aggregate scope)

`custody_reference.evaluator.verify_bundle` now **requires separately expected**
sealed task count, campaign ID, custodian ID and preregistered per-arm budget,
in addition to hashes and the pinned signing key. This closes a local validation
hole in which a syntactically valid, locally re-signed *partial* result for a
different campaign/custodian was described as signature/hash-valid. The checks
only establish internal consistency against supplied expectations; a signer
can still lie about the actual work, and an operator controlling both keys and
expectations defeats the check. **No independent custodian, external Lean, or
scientific result is established.** GEN-AUD-025 negative reproducer and tests
are retained under `audit/` and `tests/test_gen_aud_025.py`.
