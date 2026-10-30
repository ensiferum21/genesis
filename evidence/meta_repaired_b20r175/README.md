# B20_R175 (F6b): the repaired meta-search (NOT_SHOWN, NOTHING_PROMOTED; DEV, calibration)

- **What ran:** the preregistered script `scripts/b20r175_meta_repaired.py` (`7878cdb`, sha256 `b5c957f6…78ba`), from
  the clean worktree `/home/claude/r175-wt`, alone on CPU 0, on 30 Oct 2026 from 19:50 to 20:23 SGT.
  `code_identity` `2ef674b3…9888`; it was recomputed at recording and matches.
- **What is here:**
  - `search.json`: the successive-halving bracket over 27 configurations on four training worlds, the guard and C_K;
  - `f6.json`: F6's procedure repeated on the first training world;
  - `rows.jsonl`: 120 evaluation runs (PK, P1, D0, D24 on 24 held-out and 6 null worlds);
  - `summary.json`;
  - `run.log`.
- **Verdict:** NOT_SHOWN (NOTHING_PROMOTED), valid. The guard kept the defaults (survivor 1.939 against 1.952 on the
  training worlds). F6's procedure promoted F6's configuration again, and it lost to the defaults by 0.456 (p 0.002).
- **Record:** `docs/checkpoints/B20_R175_RECORD.md`. The record tests are `RecordB20R175` in
  `tests_genesis/test_meta_repaired_study.py`.
