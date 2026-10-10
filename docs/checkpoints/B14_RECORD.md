# B14 checkpoint record (roadmap §14.1)

**Phase:** B14 — repair acceptance (W01–W03; R-01/R-02 regression
reproductions; certificate custody). **Parent:** `GENESIS_COMPLETION_CHECKPOINT_B13.zip`
(SHA-256 `369089741614b4b4763ea1dae16318fdd879a788ef9efea78378cce5742c3f45`,
commit `82aa557`, tag `b13-baseline`). B13 is unchanged.

## What changed

- R-01, R-02, R-03 repaired (see `docs/BLOCKING_DEFECTS.md`), with the original
  B13 reproduction log kept (`audit/reproductions/logs/`).
- Three internal red-team rounds on the repairs: 11, 12 and 9 findings (4, 2
  and 1 critical). All are closed with regression tests. Scripts and logs from
  before and after each repair are in `audit/redteam_b14*/`.
- W01 requirements ledger: `docs/REQUIREMENTS_LEDGER.md` and
  `ledger/requirements_ledger.json` (343 rows). Every test reference resolves,
  and no row is accepted.
- The matrix now fails on undeclared skips (`docs/NONMANDATORY_SKIPS.json`).

## Tests actually executed

See `test_report` in `CHECKPOINT_RECORD.json`. It covers every suite with
pass, skip and failure counts, and records each skip with its reason; a skip
in a release-blocking suite fails the checkpoint. Original failure logs and
their repairs are kept as noted above.

## Identities

Source commit and tree, toolchain pins, interpreter and packages are in
`CHECKPOINT_RECORD.json`. The deviation is unchanged: Python 3.13 here, while
the lock was written for 3.12 (R-04). No language model is called by any
campaign.

## Budgets and attempts

This was an engineering batch. No sealed evaluation was run.

- The e2e walkthrough re-ran three times on successive code. All runs are kept
  in `evidence/e2e_walkthrough_b14/` (`run1_…`, `run2_…`, `final/`).
- Its fixture-role sealed panel (3 hard CONFIRM hosts, 12 rows) gave 0 wins,
  0 losses and 3 ties. That was signed NOT_SUPPORTED, preflight returned
  BLOCKED, and the release was refused.

## Evidence graph and effective claim levels

`evidence/e2e_walkthrough_b14/final/effective_claims.json`:
- World loop: 10 claims (6 WITNESS_VALID, 4 OPTIMALITY_CHECKED), each re-derived
  with certificate replay.
- Campaign: no claims.
- Without a trust root, the campaign's verified phase is CANDIDATE_FROZEN.

## Reproduction

`RESUME.md`. Verify bundles with your own trusted installation:
`genesis verify-bundle <zip> --trust-root <root>`.

## Migration

The schemas changed, so stores written before B14 behave differently:
- Request v2 → v3: adds claim_id, statement_hash, scope, evidence_kind and the transfer/generation fields.
- Anchor v2 → v3: adds the claim binding, registration slot and salted panel commitment.
- Receipt `genesis-evaluation-receipt-v1` → `genesis-scientific-receipt-v2`.
- `bound_state` v2 and `witness_check` v2 now carry custody and replay data.
- Claims carry `binding` (confirmation) or `problem` (math).

Consequences for older stores and requests:
- On pre-B14 stores, effective levels drop wherever the evidence is not
  replayable, which is the intended fail-closed behaviour. The recorded
  history stays visible.
- Pre-B14 requests are refused by the custodian.

## Rollback

`git checkout b13-baseline` (or extract the B13 checkpoint). B14 adds no data
migration that changes existing files.

## Next actions (honest)

1. **GV0 needs an independent source review** of the B14 repairs. Three
   internal rounds each found critical issues, so more should be expected.
2. **B15 (R-04):** pin the image digest, choose one Python version across lock
   and runtime, and run the release matrix on a second supported machine.
3. **Open items:**
   - B14-OPEN-2: multiplicity across candidates.
   - B14-OPEN-3: the improver/generation lineage protocol.
   - B14-OPEN-4: replay contracts for exact, formal, causal, replication, DEV
     and priority evidence.
   - B14-OPEN-5: per-claim report wording.

## Claim ceiling

This is an engineering checkpoint only. P0–P2 are builder assessments pending
independent acceptance, and P0 is also blocked by R-04. There is no sealed
evaluation, independent custody, scientific promotion, novelty, transfer,
better-improver or self-improvement claim.

## Unresolved critical audit issues

None known after round 3, but this rests on internal review only, and GV0 is
not passed.
