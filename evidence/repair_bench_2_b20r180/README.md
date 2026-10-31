# B20_R180 (SR-1a2): the obstacle loop version 2 on new held-out defects in larger components

The run of `scripts/b20r180_repair_bench_2.py` (preregistered at `9305178`), from the clean clone `/home/claude/r180-run`
on CPU 1, 31 Oct 2026, 08:46:15 to 09:55:53 SGT. The record is `docs/checkpoints/B20_R180_RECORD.md`; the record tests
are `RecordB20R180` in `tests_genesis/test_repair_bench_2_study.py`.

- `result.json`: MILESTONE_DEMONSTRATED; NO_DIFFERENCE_SHOWN against loop_v1, nolocal, random, enum and retrieval;
  REUSE_NOT_SHOWN; the tables;
- `rows.jsonl`: one row per episode (315); `episodes.jsonl`: the research and kernel records of each, and the final
  source of every changed component;
- `isolation.json`; `vault_dev.jsonl`, `vault_after_seed1.jsonl`, `vault_grown.jsonl`; `run.log`.
