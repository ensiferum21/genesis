# B20_R102 evidence: where the published tools stand on Gset G1–G54 (calibration; no record candidate)

Builder-run on DEV (the open-record track, `docs/OPEN_RECORDS_PLAN.md`). It licenses nothing; no record claim.
- **Script:** `scripts/b20r102_gset_standing.py`, preregistered at `cc7f4bb` (SHA-256 `afaf0719…bee0`).
- **Run:** alone on CPU 0, on 23 Oct 2026, in two slices:
  - 12:55–14:46 SGT, 52 instances, then paused at its 6,600 s limit;
  - 14:46–14:51 SGT, the last two.
- **Code identity:** `e7a8ac93…`, the committed tree (`b640aa1`), the same for both slices.
- **The other core.** While it ran, the builder recorded B20_R105 on CPU 1 (documents, one 26 s test run, a few
  hash checks) and wrote the scripts of B20_R107 and B20_R108 (files only, nothing run).
- **The best-known table.** It changed before the run (B20_R104: the BLS 2013 and MACUT 2012 papers' tables, Daniel's
  PDFs); the run records its SHA-256 (`3b97a82b…`). Every fraction below is against those 2012–13 values.

| File | What |
|---|---|
| `rows.jsonl` | 54 instances, each with 14 runs and their witness cuts: BURER2002 and dSB at 1 s and 10 s, and MQLib's other ten max-cut heuristics at 10 s. Every cut was re-checked by the domain's two checkers |
| `summary.json` | Per arm and budget: mean fraction of the best known value, overall and per family, and instances reaching it; the virtual best at 10 s; record candidates; validity; descriptors |
| `run.log` | Both slices |

## Result

| Arm | Mean fraction of best known | Random | Toroidal | Planar | Instances reaching it |
|---|---|---|---|---|---|
| **Virtual best of the 12 at 10 s** | **0.99675** | 0.99882 | 0.99483 | 0.99502 | 11 |
| dSB at 10 s | 0.99618 | 0.99869 | 0.99290 | 0.99451 | 6 |
| BURER2002 at 10 s | 0.99537 | 0.99758 | 0.99320 | 0.99359 | 6 |
| dSB at 1 s | 0.99328 | 0.99537 | 0.99113 | 0.99164 | 2 |
| BURER2002 at 1 s | 0.99202 | 0.99440 | 0.98928 | 0.99030 | 3 |
| The next best at 10 s (FESTA2002VNSPR, DUARTE2005, FESTA2002GVNSPR) | 0.9845–0.9848 | | | | 0–4 |

- **The physics arm leads.** dSB (discrete simulated bifurcation) is the best single tool at both budgets. Against
  BURER2002 it wins 25 instances and loses 19 at 10 s, and wins 28 and loses 22 at 1 s.
- **Which tools set the virtual best.** It equals dSB's run on 32 instances and BURER2002's on 26; the GRASP and path-relinking
  heuristics (FESTA2002 variants) tie it on up to 6 instances each.
- **Where the best known value is reached.** The virtual best reaches it on 11 instances: G1, G4, G6–G8, G11, G12,
  G20 and the weight-1 tori G48–G50.
- **The ±1 tori stay furthest below.** On G32–G34 the best of the twelve is 20 below the best known value (1390 against 1410,
  1362 against 1382, 1364 against 1384), about 1.4%.
- **No run exceeded a best known value: no RECORD_CANDIDATE.**
- **Validity:** median metered CPU 1.22 of the budget at 1 s (the child's start-up is metered) and 1.01 at 10 s; 0
  failed runs of 756.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| BURER2002 at 10 s within 0.5% of the best known on random and planar instances | Random yes (0.24% below); planar no (0.64% below) |
| ...and about 1% below on the toroidal ±1 instances | Further below on G32–G34 (1.4%) and closer on G11–G13 (0.3–0.7%) |
| dSB at 10 s close to BURER2002 on random instances and behind on planar ones | Ahead on both (random 0.99869 vs 0.99758; planar 0.99451 vs 0.99359) |
| The virtual best reaches the best known value on fewer than half the instances | Yes, 11 of 54 |
| No RECORD_CANDIDATE | None |

## What it means

This is the bar a Genesis method has to clear on public instances, at equal short budgets on one core. The best
published tool here is dSB, a physics-inspired method, not BURER2002. The best of all twelve, which uses twelve times
the compute, still ends 0.33% below the 2013 values on average and 1.4% below on the ±1 tori. B20_R106 runs
Genesis's configured engine against these numbers, once.
