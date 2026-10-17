# B20_R62 record: power analyses bound to the custodian's families, and sizing at 10,000 simulations

- **Built by:** the builder. A DEV recomputation from committed pilot rows; nothing adopted, no package file
  changed except README pointers.
- **Files:** `scripts/b20r62_power_rebind.py`, `evidence/power_rebind_b20r62/`, `tests_genesis/test_power_rebind.py`.

## Why

The statistician's brief (B20_R61) found two problems. This batch prepares their fixes for a freeze.
- **Finding 2:** four causal power analyses are bound to the wrong hypothesis family, so the custodian would
  refuse their follow-ups.
- **Finding 1:** sizes rest on 1,000 simulations, and E1b-C4's placebo is underpowered at its chosen size.

## Result

**The four rebound analyses** are the registered recomputation under `ablation:` or `placebo:`.

| Analysis | Size per stratum | Power |
|---|---|---|
| E1b ablation | 10 | 1.000 |
| E1b placebo | 10 | 0.980 |
| E1b-C4 ablation | 10 | 0.992 |
| E1b-C4 placebo | **12** | 0.879 |

**All nine analyses at 10,000 simulations, under the assigned families.** Only E1b-C4's placebo changes size, from
10 to 12 per stratum (0.863 at 12). Every other size holds. E1d stays at 80 per stratum, with power 0.821 at
10,000 simulations. The rejection rate at zero effect is at most 0.015 everywhere.

## Consequence

A freeze of E1b or E1b-C4's causal follow-ups takes the rebound analyses. E1b-C4's placebo needs 12 hosts per
stratum. The e1b and e1b_c4 package READMEs now say so. Whether to size with 10,000 simulations is the
statistician's decision.

## Tests

`tests_genesis/test_power_rebind.py` (5). It checks:
- the family binding of every written file;
- the rebound analyses against an exact recomputation;
- the 10,000-simulation choices against their grids;
- a re-simulation of the flagged analysis;
- the summary against the files.

## Open

B19-OPEN-4 is updated with these files.
