# B20_R136: a synthesised sense chooses the engine per graph (NOT_SHOWN; DEV)

- **What ran:** the preregistered script `scripts/b20r136_sense_choice.py` (`6bb39ab`, sha256 `357cd5ed…2bcb`), from
  the clean worktree `/home/claude/r136-wt`, alone on CPU 0, in one slice on 30 Oct 2026, 07:25–07:38 SGT.
  `code_identity` `26a4b72b…45bd5` (recomputed at recording; it matches).
- **What is here:**
  - `runs.jsonl`: 400 full 1 s runs, 240 charged runs and 120 sense timings (key, CPU, value);
  - `search.json`: the sense search's result, the hand features' fit, and FIXED's choice;
  - `summary.json`: validity, P1, P2, S1–S5, the graph ids, the per-graph rows, and the verdict;
  - `run.log`: the slice log.
- **Verdict:** NOT_SHOWN, valid.
  - FIXED is C0_1.
  - The synthesised sense m / q90(degree) beat always-C0_1 by +0.087%: p_Holm 0.0009, but below the material 0.1%.
  - It lost to the builder's degree CV by 0.054%.
- **Record:** `docs/checkpoints/B20_R136_RECORD.md`. The record tests are `RecordB20R136` in
  `tests_genesis/test_sense_choice_study.py`.
