# B20_R63 record: how much CPU HiGHS needs to match E1d's 0.5 s candidate (CROSSOVER_AT_8S)

- **Run by:** the builder. DEV only; no claim.
- **Setup commit:** `fca3c47` (script SHA-256 `b9d49322…30cb`).
- **Evidence:** `evidence/e1d_crossover_b20r63/`.

## Problem

E1d's claim is that a 0.5 s solver beats HiGHS at four times its budget. Which MILP budget a GV3 comparison must
beat is the reviewer's decision (B20R41-OPEN-1). Nothing had run HiGHS above 2 s on these settings, so the reviewer
could not tell a knife-edge from a robust advantage.

## Design

- **Hosts:** 30 fresh hosts in the three E1d settings.
- **Arms:** E1's frozen candidate, and HiGHS at 2, 4, 8, 16 and 32 s (4×–64×). The 2 s arm is the package's
  descriptor.
- **Per budget:** candidate − HiGHS, with a stratified bootstrap 90% interval.
- **Verdict:** ADVANTAGE iff the lower end is above 0.5.

## Result: **CROSSOVER_AT_8S**

| HiGHS budget | Candidate − HiGHS | Verdict |
|---|---|---|
| 2 s (4×) | +10.30 [8.77, 11.83] | ADVANTAGE |
| 4 s (8×) | +6.37 [4.73, 8.00] | ADVANTAGE |
| 8 s (16×) | +0.43 [0.03, 0.90] | UNRESOLVED |
| 16 s (32×) | −0.03 | NO_MATERIAL_DIFFERENCE |
| 32 s (64×) | −0.03 | NO_MATERIAL_DIFFERENCE |

- **At 16 s and 32 s** HiGHS proved all 30 optima, using about 6 CPU s per host (median).
- **The candidate** was optimal on 29 of 30 hosts.
- **Every optimum** was certified, and no run failed.

## Two builder statements were wrong

1. **The expectation.** It was ADVANTAGE through 16×. It is not: the advantage is lost between 8× and 16×.
2. **The reading of HiGHS's weakness.** The GV4 fallback draft said the MILP's relaxation is too weak on dense
   hosts. In fact HiGHS solves every host exactly, given about ten times the candidate's time.

Both are corrected in the draft and the E1d package.

## Consequence

- **The 4× claim replicates.** This is the third fresh sample, after +10.6 (B20_R41) and +9.80 (B20_R43).
- **The advantage is speed, not quality at any budget.** It is about an order of magnitude at equal answers. A
  claim must state the crossover.
- **What stays open.** Whether "beats an exact solver at 4×" is enough for GV3 is B20R41-OPEN-1, now with the
  budget curve in hand.

## Tests

`tests_genesis/test_e1d_crossover.py`.
- **Design (4):** fresh seeds, the arms, the profiles, the rule.
- **Record (3):** the verdict recomputes from the rows; the arms and the optima; the hosts are distinct and in the
  e1/e1b exposure addenda.
