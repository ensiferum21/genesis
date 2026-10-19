# B20_R73 record: multiverse analysis of E1d's DEV verdicts (12 ROBUST, 5 MIXED, 1 FRAGILE)

- **Run by:** the builder. Analysis of committed rows only; no verdict changes.
- **Setup commit:** `b8e4fba`, script SHA-256 `698621ed…5889`, sent to Daniel before the run.
- **Evidence:** `evidence/multiverse_b20r73/`. Physics plan, idea 5 (multiverse and many-analysts analysis).

## Result

- 18 contrasts from B20_R63, R64, R66, R68 under 54–108 reasonable analyses each: 12 ROBUST, 5 MIXED, 1 FRAGILE.
- Study level: B20_R64 (ADVANTAGE_GROWS) and B20_R68 (E1D_MATCHES_DOMAIN_HEURISTIC) ROBUST; B20_R63 (crossover at
  8 s; 4 s in 11% of analyses) and B20_R66 (advantage through 120×; a crossover by 120× in 15%) MIXED.
- FRAGILE: B20_R68 Part B, tabu ahead at n60 (−1.15): it holds only with the mean and MUE ≤ 0.5.
- MUE and the mean-vs-median choice cause nearly all changes; the seed and the interval method almost none.

## Consequence

- The central conclusions are robust; crossover points should be quoted as ranges.
- B20_R68 Part B is now labelled fragile wherever it is cited; B20_R70 is the separate evidence for heuristics
  beating the candidate at n60.
- Two concrete questions for the statistician (B19-OPEN-4): the MUE, and mean versus median for per-host
  differences that are mostly ties.

## Tests

`tests_genesis/test_multiverse.py`: Design (7); Record (1).
