# B20_R124 evidence: with Gaussian noise, experiments become necessary to find hidden causes: EXPERIMENTS_NEEDED

Builder-run on DEV (Daniel's research alert of 22 Oct 2026, item 2). It licenses nothing.
- **Script:** `scripts/b20r124_gaussian_hidden_causes.py`, preregistered at `d6f1073` (committed through the index
  while B20_R123 ran).
- **Run:** alone on CPU 0, 126 s, on 24 Oct 2026 (12:39–12:41 SGT).
- **Code identity:** `d930eadf…`, the committed tree `bc7e424`.

| File | What |
|---|---|
| `runs.jsonl` | 280 runs (40 fresh instances x 7 arms): answer, scores, targets, intervention classifications, suspicion, the planted truth |
| `summary.json` | Means per arm, Test 1, the secondary tests, the verdict, validity |
| `run.log` | The run |

**Design, in one line:** B20_R122's settings with **Gaussian** noise, where the observational flag (residual
dependence) has nothing to see. It compares FCI, the flag, four interventions chosen four ways, and random at eight.

## Result: EXPERIMENTS_NEEDED

| Arm | Hidden-cause F1 | precision | recall | Directed F1 | Spurious rate |
|---|---|---|---|---|---|
| FCI alone | 0.15 | 0.24 | 0.12 | 0.21 | 0.44 |
| flag (observational) | 0.15 | 0.22 | 0.12 | 0.21 | 0.44 |
| random, 4 | 0.25 | 0.42 | 0.19 | 0.62 | 0.35 |
| degree, 4 | 0.29 | 0.45 | 0.23 | 0.68 | 0.30 |
| suspicion, 4 (Genesis) | 0.25 | 0.41 | 0.19 | 0.66 | 0.36 |
| oracle, 4 | 0.46 | 0.65 | 0.38 | 0.55 | 0.11 |
| random, 8 | 0.44 | 0.67 | 0.34 | 0.83 | 0.16 |

**Test 1 (primary):** random experiments at budget 4 against the flag, on hidden-cause F1: **EXPERIMENTS_ADD**,
+0.11 (12 non-zero differences, p = 0.0015). **Verdict: EXPERIMENTS_NEEDED.**

**Secondary tests:**

| Comparison | Label | Difference | p |
|---|---|---|---|
| flag against FCI | NO_DIFFERENCE | −0.004 | 1.0 (2 non-zero differences) |
| oracle against random, budget 4 | ORACLE_BETTER | +0.21 | 3 x 10^-5 |
| suspicion against random, budget 4 | NO_DIFFERENCE | | 0.86 |
| random at 8 against random at 4 | MORE_HELPS | +0.18 | 6 x 10^-5 |

**Validity:** every answer valid; every arm used exactly its budget of distinct targets.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| The flag marks almost nothing beyond FCI | Yes: 0.15 and 0.15 (the two differ on 2 of 40 instances) |
| Experiments add hidden-cause marks; more at budget 8 | Yes, both |
| The oracle's choice clearly better than random | Yes (+0.21) |
| Genesis's suspicion no better than random (its signal is blind here) | Yes |
| Hidden-cause F1 lower than on Laplace data for every arm | Yes: FCI 0.15 against 0.21 (B20_R122), the flag 0.15 against 0.49, the budget-4 arms 0.25–0.29 against about 0.47, the oracle 0.46 against 0.56 |

## What it means

- **The prediction from theory held.** When the data are Gaussian, the observational route to hidden causes closes:
  the flag sees almost exactly what FCI sees. Only experiments separate a hidden common cause from a direct one, and more
  of them help (F1 from 0.15 to 0.25 with four, to 0.44 with eight).
- **This is where choosing experiments well is worth the most.** The oracle's choice at four interventions (0.46) is
  as good as random at eight (0.44). Choosing well would halve the experiments needed.
- **Genesis does not yet choose well: the fourth NOT_SHOWN on experiment choice** (B20_R120, R122 twice, R124). Its
  suspicion here is built from the same blind signal. A choice that works in this regime must use what
  experiments reveal as they arrive (sequential design), not an observational score fixed in advance. That is the
  concrete next step for this track.
