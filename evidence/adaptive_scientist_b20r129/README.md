# B20_R129 evidence: the adaptive experimental scientist: ADAPTIVE_SCIENTIST

Builder-run on DEV (Genesis Ω, P1; Daniel's design notes of 24 Oct 2026, 13:15). It licenses nothing.
- **Script:** `scripts/b20r129_adaptive_scientist.py`, preregistered at `eb60843` with its design tests. The
  preregistration was committed through the index while B20_R127 ran.
- **Run:** alone on CPU 0 for 659 s, on 24 Oct 2026, 14:33:35–14:44:38 SGT. It ran in the planned pause between
  B20_R127's two slices, from a clean worktree of `166d1f1`: the preregistration plus documentation, and the same
  `.py` tree as `eb60843`.
- **Code identity:** `1ff03cbb…`, the tree of `166d1f1`.
- **The other core.** While it ran, the builder used CPU 1 for unit tests and development looks: the vault, the
  Problem Compiler, and B20_R130's estimators. This study's outcomes do not depend on timing. The CPU spent choosing
  is reported, and it is milliseconds.

| File | What |
|---|---|
| `worlds_<set>.jsonl` | Every world: seed, settings, the planted truth, FCI's answer and skeleton, the marks, the lab (the pre-drawn outcome of intervening on every variable) |
| `model.json` | The instrument's calibrated model (from the 100 calibration worlds only) |
| `lambda.json` | The hybrid's lambda, chosen on A (1.0) |
| `search.json` | The four invention searches: winners and the judge's reports |
| `choice.json` | Genesis's choice of scientist on the validation worlds, every candidate's scores there, and the invented program |
| `runs.jsonl` | 8,100 full runs on test and transfer: targets, hidden-cause F1 after every experiment, experiments needed, entropies, directed F1, SHD, beliefs at 4 |
| `summary.json` | Means, T1, T2, Holm, the verdict, the secondary tests, calibration, the instrument's confusion, CPU |
| `run.log` | The run |

**Design, in one line:**
- 200 fresh Gaussian worlds (p = 10, 3 hidden causes) and 100 worlds of a shifted family (p = 14, 4 hidden causes).
- Every strategy sees the same pre-drawn experiment outcomes.
- Genesis chose its scientist on validation worlds, from the established, builder-designed and invented acquisitions.
- Primary outcome: the experiments needed to reach what all experiments can tell (the hidden-cause F1 with all 10).

## Result: ADAPTIVE_SCIENTIST

**Genesis's choice:**
- On validation, Genesis chose `decfall`: the expected improvement of the hidden-cause decision, looking past one
  step. It needed 4.42 experiments there; its own invented rule `inv1` needed 4.59.
- The searches' only invention, `inv1` = `max (sqrt(sq(decall)) * sq(min(pf, 1.0)))`, was one of search 0's first
  random programs. It scored best on that search's training split. The judge released nothing in any of the four
  searches; the other three returned `decfall` itself, a seed.

**Test worlds (200):**

| Acquisition | Experiments needed | Hidden-cause F1 at 2 / 4 / 6 / 8 / 10 | Directed F1 at 4 / 8 | Entropy reduction at 4 |
|---|---|---|---|---|
| random (expected over 10 orders) | 6.81 | 0.02 / 0.10 / 0.24 / 0.41 / 0.59 | 0.71 / 0.87 | 4.0 |
| degree | 5.69 | 0.04 / 0.20 / 0.37 / 0.54 / 0.59 | 0.79 / 0.90 | 5.7 |
| static_eig (non-adaptive) | 5.68 | 0.04 / 0.18 / 0.37 / 0.55 / 0.59 | 0.80 / 0.90 | 5.8 |
| eig | 4.98 | 0.04 / 0.23 / 0.46 / 0.57 / 0.59 | 0.82 / 0.91 | 6.0 |
| dec | 4.965 | 0.05 / 0.24 / 0.47 / 0.57 / 0.59 | 0.83 / 0.91 | 6.0 |
| hybrid (lambda 1) | 4.96 | 0.05 / 0.23 / 0.46 / 0.57 / 0.59 | 0.82 / 0.91 | 6.0 |
| decf | 4.94 | 0.15 / 0.31 / 0.45 / 0.55 / 0.59 | 0.74 / 0.89 | 5.0 |
| **decfall (Genesis's choice)** | **4.49** | 0.13 / 0.35 / 0.50 / 0.57 / 0.59 | 0.80 / 0.91 | 5.9 |
| inv1 (invented) | 4.34 | 0.195 / 0.40 / 0.51 / 0.58 / 0.59 | 0.76 / 0.91 | 5.0 |
| oracle (reference; reads the truth) | 3.61 | 0.22 / 0.47 / 0.59 / 0.59 / 0.59 | 0.75 / 0.91 | 4.5 |

**Primary tests (Holm):**

| Test | Label | Result | Holm |
|---|---|---|---|
| T1 | **FEWER_EXPERIMENTS** | 4.49 against 6.81 (2.32 fewer, 164 non-zero differences, p = 1.2 x 10^-27) | rejected |
| T2 | NOT_SHOWN | at 4, 0.347 against random's 0.411 at 8 (p = 0.38 for non-inferiority at margin 0.05; two-sided, RANDOM@8_BETTER, p = 0.003) | not rejected |

Genesis's scientist reaches random's 8-experiment F1 at **5** experiments.

**Secondary tests:**

| Comparison | Label | Difference | p |
|---|---|---|---|
| eig, dec, hybrid against random | FEWER_EXPERIMENTS | 1.83–1.85 experiments | about 10^-26 |
| degree against random | FEWER_EXPERIMENTS | 1.12 | 10^-16 |
| eig against static_eig (the value of adapting) | **ADAPTING_HELPS** | 0.70 experiments | 1.4 x 10^-12 |
| inv1 against eig | **INVENTED_BETTER** | 0.64 experiments | 1.7 x 10^-7 |
| inv1 against decfall (the best non-invented on validation) | NO_DIFFERENCE | 0.15 | 0.16 |
| genesis against the oracle | ORACLE_BETTER | regret 0.89 experiments; 0.13 F1 at 4 | 9 x 10^-10 |
| the theory model against the calibrated one (Genesis's acquisition), hidden-cause F1 at 4 / 8 | **THEORY_BETTER** | +0.038 / +0.017 | 0.029 / 0.010 |
| information gained at 4 against F1 gained (eig), rank correlation | none | Spearman 0.02 | 0.75 |

**Transfer** (100 worlds of the shifted family, p = 14, 4 hidden causes; the model calibrated on the base family):

| Acquisition | Experiments needed | Hidden-cause F1 at 4 / 8 |
|---|---|---|
| random | 10.42 | 0.06 / 0.25 |
| eig | 7.50 | 0.14 / 0.48 |
| decfall (Genesis) | **6.54** | 0.28 / 0.54 |
| inv1 | 6.58 | 0.36 / 0.55 |
| oracle | 5.01 | 0.39 / 0.61 |

On transfer:
- T1 is FEWER_EXPERIMENTS (3.88 fewer, p = 2 x 10^-16).
- **T2 is HALF_SUFFICES**: Genesis at 4 is 0.284 against random's 0.245 at 8 (non-inferior, p = 3 x 10^-5).
- Genesis reaches random's 8-experiment F1 at 4 experiments.

**Calibration** (1,940 test pairs, beliefs after Genesis's 4 experiments):

| Model | Brier score | Log score of the true explanation | Expected calibration error of P(hidden cause) |
|---|---|---|---|
| calibrated (by simulation) | **0.244** | **-0.46** | **0.012** |
| theory | 0.304 | -0.60 | 0.070 |

**The instrument's confusion** (test worlds, every pair from both ends):

| True relation, seen from the intervened variable | Outcome: direct | indirect | none |
|---|---|---|---|
| it causes the other | 1,528 | 26 | 13 |
| the other causes it | 12 | 6 | 1,549 |
| a hidden cause, no edge | 13 | 25 | 602 |
| neither (FCI's adjacency is an error) | 32 | 2 | 72 |

**Validity:** every answer at every budget valid; every run used all p experiments with distinct targets.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| T1 FEWER_EXPERIMENTS | Yes: 4.49 against 6.81 |
| T2 NOT_SHOWN (dev: about 0.30 at 4 against 0.34 at 8) | Yes: 0.35 against 0.41. But on the shifted family it holds |
| Adapting beats not adapting | Yes: 0.70 experiments (eig against static_eig) |
| The invented winner about as good as decfall | Yes: 4.34 against 4.49, NO_DIFFERENCE. It is clearly better than every established acquisition |
| The oracle still clearly better (regret about one experiment) | Yes: 0.89 |
| On transfer, still fewer than random | Yes, and half the experiments suffice there |

## What it means

- **For the first time, Genesis chooses experiments better than chance.** After four ties with random choice
  (B20_R120, R122 twice, R124), its scientist needs 34% fewer experiments than random to learn what all the
  experiments can tell (4.49 against 6.81). Every adaptive acquisition beats random. Adapting to results is itself
  worth 0.7 experiments.
- **"Four experiments as good as eight random ones":**
  - on the base family it is not shown: Genesis needs 5;
  - on the larger, unfamiliar family it holds, with the model calibrated elsewhere.
- **Genesis's own rule.**
  - What it is: a program from its own language, `max |decall| x min(pf, 1)^2`. It follows up the pair whose resolution
    from both ends is worth most, weighted by the square of its chance of a hidden cause.
  - What it shows: it beats every established acquisition (information gain, decision improvement, their hybrid) by
    0.64 experiments.
  - What it does not show: it is not distinguishable from the builder's `decfall`. Genesis did not choose it on
    validation (4.59 against 4.42 there; 4.34 against 4.49 on test).
  - Its standing: no claim of novelty. It is a lookahead value-of-information rule, prior-art territory, on the
    novelty ladder's "behavioural" rung. The judge never released it: it was the best of a search's first population.
- **More confident is not more accurate (Daniel's warning, measured).** The information an acquisition gains does not
  predict the accuracy it gains (rank correlation 0.02). The decision-aware rules gain less entropy (5.0 against
  6.0) and more F1. The calibrated model is far better calibrated (Brier 0.24 against 0.30), yet its decisions mark
  fewer hidden causes early, so the theory model's F1 is higher (+0.04 at 4). The decision rule (MAP over four
  explanations) does not target F1 on a rare class. That is a lesson for the next design.
- **The limit is not the choice.**
  - With all experiments, F1 is only 0.59; the oracle needs 3.61.
  - B20_R130's development looks find the interpretation is the limit: an established global estimator gets about 0.7
    from the same data.
  - B20_R130 tests that, with this study's scientist as its `genesis` arm.
