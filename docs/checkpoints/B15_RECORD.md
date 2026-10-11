# B15 checkpoint record — Independent execution (roadmap W04, defect R-04)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B14_R1.zip` (commit `c156a50`).

## Environment limits found at the start

| Limit | Consequence |
|---|---|
| PyPI denied by the egress proxy (403) | No wheel download hashes. |
| No container registry or Docker daemon | No image digest; the Containerfile keeps its failing `PIN_REQUIRED` placeholder. |
| No second machine | The roadmap's exit criterion, "verified on a second machine", is **not met**. Everything below was built and tested on the build host only. |

## What changed

1. **Supported platform.** One Python version, 3.13, everywhere.
   - `deployment/SUPPORTED_PLATFORM.json` defines the supported platform, and
     `genesis platform check` (`src/genesis/deployment.py`) checks a host against it.
   - `requirements.lock` v2 is the full closure, with wheel-content fingerprints in
     `environment/lock_fingerprints.json`.
2. **Crash consistency.** `genesis.faults` has 14 crash points, each tested by real
   process death.
   - Writes are atomic: CAS objects, exports, zips, snapshots, reports and requests.
   - Rebuild constructs the new database aside and swaps it in.
   - Each generation is committed in one transaction.
3. **Resume and recovery.**
   - `genesis campaign resume` reuses journalled attempts, charges interrupted ones
     and keeps the freeze.
   - `custodian.recover` publishes a signed receipt for an interrupted sealed
     evaluation; it is INVALID unless the evaluation completed.
4. **Backup and restore.** `genesis store backup` / `restore`.
5. **Toolchain.**
   - `toolchain/build_reproducible.sh` gives byte-identical zstd, CaDiCaL, drat-trim
     and E across paths and times (gcc 13.3.0, glibc 2.39).
   - `toolchain/known_answers.py` runs 10 behavioural cases.
   - `toolchain/revise_pins.py` with `PINS_HISTORY.jsonl` changed the pins twice;
     evidence is in `audit/b15_toolchain/`.
6. **Roles.** `genesis.launcher` is a root service for one unprivileged worker UID.
   - It checks the peer with SO_PEERCRED and enforces a ceiling, allowlists and a
     budget.
   - It keeps a hash-chained log, anchored by the worker's receipts.
   - `sandbox.run` delegates to it when the worker is not root.
7. **Second machine.** `deployment/reproduce.{sh,py}` runs seven verified steps
   against `deployment/reference_run.py` and `EXPECTED_RESULTS.json`. The guide is
   `deployment/DEPLOYMENT.md`.
8. **Internal red team.** Five findings, all repaired (`tests_genesis/test_redteam_b15.py`).
   The reviewer was the same operator, so this is not independent review.

## Still open

- **R-04.** A second-machine run with operator attestation, the image digest and
  wheel hashes.
- **B14-OPEN-2..4.**
- **B15-OPEN-1.** Unrecovered registered evaluations are visible only to whoever holds
  the anchor (W06).
- **GV0.** Independent review of B14, B14_R1 and B15.

## Next

1. Run `deployment/reproduce.sh` on a second machine against this checkpoint, with
   its SHA-256 sent separately, and have that operator attest the report.
2. Then B16: evaluator readiness (W05–W07).
