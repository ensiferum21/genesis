# B20_RX3: capability pilot for GV4 in graph construction (DEV design diagnostic)

- **Script:** `scripts/b20rx3_capability_pilot.py` and `discovery/construct.py`, committed as `0dec3f6` before running.
- **Design:** chosen by the user on 13 Oct 2026, after B20_R13 (no selection headroom) and B20_R14 (room to the optimum on harder families).
- **Status:** a design diagnostic. It licenses no claim.

## Design (fixed before running)

**Settings.** Three fresh families with room to the optimum:
- C1: triangle-free n30 p0.3 (S2-like);
- C2: triangle-free n40 p0.2 (S3-like);
- C3: C4 n30 p0.2 (S7-like).

Each has 10 selection hosts and 16 held-out hosts.

**Budget.** Every method gets **2.0 CPU s per host, child processes (the SAT solver) included**. A run over 1.25× the budget scores 0.

**Methods.**
- **Menu:** the R13 solver space at that budget (24 configurations on triangle-free hosts, 20 on C4).
- **New methods (6):** builder-written LP- and SAT-guided constructions:
  - LP-ordered greedy with LP-perturbed restarts;
  - that greedy followed by CaDiCaL climbing;
  - the menu head followed by climbing;
  - random greedy followed by climbing.

**Improvers.** Every improver gets the same research budget (CAP = 25% of exhaustive menu evaluation).
- **Menu only:** fixed orders, random order, and successive halving.
- **With the new methods:** successive halving and random order.

## Result

**DEPLOYABLE_CAPABILITY_HEADROOM in all three settings.** All 2,236 runs were valid and within budget.

| Setting | Best menu-only improver | SH over menu + new | Gain | 90% bootstrap (paired) | ORACLE[menu] → ORACLE[all] | Best new method |
|---|---|---|---|---|---|---|
| C1 tf n30 p.3 | 94.31 | 95.56 | **+1.25** | [0.81, 1.69] | 94.38 → 95.63 | lp_greedy+sat_25_75 (95.63), lp_greedy (95.56) |
| C2 tf n40 p.2 | 122.81 | 123.56 | **+0.75** | [0.44, 1.06] | 122.81 → 123.56 | lp_greedy, lp_greedy+sat (123.56) |
| C3 c4 n30 p.2 | 59.38 | 60.19 | **+0.81** | [0.50, 1.13] | 59.38 → 60.50 | lp_greedy+sat_25_75, head+sat (60.50) |

Successive halving finds a new method within the same research budget in every setting. The LP-ordered greedy alone accounts for most of the gain on triangle-free hosts. SAT climbing adds to it on C4 hosts.

## Reading, and what it does not show

**It shows** that at matched CPU per host, making LP- and SAT-guided construction available to a research process is worth about +0.75 to +1.25 edges per host on families with room to the optimum. That is a capability gain. In B20_R13 and B20_R14, choosing among the existing configurations was worth nothing.

**It does not show** that a research process can *invent* such methods:
- The components are builder-written.
- The improver only selected among them.
- A GV4 study must let the improver produce the methods itself (for example, synthesis over a component grammar) and compare a learned improver with a fixed one at matched research and solver budgets.

**Status of the result.** Per the rule, a positive setting is a lead for a fresh replication with new seeds and for a GV4 study design, not a finding. 16 held-out hosts per setting is small.

**The LP producer** (scipy/HiGHS) is untrusted. It only orders the search, and every witness is re-checked by both graph checkers.
