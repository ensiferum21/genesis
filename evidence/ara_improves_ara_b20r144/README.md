# B20_R144: ARA applied to its own settings (NOTHING_ADOPTED; DEV)

- **What ran:** the preregistered script `scripts/b20r144_ara_improves_ara.py` (`7acf0e4`, sha256 `05523955…58c3`),
  from the clean worktree `/home/claude/r144-wt`, alone on CPU 0, in one slice on 30 Oct 2026, 07:38–08:23 SGT.
  `code_identity` `72be39a0…c1cd` (recomputed at recording; it matches).
- **What is here:**
  - `runs.jsonl`: all 792 ARA runs, 552 on meta-development and 240 held out;
  - `summary.json`: validity, P1, P2, S, S1–S6, the settings (v1, v2, tune), the operator prior, and the verdict;
  - `run.log`: the slice log.
- **Verdict:** NOTHING_ADOPTED, valid.
  - The meta-ladder located nothing.
  - The six one-step neighbours it tried changed no released gain on the choice set.
  - Held out: v1 0.679 on 50 defects; the tuning control 0.718, at 2.8 times the units.
  - S: 1 release on 30 controls, on H2's NO_HEADROOM 62077, which had a real sealed gain.
- **Record:** `docs/checkpoints/B20_R144_RECORD.md`. The record tests are `RecordB20R144` in
  `tests_genesis/test_ara_improves_ara_study.py`.
