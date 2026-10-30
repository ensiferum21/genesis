# A diagnosis of B20_R170's meta-search (at recording)

- **What ran:** `diagnose.py`, on 30 Oct 2026 from 15:39 to 15:48 SGT, on CPU 1 (B20_R172 and then B20_R174 had CPU
  0), from the worktree `/home/claude/r170-wt` at B20_R170's preregistration commit `405741e`. It repeats the
  meta-search exactly and keeps what the study's `meta.json` did not: every rule's inner spend and value, and every
  outer branch's outer spend.
- **It matches the study** (`matches_study`: the promoted rule, C_meta 83,483 and outer spend 143,430).
- **What it shows** (`diagnosis.json`), for defect B20R163-META:
  - the promoted rule had 17,996 inner units (value 2.721) and the identity 17,407 (2.405), so those two were
    compared at about equal spend;
  - the other 19 branches had about 2,400 each (one 4,808); 9 of the 21 branches ran the identity's behaviour;
  - the promoted rule's branch was charged 78,000 outer units for 17,996 inner ones.
- **Use:** `docs/checkpoints/B20_R170_RECORD.md`. Nothing here was used by the study.
