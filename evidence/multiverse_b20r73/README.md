# B20_R73 evidence: how robust are E1d's DEV verdicts to reasonable analysis choices? (multiverse analysis)

An analysis of committed DEV evidence. It changes no verdict and licenses nothing.
- **Script:** `scripts/b20r73_multiverse.py`, committed with its universe, rule and expectation before it ran
  (`b8e4fba`; SHA-256 `698621ed…5889`, sent to Daniel before the run). Analysis only: it reads the rows of B20_R63,
  R64, R66 and R68 and runs no solver. 15 s. `code_identity` in `summary.json`.

## Why

Each E1d study fixed one analysis in advance (mean difference, 90% percentile bootstrap, MUE 0.5, stratified where
there are strata). Multiverse analysis (Steegen et al. 2016) and many-analysts studies (Silberzahn et al. 2018)
report how many *reasonable* analyses agree with a conclusion. The statistician's review (B19-OPEN-4) is still
pending; this shows where the conclusions depend on the choices.

## The universe

MUE ∈ {0.25, 0.5, 1.0} × level ∈ {90%, 95%} × {bootstrap mean, Student-t mean, bootstrap median} ×
{as preregistered, pooled} × bootstrap seed ∈ {the study's, 20267301, 20267302, 20267303}: 108 analyses for a
stratified contrast, 54 for an unstratified one. Study-level verdicts are recomputed with each study's own
combination rule. ROBUST ≥ 90% agreement with the preregistered verdict, MIXED 50–90%, FRAGILE < 50%. A design
test checks that the preregistered analysis reproduces every study's verdict exactly.

## Result: 12 ROBUST, 5 MIXED, 1 FRAGILE of 18 contrasts

| Contrast | Preregistered | Agreement | Label | Changes under |
|---|---|---|---|---|
| B20_R63 HiGHS 2 s | AHEAD | 1.00 | ROBUST | — |
| B20_R63 HiGHS 4 s | AHEAD | 0.89 | MIXED | median estimator, pooling, MUE 1.0 |
| B20_R63 HiGHS 8 s | UNRESOLVED | 0.57 | MIXED | becomes NO_MATERIAL_DIFFERENCE under the median, pooling, 95% intervals |
| B20_R63 HiGHS 16 s, 32 s | NO_MATERIAL_DIFFERENCE | 1.00 | ROBUST | — |
| B20_R64 n40 2 s, n40 32 s, n50 2 s, n50 8 s, n60 2/8/32 s | as preregistered | 1.00 | ROBUST | — |
| B20_R64 n40 8 s | NO_MATERIAL_DIFFERENCE | 0.81 | MIXED | MUE 0.25 |
| B20_R64 n50 32 s | UNRESOLVED | 0.78 | MIXED | becomes NO_MATERIAL_DIFFERENCE at MUE 1.0 |
| B20_R66 HiGHS 32 s | AHEAD | 1.00 | ROBUST | — |
| B20_R66 HiGHS 60 s | AHEAD | 0.85 | MIXED | MUE 1.0, median estimator |
| B20_R68 Part A | NO_MATERIAL_DIFFERENCE | 1.00 | ROBUST | — |
| **B20_R68 Part B** | **BEHIND** (tabu ahead) | **0.37** | **FRAGILE** | never BEHIND at MUE 1.0 or under the median; BEHIND only with the mean and MUE ≤ 0.5 |

**Study-level verdicts.**

| Study | Preregistered | Agreement | Label |
|---|---|---|---|
| B20_R63 | crossover at 8 s | 0.89 | MIXED (crossover at 4 s in 12 of 108 analyses) |
| B20_R64 | ADVANTAGE_GROWS | 1.00 | ROBUST |
| B20_R66 | REPLICATED_ADVANTAGE_THROUGH_120X | 0.85 | MIXED (REPLICATED_CROSSOVER_BY_120X under MUE 1.0 or the median) |
| B20_R68 | E1D_MATCHES_DOMAIN_HEURISTIC | 1.00 | ROBUST |

(For an unstratified study the study-level grid repeats the pooled and preregistered analyses, which are the same;
the shares are unaffected.)

## Reading

- **The central conclusions hold under every analysis.** E1d's candidate beats HiGHS at short budgets (B20_R63 at
  2 s, B20_R64 at every n60 budget), the advantage grows with host size (B20_R64, ROBUST), and a standard max-cut
  heuristic ties the candidate on the calibrated settings (B20_R68, ROBUST).
- **The boundaries move.** Where exactly HiGHS catches up (B20_R63's crossover at 8 s, sometimes 4 s; B20_R66's 120×
  advantage, a crossover under a 1-edge materiality threshold) depends on the analysis. A claim should quote these
  as ranges, not points.
- **One verdict is fragile: B20_R68 Part B,** "tabu search is ahead of the candidate at n60". It holds only with the
  mean and MUE ≤ 0.5; with a 1-edge threshold or the median (the typical host difference is a tie or one edge) it is
  UNRESOLVED. The direction is not in doubt (13 of 20 hosts favour tabu, 1 favours the candidate), but its size is
  close to the materiality threshold. B20_R70's time-to-solution result is separate evidence that heuristics beat
  the candidate at n60, and it rests on a different measurement.
- **Which choices matter.** MUE and the estimator (mean vs median) cause nearly all changes; the bootstrap seed and the
  interval method (bootstrap vs t) almost none. These are the two questions to put to the statistician
  (B19-OPEN-4).
- **The builder's expectation:** right on every point except that B20_R68 Part B came out FRAGILE, not MIXED.

## Tests

`tests_genesis/test_multiverse.py`: Design (7), including that the preregistered analysis reproduces every
study's verdict and that the t interval is the textbook one; Record (1): the whole summary recomputes.
