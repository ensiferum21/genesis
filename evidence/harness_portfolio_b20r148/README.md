# B20_R148 evidence: the portfolio of discovery processes (Genesis Ω², DEV)

Written by `scripts/b20r148_harness_portfolio.py` (preregistered `251c956`, SHA-256 `d20a30d4…3409`), alone on
CPU 0 from a clean worktree of `13bd014`, 26–27 Oct 2026, in four slices. The record is
`docs/checkpoints/B20_R148_RECORD.md`: verdict NOT_SHOWN; G3_NOT_SHOWN; H1 UNIVERSAL_HARNESS by its rule.

| File | What it holds |
|---|---|
| `summary.json` | design, development choices, norms and highs, mean AUDC per arm and task, mean CPU per arm, H1, the primary family (T1–T3 with Holm), secondary comparisons, validity, verdict |
| `rows.jsonl` | the 600 test runs (task, arm, seed): the measured T value of the validated answer at each checkpoint (32 … 1,024), evaluations charged, the allocation across processes, CPU (evaluation and logic), the answer and its V score |
| `norms.json` | per test task: low (median of 32 reference random programs) and the stated references |
| `dev.json` | written before the test phase: H*, the tuned parameters of every process and the tuning table |
| `dev_rows.jsonl`, `dev_norms.json` | the 108 development runs that chose H* (six development tasks × six processes × seeds 100–102) and their norms |
| `instances/` | the acquisition worlds of every split (development and test) and the max-cut graphs, as generated from the preregistered seeds; formula items are not stored (they regenerate from their seeds in under a second) |
| `run.log` | the log of all four slices |

Re-check: `tests_genesis/test_harness_portfolio.py::RecordB20R148` (the script's digest, validity, the verdict and
every primary label recomputed from these rows by `analyse`, development from development rows only).
