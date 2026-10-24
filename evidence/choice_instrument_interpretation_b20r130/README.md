# B20_R130 evidence: choice, instrument and interpretation, separated: CHOICE

Builder-run on DEV (Genesis Ω, Ω1; Daniel's notes of 24 Oct 2026, 13:58). It licenses nothing.
- **Script:** `scripts/b20r130_choice_instrument_interpretation.py`, preregistered at `f812701` before B20_R129 ran.
- **Run:** alone on CPU 0, 24 Oct 2026, 18:31:43–19:33:34 SGT (3,707 s).
  - It ran from a clean worktree of `56e1301`: the preregistration plus later code that this study does not use.
  - It started two hours after B20_R127 ended, because of the builder's delay.
- **Code identity:** `48d08b3e…`, the tree of `56e1301`.
- **The other core.** During the run the builder used CPU 1 for tests and engineering, and for B20_R132's development
  look (engine runs). This study's outcomes do not depend on timing; only the CPU figures it reports could.

| File | What |
|---|---|
| `worlds_<set>.jsonl` | Every world (calibration 100, A/B/C 40 each, test 200, transfer 50): seed, settings, planted truth, FCI's preparation, the instrument p-value table |
| `models.json` | The per-pair model, the joint re-analysis priors and the global estimator's thresholds (tb 0.35, to 0.10), all fitted on the calibration worlds only |
| `instruments.json` | Every instrument of the language (45) with its ceiling on A+B and on C; the chosen one (gap + pgap at alpha 0.05) |
| `runs.jsonl` | 14,150 runs: every (world, choice, order, interpretation, budget), its targets, answer and F1s |
| `summary.json` | The tests, Holm, the verdict, means, secondary tests, identifiability, convergence, CPU |
| `run.log` | The run |

## Result: CHOICE (the interpretation hypothesis failed)

**Primary tests** (200 test worlds; the measure is a world's hidden-cause F1 averaged over budgets 2, 4, 6 and 8;
Holm):

| Test | Comparison | Mean difference | Non-zero | p | Label | Holm |
|---|---|---|---|---|---|---|
| T_choice | Genesis's scientist (decfall) against random, both under the global estimator | **+0.165** | 194 | 7.5 x 10^-26 | **CHOICE_BETTER** | rejected |
| T_interpretation | global against per-pair, both with Genesis's experiments | +0.021 | 180 | 0.52 | NO_DIFFERENCE | not rejected |
| T_instrument | the invented instrument (gap + pgap) against B20_R129's, per-pair, every experiment | −0.014 | 130 | 0.41 | NO_DIFFERENCE | not rejected |

**Hidden-cause F1 by budget** (test; directed F1 in brackets):

| Choice, interpretation | 2 | 4 | 6 | 8 | all 10 |
|---|---|---|---|---|---|
| genesis, global | 0.136 (0.50) | 0.366 (0.73) | **0.581** (0.87) | **0.686** (0.95) | — |
| genesis, per-pair | 0.176 (0.69) | 0.375 (0.81) | 0.530 (0.88) | 0.602 (0.92) | — |
| genesis, joint re-analysis | 0.176 | 0.364 | 0.528 | 0.644 | — |
| random, global | 0.072 | 0.180 | 0.340 | 0.516 | — |
| random, per-pair | 0.026 | 0.124 | 0.262 | 0.426 | — |
| degree, global | 0.079 | 0.220 | 0.430 | 0.588 | — |
| oracle, global (reference; reads the truth) | 0.268 | 0.488 | 0.608 | 0.636 | — |
| every experiment: global / per-pair / LLC / per-pair with the invented instrument | | | | | 0.688 / 0.613 / 0.439 / 0.599 |

**Secondary (uncorrected):**
- **Directed F1:** choice better (+0.071, p = 2.6 x 10^-18). Interpretation **worse** (−0.060, p = 1.3 x 10^-11): the
  global estimator orients edges less well than the per-pair framework at 2–4 experiments.
- **Joint re-analysis against per-pair:** NO_DIFFERENCE (p = 0.07).
- **Global against LLC with every experiment:** global better, 0.688 against 0.439 (p = 8 x 10^-20). This rests on
  thresholds fitted for the global estimator's fits; the development looks gave LLC 0.71–0.77 with thresholds chosen
  for it. It is **not** evidence that the established estimator is worse.
- **The headline**, Genesis + global at 4 against random + per-pair at 8: 0.366 against 0.426.
  - Non-inferiority is NOT_SHOWN; the two-sided test says RANDOM@8_BETTER (p = 0.011).
  - Genesis + global first matches random's 8 at **6** experiments.
- **Regret against the oracle** (global): 0.13, 0.12, 0.03 and −0.05 at 2, 4, 6 and 8. At 8, Genesis's choices beat
  the oracle's, whose order is by truth, not by what resolves the estimator.
- **Transfer** (50 worlds, p = 14, 4 hidden causes): choice better (+0.162, p = 1.9 x 10^-9); interpretation
  NO_DIFFERENCE (p = 0.89).
- **Identifiability** (genesis + global): recall of hidden causes by how many endpoints were intervened on.

  | Budget | Neither endpoint | One | Both |
  |---|---|---|---|
  | 4 | 0.09 (108 causes) | 0.13 (267) | 0.72 (225) |
  | 8 | 0.00 (3) | 0.37 (78) | 0.64 (519) |

- The global fit converged (L-BFGS) in 69% of fits. Mean CPU per answer: global 0.30 s, joint 0.60 s, per-pair
  0.0005 s.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| INTERPRETATION_BETTER | **No** (failed hypothesis). Global is better only from 6 experiments on (0.581 against 0.530 at 6, 0.686 against 0.602 at 8, 0.688 against 0.613 with all), worse at 2 and level at 4, so the primary measure averaged over 2–8 shows no difference. Directed F1 is worse |
| CHOICE_BETTER | Yes, by a wide margin, on test and on transfer |
| T_instrument NO_DIFFERENCE | Yes |
| The headline borderline (dev: 0.33 against 0.34) | Not reached: 0.37 against 0.43; it needs 6 experiments |
| global close to LLC with every experiment | No: LLC 0.44 under thresholds fitted for the global estimator (see above) |
| Recall near zero with neither endpoint intervened | Yes: 0.09 at 4, 0.00 at 8 |

## What it means

- **The capability that is verified here is experiment choice.** The scientist Genesis chose in B20_R129, carried
  into a different interpretation, beats random choice by 0.17 hidden-cause F1. That is the second independent
  confirmation of Ω1.
- **The global interpretation is not a verified capability at the preregistered measure.** Its advantage appears only
  with 6 or more experiments, where both endpoints of most hidden causes have been intervened on (the
  identifiability table). With 2–4 experiments the bottleneck is what the experiments make identifiable, not how
  they are interpreted.
- **Consequences:**
  - **B20_R131**'s trigger is not verified: by its preregistration it records NO_VERIFIED_TRIGGER and runs only its
    null trigger and comparators.
  - The next step on this track is co-invention, choosing experiments that serve the global estimator, measured at
    6–8 experiments where it helps. It would be preregistered as a new study.
- **Limitations:**
  - one family of linear Gaussian worlds;
  - thresholds fitted on calibration worlds for the global estimator and reused for LLC;
  - 31% of global fits stopped before L-BFGS converged; their answers are used as they are.

## The record

`RecordB20R130` (in `tests_genesis/test_choice_instrument_interpretation.py`):
- recomputes the analysis, the Holm family, the verdict and identifiability from the saved rows;
- checks validity and every set's size;
- recalibrates the per-pair model;
- re-chooses the instrument from its table;
- refits the thresholds on the 100 calibration worlds;
- regenerates 5 worlds (3 test, 2 transfer) from their seeds, replays every global, per-pair, LLC and
  invented-instrument answer of theirs exactly, and checks the code identity.
