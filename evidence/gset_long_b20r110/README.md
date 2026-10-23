# B20_R110 evidence: the engine at 60 s on Gset: LONGER_HELPS; every torus at its best known value; no record

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r110_gset_long.py`, preregistered at `34234fa` (committed through the index while B20_R108
  ran, before its result).
- **Run:** alone on CPU 0, on 23 Oct 2026, in two parts:
  - 16:59–17:23 SGT, 22 instances, until the background job's two-hour limit stopped it mid-instance (G23, whose
    unfinished run left no row);
  - 17:23–17:56 SGT, resumed from G23. The study is resumable per instance, and the two parts use one seed per
    instance, so the interruption changes no value.
- **Code identity:** `d1d6fe3a…`, the committed tree `34234fa`, in both parts.
- **The other core.** While it ran, the builder recorded B20_R109 (documents, a one-second test run, one worktree
  hash).
- **Configuration:** B20_R105's, by the preregistered rule: B20_R108's 10 s label was NO_DIFFERENCE, not
  MATURED_BETTER.

| File | What |
|---|---|
| `rows.jsonl` | 54 instances: class, configuration, the 60 s value with its witness cut (re-checked by the domain's two checkers), and B20_R106's 10 s value |
| `summary.json` | Fractions overall and per family, instances reaching the best known value, the sign test against 10 s, record candidates, validity |
| `run.log` | Both parts |

## Result

| | 60 s (this study) | 10 s (B20_R106, same configuration, another seed) |
|---|---|---|
| Mean fraction of the best known value | **0.99912** | 0.99860 |
| Random (25) | 0.99977 | 0.99954 |
| Toroidal (9) | **1.00000** | 0.99984 |
| Planar (20) | 0.99792 | 0.99686 |
| Instances reaching the best known value | **27** | 24 |

- **Sign test, 60 s against 10 s:** 22 wins, 5 losses, 27 ties (p = 0.0015): **LONGER_HELPS.** The losses are one
  run each at a different seed: G14, G15, G18, G37 and G46.
- **Every torus reaches its best known value at 60 s:** G11–G13, G32–G34 (1410, 1382, 1384) and G48–G50.
- **One or two below on most of the rest:**
  - G23 13,343 vs 13,344;
  - G24 13,336 vs 13,337;
  - G30 3,412 vs 3,413 (3,412 is the BLS paper's value; 3,413 comes from the authors' page);
  - G31 3,308 vs 3,309;
  - G46 6,648 vs 6,649;
  - G54 3,851 vs 3,852.
- **Furthest below** are the larger planar ±1 instances: G39–G42 at 0.992–0.999, and G38 at 0.997.
- **No run exceeded a best known value: no RECORD_CANDIDATE.**
- **Validity:** median metered CPU 1.00 of the budget; 0 failed runs.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| LONGER_HELPS | Yes (22–5) |
| The best known value reached on 30–36 instances | 27 |
| The planar instances still furthest below | Yes |
| No RECORD_CANDIDATE | None |

## What it means

In one minute on one core, Genesis's configured engine reaches the 2012–13 best known values on half the Gset
instances, including all nine tori. It is within 0.21% on average on the planar ones. The published runs that set
those values took minutes per instance: BLS reports up to about 10 minutes on average to reach its best on these
sizes, and MACUT allowed runs of 30 minutes. No value was exceeded, so there is no record. The remaining gap is mostly the
larger planar ±1 graphs (G39–G42). The B20_R108 lead, renormalisation for planar graphs, points at exactly those.
