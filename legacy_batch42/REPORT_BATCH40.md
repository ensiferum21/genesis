# Genesis Batch 40 — Query-budgeted C4 heuristic comparison (DEV)

Implemented `c4_budget_search.py`: a multistart greedy method and a one-for-two local edge swap method, both charged one unit for each full C4 feasibility predicate call. A separate exact cycle-hitting-set replay verifies the optimum for every tested host. Added `test_c4_budget_search.py` (8 tests). Cumulative unittest suite: 245 passing.

## Public development results

60 deterministic public graph instances, 60 feasibility queries per arm: swap wins 2, multistart wins 20, ties 38. Swap suboptimal on 25 instances; multistart suboptimal on 9. At budget 660, both tie at optimum on all 60. Results are in `BATCH40_RESULTS.json`.

## Caveats

- Public, previously used development families; budgets 15, 30, 60, 120, 660 were inspected. This is NOT a sealed prospective evaluation.
- Only feasibility queries are counted, not cycle preprocessing, candidate construction, wall time, memory, or randomization overhead. NOT matched CPU.
- The exact replay and heuristic share graph normalization and C4 cycle definitions; not independent institutional replication.
- No new theorem, Lean proof, policy learning, or self-improvement claim.
- Future work: better targeted search methods, matched wall/CPU/resource budgets, and separately frozen fresh test instances.
