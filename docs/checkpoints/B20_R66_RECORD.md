# B20_R66 record: E1d's n60 lead replicates and survives 120× HiGHS budget (REPLICATED_ADVANTAGE_THROUGH_120X)

- **Run by:** the builder. DEV only, outside every calibrated setting; no claim.
- **Setup commit:** `f2731ba` (script SHA-256 `9618ae76…aaa`).
- **Evidence:** `evidence/e1d_n60_b20r66/`.

## Problem

B20_R64, a 10-host pilot, found the strongest GV3 signal so far: at n60 the 0.5 s candidate led HiGHS at 64× its
budget. As with B20_R57 → R59, a positive pilot gets an internal replication before anyone leans on it. This study
also raises HiGHS to the kind's 60 s ceiling (120×).

## Design

- **Hosts:** 20 fresh n60 planted hosts (0.8, 0.06), 415–465 edges.
- **Arms:** the candidate at 0.5 s; HiGHS at 32 s and 60 s.
- **Rule:** B20_R63's rule. Validity requires HiGHS to receive at least 0.9 of its CPU.
- **Conditions:** it ran alone on the machine.

## Result: **REPLICATED_ADVANTAGE_THROUGH_120X** (valid: CPU delivery 0.99)

| HiGHS budget | Candidate − HiGHS | W/T/L |
|---|---|---|
| 32 s (64×) | +18.75 [12.85, 24.80] | 19/1/0 |
| 60 s (120×) | +2.20 [1.60, 2.80] | 17/3/0 |

Mean gap to the reference's proven upper bound:

| Arm | Mean gap |
|---|---|
| Candidate | 1.65 |
| HiGHS at 60 s | 3.85 |
| HiGHS at 32 s | 20.4 |

The builder's expectation (an advantage through 120× with a smaller lead) held.

## Consequence

E1d's speed advantage widens with host size:

| n | HiGHS catches up at |
|---|---|
| 40 | 16× (B20_R63, R64) |
| 50 | 64× (B20_R64) |
| 60 | just beyond 120× (B20_R64, R66) |

A larger-host GV3 claim is the strongest one available. It needs reviewer decisions:
- the family space extended beyond n40;
- the 200-edge bound lifted for the exact LP-dual route;
- a reference that certifies at n60. It certified 10 of 20 in 120 s.

## Tests

`tests_genesis/test_e1d_n60.py`.
- **Design (4).**
- **Record (3).**
