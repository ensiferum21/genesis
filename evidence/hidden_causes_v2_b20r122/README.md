# B20_R122 evidence: the repaired procedure on fresh instances: HIDDEN_CAUSES_MARKED; Genesis's experiments add direction, not detection

Builder-run on DEV (Daniel's research alert of 22 Oct 2026, item 2). It licenses nothing.
- **Script:** `scripts/b20r122_hidden_causes_v2.py`, preregistered at `120daef` with B20_R121's version 2. Its
  expectations were written from development looks on B20_R120's instances, all disclosed in the docstring.
- **Run:** alone on CPU 0, 161 s, on 24 Oct 2026 (09:01–09:04 SGT).
- **Code identity:** `fd29e7ef…`, the committed tree `120daef`.

| File | What |
|---|---|
| `runs.jsonl` | 400 runs (40 fresh instances x 10 arms): answer, scores, targets, each intervention's classification (direct / indirect / none), the suspicion of each adjacent pair, CPU time, the planted confounded pairs and edges |
| `summary.json` | Means per arm, Tests 1-3, the verdict, validity |
| `run.log` | The run |

## Result: HIDDEN_CAUSES_MARKED

| Arm | Hidden-cause F1 | precision | recall | Directed F1 | Spurious rate |
|---|---|---|---|---|---|
| FCI alone | 0.21 | 0.27 | 0.18 | 0.26 | 0.44 |
| flag (observational) | 0.49 | 0.58 | 0.46 | 0.25 | 0.19 |
| random, 2 | 0.47 | 0.58 | 0.44 | 0.43 | 0.18 |
| degree, 2 | 0.47 | 0.61 | 0.42 | 0.52 | 0.19 |
| **suspicion, 2** | 0.45 | 0.60 | 0.40 | 0.47 | 0.20 |
| oracle, 2 | 0.54 | 0.68 | 0.50 | 0.45 | 0.12 |
| random, 4 | 0.48 | 0.59 | 0.43 | 0.59 | 0.16 |
| degree, 4 | 0.47 | 0.63 | 0.40 | 0.69 | 0.16 |
| **suspicion, 4** | **0.47** | 0.63 | 0.41 | **0.64** | 0.14 |
| oracle, 4 | 0.56 | 0.72 | 0.52 | 0.62 | 0.05 |

**Test 1 (primary):** suspicion at budget 4 against FCI on hidden-cause F1 is **GENESIS_BEATS_FCI**, +0.26
(34 non-zero differences, p = 1 x 10^-4). **Verdict: HIDDEN_CAUSES_MARKED.**

**Test 2, do experiments add to the observational flag?**
- **Hidden-cause F1: NO_DIFFERENCE** (−0.02, p = 0.73).
- **Directed F1: EXPERIMENTS_ADD**, +0.39 (p = 1 x 10^-7).

**Test 3, is Genesis's choice of experiments better than chance?** **NO_DIFFERENCE** at budget 2 (−0.02, p = 0.42)
and at budget 4 (−0.01, p = 0.81).

**Validity:** every answer valid; every arm used exactly its budget of distinct targets.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| HIDDEN_CAUSES_MARKED (about 0.45 against about 0.2) | Yes: 0.47 against 0.21 |
| Test 2: NO_DIFFERENCE on hidden-cause F1, EXPERIMENTS_ADD on directed F1 | Yes, both |
| Test 3: NO_DIFFERENCE at both budgets | Yes |

The development numbers on B20_R120's instances held on fresh ones. For example, flag 0.46 → 0.49 and suspicion at
budget 4 0.50 → 0.47.

## What it means

- **Genesis can now tell when its measurements cannot explain what it sees, and say where.** It marks hidden causes
  with F1 0.47 against FCI's 0.21. The share of confounded pairs reported as causal falls from 0.44 to 0.14. On
  this benchmark that answers the first half of Daniel's alert.
- **The capability comes from a prior-art principle, put to work.** Most of the gain is the observational flag:
  residual dependence in linear non-Gaussian models (Hoyer et al. 2008; RCD, Maeda and Shimizu 2020). It is not a
  new method and is not claimed as one.
- **Experiments resolve direction, not hidden causes.** Four interventions raise directed F1 from 0.25 to 0.64 but
  add nothing to hidden-cause detection beyond the flag.
- **Genesis does not yet choose experiments better than chance.** This is the second half of the alert, and it
  stays NOT_SHOWN for the third time (B20_R120 and both budgets here). The oracle's targets show what is left to
  win: hidden-cause F1 0.56 and a spurious rate of 0.05.
- **What would test it next.** A target choice that aims at what the experiments decide, which is direction.
  Expected information gain over the undecided marks would do that; Genesis's `discovery.active` module already
  computes it. It should be judged on directed and hidden-cause F1 together, on fresh instances.
