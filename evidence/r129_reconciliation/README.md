# B20_R129 reconciliation: inv1 and decfall

Daniel's directive of 24 Oct 2026, 15:35, item 5. This is a read-only recomputation from B20_R129's saved evidence
(`evidence/adaptive_scientist_b20r129/`); no study was run. Script: `scripts/b20r129_reconcile.py`. Test:
`tests_genesis/test_r129_reconcile.py`, which recomputes `summary.json` and checks the preregistered numbers against
B20_R129's own summary.

## Which rule was selected, and on which set

Genesis's scientist was chosen on the **validation** set (100 worlds, seeds from 4000), before the test, by the
preregistered rule: the fewest mean experiments needed; ties go to the higher mean hidden-cause F1 at 4.

| Rank | Rule | Experiments needed (validation) | F1 at 4 (validation) |
|---|---|---|---|
| 1 | **decfall** (builder-designed lookahead; **chosen**) | 4.42 | 0.369 |
| 2 | inv1 (found in Genesis's acquisition language) | 4.59 | 0.379 |
| 3 | hybrid | 4.96 | 0.236 |
| 4 | eig | 4.97 | 0.238 |
| 5 | dec | 4.99 | 0.231 |
| 6 | decf | 5.05 | 0.325 |

**What inv1 is.** `max (sqrt(sq(decall)) * sq(min(pf, 1.0)))` simplifies exactly to `max(decall * pf^2)` under the
features' declared ranges. It was a random program in search 0's initial population, selected on training data. The
judge released nothing in any of B20_R129's four searches.

## Is the difference statistically supported?

**Preregistered** (B20_R129's secondary tests, uncorrected; test set, 200 worlds; experiments needed; two-sided
Wilcoxon, zeros dropped):

| Comparison | Means | Improvement of inv1 [bootstrap 95%] | Non-zero | p | Supported? |
|---|---|---|---|---|---|
| inv1 vs decfall | 4.34 vs 4.49 | 0.15 [−0.045, 0.35] | 108 | 0.158 | **No** |
| inv1 vs eig | 4.34 vs 4.98 | 0.64 [0.42, 0.87] | 135 | 1.7 x 10^-7 | Yes |

**Exploratory** (not preregistered; Holm across these seven; two-sided):

| Set | Measure | Comparison | Improvement of inv1 [95%] | p | Holm p | Label |
|---|---|---|---|---|---|---|
| transfer (100) | experiments needed | vs decfall | −0.04 [−0.41, 0.34] | 0.59 | 0.59 | NO_DIFFERENCE |
| test | experiments needed | vs dec | 0.625 [0.41, 0.85] | 1.6 x 10^-7 | 8.1 x 10^-7 | inv1 better |
| test | experiments needed | vs hybrid | 0.62 [0.41, 0.85] | 3.5 x 10^-7 | 1.4 x 10^-6 | inv1 better |
| test | experiments needed | vs static_eig | 1.335 [1.08, 1.61] | 3.4 x 10^-16 | 2.0 x 10^-15 | inv1 better |
| test | experiments needed | vs degree | 1.35 [1.10, 1.62] | 1.1 x 10^-16 | 8.0 x 10^-16 | inv1 better |
| test | hidden-cause F1 at 4 | vs decfall | +0.054 [0.020, 0.087] | 0.0026 | 0.0077 | inv1 better |
| transfer | hidden-cause F1 at 4 | vs decfall | +0.077 [0.034, 0.121] | 0.0027 | 0.0077 | inv1 better |

## Reconciled statements

1. Genesis selected **decfall**, correctly by its preregistered rule. inv1 ranked second on validation.
2. inv1's lower mean on test (4.34 against 4.49) is **not** a supported difference: p = 0.158 on test and 0.59 on
   transfer. inv1 and decfall tie on the primary outcome.
3. "inv1 beats every established acquisition" holds:
   - against eig, preregistered;
   - against dec, hybrid, static_eig and degree, exploratory but Holm-corrected.
4. Not preregistered, but Holm-corrected: inv1 reaches a **higher hidden-cause F1 after 4 experiments** than decfall,
   by 0.054 on test and 0.077 on transfer. It learns more early without reaching the ceiling sooner. Only a new
   preregistered study can claim this.
5. "Invented" means found in Genesis's language and selected on training data; it was not released by the judge.
   Its credit as an invention is that of a well-chosen random program.

The ledgers (`BATCHES.md`, `NEXT_ACTIONS.md`, `docs/OMEGA_RESULTS_LEDGER.md`) were reworded to match.
