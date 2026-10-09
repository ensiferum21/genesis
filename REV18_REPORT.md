# Genesis — REV18 custodian task-reuse gate (DEV ONLY)

Date: 9 October 2026 Singapore time. Derived from the highest Library state/handoff REV17. **No accepted campaign batch, no external custody, no Lean verification, no new sealed task run, no promotion.**

## GEN-AUD-027 — critical local replay boundary

**Prepatch reproduction A:** Calling `evaluate_frozen` twice with the identical synthetic pool and preregistration while omitting `reservation_dir` succeeded twice; zero reservation records existed. `reservation_dir` was optional.

**Prepatch reproduction B:** Even with a reservation directory, evaluating the same synthetic pool a second time under a changed preregistered `campaign_id` succeeded; two `.reserved` files were created. Reservations were keyed by preregistration hash, not by the private task identities. A changed candidate or budget would similarly change the preregistration hash.

**Consequence:** A custodian using the reference evaluator as written could repeatedly query the same sealed examples and export signed aggregate feedback under new preregistrations. This invalidates a one-shot sealed evaluation claim and could enable test-set tuning. These reproductions are local synthetic tests, not evidence that historical sealed jobs were rerun.

**REV18 development repair:** `evaluate_frozen` now refuses to run without a pre-existing owner-only custodian reservation directory. Before any candidate prediction, it atomically reserves the preregistration and **every private task content fingerprint** (hash of canonical `features` and `answer`, deliberately excluding mutable task IDs) in an on-disk SQLite transaction with `BEGIN IMMEDIATE`, unique task keys and `synchronous=FULL`. Exact repeats, renamed/reordered pools, changed campaigns/candidates, overlapping subsets, concurrent attempts and post-failure retries fail closed. The task-fingerprint ledger stays inside the custodian directory and is not exported to researchers. Duplicate task contents inside one pool are rejected. Reservation is committed before scoring; failed signing does not permit a retry.

**Limits:** This is local replay protection only. The Python caller, signing key, pool, and reservation directory are not held by an independently operated authority. A root/operator able to replace the database can still reset it; fingerprints of low-entropy tasks must never be exported; semantically equivalent but structurally different tasks can still overlap; OS path-race hardening and immutable remote attestation remain incomplete. SQLite commit is a local durability mechanism, not an independently anchored timestamp. The public `budget_charged` still counts tasks rather than measured solver CPU/operations; equal compute budgets are NOT established by this reference evaluator.

## Tests and evidence

- Prepatch reproductions A/B captured from REV17 source; both allowed repeated synthetic evaluation.
- New negative tests in `tests/test_gen_aud_027.py` cover missing reservations, changed campaign, changed candidate, reordered/renamed pool, partially overlapping pool, disjoint pool, duplicate contents, symlink directory, concurrent races, failed-signing retry, group-writable and group-readable directory permissions.
- Existing reference-custody test fixtures were updated to use owner-only reservation directories; synthetic custody smoke passes, and its 10-task V2p score is **planted synthetic data, not mathematics**.
- First full-suite foreground attempt was interrupted by execution time limit; a subsequent full-suite attempt was completed, then a stricter POSIX permission change initially caused fixture failures. All attempts are retained in the attempt ledger; final full regression and fresh-extracted replay results are recorded separately.

## Release gates still blocked

GEN-AUD-002: actual separately controlled external sealed evaluator, private key and custodian-side task ledger; GEN-AUD-003: 11/20 historical raw sealed jobs missing (do not rerun/reuse). REV11 independent audit still says BLOCK_PROMOTION; all later fixes including GEN-AUD-027 are local and await independent red-team acceptance. Pinned external Lean theorem/axiom audit, 300 independently proved fresh diverse statements, externally frozen preregistration and matched D/U/V2n/V2p prospective comparisons remain outstanding. Alpha .05 and complete attempt/cost accounting remain mandatory.
