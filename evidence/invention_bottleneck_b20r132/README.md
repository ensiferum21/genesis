# B20_R132 evidence: the four bottlenecks of Genesis's invention (DEV)

Written by `scripts/b20r132_invention_bottleneck.py` (preregistered `c0431f6`, SHA-256 `42769fcc…a0a6`), alone on
CPU 0 from a clean worktree of `13bd014`, 27 Oct 2026 from 00:09 SGT. It ran in four slices. The third was stopped by
a container restart 4,583 s in; every run saved before the restart was kept, and the fourth slice resumed from them.
A first attempt on 24 Oct left no evidence. The record is `docs/checkpoints/B20_R132_RECORD.md`: verdict NOT_SHOWN;
diagnosis EXPRESSIVENESS in every class.

| File | What it holds |
|---|---|
| `summary.json` | the analysis (every trajectory, the per-class diagnosis with its four instruments, P1, P2, S1, releases and audits, the zero-signal counts, verdict), validity (median CPU per budget, consistency, the protected judge), the graph identities, the inputs of the analysis (trajectories with every arm's release history, the T1 and T2 tables, baselines, REX at 10 s, the fixed pool) and the code identity |
| `runs.jsonl` | all 19,600 engine runs of the pinned `mcx2` binary, keyed by engine, graph, occurrence and budget: the checked cut and the CPU seconds |
| `controls.json` | the zero-signal and planted pool searches (releases, tau, found, released) and the power curves |
| `programs.json` | every engine program referred to by key |
| `run.log` | the study's own log, all four slices |

Re-check: `tests_genesis/test_invention_bottleneck.py::RecordB20R132`.
