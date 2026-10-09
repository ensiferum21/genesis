# Genesis Batch 1 — Rev12 integrated DEV security hardening

**Classification:** DEV ONLY / NOT PROMOTED. Accepted base unchanged. Independent re-audit required. Zero new sealed mathematical jobs; zero external Lean proof replays.

## Independent-audit input

The independent 2026-10-08 19:00Z audit (`GENESIS_INDEPENDENT_AUDIT_20261008T190009Z.json`) independently replayed 211 tests and found six CRITICAL blockers. Its findings include same-process sealed callback exfiltration, mutable local prereg anchors, and untracked regular files under cache directories. It directed **BLOCK PROMOTION**. Rev12 addresses the local engineering failure modes without closing external custody or historical evidence gaps.

## Implemented changes

1. **GEN-AUD-017 (WARN):** `scripts/evidence_manifest.py` no longer ignores regular files under `__pycache__`/`.pytest_cache` or `.pyc/.pyo`; verification fails closed on any such file, including untracked post-manifest additions. Custom exclusions beyond `EVIDENCE_MANIFEST.json` are rejected. This does not turn local hashes into independent attestations.
2. **GEN-AUD-018 (CRITICAL structural):** `SealedStore.judge` now blocks arbitrary Python callbacks by default and logs denial. Historical research scripts explicitly opt into `unsafe_dev=True` and receive `UNTRUSTED_DEV_ONLY_IN_PROCESS_CALLBACK` with `independent_custody_proven=False` and `eligible_for_scientific_promotion=False`. The sealed pool remains in the research process and is **not** protected by this change. The same-process oracle and explicit unsafe path remain DEV-only. This does **not** resolve GEN-AUD-002.
3. **GEN-AUD-019 (CRITICAL provenance):** Added `scripts/prereg_anchor.py`, a fail-closed verifier requiring a separately pinned Ed25519 key, externally expected experiment hashes, a signed UTC issuance time preceding an independently known evaluation start, and a matching local prereg plan. It returns `promotion_allowed=False` even for valid signatures. No real external anchor or signer has been provisioned. Legacy `load_verified` remains local-consistency-only for old DEV scripts.
4. Replaced stale embedded regression transcript with the actual Rev12 test output and command/environment receipt.

## Synthetic before/after reproductions

- Before: hidden cache JSON accepted; after: verification rejects it.
- Before: legacy sealed callback copied a synthetic marker; after: default callback invocation rejects before execution (unsafe DEV opt-in remains).
- Before: local prereg plan and `.lock` rewritten together were accepted; after: an externally expected original hash makes the strict signed-anchor verifier reject the rewritten plan.

## Tests and limitations

220 integrated tests run; 219 passed, 1 skipped. Nine new adversarial tests passed. Run with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest discover -s tests -q`. This is local engineering evidence, not external custody or scientific confirmation. `audit/REGRESSION_RUN.json` records command, Python version, and transcript hashes.

**Still blocked:** accepted base unsoundness, same-process sealed data in old design, no independent custodian or out-of-band signing key, no trusted pinned Lean theorem/axiom replay, no fresh independently proven 300-task pool, no externally anchored prereg, no matched new sealed D/U/V2n/V2p results, and historical 11/20 missing raw jobs. Do not reuse or rerun historical sealed jobs. Alpha remains .05.

**Required next:** independent re-audit of rev12, separate custody service and independent release authority, real trusted Lean replay, fresh theorem pool and new preregistration before any prospective sealed evaluation.
