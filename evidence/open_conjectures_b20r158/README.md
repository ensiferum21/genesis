# B20_R158 (F5): Genesis's own conjectures, attacked by FULL and PLAIN (NOT_SHOWN; DEV)

- **What ran:** the twice-amended preregistered script `scripts/b20r158_open_conjectures.py` (`f7803e3`, sha256
  `f44333c3…c06c`), from the clean worktree `/home/claude/f5c-wt`, alone on CPU 0, in one slice on 30 Oct 2026,
  12:29–12:53 SGT. `code_identity` `4f81e33b…c87a` (recomputed at recording; it matches). The stopped first run is in
  `../open_conjectures_b20r158_attempt1/` and is not used.
- **What is here:**
  - `generations.jsonl`: per generation, the posed and withheld conjectures, labels, both arms' records (artifacts,
    refuted, procedures, templates, sources), the confirmed refutations, survivors and new data;
  - `summary.json`;
  - `gen1/`–`gen3/`: each generation's conjectures, arm records and engine states;
  - `run.log`: the slice log.
- **Verdict:** NOT_SHOWN, valid.
  - P1: FULL alone refuted 1, PLAIN alone 0; p 0.5.
  - Generation 1 posed 9 conjectures, of which 2 were withheld. FULL refuted 6 and PLAIN 5.
  - Generations 2 and 3 posed nothing new.
  - The survivors are Merris (proved), bound 10 (proved) and one unlabelled candidate, `sqrt((5d² + 3m³/d)/2)`,
    which has not been checked against the literature.
- **Record:** `docs/checkpoints/B20_R158_RECORD.md`. The record tests are `RecordB20R158` in
  `tests_genesis/test_open_conjectures_study.py`.
