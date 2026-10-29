# B20_R167: ARA's calibration on the sealed Limitation Zoo, re-run (ARA_CALIBRATED; DEV)

- **What ran:** the preregistered script `scripts/b20r167_ara_zoo_rerun.py` (`33e8905`, sha256 `233610d0…af81`),
  from the clean worktree `/home/claude/r167-wt`, alone on CPU 0, in three slices from 29 Oct 2026, 13:30 UTC, to
  17:15 UTC (3.7 h). `code_identity` `74f488ab…7d` (recomputed at recording; it matches).
- **What is here:**
  - `rows.jsonl`: one row per (environment, arm), 475 in all (95 environments, five arms);
  - `ledger.jsonl`: the protected zoo judge's 275 submissions, with the oracle, range and sealed gain of each;
  - `run.log`: the study's log over the three slices;
  - `summary.json`: the validity record, experiments A–D and S, the keys, the gains, and the verdict.
- **Verdict:** ARA_CALIBRATED, failed [], valid. A 42 of 50 localised (p 3 × 10⁻¹⁸) and NONE on 30 of 30; B
  significant on four of five classes (not SEARCH_WEAK); C no failures; D ara2 over blind2 +0.408 and over tuning
  +0.559; S no release by ara or ara2 on 45 controls.
- **An earlier attempt** (the second session's, from 28 Oct 2026, 02:16 UTC) left nothing on the branch and is not
  here; nothing of it was used.
- **Record:** `docs/checkpoints/B20_R167_RECORD.md`; record tests `RecordB20R167` in
  `tests_genesis/test_ara_zoo_rerun_study.py`.
