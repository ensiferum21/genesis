# B20_R36 evidence: generated K5 rows as a construction component in the dense regime (relaxation family, attempt 2; DEV)

Builder-run. Nothing here is independently reviewed, and it licenses no claim.
- **Script:** `scripts/b20r36_dense_construction.py`. It was committed before running in
  `9cfe851`, and its SHA-256 was sent to the user beforehand.
- **Run:** one pinned core, nothing else running, no resume.
- **Log:** `run.log`, 1,530 s.

## Design (fixed before running)

**Settings and hosts.** The two settings where B20_R35 found the triangle LP loose (planted n40
0.8/0.06, erdos n30 p0.42). Per setting, SELECT 8 and EVAL 16 fresh hosts.

**Arms**, 2.0 CPU s each:
- **new:** B20_R31's `cut_lp_greedy` with the Lean-checked K5 bound only;
- **control:** the plain LP greedy;
- **menu:** the best SELECT total of the four B20_R17 decoders;
- **conventional:** the best time-matched DSL program;
- **matched:** the control with +0.4666 s;
- **MIP:** an exact HiGHS MILP, reported separately as `beyond_mip`.

**Verdict.** The B20_R17 rule: every comparison needs a mean ≥ 0.5 and a 90% interval above 0.

## Result (`summary.json`, `part_b_rows.jsonl`, `hosts.json`)

**SELECT.** It chose `cross_2` for the menu (1,951, tied with `adjacent_2` and `adjacent_3`;
ties are broken by name) and `low_cycle_tm` for the conventional arm.

| new − … | Mean per host | 90% interval | W / T / L | Planted / erdos | Passes |
|---|---|---|---|---|---|
| control (plain LP greedy) | **+3.94** | [+2.41, +5.41] | 21 / 8 / 3 | +4.06 / +3.81 | yes |
| matched | **+3.31** | [+1.75, +4.84] | 19 / 8 / 5 | +2.88 / +3.75 | yes |
| conventional | +11.00 | [+9.53, +12.50] | 32 / 0 / 0 | +12.5 / +9.5 | yes |
| **menu (`cross_2`)** | **−2.97** | [−4.03, −1.94] | 1 / 12 / 19 | −4.44 / −1.50 | **no** |
| MIP (secondary) | +4.31 | [+3.34, +5.28] | 16 / 7 / 9 | +9.81 / −1.19 | yes (**BEYOND_MIP**) |

**Verdict: NO_UTILITY_AFTER_COST.** The menu's `cross_2` decoder dominates.

**Certified reference.** The generated-row route at 60 s certified 23 of 32 EVAL hosts. Mean gap
to the optimum on certified hosts:

| | new | control | menu | MIP (2 s) | conventional |
|---|---|---|---|---|---|
| planted (10 certified) | 3.6 | 8.5 | **0.0** | 13.9 | 16.0 |
| erdos (13 certified) | 1.0 | 4.5 | 0.31 | **0.15** | 11.2 |

**The component's own cost.** On planted hosts, K5 copy enumeration (B20_R31's generic
monomorphism search) finished within its 1.0 s share on only 2 of 16 hosts (median 1,835 copies
found). The LP therefore had only part of its rows there. On erdos it finished on all 16 (median
30 copies).

**The MIP at 2 s** proved no planted optimum, and 12 of 16 erdos optima.

## What it means

1. **As a construction component, attempt 2 of the relaxation family fails the preregistered
   rule.** The reason is that a builder-written menu decoder is better. Against everything else
   it is strongly positive:
   - +3.9 over the same LP greedy without the generated rows, and +3.3 after the cost of
     constructing them;
   - +4.3 over an exact MIP at the same budget.

   The generated rows turn the LP from a weak guide into a good one in the dense regime. But a
   2-colouring decoder (`cross_2`) is better still on near-bipartite optima.
2. **An exploratory finding for B20R33-OPEN-1.** In the dense planted regime, the menu's
   `cross_2` decoder reaches the certified optimum on all 10 certified hosts, while HiGHS at 2 s
   is 13.9 below. E1's frozen candidate is represent-and-repair `cross_2`, at 0.5 s. So a dense
   regime is where a candidate could be "beyond strong baselines". But that regime is certifiable
   only in part:
   - B20_R35: 27/40 with the generated rows, 7/40 without;
   - here: 23/32.

   Raising certification coverage there is the open engineering step. Generated rows on 7
   vertices (K7 and K7−e, among others) close most of the remaining LP gaps on B20_R35's
   uncertified hosts in a development look. That is B20_R37.

The 48 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r36.json`).
