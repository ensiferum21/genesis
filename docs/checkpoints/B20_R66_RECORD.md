# B20_R66 record: E1d at n60 replicates and leads HiGHS through 120× (REPLICATED_ADVANTAGE_THROUGH_120X; DEV)

- **Run by:** the builder. DEV only, outside every calibrated setting; no claim.
- **Setup commit:** `f2731ba` (script SHA-256 `9618ae76…9aaa`), run unchanged at `4341806`, alone, pinned to CPU 0.
- **Evidence:** `evidence/e1d_n60_b20r66/`.

## Problem

B20_R64 found, on 10 hosts, that the 0.5 s candidate leads HiGHS at 64× its budget on n60 planted hosts. A
positive pilot gets an internal replication on fresh hosts before anyone leans on it (as B20_R57 → R59). This study
also raises HiGHS to `milp-highs-v1`'s ceiling, 60 s (120×).

## Design

- **Hosts:** 20 fresh n60 planted (0.8, 0.06) hosts, 415–465 edges, excluding every host named in the evidence.
- **Arms:** the candidate at 0.5 s; HiGHS at 32 s and 60 s; all in runc.
- **Rule:** B20_R63's per-budget rule (ADVANTAGE iff the 90% interval's lower end > 0.5); validity: median HiGHS
  CPU/budget ≥ 0.9 where it ran to its limit.

## Result: **REPLICATED_ADVANTAGE_THROUGH_120X**

| HiGHS budget | candidate − HiGHS | W / T / L | CPU delivery |
|---|---|---|---|
| 32 s (64×) | +16.65 [11.0, 22.6] | 19 / 1 / 0 | 0.994 |
| 60 s (120×) | +2.00 [1.35, 2.65] | 17 / 2 / 1 | 0.990 |

Mean gap to the proven upper bound: candidate 1.65, HiGHS 32 s 18.3, HiGHS 60 s 3.65. The reference certified
10 of 20 hosts; the candidate is optimal on 4 of them, HiGHS on none.

## Consequence

- B20_R64's n60 result replicates (+16.65 vs +17.6 at 64×).
- The lead at 120× is small (2 edges) and HiGHS's gap is closing fast; the crossover at n60 is likely just above
  `milp-highs-v1`'s 60 s ceiling. The pattern of B20_R63 holds at every size measured: the candidate's advantage
  over the exact solver is speed, and the catch-up budget grows with host size.
- At n60 the candidate leaves room: optimal on 4 of 10 certified hosts. That makes B20_R68 (a standard max-cut
  heuristic as a domain baseline) sharper on these hosts.
- No package, rule, comparator or bound changes. B20_R64's three reviewer decisions (family-space extension,
  lifting the 200-edge bound for the LP-dual route, a reference that certifies at n60) still stand.

## Tests

`tests_genesis/test_e1d_n60.py`: Design (4); Record (3): the verdict recomputes; the arms are the recorded ones;
the hosts are fresh, match the rows and are in the e1/e1b exposure addenda.
