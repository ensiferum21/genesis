# B20_R173: a release attempt through the protected judge (RELEASED; DEV)

- **What ran:** the preregistered script `scripts/b20r173_protected_release.py` (`d8cb798`, sha256 `a3e03841…7291`),
  from the clean worktree `/home/claude/r173-wt`, alone on CPU 0, in one slice on 30 Oct 2026, 01:16–01:50 SGT.
  `code_identity` `9a070bd0…e245` (recomputed at recording; it matches).
- **What is here:**
  - `runs.jsonl`: all 1,680 runs of the pinned mcx3 binary (key, CPU, value);
  - `calls.json`: every evaluation the protected judge (v2) and version 3 asked for, in order;
  - `summary.json`: validity, R1 (the protected judge's decision), S1–S4, the graph ids, and the verdict;
  - `run.log`: the slice log.
- **Verdict:** RELEASED, valid. The protected judge, unchanged and calibrated on REX and 47 random L0 engines
  (tau 0.782%), released C0_1, B20_R165's pre-specified engine. Its B score was 1.220% above REX's. On 24 fresh truth
  graphs, C0_1 beat REX by +1.122% on 24 of 24 (p 6 × 10⁻⁸). Version 3 also releases it. The expectation,
  NOT_RELEASED, was wrong.
- **Record:** `docs/checkpoints/B20_R173_RECORD.md`. The record tests are `RecordB20R173` in
  `tests_genesis/test_protected_release_study.py`.
