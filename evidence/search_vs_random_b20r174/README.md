# B20_R174: Genesis's search against random sampling of the same language (NOT_SHOWN, RANDOM_MATCHES_SEARCH; DEV)

- **What ran:** the preregistered script `scripts/b20r174_search_vs_random.py` (`bc57958`, sha256 `842a9d73…2924`),
  from the clean worktree `/home/claude/r174-wt`, alone on CPU 0, on 30 Oct 2026 from 15:48 to 19:24 SGT in two
  slices. `code_identity` `5d6b046b…f0f0`; it was recomputed at recording and matches.
- **What is here:**
  - `runs.jsonl`: all 12,432 engine runs (key, cut, CPU), from which the record test replays the whole study;
  - `summary.json`;
  - `run.log`.
- **Verdict:** NOT_SHOWN, read RANDOM_MATCHES_SEARCH, valid. On 24 fresh ±1-weighted planar graphs the three search
  winners gained +1.092% over REX and three random-sampling winners +1.097% (P1 p 0.40; permutation p 0.55). The best
  random winner beat C0_1, B20_R173's released engine, by 0.27% (p 0.0004).
- **Record:** `docs/checkpoints/B20_R174_RECORD.md`. The record tests are `RecordB20R174` in
  `tests_genesis/test_search_vs_random_study.py`.
