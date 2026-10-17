# B20_R62: power analyses bound to the custodian's families, and sizing at 10,000 simulations

- **Script:** `scripts/b20r62_power_rebind.py`.
- **What it is:** a DEV recomputation for the statistician (B19-OPEN-4; `docs/STATISTICIAN_BRIEF.md`, findings 1
  and 2). Nothing is adopted, and no package file changes.

## Why

The statistician's brief (B20_R61) found two problems.
- **Four causal power analyses are bound to the wrong family.** They are E1b's ablation and placebo (B20_R28) and
  E1b-C4's (B20_R50). Each is bound to the plan core of the `sealed_evaluation` family. The custodian assigns
  `<evidence kind>:<domain>` and refuses any other family, so these follow-ups cannot be registered with their
  current sample-size justification.
- **Sizes rest on 1,000 simulations.** Two chosen powers sit within two Monte Carlo standard errors of the target.

## Result

| Analysis | Stored: n per stratum (power) | Under the assigned family, 1,000 sims | Under the assigned family, 10,000 sims | Size changes |
|---|---|---|---|---|
| E1 | 10 (0.881) | (already bound correctly) | 10 (0.888) | no |
| E1b | 10 (0.974) | (already bound correctly) | 10 (0.982) | no |
| E1b ablation | 10 (1.000) | 10 (1.000) | 10 (1.000) | no |
| E1b placebo | 10 (0.985) | 10 (0.980) | 10 (0.981) | no |
| E1b-C4 | 10 (0.841) | (already bound correctly) | 10 (0.839) | no |
| E1b-C4 ablation | 10 (0.991) | 10 (0.992) | 10 (0.992) | no |
| **E1b-C4 placebo** | **10 (0.800)** | **12 (0.879)** | **12 (0.863)** | **yes** |
| E1d | 80 (0.814) | (already bound correctly) | 80 (0.821) | no |
| E1d ablation | 15 (0.838) | (already bound correctly) | 15 (0.845) | no |

At 10,000 simulations, the rejection rate at zero effect is at most 0.015 everywhere, below the worst-rank Holm
level of 0.0167.

## Reading

- **One size changes.** E1b-C4's placebo follow-up needs 12 hosts per stratum, not 10. Every other package's size
  holds at 10,000 simulations.
- **The four rebound analyses** are what a freeze would put in the causal follow-ups' decision records.
- **Proposed sizing practice.** The builder proposes sizing with 10,000 simulations. Adopting that is the
  statistician's decision (brief, question 2).

## Files

| File | What |
|---|---|
| `power_analysis_centred_<analysis>_<family>.json` | The four rebound analyses: the registered recomputation under the assigned family |
| `power_analysis_centred_<analysis>_<family>_10k.json` | All nine analyses under the assigned family, with 10,000 simulations |
| `summary.json` | The choices side by side |

## Tests

`tests_genesis/test_power_rebind.py` checks:
- the family binding of every file;
- the rebound analyses against an exact recomputation;
- the 10,000-simulation choices against their grids;
- a re-simulation of the flagged analysis;
- the summary against the files.
