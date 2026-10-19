# B20_R70 record: time-to-solution scaling, E1d's candidate against three domain heuristics (E1D_SLOWER_THAN_SOME; DEV)

- **Run by:** the builder. DEV only; no claim, and no package, rule or comparator changes.
- **Setup commit:** `e48c5e7`, script SHA-256 `ba258a47…6a62`, sent to Daniel before the run. Run alone, pinned
  to CPU 0, 3,424 s, 2,688 runs in runc, no failures.
- **Evidence:** `evidence/tts_scaling_b20r70/`.
- **Origin:** idea 1 of `docs/PHYSICS_INSPIRED_PLAN.md`: benchmark speed as quantum-annealing studies do (Rønnow et
  al. 2014), by time-to-solution at the optimal run time per size, not one fixed budget.

## Design

8 fresh planted hosts at each of n40, n50, n60. Arms at every rung of 0.02–2 s, 4 seeds each: the candidate,
`maxcut-tabu-v1`, `ising-dsb-v1`, `maxcut-eo-v1`. Target: certified optimum (20 of 24) or best known. Primary:
median log2(TTS*_H / TTS*_candidate) per size and heuristic, bootstrap 90% interval, 2× margins.

## Result: **E1D_SLOWER_THAN_SOME**

| | n40 | n50 | n60 |
|---|---|---|---|
| tabu | −2.06, HEURISTIC_FASTER | −3.32, HEURISTIC_FASTER | −3.32 [−4.89, +0.24], UNRESOLVED |
| dSB | −0.74, UNRESOLVED | −2.32, HEURISTIC_FASTER | −3.20 [−4.59, −2.56], HEURISTIC_FASTER |
| EO | −0.94, UNRESOLVED | −1.82, UNRESOLVED | −1.32, UNRESOLVED |

The candidate's median TTS* grows 0.14 → 0.5 → 0.85 s (75th percentile 0.2 → 0.5 → 3.4 s); tabu's and dSB's
stay at 0.02 and 0.1 s, their effective floors. Both disclosed biases (tabu's floors, dSB's start-up inside its
budget) understate the heuristics' advantage.

The builder's expectation was right overall, and wrong in one part: tabu at n60 is UNRESOLVED, not
HEURISTIC_FASTER, because it needed 7 s on one host and never solved another.

## Consequence

- Measured by time-to-solution, E1d's candidate is the slowest of the four methods at n50 and n60, and its time
  grows fastest with size. Its lead over HiGHS is not a speed advantage over the field.
- With B20_R68 this is the DEV answer to the strong-baseline question for E1d: if domain heuristics count, E1d has
  no GV3 claim. B20R41-OPEN-1, the GV4 fallback draft and the review brief now cite it.
- For the system: its invention search found the right reduction, but its search engine is not competitive.
  B20_R71–R72 test whether physics move rules fix that for every representation it invents.

## Tests

`tests_genesis/test_tts_scaling.py`: Design (7); Record (3).
