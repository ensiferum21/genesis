# B20_R172 (Foundry G4): a state feature found by replaying the engine's own decisions (NOT_SHOWN; DEV, calibration)

- **What ran:** the preregistered script `scripts/b20r172_state_features.py` (`73f8ad4`, sha256 `46e571f4…9b33`), from
  the clean worktree `/home/claude/r172-wt`, alone on CPU 0, on 30 Oct 2026 from 15:27 to 15:45 SGT. `code_identity`
  `508a6f96…d08e`; it was recomputed at recording and matches.
- **What is here:**
  - `search.json`: the counterexample search (two training worlds, 240 replayed decisions, the proposed feature);
  - `rows.jsonl`: 90 evaluation runs, three arms on 24 held-out worlds and 6 null worlds;
  - `summary.json`;
  - `run.log`.
- **Verdict:** NOT_SHOWN, valid. The proposed feature, slope4 / hi, against the defaults given the search's compute:
  −0.022 (p 0.77); at equal budget a tie (+0.048). It generalised: on the held-out worlds' decisions it agreed with
  replays 0.768 against the index's 0.702 (p 0.001).
- **Record:** `docs/checkpoints/B20_R172_RECORD.md`. The record tests are `RecordB20R172` in
  `tests_genesis/test_state_features_study.py`.
