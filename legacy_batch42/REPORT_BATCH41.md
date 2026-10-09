# Genesis Batch 41 — Cycle-aware C4 search (DEV)

Added `c4_conflict_search.py`, a cycle-incidence-aware greedy multistart heuristic with an explicit C4-feasibility query budget, and `test_c4_conflict_search.py` (8 tests). It uses an exact independent hitting-set replay to check the optimum on each graph (<=20 edges).

## Results at 60 feasibility queries per method

| Dataset | Cycle-aware wins | Multistart wins | Ties | Cycle-aware suboptimal | Multistart suboptimal |
|---|---:|---:|---:|---:|---:|
| 60 public DEV graphs (seed 20261009) | 8 | 1 | 51 | 2 | 9 |
| 60 newly generated DEV graphs (seed 20261010) | 4 | 1 | 55 | 3 | 6 |

Exact replay checked optima on all 120 graphs. 253 cumulative unittest tests passed. Machine-readable trial records in `BATCH41_PUBLIC_DEV.json` and `BATCH41_FRESH_DEV.json`.

## Limitations

The algorithm was developed using the known graph generator and public DEV family. The fresh set is not independently sealed, the graph families are not a broad sample, and the query budget does not charge cycle indexing, preprocessing, wall time, or CPU time. Exact replay shares some graph conventions with the candidate. This does not demonstrate a general mathematical discovery, formal proof, or autonomous research improvement. No promotion allowed.

## Next

Freeze a prospectively held-out graph distribution under external custody; measure CPU time and memory as well as feasibility queries; compare against 33-start greedy and stronger exact/constraint baselines, then seek independent replay and Lean verification.
