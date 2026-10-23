# B20_R105 evidence: the system configures its max-cut engine on generated graphs: TUNED_BETTER at 1 s, MCX_AHEAD at both budgets

Builder-run on DEV (the open-record track; `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md` §3, item 2a). It licenses
nothing.
- **Script:** `scripts/b20r105_mcx_configure.py`, preregistered at `ff08000` and amended before any run at `1230b5a`.
  The first start stopped while building its graphs: its weight-1 tori all had 3,000 vertices, which the exposure
  identity counts as Gset's. The shapes were changed and nothing else (SHA-256 `08c8eb23…`).
- **Run:** alone on CPU 0, 2,394 s, on 23 Oct 2026 (09:30–10:10 SGT). `code_identity` `f55254f2…`, the committed tree
  (`1230b5a`).
- **The other core.** While it ran, the builder recorded B20_R103 on CPU 1: documents and two record tests (under a
  second of CPU).
- **Engine:** `mcx-v1`, binary pinned `10825596…0978`. **Comparator:** `mqlib-maxcut-v1` BURER2002.

| File | What |
|---|---|
| `runs.jsonl` | 792 runs, each keyed by graph, arm and budget, with status, metered CPU and value: 576 race runs at 1 s, 72 at 10 s, and 144 held-out |
| `configs.json` | The classifier (standardised nearest centroids on two order parameters) and the chosen configuration per class and budget: B20_R106's input |
| `summary.json` | The races round by round, the held-out values, the labels, the classifier's accuracy, validity |
| `run.log` | Both starts |

No Gset graph was used. All 96 graphs are fresh draws, and none shares an identity with any of the 54 Gset graphs.
Gset has 52 distinct identities, because G48-G50 share one.

## Result

**What the system chose.** It chose a perturbation five times BLS's (L0 = 0.05 n, the largest value offered) in
every class and at both budgets. The rest differs by class:

| Class | 1 s | 10 s |
|---|---|---|
| random | P 0.75, tenure n/10, no restarts, the builder's perturbation rule | the same |
| toroidal | P 0.8, tenure n/5, pool 16, no restarts, recency-based flips | the same |
| planar | P 0.5, tenure n/5, pool 16, **Houdayer cluster exchange** every 2,000 local optima, BLS's rules | P 0.5, tenure n/5, pool 8, **cluster exchange** every 20,000, the builder's rule |

DEFAULT (BLS's published setting) reached the final round of no 1 s race. After the first round it ranked 9th of 32
(planar), 21st (random) and 17th (toroidal). In the 10 s races, where it re-entered, it came second or third. The renormalisation step and MACUT's crossover were not chosen anywhere.

**The classifier** placed all 24 held-out graphs in their classes (accuracy 1.0).

**Held out** (24 fresh graphs, 8 per class; one seed each):

| Budget | Chosen vs DEFAULT (BLS) | Chosen vs BURER2002 |
|---|---|---|
| 1 s | **TUNED_BETTER** (p = 0.005): mean gap 0.003% vs 0.24%; wins 10, losses 1 | **MCX_AHEAD** (p = 5e-7): 22 wins, 0 losses, 2 ties; BURER2002's mean gap 0.64% |
| 10 s | **NO_DIFFERENCE** (p = 1.0): mean gap 0.055% vs 0.048%; wins 7, losses 6 | **MCX_AHEAD** (p = 0.0014): 17 wins, 2 losses, 5 ties; BURER2002's mean gap 0.31% |

Gaps are relative to the best of the three arms on each graph at that budget. The two losses at 10 s are planar
graphs (planar2 3049 against 3051; planar2_pm1 960 against 967). By class at 1 s, chosen beat BURER2002 on all 8
random, 6 of 6 decided toroidal and 8 of 8 planar graphs.

**Validity:** median metered CPU 1.18 of the budget at 1 s (the Python child's start-up is metered) and 1.02 at 10 s;
0 failed runs of 792.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| The races keep DEFAULT or a near variant in most classes | No: DEFAULT lost every race; every class chose a 5x larger perturbation |
| Chosen vs DEFAULT NO_DIFFERENCE at both budgets | At 10 s, yes. At 1 s, TUNED_BETTER |
| MCX_AHEAD of BURER2002 at 1 s | Yes (22-0) |
| COMPARABLE at 10 s | No: MCX_AHEAD (17-2) |
| The classifier places every held-out graph in its class | Yes |

## What it means

- **The system improved on the published method's setting.** On graphs it had never seen, its choice beats BLS's
  published setting at 1 s and ties it at 10 s. The tie means the gain is speed: it gets there sooner.
- **Both the system's choice and BLS's setting, inside this engine, beat BURER2002** (the best single heuristic of
  the 2018 MQLib study) at both budgets on Gset-like graphs.
- **One physics move earned its place.** The Houdayer cluster exchange is chosen on planar graphs only. The
  renormalisation step and MACUT's crossover were not chosen at these budgets.
- **Every class chose the boundary value of L0.** Larger perturbations might do better still; the space should be
  widened in a later study.
- **This is not yet Gset.** B20_R106 applies these configurations to G1-G54 once.
