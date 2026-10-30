# B20_R163 (F6): the Frontier searching its own configuration (NOT_SHOWN; DEV, calibration)

- **What ran:** the preregistered script `scripts/b20r163_frontier_meta.py` (`77d725d`, sha256 `e71bfb69…777f`), from
  the clean worktree `/home/claude/f6-wt`, alone on CPU 0, on 30 Oct 2026 from 14:38 to 14:59 SGT. `code_identity`
  `d3a98661…b228`; it was recomputed at recording and matches.
- **What is here:**
  - `meta.json`: the meta-search's record (the promoted configuration, C_meta, the curve);
  - `rows.jsonl`: 90 evaluation runs, from three arms on 24 held-out worlds and 6 null worlds;
  - `summary.json`;
  - `run.log`.
- **Verdict:** NOT_SHOWN, valid.
  - P (the promoted configuration) against D (the defaults with C_meta spread as extra budget): −0.221, p 0.99.
  - S1, P against D0: a tie (−0.073).
  - S2, D against D0: +0.148, p 8 × 10⁻⁶.
- **Record:** `docs/checkpoints/B20_R163_RECORD.md`. The record tests are `RecordB20R163` in
  `tests_genesis/test_frontier_meta_study.py`.
