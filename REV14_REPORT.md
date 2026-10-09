# Genesis revision 14 — proof evidence substitution gate

**Status:** DEV_ONLY_NOT_PROMOTED; Batch 1 `FAILED_REPAIR_REQUIRED`; completed batches 0. Updated 2026-10-08T21:40:55Z. The accepted base is unchanged.

## Re-audit scope

Read authoritative campaign revision 13 and its handoff; verified its source-only checkpoint SHA256 `562b44161308e4a563e3d0839d1d299e1edca7acb3b2670a417349c1c3d3fd76`, and verified the 149-entry manifest from a separate clean extraction. Examined integrated proof store and receipt interfaces. This is a **local adversarial source review**, NOT an independent external security audit or accepted-base release. The latest genuine independent read-only audit remains revision 11, with six critical blockers and `BLOCK_PROMOTION`.

## GEN-AUD-022 — HIGH: proof plus public digest substitution

The revision-13 `LemmaStore.verify` treated public `proof_digests` as its admission-time identity for a repeated lemma ID. An attacker who could mutate caller-visible `proofs` and `proof_digests` together could replace the genuine reflexivity proof for `Z = Z` with an invalid rewrite citing a nonexistent lemma, recompute the public digest, and obtain `verify('ok', Z=Z, forged_proof) == True` **without replaying the forged proof**. `replay_all()` detected the forgery, but the individual proof acknowledgement was false. **This did not demonstrate acceptance of a false theorem**; the originally admitted equation was true. It demonstrates a forged proof-evidence acknowledgement that could mislead a downstream consumer omitting full replay.

**Repair:** Record a separate admission-time `_trusted_proof_digests` snapshot. Every `verify` (both new and repeated IDs) checks the complete public registry, admission order, proof bytes and private digest before returning. Legacy pickles without the private digest fail closed and must be replayed. `replay_all` uses the same invariant. Six adversarial tests cover forged proof+digest, further admission, order injection, digest tampering, idempotence, and legacy replay.

This is an in-process integrity check, **not an isolation boundary**. A malicious worker able to mutate private Python attributes or execute arbitrary code inside the checker process remains out of scope; external proof checker isolation and independently pinned Lean verification remain mandatory.

## Regression and negative evidence

First full regression ran 237 tests and failed one existing test because the new registry error wording differed from a preexisting assertion. A targeted rerun exposed a second expected wording. Both were fixed without relaxing any verification condition. The final complete suite ran **237 tests: 236 passed, 1 skipped, 0 failed**. The raw failed and successful stderr logs and a multi-attempt ledger are packaged; a clean extracted archive must be replayed separately.

## Campaign hard blockers unchanged

No genuine external custodian/key or operational isolation audit; no trusted Lean theorem/axiom audit; no >=300 genuinely diverse independently proved fresh theorem statements; no new preregistration, no equal-budget D/U/V2n/V2p sealed jobs. Historical 11/20 raw sealed jobs remain missing and must never be rerun/reused. Alpha remains 0.05. No promotion and no claimed mathematical or multi-generation success.
