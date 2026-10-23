# B20_R113 evidence: renormalisation on planar graphs: RENORM_BETTER on generated graphs and on Gset; no record

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r113_planar_renorm.py`, preregistered at `1bd3543` (committed through the index while
  B20_R111 ran, before any result of this study).
- **Run:** alone on CPU 0, 2,098 s, on 23 Oct 2026 (18:42–19:17 SGT), in one slice.
- **Code identity:** `95c5ed5a…`, the committed tree `067a523`. B20_R115's and B20_R116's files were kept out of the
  working tree (committed through the index only).
- **The other core.** While it ran, the builder finished recording B20_R112 (documents), wrote B20_R115's and B20_R116's
  designs, and ran their design tests and language v2's validity checks (a few seconds each), one listing of the Gset
  instances not yet reached, and one run of the ledger test (under a second).

| File | What |
|---|---|
| `runs.jsonl` | Every run: Part A's 40 graphs x 2 configurations at 10 s, Part B's 20 Gset planar instances at 60 s, each with its witness cut, metered CPU and descriptor |
| `summary.json` | The two configurations, Part A's values and Wilcoxon label, Part B's rows, sign test, instances reaching the best known value, record candidates, validity |
| `run.log` | The run |

**The configurations** (both read as recorded and checked against their studies' SHA-256):
- **INCUMBENT**, B20_R105's planar choice at 10 s: Houdayer cluster exchange (`rs` 1), L0 0.05, no strong
  perturbation.
- **RENORM**, B20_R108's planar choice at 10 s: renormalisation restarts (`rs` 2), L0 0.2, BLS's perturbation,
  pool 16.

## Result

**Part A (40 fresh generated planar graphs, 10 s each): RENORM_BETTER.**
- 25 wins, 8 losses, 7 ties; Wilcoxon p = 0.0005.
- Mean gap below the best of the two: RENORM 0.03%, INCUMBENT 0.17%.

**Part B (Gset's 20 planar instances, RENORM at 60 s against B20_R110's 60 s values): RENORM_BETTER.**
- 13 wins, 2 losses, 5 ties; sign test p = 0.0074.
- Mean fraction of the best known value: 0.99923, against 0.99792.
- **5 of 20 reach the best known value** (G16, G18, G20, G21, G40), against 3 (G16, G20, G21).
- **No record candidate.**

| Instance | Best known | INCUMBENT 60 s (B20_R110) | RENORM 60 s | Change |
|---|---|---|---|---|
| G14 | 3,064 | 3,060 | 3,063 | +3 |
| G15 | 3,050 | 3,042 | 3,049 | +7 |
| G16 | 3,052 | 3,052 | **3,052** | 0 |
| G17 | 3,047 | 3,045 | 3,045 | 0 |
| G18 (±1) | 992 | 991 | **992** | +1 |
| G19 (±1) | 906 | 904 | 905 | +1 |
| G20 (±1) | 941 | 941 | **941** | 0 |
| G21 (±1) | 931 | 931 | **931** | 0 |
| G35 | 7,686 | 7,669 | 7,685 | +16 |
| G36 | 7,679 | 7,673 | 7,672 | −1 |
| G37 | 7,690 | 7,674 | 7,683 | +9 |
| G38 | 7,687 | 7,667 | 7,679 | +12 |
| G39 (±1) | 2,408 | 2,389 | 2,403 | +14 |
| G40 (±1) | 2,400 | 2,383 | **2,400** | +17 |
| G41 (±1) | 2,405 | 2,402 | 2,404 | +2 |
| G42 (±1) | 2,481 | 2,463 | 2,468 | +5 |
| G51 | 3,848 | 3,844 | 3,846 | +2 |
| G52 | 3,851 | 3,849 | 3,847 | −2 |
| G53 | 3,850 | 3,847 | 3,848 | +1 |
| G54 | 3,852 | 3,851 | 3,851 | 0 |

Bold: at the best known value. Each arm is one seed per instance, so single-instance differences are noisy; the test
is over all 20.

**Validity:** median metered CPU 1.02 of the 10 s budget and 1.00 of the 60 s budget; no failed run.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| NO_DIFFERENCE slightly more likely than RENORM_BETTER (a 5–0 lead on 8 graphs often shrinks) | The lead held: RENORM_BETTER, 25–8 |
| If RENORM_BETTER, Part B gains on the larger planar ±1 instances but sets no record | Yes, and more broadly: the largest gains are on the 2,000-vertex instances (G35–G42: +9 on average, seven of eight up), +1 and ±1 alike. No record |

## What it means

- **A lead found by maturation and decided on fresh graphs transferred to the benchmark.** B20_R108 found the
  renormalisation configuration on generated planar graphs with too few decided graphs for its test. This study
  decided it on 40 new graphs, and only then took it to Gset, where it won 13–2.
- **The renormalisation restart is the move that matters on planar graphs.** It fixes the edges every elite agrees
  on, solves the coarse problem and projects back, which is a move at the scale of whole regions. That is the kind
  of move B20_R99 pointed to: where the search stalls, the best solutions differ globally.
- **The planar gap narrows but stays.** With RENORM on planar instances and B20_R110's runs on the others, Genesis's
  engine reaches the best known value on 29 of the 54 Gset instances at 60 s; over all its recorded runs, 33. It
  exceeds none.
- **Next:** B20_R116 gives every instance not yet reached five minutes with the best configuration Genesis has by
  this evidence (RENORM for planar instances).
