# B20_R159 (PT-1, the proving test): INADEQUACY_GATE_FAILED (DEV)

- **What ran:** the preregistered script `scripts/b20r159_proving_test.py` (`a775227`, sha256 `56037017…3a05`), from
  the clean worktree `/home/claude/pt1-wt`, alone on CPU 0, on 30 Oct 2026 from 19:24 to 19:49 SGT. It stopped after
  stage 1, as the rule requires when the gate fails. `code_identity` `2d131c91…8dd6`; it was recomputed at recording
  and matches.
- **What is here:**
  - `stages.json`: stage 1's records for P0 and G on family A, with every claimed artifact (graphs as edge lists);
  - `state_A_P0.json`, `state_A_G.json` and their `.domain.json`: the engines' saved states and G's made
    representations (templates, derived operation sets, macros, libraries);
  - `summary.json`;
  - `run.log`.
- **Verdict:** INADEQUACY_GATE_FAILED, valid. P0 certified bound 40 (273 vertices); G certified bounds 40 and 21 (352
  and 360 vertices) from derived graph products. Parts 1 and 3-5 were not run.
- **Record:** `docs/checkpoints/B20_R159_RECORD.md`. The record tests are `RecordB20R159` in
  `tests_genesis/test_proving_test_study.py`.
