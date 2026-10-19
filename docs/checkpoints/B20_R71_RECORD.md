# B20_R71 record: the system's representation engine with physics move rules (`represent-search-v1`)

- **Run by:** the builder. Engineering only; no study, claim, rule, comparator or package change.
- **Why:** idea 3 of `docs/PHYSICS_INSPIRED_PLAN.md`. The engine that turns every invented representation into a
  solver (`invention.representations.represent_and_repair`) is zero-temperature descent, which stops at the first
  local optimum. B20_R66, R68 and R70 measured the cost on large hosts: the candidate is optimal on 3–4 of 10–13
  certified n60 hosts and is the slowest of four methods by time-to-solution.

## What was built

`candidate_kinds/represent_search.py`, registry-v2 kind `represent-search-v1`, parameters
`{representation, move, cpu_seconds}`:
- **representation:** any of B18's typed proposals whose soundness mode on the domain is SUFF or EQ, read from the
  same Lean-checked package the v1 kind uses (on triangle-free hosts: cross_2, adjacent_2, adjacent_3, ordered_2);
- **move:** a closed choice of three rules over encodings, all followed by the same greedy repair:
  - `descent`, the frozen engine's rule (first-improvement one-label changes in random sweeps, until none helps);
  - `eo`, τ-extremal optimization (fitness: the fraction of a vertex's host edges the decoder keeps);
  - `anneal`, simulated annealing (Metropolis acceptance, T from 2.0 to 0.05 geometrically over 200n proposals).
The repair here is faster than the frozen engine's (incremental neighbour sets), so comparisons between the rules
of this kind isolate the move rule; B20_R72 also reports the descent rule against the frozen candidate, to show
what the faster repair alone is worth. The frozen v1 candidate and its engine are not touched.

Identity: the kind's file, `invention/representations.py`, `invention/soundness.py` and
`formal_research/triangle_theory.py` (everything the child imports to decode), plus the v2 core.

## Tests

`tests_genesis/test_represent_search.py` (6): only licensed representations and closed fields (unsound and unknown
proposals refused); the identity covers the representation engine; the kept-edge counts equal the frozen decoder's
for every proposal; descent ends at a local optimum; every licensed representation and move finds K10's 25 with
a checked witness; a metered runc run per move.
