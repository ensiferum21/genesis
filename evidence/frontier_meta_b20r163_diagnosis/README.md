# A diagnosis of B20_R163's meta-search (after recording)

- **What ran:** `diagnose.py`, on 30 Oct 2026 from 15:14 to 15:20 SGT, on CPU 1 (B20_R170 had CPU 0), from the
  worktree `/home/claude/f6-wt` at B20_R163's preregistration commit `77d725d`. It repeats the meta-search exactly and
  keeps what the study's `meta.json` did not: every configuration's inner spend and value, and every outer branch's
  outer spend.
- **It matches the study** (`matches_study`: the promoted configuration, C_meta 76,886 and outer spend 143,428).
- **What it shows** (`diagnosis.json`):
  - the first configuration opened had 17,992 inner units and was promoted (its best artifact at 15,602);
  - one other had 13,202; the other 19 about 2,400 each;
  - the first configuration's branch was charged 84,600 outer units for its 17,992 inner ones;
  - the defaults were never opened.
- **Use:** defect B20R163-META (`docs/BLOCKING_DEFECTS.md`) and the correction in
  `docs/checkpoints/B20_R163_RECORD.md`. Nothing here was used by the study.
