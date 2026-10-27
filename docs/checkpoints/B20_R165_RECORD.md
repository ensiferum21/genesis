# B20_R165 record: Genesis's searched max-cut engines beat REX on fresh planar graphs, all of it on ±1-weighted ones (REPLICATED_WITH_SINGLE_ENGINE; DEV)

**Run by:** the builder, on DEV. It is a confirmatory replication of B20_R151's secondary S5. It licenses nothing and
releases nothing: the protected judge was not asked.

**Preregistration.** Preregistered at `ff6475b`. The script is `scripts/b20r165_planar_replication.py`, SHA-256
`fbf968c5e2cf22f3e6f2720df16ae2586f08dbcc32f5f556ca4df99ed523516f`, unchanged. It ran from the clean worktree
`/home/claude/r165-wt` at that commit.

**This run.** Alone on CPU 0, from 27 Oct 2026, 20:36 UTC:
- **A container restart** stopped the first slice at about 21:19 UTC, with no exit logged:
  - every one of the 2,031 runs saved before it parses. At most the run in progress was lost, and it was redone
    under its own seed;
  - the CPU after the restart was "Intel(R) Xeon(R) Processor @ 2.10GHz". The model before it was not recorded;
  - budgets are CPU seconds: median 1.0009 of the 1 s budget and 1.00007 of the 10 s.
- The second slice resumed at 21:21 UTC and ended at 21:50 UTC with exit 0.

**Evidence and checks.** `code_identity` `139eaad5…727f`. The evidence is in
`evidence/planar_replication_b20r165/` (`summary.json` SHA-256 `df8fde1b…e119`). The record tests (`RecordB20R165`
in `tests_genesis/test_planar_replication_study.py`) were written before the study ran and checked against a stub
run. They pass unchanged on the evidence:
- the script's digest;
- validity, with the CPU medians recomputed;
- every final value recomputed from the saved runs;
- the analysis and the verdict recomputed;
- the graphs regenerate.

## Result

**Verdict REPLICATED_WITH_SINGLE_ENGINE, as expected before running.**

| | Result |
|---|---|
| P1: the 18 engines' mean gain over REX at 1 s, 48 fresh planar graphs | **+0.582%**, p_Holm 6.2 × 10⁻⁷: PASS |
| P2: C0_1 (`R B1296 B703 C b1 R B703 B703 C C`, chosen by training score) | **+0.661%**, p_Holm 6.2 × 10⁻⁷: PASS |
| S1: each engine, Holm over 18 | all 18 positive, from +0.430% to +0.773%, each p_Holm ≤ 0.003 |
| S3: REX at 10 s over REX at 1 s (the headroom) | +0.574% (p 8 × 10⁻¹⁰) |
| S3: the engines at 1 s against REX at 10 s | +0.008% (p 0.67): **at 1 s they equal REX at ten times the time** |
| S5: the Λ1 engines' mean against the Λ0 engines' | −0.079% (p 4 × 10⁻¹¹): Λ1's engines are slightly worse |
| S2: generalisation to toroidal2000 (±1 tori) | −0.277%: every engine is worse than REX |
| S2: generalisation to random2000 | −0.211%: every engine is worse than REX |

**The qualification that matters, S4: the whole gain is on the ±1-weighted family.**

| Family (24 graphs each) | The 18 engines' mean gain | Graphs where it is positive | REX at 10 s |
|---|---|---|---|
| planar2 (unweighted) | +0.003% (p 0.36) | 14 of 24 | +0.143% |
| planar2_pm1 (±1 weights) | **+1.161%** (p 6 × 10⁻⁸) | **24 of 24** | +1.004% |

The same split holds in B20_R151's truth graphs, recomputed for this record from its evidence: +0.010% on planar2
(7 of 12 graphs positive) and +1.193% on planar2_pm1 (12 of 12).

*A defect in the script's secondary analysis (S4), disclosed.* The S4 table in `summary.json` also lists the
toroidal and random families, at +0.000% and p 1. That is an artefact: S4 is computed over the planar graphs only,
so those families have no graphs in it. The two planar rows are correct, and the toroidal and random results are
S2's. No preregistered quantity is affected.

## What it means

1. **Replicated.** The engines Genesis's searches found in B20_R151 beat REX on 48 graphs that nothing had seen,
   with large margins and a single pre-specified engine passing on its own. B20_R151's S5 was not a fluke.
2. **What it is, precisely.**
   - The gain is on ±1-weighted planar graphs of 2,000 vertices at 1 s. There the engines beat REX by 1.16% on every
     graph, more than REX gains from ten times the time (+1.00%).
   - On unweighted planar graphs they tie REX.
   - On ±1 tori and random graphs they lose to it (−0.2% to −0.3%).
   - So the searches specialised to the structure of their training graphs. These were mixed planar families, and
     the ±1 family is where REX's fixed configuration leaves room. They did not find a better general engine.
3. **This is the first confirmed engine gain of Genesis's own searches over the builder-configured REX on fresh
   graphs.** B20_R127 tied it, and B20_R132 found nothing confirmed. It is narrow (one family, one size, one budget),
   it is at DEV, and it is not a release.
4. **For the language line:** S5 adds that the Λ1 engines are slightly but clearly worse than the Λ0 engines on
   fresh planar graphs. That fits B20_R151's NO_LANGUAGE_EFFECT reading in the hurting direction, and B20_R152's
   refusals.
5. **Possible next steps (not preregistered):**
   - a release attempt through the protected judge on planar2_pm1, whose power at +1.2% should be far better than
     at B20_R132's sizes;
   - and a search on ±1 tori and random graphs to see whether the specialisation transfers as a method.

## Looks at the study's data before it finished (disclosed)

- After the restart, the saved runs were parsed to check their integrity. No value was printed.
- The study's `run.log` was not read until it finished. Its modification time was noticed, nothing else.
- Progress was checked by the count of slice exits only.

## Prior art

None is claimed. The engines are the searches' own (B20_R151). REX is the builder's configuration of mcx3.
