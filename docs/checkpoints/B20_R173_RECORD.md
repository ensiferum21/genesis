# B20_R173 record: the protected judge releases an engine Genesis's own search found, on ±1-weighted planar graphs (RELEASED; DEV)

**Run by:** the builder, on DEV. The protected judge (`autonomy/feedback.py`, contract version 2, SHA-256
`2ff4a5ab…bdd6`) was called through its own class and was not changed. The release is the judge's, under its own
rules, and it licenses nothing beyond what that judge releases.

**Preregistration.** Preregistered at `d8cb798` (29 Oct 2026). The script is `scripts/b20r173_protected_release.py`,
SHA-256 `a3e038415e1b57199dc2aeab759f413338e0f61fec05db6786077afdabaa7291`, unchanged. It ran from the clean
worktree `/home/claude/r173-wt` at that commit.

**This run.** Alone on CPU 0, in one slice, from 30 Oct 2026, 01:15:56 to 01:49:55 SGT (29 Oct, 17:16 to 17:50
UTC): 34 min, against "about 35 min". There were 1,680 runs of the pinned mcx3 binary: the median 1 s run used
1.00 s of CPU, and the median 10 s reference used 10.00 s.

**After this run (disclosed): CPU 0 was idle for 5 h 35 min.** The builder wrote the script that would start
B20_R136 when this study ended, but did not launch it before the session's turn ended. CPU 0 was idle from 01:50
until 07:25 SGT, when B20_R136 started. No study was affected, but the rule that CPU 0 is never idle was broken.

**Evidence and checks.**
- `code_identity` `9a070bd026b6802c2843740191c88e2d027335fdb7ce53c4201f4cd9c2ade245`. It was recomputed at recording
  from a temporary worktree of the run tree `d8cb798`, and it matches.
- The evidence is in `evidence/protected_release_b20r173/`:
  - `runs.jsonl`: every run, with its CPU and value;
  - `calls.json`: every evaluation both judges asked for, in order;
  - `summary.json`;
  - `run.log`: the slice log.
- The record tests are `RecordB20R173` in `tests_genesis/test_protected_release_study.py`. They were drafted before
  the study ran (`docs/handoff/RECORD_TEST_DRAFTS.md`, 29 Oct 2026, 23:30 SGT). They are unchanged except for the
  `import statistics` the draft asked for, and they pass on the evidence (3 tests, 89 s). They check:
  - the script's digest;
  - validity, with the median CPU of the 1 s and 10 s runs recomputed;
  - the three graph sets, regenerated from the seed;
  - both judges rebuilt from the saved runs, using the protected `Judge` class itself with every run replayed from
    the evidence (no run is missing). Each judge's tau, starting score, candidate score and decision recompute to 12
    places;
  - the truth set's 24 per-graph gains, recomputed;
  - the verdict.

## Result

**Verdict RELEASED, by the preregistered rule; valid.** Every validity check held: the CPU medians, disjoint graph
sets, C0_1's recorded key, B20_R151's summary digest, mcx3's pin, and the protected judge's source.

| | Result |
|---|---|
| R1: the protected judge (v2), calibrated on REX and 47 random L0 engines (B − C, 12-graph splits) | tau 0.782% of the reference |
| C0_1's B score against REX's | 1.00273 against 0.99053: **+1.220%, above tau. Released** |
| S1: version 3 (16 one-step mutants of REX; research plane, adopted nowhere) | tau 0.493%; +0.957% over its start; released |
| S2: the truth, C0_1 against REX on 24 fresh graphs the judge never saw (two runs each) | **+1.122% mean (median 1.10%), positive on 24 of 24, range +0.45% to +2.15%; one-sided Wilcoxon p 6 × 10⁻⁸** |
| S3: the spread behind tau | SD of B − C 0.225% over all 48 calibration programs, and the same over the random engines alone; 0.124% over v3's mutants |
| S4: the split size at which version 2's tau would fall below C0_1's B gain | 5 graphs (descriptive) |

- **One detail of the evaluator, which does not change the verdict.** REX is one of version 2's calibration
  programs, so its first B evaluation (0.99316) went to the calibration. The judge's starting score is REX's second B
  evaluation (0.99053), a fresh seeded run, as B20_R132's evaluator counts occurrences. Measured against the first
  evaluation instead, C0_1's margin is +0.957%, still above tau. Version 3's calibration does not include REX, so its
  start is REX's first evaluation.
- **The candidate was fixed before the judge saw anything.** C0_1 was the engine B20_R165 pre-specified: the best
  training score of B20_R151's planar2000 searches. It was read from B20_R151's committed evidence with its recorded
  key and submitted once. No choice was made on the judge's splits.

## Against the expectation

The expectation was NOT_RELEASED, with moderate confidence: "random engines vary far more from graph to graph than
good ones, so version 2's tau will be several times C0_1's gain". **That was wrong.**
- On ±1-weighted planar graphs with 12-graph splits, random engines' split-to-split spread was small (SD 0.225%), so
  tau was 0.78%. That is at the bottom of B20_R132's range on other classes (0.75–2.45%).
- C0_1's gain was larger than that. Its B gain was 1.22%, and its truth-set gain 1.12%. That is consistent with
  B20_R165, where the 18 engines gained +1.16% on these graphs and C0_1 more.
- The expectation's other parts held: version 3 releases, and C0_1 beats REX on the truth set by about 1%.
- B20_R165's record had predicted the judge's power on this family better than this script's expectation did.

## Against random engines (an analysis added on 30 Oct 2026, 08:05 SGT, after this record was first pushed; disclosed)

The judge's calibration evaluated REX and 47 random engines of the L0 language on the same B and C splits
(`calls.json`). Their B scores show that **on this family REX is weak, and much of C0_1's margin over it is available
to random engines**:
- 21 of the 47 random engines scored above REX's first B evaluation (0.99316).
- 7 of them scored above the judge's release bar (its start 0.99053 plus tau, 0.99835). Measured against REX's first
  evaluation instead, 4 did. Had they been submitted, the judge would have released them as well.
- The best random engine scored 1.00219 on B. C0_1 scored 1.00273, 0.05% higher, from one run per graph on 12 graphs.

So the release shows two things: the builder's L0 language contains engines about 1% better than REX on ±1-weighted
planar graphs, and the judge can see a gain of that size. It does not show that Genesis's search beats random
sampling in that language. C0_1 came from a search of 480 evaluations, and sampling as many random engines would
likely have found engines close to it. That needs a random-sampling control at matched evaluations, which no study
has run on this family. The record test `test_random_engines_against_the_release_bar` (also added at this time)
recomputes these counts from `calls.json`.

## What it means

1. **The first release by the protected judge of an engine Genesis's own search found** (but see the section above:
   on this family, random engines of the same language would also have been released). The script's
   preregistration states the background: nothing Genesis invented had been released by this judge before (B20_R127
   and B20_R132 released nothing). Here, by the judge's unchanged rules and a single pre-specified submission, C0_1
   is released over the builder-configured REX on ±1-weighted planar graphs of 2,000 vertices at 1 s. The gain is
   confirmed on 24 further fresh graphs the judge never saw. That makes three independent sets of fresh graphs:
   B20_R165's 24, this study's B and C splits, and this truth set.
2. **How narrow it is.**
   - It covers one family. On unweighted planar graphs, tori and random graphs, B20_R165 found the same engines tie
     or lose.
   - The incumbent is REX, the builder's configuration of Genesis's engine, not a published state-of-the-art solver.
   - C0_1 came from a search over the builder's L0 language (B20_R151's Λ0 lane). The search found the engine, but
     the language was the builder's.
   - DEV scope. No independent replication, and no external claim.
   - On this family REX is weak: 7 of 47 random L0 engines would have cleared the same bar (above). The release is
     evidence about the language and the judge, not about the search.
3. **What it changes.** The case for a supervisor's decision on the judge's calibration, which a NOT_RELEASED verdict
   would have made concrete, is not made here: on this family, version 2 can see a confirmed gain of about 1%. Version
   2's blindness below about 1% (B20_R132) still stands on other classes.
4. **Next (candidates, not queued here):**
   - The control this result lacks: Genesis's search against random sampling of the same language at matched
     evaluations, on fresh ±1-weighted planar graphs, both through the protected judge.
   - B20_R136 (running) asks whether an invented sense can use C0_1 only where it wins.
   - An invention search on planar2_pm1 with this judge in the loop, from C0_1 as the incumbent, would ask whether
     Genesis compounds a released gain.

## Looks at the study's data before it finished

None. The study ran in one slice. Its log and summary were read after exit 0.

## Prior art

None is claimed for the judge or the procedure. The judge's calibration (z = 3 over a chi-square bound on the
spread of B − C) is the contract's (`autonomy/feedback.py`, version 2).
