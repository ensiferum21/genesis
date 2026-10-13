# B20_R14: is the B20_R13 portfolio already at the optimum? (DEV design probe)

- **Script:** `scripts/b20r14_optimum_gap_probe.py`, committed as `331825f` before it ran. The rule is in its docstring.
- **Hosts:** the 112 B20_R13 held-out hosts, which were already exposed.

**Method.** For each host, the setting's ORACLE-chosen configuration is re-run once to get a witness. Then `obstruction.certify` runs with 60 s:
1. an exact LP dual bound;
2. SAT/DRAT on the remaining gap (SAT models can also raise the lower bound).

The result is compared with the R13 per-host best over all 20–24 configurations (BEST_OF).

## Result

| Setting | Certified optima | Mean optimum − BEST_OF | Hosts where BEST_OF is optimal | Verdict |
|---|---|---|---|---|
| S1 tf n22 p.35 (E1 family) | 16/16 | 0.31 | 11 | AT_CEILING |
| S2 tf n30 p.3 | 16/16 | **1.31** (max 3) | 2 | **ROOM_TO_OPTIMUM** |
| S3 tf n40 p.2 | 16/16 | **0.56** (max 3) | 9 | **ROOM_TO_OPTIMUM** |
| S4 tf planted n30 | 16/16 | 0.31 | 11 | AT_CEILING |
| S5 tf n40 p.35 | 2/16 | — (LP gaps 1–7 remain at 60 s) | — | UNSETTLED_BOUNDS |
| S6 c4 n20 p.25 | 16/16 | 0.19 | 13 | AT_CEILING |
| S7 c4 n30 p.2 | 11/16 | 1.36 on the certified hosts | 0 of 11 | UNSETTLED_BOUNDS |

**Reading.** B20_R13 showed that choosing among the existing configurations is saturated. B20_R14 shows that those configurations are not at the optimum everywhere. On S2, S3 and probably S7, the best of 20–24 configurations, each with 0.5 CPU s of search, stays 0.6–1.4 edges per host below the certified optimum. The LP dual bound plus SAT closes that gap within seconds on most of these hosts.

So the headroom in graph construction is **capability headroom**, which a research process could earn by producing better methods. It is not **selection headroom**, which no improver can exploit here. The comparison above is not cost-matched: the certifier used up to 60 s per host against 0.5 s. Any study has to match budgets.

## Consequences (design options for the user; nothing is decided here)

**E1 (B20R12-OPEN-1).** The E1 family (S1) is at the ceiling: 11 of 16 hosts are already optimal. That is consistent with the underpowered E1 redo in the lost run. Of the options for E1, "a harder host family calibrated on DEV" is supported: S2-like triangle-free hosts (n30 p.3) leave 1.3 edges per host to win.

**GV4 (B20R13-OPEN-1).** A better-improver study in graph construction should let research produce *new methods*, for example LP- or SAT-guided construction and repair, or representations beyond the menu (s15.3). It should run on families with room to the optimum (S2, S3, S7-like), at matched CPU budgets. Choosing among fixed configurations is not enough.

## Claim ceiling

A DEV design probe. It licenses no claim.
