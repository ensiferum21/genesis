# Genesis Batch 42 — Measured-resource C4 benchmark (DEV)

Implemented `c4_resource_benchmark.py` and nine tests. It measures process CPU nanoseconds, wall nanoseconds and peak Python traced allocations for full algorithm calls, alternates algorithm execution order, checks witnesses, enforces equal C4 feasibility-query caps, and independently recomputes finite optima with the cycle-hitting-set replay. Results: `BATCH42_RESOURCE_DEV.json`.

## Reproducible DEV run

40 generated graphs, `sample_cases(seed=20261011,count=40)`, budget 60 C4-feasibility queries per arm. Cycle-aware wins 2, multistart wins 1, ties 37. Median process CPU: baseline 1.249 ms, cycle-aware 1.450 ms. Median traced Python peak allocations: baseline 7.20 KiB, cycle-aware 7.43 KiB. These values are machine/run dependent and should not be treated as reproducible constants. Cumulative tests: 262 passed.

## Limitations

These are public local DEV tasks, not independently sealed. Query budgets match but CPU time, wall time and memory are only measured, not capped or equalized. `tracemalloc` is not resident set size (RSS). Both methods use Python and share graph conventions; the exact replay is algorithmically distinct but not independently operated. Timing measurements are noisy and should be repeated with process isolation. No Lean proof, new theorem, or autonomous improvement demonstrated. `promotion_allowed=false`.

## Next

Implement fair CPU-budgeted subprocess trials and preregistered unseen task custody, ideally with an independently controlled evaluator; repeat trials to quantify timing variability.
