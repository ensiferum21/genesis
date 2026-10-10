# Known-answer ladder, C4 domain — baseline run (Batch 1 code)

- Code: commit `94c249c` (source identity in `ladder_results.json` → `source_hash`), run from a frozen worktree.
- Preregistration: development rungs n = 4–20, test rungs n = 21–40, 10 CPU-seconds per arm per rung,
  arms = multistart, exchange, low_cycle (the fixed DSL baselines). Seed 20261010.
- Full store (events, CAS, receipts): `ladder_c4_b1_replication.zip`, SHA-256 in `replication_bundle.sha256`
  (11 MB; shipped beside the checkpoint, not in git).
- Status: PUBLIC_CALIBRATION_COMPLETE. Public calibration only; no promotion.

Result: every arm matches the published optimum on n ≤ 14; on the 20 test rungs no arm matches once.
Shortfall at n = 40: best 112 (low_cycle) vs published 127. Total shortfall over test rungs:
multistart 194, low_cycle 194, exchange 232. This is the baseline any Genesis research policy must
beat on held-out rungs under the same realized-CPU budget.
