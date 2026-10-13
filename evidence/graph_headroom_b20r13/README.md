# B20_R13: graph-construction headroom pilot for GV4 (DEV design diagnostic)

- **Script:** `scripts/b20r13_graph_headroom_pilot.py`, committed as `01e92e8` before it ran. The script was restored after a workspace loss; its rules are unchanged, see the commit message.
- **Domain:** the user chose graph construction as the GV4 domain on 13 Oct 2026, after three equational pilots found no research-policy headroom (B20R9-OPEN-1).
- **Question:** does it matter enough which solver configuration a research process picks, at the same research budget, that one improver could beat another?
- **Status:** a design diagnostic. It licenses no claim.

## Design (fixed before running)

**Settings.** 7 settings:
- 5 triangle-free: Erdős–Rényi n22/p.35 (the E1 family, with all 145 E1 hosts excluded), n30/p.3, n40/p.2, n40/p.35, and a planted cluster n30;
- 2 C4: n20/p.25 and n30/p.2.

**Hosts.** For each setting, 10 selection hosts and 16 held-out hosts.

**Configurations.** 24 for triangle-free and 20 for C4, each with 0.5 s of CPU search per host:
- 4 represent-and-repair representations, licensed on the triangle-free domain only;
- 3 time-matched conventional baselines, plus 1 with exchange;
- 16 grammar points.

**Improvers.** At a research budget CAP of 25% of exhaustive evaluation:
- fixed order (two orders);
- random order;
- successive halving;
- exhaustive evaluation.

**References.** ORACLE, cross-validated ORACLE, and BEST_OF (the per-host maximum).

**Verdict rule.** DEPLOYABLE_HEADROOM if SH − best fixed or random ≥ 0.5 edges per host; else HEADROOM if ORACLE − that ≥ 0.5; else NO_HEADROOM.

## Result

All 4,160 runs completed, and every witness was re-checked by both graph checkers (0 invalid). The verdict is **NO_HEADROOM** in all 7 settings.

| Setting | Base (cheapest fixed order) | ORACLE − base | BEST_OF − base | Rank correlation, selection vs held-out |
|---|---|---|---|---|
| S1 tf n22 p.35 | 59.56 | 0.00 | 0.25 | 0.99 |
| S2 tf n30 p.3 | 95.50 | 0.00 | 0.13 | 1.00 |
| S3 tf n40 p.2 | 122.50 | 0.00 | 0.19 | 0.99 |
| S4 tf planted n30 | 91.88 | 0.00 | 0.00 | 0.98 |
| S5 tf n40 p.35 | 179.56 | 0.00 | 0.00 | 0.96 |
| S6 c4 n20 p.25 | 34.19 | 0.00 | 0.25 | 0.94 |
| S7 c4 n30 p.2 | 61.63 | 0.00 | 0.38 | 0.99 |

**Reading.**
- **The configuration space is saturated.** The best few configurations tie on held-out hosts:
  - triangle-free: the three represent-and-repair representations cross_2, adjacent_2 and adjacent_3, or low_cycle on sparse hosts;
  - C4: low_cycle with or without exchange.
- **Choosing is easy.** Selection and held-out rankings agree, so the cheapest fixed improver already picks a tying configuration.
- **There is no complementarity to exploit.** Even a per-host oracle over all configurations (BEST_OF) gains at most 0.38 edges per host, below the 0.5 minimum useful effect.
- **Successive halving loses a little** in S5–S7 (−0.06 to −0.38), from noise in its short early rungs.

## Consequence for GV4

With the equational pilots (B20_R3, R6 and R9), this makes **four DEV pilots without research-policy headroom**. In graph construction, as on the equational systems, choosing well among existing configurations cannot separate a better improver from a fixed one.

The better-improver question needs a setting where research output changes what solvers can do, not which existing one is picked. Options:
- representations outside the hard-coded menu (handoff s15.3);
- harder host families calibrated so that the per-host ceiling exceeds the best single configuration by at least 0.5 edges per host;
- multi-generation horizons.

GV4 stays **UNESTABLISHED**. The next step needs the user's design decision (B20R13-OPEN-1).

## Note

An earlier run of this pilot (about 1,700 of 4,160 rows) was lost with the workspace before anything was summarised. This run is complete and is the only one analysed. It was restarted once (one worker → two) and resumed from its rows file. The search budgets are CPU-time, so the restart does not affect values.
