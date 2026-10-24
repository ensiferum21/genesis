# B20_R123 evidence: three more five-minute seeds on the 14 Gset instances still below: 5 reached; a "record" on G38 that the literature already had

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r123_gset_seeds.py`, preregistered at `2f76aab`.
- **Run:** alone on CPU 0, on 24 Oct 2026, in two planned slices: 09:06–10:57 SGT (22 runs) and 10:57–12:39 SGT
  (20 runs).
- **Code identity:** `646dc6d3…`, the committed tree `2f76aab`, in both slices. The later setups (B20_R124–R128) were
  committed through the index only and kept out of the working tree.
- **The other core.** While it ran, the builder built and tested B20_R125–R126 (mcx2 and the self-improvement
  machinery), which used CPU 1 for unit tests and a few short engine runs: one look at six graphs at 1 s,
  sanitizer runs, and brute-force checks on small graphs. It also searched the literature (web).

| File | What |
|---|---|
| `plan.json` | The 14 instances (computed at the start from every recorded run), their best earlier values, the configurations (B20_R116's) |
| `rows.jsonl` | 42 runs of 300 s: value, witness cut (re-checked by the domain's two checkers), metered CPU, descriptor |
| `summary.json` | Per instance: the three values, runs at the best known value, spread of the four 300 s values (with B20_R116's), mean gap; record candidates; validity |
| `run.log` | Both slices |

## Result

- **5 of the 14 reach the best known value in at least one of three runs:** G15, G22, G31 (all three runs), G38 and
  G41.
- **Over all recorded runs, Genesis's engine now matches the best known values on 45 of the 54 Gset instances.**
  G38 counts at its corrected value (below).
- **Spread of a single 300 s run:** 0–2 on the random and smaller planar instances. On the 2,000-vertex planar
  instances it is 4–12: G35 10, G36 11, G38 12, G41 8, G42 4.

| Instance | Best known (table at the run) | Three 300 s runs | Best | Spread (4 runs) |
|---|---|---|---|---|
| G14 | 3,064 | 3,062, 3,063, 3,063 | 3,063 | 1 |
| G15 | 3,050 | 3,049, 3,049, **3,050** | 3,050 | 1 |
| G22 | 13,359 | 13,358, 13,358, **13,359** | 13,359 | 1 |
| G24 | 13,337 | 13,336, 13,336, 13,335 | 13,336 | 1 |
| G26 | 13,328 | 13,325, 13,325, 13,326 | 13,326 | 2 |
| G31 | 3,309 | **3,309**, **3,309**, **3,309** | 3,309 | 1 |
| G35 | 7,686 | 7,675, 7,669, 7,679 | 7,679 | 10 |
| G36 | 7,679 | 7,673, 7,669, 7,671 | 7,673 | 11 |
| G38 | 7,687 | **7,688**, 7,677, **7,688** | 7,688 | 12 |
| G41 | 2,405 | 2,404, **2,405**, 2,404 | 2,405 | 8 |
| G42 | 2,481 | 2,472, 2,476, 2,473 | 2,476 | 4 |
| G51 | 3,848 | 3,847, 3,844, 3,846 | 3,847 | 3 |
| G53 | 3,850 | 3,847, 3,848, 3,847 | 3,848 | 2 |
| G54 | 3,852 | 3,851, 3,851, 3,851 | 3,851 | 0 |

**Validity:** median metered CPU 1.00 of the budget; no failed run.

## The record candidates on G38, and why they are not records

Two independent runs found cuts of **7,688** on G38. The table the study ran with held 7,687, from the 2013
breakout-local-search and 2012 MACUT max-cut papers. Both witnesses pass the domain's two independent checkers, so
the study flagged them as RECORD_CANDIDATEs, as preregistered.

**Before anything was said, the literature after 2013 was checked:**
- Wu and Hao's memetic algorithm for **max-bisection** (Comput. Oper. Res. 40:166–179, 2013) reports 7,688 on G38. It
  was reproduced in 2015 (MA-ZLL) and in 2016–17 (ITS: Ma, Hao and Wang, Comput. Oper. Res. 81:78–89). This was read
  from their table of 18 of the instances above.
- A bisection is a cut, so **7,688 was already a known max-cut value**. The table had missed the bisection
  literature.
- **Result: G38 is matched, not beaten. No record.**

**The table is corrected** (`data/gset/best_known.json`, commit `8d7e402`):
- the bisection values are held as a source (`wuhao2013_bisection`); among the 18, only G38 changes;
- every source records when it was added, and `gset.best_known(as_of)` gives the table as it stood at a time;
- the records of B20_R102–R123 are recomputed against the table they ran with.

The literature check also found later work to check any future candidate against:
- Ma and Hao's multiple search operator heuristic (2017) improved six max-cut values. Which six could not be read
  from the PDF.
- A 2025 preprint (Cosm) reports new cuts on G72, G77 and G81, outside G1–G54.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| About a third of the 14 reach their best known value in at least one of three runs | 5 of 14 (36%) |
| More of the one-short instances than of G36, G38 and G42 | Four of the five reached were one short; G38 also reached, G36 and G42 did not |
| Spread of single 300 s runs on the 2,000-vertex planar instances about 10 | 4 to 12 |
| No RECORD_CANDIDATE | Two, on G38; both resolved by the literature as an already-known value |

## What it means

- **More seeds close one-unit gaps; the large planar instances need more than luck.** Single five-minute runs
  there vary by up to 12. Three seeds did not reach G35, G36 or G42.
- **The record check worked as designed, and caught a gap in our own table.** The value was flagged, re-checked and
  cross-checked against the literature, and found already known. The table now includes bisection lower bounds.
- **Standing: 45 of 54 Gset instances matched over all of Genesis's runs, none beaten.**
