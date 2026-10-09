# Genesis Batch 37 — Independent C4 replay (DEV)

Date: 2026-10-09

## Delivered

- `c4_independent_replay.py`: enumerates all non-induced C4 cycles as edge-bitmasks and solves minimum cycle-hitting set with a memoized recurrence, independently of the existing maximum-subgraph branch-and-bound optimizer.
- `cross_check`: validates candidate witness membership, C4-freeness, optimum count, and independently recomputes the optimum.
- `test_c4_independent_replay.py`: 12 tests, including all 64 graphs on 4 labeled vertices and 20 seeded 7-vertex graph instances.

## Verification

`python -m unittest discover -q`: 213 tests passed. Exact finite replay limited to 20 host edges. The two algorithms share the same runtime and source archive, so they are not independent institutional replication. The cycle enumeration and witness check are Python code, not formal proof terms.

## Limitations / next work

No trusted Lean installation; no Lean proof replay. No fresh independently held sealed graph panel; seeded examples are visible to developers. No claim of mathematical novelty, general theorem, or improved research policy. Next: sealed graph-family experiment, stronger baselines, and a separate custodian-run checker on trusted hardware.
