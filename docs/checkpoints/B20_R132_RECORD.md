# B20_R132 record: why Genesis's invention releases nothing: nothing it reached is big enough to see (NOT_SHOWN; diagnosis EXPRESSIVENESS in every class; DEV)

- **Run by:** the builder, on DEV; licenses nothing; adopts nothing. Version 3 of the contract is adopted nowhere.
  Preregistered at `c0431f6` (`scripts/b20r132_invention_bottleneck.py`, SHA-256
  `42769fcc9888090c82a88b5d47a437348508297e29fc3902bb829c064fe5a0a6`), unchanged. Run from a clean worktree of
  `13bd014`. The script and every module it imports are unchanged since `c0431f6`.
- **Disclosed: a lost first attempt.** A run started on 24 Oct 2026 at 20:50 in the third builder session. It left no
  evidence and no record: that session ended, nothing was pushed after 21:01, and Daniel confirmed on 26 Oct that it
  had stopped. Nothing from it was seen, so nothing from it could inform this run. This run started from an empty
  output directory.
- **This run:** alone on CPU 0, from 27 Oct 2026, 00:09 SGT (16:08:44Z on 26 Oct), in four slices:
  - slices 1 and 2: 6,601 s each, paused as designed;
  - slice 3: **stopped by a container restart** 4,583 s in (at about 21:06Z);
  - slice 4: 3,092 s to the end, resumed from the saved runs.

  Total 20,877 s (5.8 h) against 5.7 h estimated.
- **The restart.** Every run is saved as it finishes, and all 16,609 saved before the restart parse. At most the run in
  progress was lost; it was redone under the same seed. The restart may have moved the study to another machine. The
  CPU model before it was not recorded; after it the CPU was "Intel(R) Xeon(R) Processor @ 2.10GHz". Budgets are CPU
  seconds (median 1.0009 of the 1 s budget both before and after). A direct check finds no drift: REX's 12 control runs
  per graph, all made after the restart, against REX's runs on the same graphs before it, have a mean ratio of
  0.99993, 1.00007 and 1.00002 (random, planar, toroidal; 28 graphs each), well within run noise.
- `code_identity` `493c3d8a…de46`. Evidence `evidence/invention_bottleneck_b20r132/`; 19,600 runs. Recomputed
  independently, every value matches. That covers the baselines and T tables from the raw runs, every release
  decision from the recorded B scores, every audit, gain, label, the diagnosis, P1, P2, S1, the verdict and the power
  curves re-simulated from the REX pools.

## Result

**Verdict NOT_SHOWN.** In all 9 trajectories (3 classes × 3 replicates), none of the four arms released anything:
the protected judge (V2 at 160 and 240 units) did not, and neither did the candidate version 3 (L, and L12 with
12-graph confirmation). Every arm ended with its starting engine, so their final gains are identical (mean +0.038%
over REX on T1 + T2). P1 (L against V2) and P2 (L12 against L) have no non-zero differences: p 1, NOT_SHOWN and
NO_DIFFERENCE. **S1 holds**: version 3 released nothing in 60 zero-signal searches (upper 95% bound 0.049 ≤ 0.10).
There was nothing to audit.

**Diagnosis by the preregistered rule: EXPRESSIVENESS in every class.** There is measurable headroom: REX at 10 s
beats REX at 1 s. But no engine among the 112–117 tried per class beat REX at 1 s on the fresh truth set T2 by a
material and significant amount.

The four instruments per class:

| | random | planar | toroidal |
|---|---|---|---|
| **(H) headroom**: REX 10 s over 1 s, 24 graphs | +0.055% (14 of 24 better; p 6e-5): HEADROOM, just above MATERIAL 0.05% | +0.232% (20 of 24; p 8e-4): HEADROOM | +0.073% (10 of 24; p 1e-3): HEADROOM |
| **(X) expressiveness**: engines tried / positive on T1 | 115 / 38 | 117 / 89 | 112 / 67 |
| best by T1 (+%), then confirmed on T2 | +0.038 → **−0.006** (p 0.58) | +0.395 → **+0.288** (p 0.26) | +0.097 → **+0.048** (p 0.063; below MATERIAL) |
| label | NOT_FOUND | NOT_FOUND | NOT_FOUND |
| **(S) search**: distinct submissions | 35 | 35 | 40 |
| the best of them | the X winner | the X winner | the X winner |
| best training (A) gain per trajectory and arm | 0.01–0.08% | 0.10–0.26% | 0.03–0.11% |
| **(E) evaluation**: tau, V2 / L / L12 (mean of 3) | 2.13% / 0.42% / 0.26% | 2.26% / 0.75% / 0.36% | 1.57% / 0.25% / 0.12% |
| power to see a true +1%: V2 / L / L12 | 0.00 / 1.00 / 1.00 | 0.06 / 0.86 / 1.00 | 0.00 / 1.00 / 1.00 |
| delta50 (smallest gain seen with power ≥ 0.5): V2 / L / L12 | none ≤ 1% / 0.5% / 0.3% | none / 1.0% / 0.5% | none / 0.3% / 0.2% |
| one-step mutations of the start better on T1 (p < 0.05), of 48 | 3 | 3 | 0 |
| **bottleneck (rule)** | **EXPRESSIVENESS** | **EXPRESSIVENESS** | **EXPRESSIVENESS** |

How to read it:
- **In every class the best engine of the whole pool was one the searches had submitted.** It was never one of the 31
  fixed engines (the human designs written in the language, B20_R127's engines and 16 random engines). The search
  found the best of what was tried. What was tried does not beat REX by an amount that a fresh 12-graph set
  confirms.
- **The protected judge could not have released any of it.** Its thresholds (1.2–3.0%) are 11–52 times the best
  training gain in the same trajectory (0.01–0.26%), and its power to see even a true +1% gain is at most 6%. Version 3's thresholds are
  1.3–17 times smaller (0.11–0.89%). Even so, the best training gains stay below its thresholds, so it released nothing
  either.
- **Planar is the one class with a candidate.** Engine `5255466d…` is +0.395% on T1 and +0.288% on T2, but 12 graphs
  with one run each do not confirm it (p 0.26). EXPRESSIVENESS there may be a limit of the confirmation's power, not
  of the language. The rule's label is a lower bound in any case (the pool is finite).
- **Random:** the headroom is barely material (+0.055%). Nothing found beats REX there.
- **Toroidal:** the best gain on T2 (+0.048%) is below the materiality threshold.

**Controls.**
- **Planted gains** (pool evaluator: every engine's runs drawn from real REX runs, ×(1 + δ) for engines with the
  pair-descent statement D; no search started with D). Of 10 searches per arm and δ:

  | Class | δ = 1%: found / released | δ = 0.25%: found / released |
  |---|---|---|
  | random | 8–10 / 8–10 for every arm | 4–8 / 4–8 |
  | planar | L12 6/6, V2@160 3/3, the others 10/10 | 7–10 found, 0–2 released |
  | toroidal | 8–10 / 8–10 | 9/8–9 |

  The planted trait is reachable and the searches find it.
- **The planted control does not test the protected judge's real sensitivity.** In the pool world the random
  engines differ from REX only by run noise, so every judge's tau is small (V2's median 0.11–0.56%). That is why V2
  released planted gains here, against the expectation. The power curves, computed at each judge's real tau from
  the trajectories, are the test of sensitivity.
- **Zero signal** (20 pool searches per arm per class, no gain at all):

  | Arm | False releases | Where |
  |---|---|---|
  | L | 0 of 60 | |
  | L12 | 0 of 60 | |
  | V2 and V2@160 | **3 of 60** (upper 95% bound 0.124) | all three in the random class, where V2's pool tau was smallest (0.08–0.14%) |

  S1 concerns version 3 only and holds. The protected judge's false-release rate in this degenerate world is
  reported, as preregistered for every arm. It is not a criterion of this study, and V2 released nothing in the
  real trajectories.

**Validity.**
- Median CPU of the runs: 1.0009 of the 1 s budget and 1.0001 of the 10 s budget.
- Every arm's release history, reconstructed from its own calls, reproduces its judge's count and final engine.
- The protected judge's source is the preregistered one (`2ff4a5ab…dd6`).

**Starting engines.** In 3 of 9 trajectories (random 2, toroidal 1 and 2) the start incumbent is REX itself (the
search seeds its population with REX). Those trajectories' final gain is exactly 0.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| V2's tau about 1–3%; version 3's 0.3–0.8% | V2 1.2–3.0%; L 0.20–0.89%; L12 0.11–0.43% |
| random NO_HEADROOM (about 0.02%) | **HEADROOM**, +0.055%, just over MATERIAL |
| toroidal borderline | HEADROOM, +0.073% |
| planar HEADROOM, about 0.6% | HEADROOM, +0.232% |
| planar: expressible gains of 0.1–0.3%, found by the searches, released by version 3 but not by V2 (EVALUATION) | gains of about 0.3% found (+0.288% on T2) but **not confirmed** (p 0.26) and **released by neither**: EXPRESSIVENESS by the rule |
| random and toroidal: HEADROOM | **EXPRESSIVENESS** (both have material headroom; nothing found is confirmed) |
| V2's delta50 above 1% (none in the grid) | yes, in every class |
| version 3's delta50 0.2–0.5% | L 0.3–1.0%; L12 0.2–0.5% |
| the planted 1% FOUND in most searches, RELEASED by version 3 only | found in most; **released by V2 as well**, because the pool world gives every judge a small tau |
| S1 holds | yes (0 of 60) |
| P1 NOT_SHOWN, only planar differing | NOT_SHOWN; **no trajectory differs at all** |
| verdict NOT_SHOWN | yes |

## What it means for Genesis's invention

B20_R127 asked why the inventor released nothing; this study separates the reasons.
- The judge is far too coarse for gains of this size: V2's power at +1% is at most 6%.
- Even a judge 3–8 times finer (version 3) sees nothing, because the language and search, at 1 s on these graphs,
  reach gains of a few hundredths to a few tenths of a percent.
- The one candidate of a useful size (planar, about +0.3%) cannot be confirmed by 12 graphs.

So a better judge alone would not have changed B20_R127's result. What would have to change first is the size of the
gains reached, through a richer engine language or a regime with more headroom (planar shows +0.23% from ten times
the time), or the power of the confirmation for gains of about 0.3%.

The queue's `engine-invention` line stays stagnant. Its diagnosis is recorded as EXPRESSIVENESS. Which answer comes
next is a decision for Daniel, none preregistered:
- extend the engine language;
- confirm the planar candidate on more graphs and runs;
- move to a regime with more headroom.

Version 3 is not validated (P1 NOT_SHOWN), so `judge-v3-followup` stays dormant. B20_R128 runs next, as preregistered.

## Limits

- DEV, builder-run, one machine (possibly two: the restart, above). Three classes of generated graphs at 1 s. Three
  replicates per class. T1 and T2 have 12 graphs each, with one run per engine and graph.
- EXPRESSIVENESS is a lower bound: the pool is finite (112–117 engines per class). On planar it may be a power
  limit of the confirmation.
- The planted and zero-signal controls draw on REX's run noise only. They bound power from above, and they give every
  judge a smaller tau than real engines would.
- No independent replication.

## Tests

`tests_genesis/test_invention_bottleneck.py::RecordB20R132` (6), on the evidence:
- the preregistered script unchanged;
- validity (the CPU rule, consistency, the protected judge);
- the T tables, baselines and REX at 10 s from the saved runs;
- the power curves re-simulated from the saved REX pools;
- the analysis recomputed by `analyse` from the saved inputs (verdict, S1, releases, audits, P1, P2, every class's
  diagnosis, every final gain);
- the graphs regenerate with the recorded identities.

The 16 design tests are unchanged.
