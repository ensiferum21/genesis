# B20_R109 evidence: B20_R106's lead survives new seeds: REPLICATED

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r109_gset_replication.py`, preregistered at `34234fa` (committed through the index while
  B20_R108 ran, before its result).
- **Run:** alone on CPU 0, 3,410 s, on 23 Oct 2026 (16:02–16:59 SGT). `code_identity` `d1d6fe3a…`, the committed tree
  `34234fa`. B20_R111's and B20_R112's scripts were kept out of the working tree.
- **The other core.** While it ran, the builder recorded B20_R108 (documents, one 26 s test run, one worktree hash).
- **Inputs:** B20_R105's configurations (checked against its recorded SHA-256), and B20_R102's and B20_R106's
  recorded runs as each arm's first seed.

| File | What |
|---|---|
| `rows.jsonl` | 54 instances: each arm's earlier value, its two new runs (with witness cuts, re-checked by the domain's two checkers), the instance's class |
| `summary.json` | The three sign tests, the headline, per-arm figures, record candidates, validity |
| `run.log` | The run |

## Result: REPLICATED

Three runs per instance and arm at 10 s: the earlier study's seed and two new ones. Comparisons use per-instance
means.

| Test (54 instances, ties dropped, alpha 0.05 / 3) | Wins–losses (ties) | p | Label |
|---|---|---|---|
| mcx vs BURER2002 | 47–3 (4) | 4e-11 | **AHEAD** |
| mcx vs dSB | 47–2 (5) | 4e-12 | **AHEAD** |
| mcx's worse new run vs the best of the tools' four new runs | 36–6 (12) | 3e-6 | **AHEAD** |

| Arm, 10 s | Mean fraction of the best known value | Random | Toroidal | Planar | Instances where any run reaches it |
|---|---|---|---|---|---|
| **mcx (B20_R105's configuration)** | **0.99882** | 0.99966 | 0.99979 | 0.99734 | **30** |
| dSB | 0.99636 | 0.99865 | 0.99362 | 0.99473 | 12 |
| BURER2002 | 0.99559 | 0.99787 | 0.99327 | 0.99380 | 8 |

- **The stringent check holds.** The engine's *worse* new run beats the *best* of the four new runs of BURER2002 and
  dSB on 36 instances and loses on 6.
- **Where a tool's mean is ahead:** G4 (BURER2002 11,644.3 vs 11,642), G19 (903.7 vs 903) and G21 (929 vs 927).
  The margins are small.
- **On the ±1 tori:**

  | Instance | Best known | Engine's three runs | Best of the tools' runs |
  |---|---|---|---|
  | G32 | 1,410 | 1,410, 1,408, 1,408 | 1,392 |
  | G33 | 1,382 | 1,382, 1,382, 1,380 | 1,366 |
  | G34 | 1,384 | 1,382, 1,384, 1,384 | 1,368 |

- **The engine's spread across seeds is small:** a mean within-instance standard deviation of 2.0.
- **No run exceeded a best known value: no RECORD_CANDIDATE.**
- **Validity:** median metered CPU 1.02 of the budget; 0 failed runs of 324.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| REPLICATED | REPLICATED |
| The stringent check AHEAD or COMPARABLE | AHEAD (36–6) |
| No RECORD_CANDIDATE | None |

## What it means

B20_R106's lead does not depend on which seed each tool happened to get. With three seeds per arm, the configured
engine is ahead of both strongest pinned tools on 47 of the 54 instances. It reaches the 2012–13 best known values on
30 instances in at least one of three 10 s runs, against 12 for dSB and 8 for BURER2002. It still exceeds none of
them. B20_R110 asks what a longer run adds.
