# F2: semantic checks of the transcribed Brankov–Hansen–Stevanović bounds (engineering, 27 Oct 2026)

This is not a study; it decides nothing about Genesis.

**What was checked.** `report.json` was written by `scripts/f2_bhs_transcription.py`, run alone on CPU 1 in about
5 s. The script checks the 68 formulas of `src/genesis/conjecture/sealed.py`. Those formulas were transcribed from
four papers and a GitHub issue that restate the 2006 bounds (sources S1–S5, listed in that module). The 2006 text
itself was not reachable from this session.

**The checks:**
- every formula parses in `conjecture.expr`'s grammar;
- its value at the regular point d = m = r, for r = 1 to 6, divided by 2r (2r is μ of every r-regular bipartite
  graph);
- on every connected graph with 2 to 7 vertices (the networkx atlas: 995 graphs), every violation of μ ≤ max f
  found in floating point, re-checked by an exact rational Rayleigh certificate (`conjecture.verify`).

**Results:**
- **No proved or open bound is violated** on any of the 995 graphs. This holds under the domain's conservative
  reading, where a graph is never a counterexample if the bound is undefined at one of its vertices or edges. It
  also holds under the lenient reading, where undefined terms are dropped from the maximum.
- **Bounds 48, 57 and 61 are refuted exactly by the path on 3 vertices** (μ = 3 against 2.929, 2.817 and 2.929).
  Taieb et al. report P3 as a counterexample to exactly these three. That independently confirms the transcription
  of 48, which has only one textual source.
- **Every formula equals 2r at the regular point except bound 28's S4 reading,** which is √1.5 × 2r. Bound 28 is
  tier X (S2 and S4 disagree on a coefficient). S2's reading would equal 2r. That does not settle the dispute, so
  28 stays excluded until the 2006 text is read.
- Many edge bounds of the form 2 + √(… − 4(…) + 4) are undefined at some edge of some small graph (a negative
  radicand). For example, the proved bound 39 is undefined on 215 of the 995 graphs. Counts are in `report.json`.

**Tiers** (the sealing rule in `sealed.py`):

| Tier | Meaning | Bounds |
|---|---|---|
| A1 | Two or more sources give the identical formula | 51 bounds |
| A2 | One source exact, a second compatible up to an extraction artefact | 10, 13, 19, 22, 24, 25, 27, 32, 40, 52, 53 |
| B | One source only | 45, 48, 50, 51 |
| X | Sources disagree; excluded | 28, 41 |

**The primary sealed set** is A1 and A2, minus the duplicate 23 and minus the proving test's held-out family A
(18, 21, 24, 30, 40). That leaves 56 bounds.
