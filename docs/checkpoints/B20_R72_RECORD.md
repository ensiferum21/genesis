# B20_R72 record: physics move rules do not improve the system's representation engine (NO_GENERAL_IMPROVEMENT; DEV)

- **Run by:** the builder. DEV only; no claim or package change.
- **Setup commit:** `3d69ae5`, script SHA-256 `5af84e42…64a2`, sent to Daniel before the run. Run alone, pinned,
  1,257 s, 240 runs in runc, no failures.
- **Evidence:** `evidence/represent_moves_b20r72/`.

## Problem

Would τ-extremal optimization or simulated annealing, in place of descent, improve the engine that turns every
invented representation into a solver (physics plan, idea 3)?

## Result: **NO_GENERAL_IMPROVEMENT** (the builder expected annealing to improve every representation)

- cross_2 and adjacent_3: no material difference for either physics move (all within ±0.2 of descent).
- ordered_2: both physics moves are worse (eo −1.25 [−1.95, −0.55]; anneal −2.50 [−3.80, −1.40]).
- The same descent with this kind's faster repair beats the frozen candidate by +0.45 [0.25, 0.65] (9/11/0).
- Discrete simulated bifurcation is best overall (13 of 16 optima, gap 0.40), ahead of the best physics-move arm
  by 0.55.

## Consequence

- The engine's limit at n60 and 0.5 s is speed, not trapping in local optima. The physics idea that works is
  whole-configuration dynamics (simulated bifurcation), not a different single-variable move.
- The plan's idea 3 is revised: the next candidate engine improvements are the faster repair (+0.45 measured) and an
  SB-style search over encodings. Neither is adopted.
- Limits: one budget, one size, one schedule; annealing with a longer schedule is untested.

## Tests

`tests_genesis/test_represent_moves.py`: Design (5); Record (3).
