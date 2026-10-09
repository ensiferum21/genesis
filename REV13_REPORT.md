# Genesis revision 13 — cross-campaign receipt and aggregate consistency repairs

**Status:** DEV_ONLY_NOT_PROMOTED; Batch 1 `FAILED_REPAIR_REQUIRED`; completed batches 0. 2026-10-08 UTC / 2026-10-09 Singapore time.

## Independent-audit scope and limitations

Read the authoritative campaign state revision 12, matching handoff, and read-only independent audit of revision 11 before modifying code. Verified revision 12 ZIP SHA256 `46345e60fb2ecdd7701a7393ffdbaa884d6646b2bd34120bb540fb6db0900b9c`. This revision performs **local adversarial reproduction and engineering repair**, not an independent external audit or release acceptance. The accepted base remains unchanged.

## GEN-AUD-020 — signed receipt from another experiment accepted as custody prerequisite

**Pre-patch reproduction:** `promotion_custody_preflight` returned `CUSTODY_PREREQUISITES_PRESENT_NOT_PROMOTION` with no reasons when passed a valid synthetic Ed25519 signature on six unrelated `f*64` hashes, a synthetic `OTHER_CAMPAIGN_SIGNER` identity, and a caller-supplied `isolation_audit_approved=True`. It did not require independently expected hashes or identity; the boolean could be self-asserted.

**Patch:** Require all six externally expected SHA256 values and a separately pinned custodian identity, compare each to signed claims, and treat a caller-supplied audit boolean as **not** proof of operational isolation. This local preflight always returns `BLOCK`, even when signatures and expected claims match. Six negative and positive tests cover cross-campaign confusion, identity, missing hashes, fake signatures and the limitation of a valid matched receipt.

## GEN-AUD-021 — impossible signed scores accepted as internally valid

**Pre-patch reproduction:** A synthetic local signer re-signed an aggregate claiming `D.correct=999` on a one-task sealed pool, recomputed both public result and manifest digests, and `verify_bundle` returned `signature_valid=True, bundle_hashes_valid=True`. A valid signature is not a consistency check.

**Patch:** `verify_bundle` now rejects malformed public/manifest schemas, missing or extra arms, non-integer/negative counts, unequal task counts, budget mismatches, impossible correct+failure totals, and false private-export/custody flags. Five new regression tests include re-signing invalid synthetic aggregates and preserving the normal reference bundle path. This **does not** independently recompute outcomes from the sealed pool; a dishonest signer can still attest plausible but false results.

## Regression and provenance

Full source regression command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest discover -s tests -q`. **231 tests, 230 passed, 1 skipped**, no failures. Raw stdout/stderr and a command/environment receipt are packaged. A freshly extracted archive must be replayed before any acceptance. Archive is source-only and contains no sealed pools, keys, or per-task private data.

## Remaining hard blockers

- Independent re-audit of REV13 and earlier DEV repairs, plus accepted-base proof-ID vulnerability (GEN-AUD-001) remains outstanding.
- Real separately controlled evaluator, external key custody and authenticated operational isolation audit do not exist. Same-process legacy sealed data and screening oracle remain accessible; do not use them for sealed science.
- Lean is unavailable here; no independently pinned Lean theorem/axiom replay was performed.
- The 300 genuinely diverse, independently checked fresh theorem statements are not available. No new preregistration was frozen and no D/U/V2n/V2p sealed jobs were executed.
- Historical 11 of 20 raw sealed jobs are missing. **Never rerun/reuse them**. No old outcomes are promoted; alpha remains 0.05.

**Release decision:** BLOCK_PROMOTION. These patches only improve the development evidence-handling boundary; they do not validate mathematical discoveries or self-improvement.
