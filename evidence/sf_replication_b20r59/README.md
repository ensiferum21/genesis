# B20_R59: internal replication of B20_R57 (DEV): **NOT_REPLICATED** (the bound result replicates)

- **Script:** `scripts/b20r59_sf_replication.py`, preregistered in commit `02415a8`.
  SHA-256 `83eae541…6aa5`.
  - It runs B20_R57's script unchanged except for its seeds: candidates 20265901 and 20265911, bootstrap 20265999.
- **Code identity:** `b0a7ba13…`.
- **Status:** a DEV measurement. Same operator and machine, so an internal replication only.

**Interruption, disclosed.** The first run stopped at host 23 of 40 when the session's disk allowance was exhausted
(ENOSPC). It failed on the log write. The 24 completed rows and both kept certificates were intact. After space was
freed, the run resumed from them through the script's resume path, and the log marks the point.

## Result

| | B20_R57 (original) | **B20_R59 (replication)** |
|---|---|---|
| Screen included / candidates | 40 / 72 | 40 / 69 |
| Certified, a (Schur rows only) | 14 | 21 |
| Certified, c (with the transferred rows) | 22 | 23 |
| Certified by c only / by a only | 8 / 0 | 2 / 0 |
| McNemar one-sided p | 0.0039 | **0.25** |
| Wall saving a − c, 90% interval | +6.02 [2.50, 9.88] | +2.76 [0.04, 5.37] |
| **Primary verdict** | CERTIFICATION_UTILITY | **NO_CERTIFICATION_UTILITY** |
| Certified bound a − c, 90% interval | +6.875 [5.375, 8.475] | **+3.875 [2.675, 5.125]** |
| **Secondary verdict** | BOUND_UTILITY | **BOUND_UTILITY** |

Under the preregistered rule this is **NOT_REPLICATED**. Coverage passes, and the time saving is positive with an
interval above 0. McNemar does not pass: only 2 hosts were certified by one route alone.

## Reading

- **What reproduced.** The bound advantage replicates: the transferred rows give certified bounds about 4–7 lower
  in both samples. So do the direction (c ≥ a, no host certified by a alone) and the 3–4× node reduction.
- **What did not.** The coverage effect did not. This sample was easier for route a: 21 of 40 certified within
  60 s, against R57's 14 of 40, despite the same 20 s screen. That left fewer hosts where only the rows could
  close the gap.
- **The two studies together.** Taken together they suggest a real but modest effect concentrated on the hardest
  hosts. This is a descriptive reading, not a preregistered pooling: 10 hosts certified by c alone and 0 by a alone
  across 80 hosts.
- **What to claim.** For GV6, the defensible claim from the sum-free target is now *stronger certified bounds*, not
  *more certified optima*. Whether bound strength counts as "helps" is the reviewer's decision (B20R35-OPEN-1).

## Tests

`tests_genesis/test_sf_replication.py` (3). The design tests check fresh seeds only and the replication rule. The
record tests check:
- the verdicts recompute;
- the replication record follows the rule;
- the screen's candidates and inclusion.
