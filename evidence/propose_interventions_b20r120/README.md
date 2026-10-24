# B20_R120 evidence: can Genesis propose the experiments that resolve hidden causes? NOT_SHOWN

Builder-run on DEV (Daniel's research alert of 22 Oct 2026, item 2). It licenses nothing.
- **Script:** `scripts/b20r120_propose_interventions.py`, preregistered at `3a6fee5` with B20_R119's procedure.
- **Run:** alone on CPU 0, 93 s, on 24 Oct 2026 (08:39–08:40 SGT).
  - A first attempt at 08:38 started while the container was restarting. It wrote nothing and never ran the study.
- **Code identity:** `65e89c0a…`, the committed tree `3a6fee5`.

| File | What |
|---|---|
| `runs.jsonl` | 360 runs (40 instances x 9 arms): answer, scores, intervention targets, the suspicion of each adjacent pair, CPU time, the planted confounded pairs and edges |
| `summary.json` | Means per arm, Test 1 (primary), the secondary tests, the verdict, validity |
| `run.log` | The run |

**Design, in one line:** 40 fresh instances (10 observed variables, 3 hidden confounders, 3 environments).
- **Arms:** FCI alone, and for budgets of 2 and 4 hard interventions (1,000 samples each), four ways of choosing
  targets: `random`, `degree`, Genesis's `suspicion`, and the `oracle` told the truth.
- **Primary test:** `suspicion` against `random` at budget 2, on the F1 of hidden-cause marks.

## Result: NOT_SHOWN

**Test 1:** `suspicion` against `random` at budget 2: **NO_DIFFERENCE** (3 non-zero differences, p = 1.0;
mean −0.02). The secondary tests all came out NO_DIFFERENCE: against `random` at budget 4, against `degree` at 2
and 4, and budget-4 interventions against FCI alone.

| Arm | Hidden-cause F1 | precision | recall | Directed F1 | Spurious rate |
|---|---|---|---|---|---|
| FCI alone | 0.19 | 0.28 | 0.17 | 0.29 | 0.49 |
| random, 2 | 0.19 | 0.29 | 0.16 | 0.49 | 0.50 |
| degree, 2 | 0.18 | 0.28 | 0.14 | 0.50 | 0.50 |
| **suspicion, 2** | **0.17** | 0.26 | 0.14 | 0.47 | 0.50 |
| oracle, 2 | 0.29 | 0.41 | 0.26 | 0.46 | 0.39 |
| random, 4 | 0.24 | 0.39 | 0.19 | 0.63 | 0.46 |
| degree, 4 | 0.22 | 0.35 | 0.18 | 0.69 | 0.46 |
| **suspicion, 4** | **0.23** | 0.38 | 0.18 | 0.69 | 0.46 |
| oracle, 4 | 0.47 | 0.65 | 0.42 | 0.60 | 0.16 |

**Validity:** every answer valid; every arm used exactly its budget of distinct targets.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| FCI marks some hidden causes (recall about 0.3) | Fewer: recall 0.17, precision 0.28 |
| GENESIS_PROPOSES_BETTER at budget 2 | **NOT_SHOWN**: no better than random |
| At budget 4, better than random and close to degree | Equal to both |
| INTERVENTIONS_HELP (budget 4 against FCI) | NO_DIFFERENCE on hidden-cause F1. Directed F1 rose from 0.29 to 0.69 |
| The oracle well above all | Yes: 0.29 and 0.47 |

## Why: post-hoc diagnosis (not preregistered; from the saved rows)

- **The choice of targets matters, and Genesis's signal for it is weak.** The oracle shows the headroom: +0.10 at
  budget 2 and +0.23 at budget 4.
  - Genesis's suspicion score gives the truly confounded adjacent pairs 0.53 on average and the others 0.48.
    FCI's marks and the environments' slope changes barely tell them apart at 3,000 samples.
  - The suspicion strategy did reach both ends of a confounded pair 8 times as often as random at budget 2: 0.20
    against 0.025 per instance. The oracle reached 1.0.
- **The decision rule loses correct marks.** Under do(X_i), dependence of X_j shows that i is an *ancestor* of j,
  not a direct cause. When i reaches j by another path, the rule turns a correct hidden-cause mark into a directed
  edge.
  - At budget 2, the suspicion arm lost 3 correct hidden-cause marks from FCI and gained none.
  - At budget 4 it lost 5 and gained 6; the oracle lost 5 and gained 35.
- **Interventions do what they should for direction:** directed F1 rises from 0.29 to about 0.69 at budget 4, for
  every strategy.

## What it means

- **Genesis cannot yet propose the experiments that resolve hidden causes better than chance.** Daniel's alert asked
  for this. The machinery works (with the oracle's targets, hidden-cause F1 is 2.5 times FCI's), so the
  missing parts are the signal and the rule:
  - a suspicion that separates confounded pairs (for example independence tests that use non-Gaussianity, or
    environments that vary more);
  - a decision rule that tests direct causation under intervention, conditioning on the other parents, instead of
    reading every dependence as a direct cause.
- **Both are concrete and testable.** A new preregistered study must fix them on fresh instances, since these 40
  have been looked at.
