# Genesis Batch 39 — C4 public hard-instance probe (DEV)

## Changes
- Added `c4_hard_cases.py`: reproducible random and bipartite graph families, strict graph normalization, exact optimization and independent cycle-hitting-set replay.
- Added `test_c4_hard_cases.py`: six adversarial and deterministic regression tests.
- Added two public DEV result files with 60 cases each and 33-start versus two-start greedy comparisons. Same graph roster, independent replay in both runs.

## Observed
- 60 public DEV graphs, n=6..8, <=20 host edges.
- 33-start greedy (one fixed plus 32 shuffled starts): 0 suboptimal, 60 ties against exact optimum.
- Two-start greedy (one fixed plus one shuffled): 30 suboptimal, maximum optimum gap 2 edges.
- Exact search and separate hitting-set recurrence agree on all cases.
- These are unequal-budget, research-visible development runs. They do not support a performance, novelty, or generalization claim.

## Remaining
- Better baselines, matched computational resources, preregistered independently controlled fresh tasks, independent proof checker and Lean formal verification.
- No theorem discovery, policy learning or recursive improvement established.
