# B20_R178 (SR-1a): the obstacle loop on the state-management testbed

The run of `scripts/b20r178_repair_bench.py` (preregistered at `0e5d46f`), from the clean clone `/home/claude/r178-run`
on CPU 1, 30 Oct 2026, 23:50:56 to 23:58:15 SGT. The record is `docs/checkpoints/B20_R178_RECORD.md`; the record
tests are `RecordB20R178` in `tests_genesis/test_repair_bench_study.py`.

- `result.json`: the verdicts and tables (MILESTONE_DEMONSTRATED; NOLOCAL_BEATS_LOOP, RANDOM_BEATS_LOOP,
  ENUM_BEATS_LOOP, NO_DIFFERENCE_SHOWN against retrieval; REUSE_SHOWN);
- `rows.jsonl`: one row per episode (phase, defect or control, job seed, arm, outcome, verification, promotion,
  resume, retention, costs);
- `episodes.jsonl`: per episode, the research plane's record (failure, reproduction, diagnosis with the obstacle
  record, regression test, synthesis, patch and diff, isolated test, what it was told of the verdict, resume), the
  kernel's record (the full verdict, the Supervisor's decision, the job's runs, CPU of every party) and the final
  source of every changed component;
- `isolation.json`: what the research plane and the trial executor could read and write, measured at the start;
- `vault_dev.jsonl` (after phase 1), `vault_after_seed1.jsonl` and `vault_grown.jsonl` (phase 4(a));
- `run.log`: the script's output.
