# B20_R144 record: ARA's cycle, applied to its own settings, adopted nothing (NOTHING_ADOPTED; DEV)

**Run by:** the builder, on DEV. ARA experiment G (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §13; milestone 2). It is a
calibration and licenses nothing.

**Preregistration.** Preregistered at `7acf0e4` (30 Oct 2026). The script is `scripts/b20r144_ara_improves_ara.py`,
SHA-256 `05523955c17aadcda17ef61f2191854b32711840bbdaf1e79726e74ed8f058c3`, unchanged. It ran from the clean worktree
`/home/claude/r144-wt` at that commit.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 07:38:30 to 08:23:26 SGT: 45 min, against "about an
hour". It made 792 ARA runs: 552 on meta-development and 240 held out. B20_R157 started on CPU 0 11 s after it
ended.

**Evidence and checks.**
- `code_identity` `72be39a04bf143770f1b491e4730023774ac0fd3b9a760959fef9686a5a8c1cd`. It was recomputed at recording
  from a temporary worktree of the run tree `7acf0e4`, and it matches.
- The evidence is in `evidence/ara_improves_ara_b20r144/`:
  - `runs.jsonl`: every ARA run, with its key, family, index, class, hint, gain, promotion, diagnosis, localisation,
    units and variants;
  - `summary.json`;
  - `run.log`: the slice log.
- The record tests are `RecordB20R144` in `tests_genesis/test_ara_improves_ara_study.py`. They pass on the evidence,
  and the whole suite passes (9 tests, 312 s). They check:
  - the script's digest;
  - the saved runs: well formed, within their units, of the right families, no held-out hint, and every held-out
    (environment, arm) key present;
  - the whole study replayed from the saved runs, with every ARA cycle forbidden. This re-derives the meta-cycle's
    choice, the tuning control's choice, validity, P1, P2, S and the verdict, all to the same summary;
  - a sample of saved runs re-executed from scratch, which reproduces the same records.
- **Two disclosures about the record tests.**
  - The draft was committed at 07:40, two minutes after the study started (07:38:30). No file of the study's output
    had been opened.
  - One line was changed at recording: the test file needed `import hashlib` at the top. The draft wrongly said it was
    already there, and without it the digest test raised a NameError.

## Result

**Verdict NOTHING_ADOPTED, by the preregistered rule; valid.** Every validity check held: well formed, within units,
the pinned judge, the families, the space, no held-out hint. The meta-cycle kept ARA_v1's settings, so v2 is v1.
P1 and P2 are reported, and nothing is claimed from them.

**The meta-ladder** (24 base-family environments; each of ARA's components replaced by a stronger stand-in), as the
mean paired gain in released gain with its 95% bootstrap interval:

| Term | Mean | Interval |
|---|---|---|
| localisation (the planted location as a hint) | +0.032 | [0, 0.082] |
| exploration (20 variants, depth 3) | +0.012 | [0, 0.034] |
| evaluation (12 exact repeats) | −0.022 | [−0.106, 0.042] |
| observation (48 random senses, four edge aggregates) | −0.028 | [−0.084, 0] |

No lower bound cleared 0.02, so the diagnosis was NONE.

**The candidates.** With no located component, the first six one-step neighbours were tried, in the alphabetical
order of the settings:
- the battery's random senses up and down;
- the depth up and down;
- the richer edge aggregates;
- the exact repeats up.

**On all 24 choice environments, every one of them released exactly what ARA_v1 released (mean difference 0.0).** So
nothing was adopted. The two settings most likely to matter, the number of variants and the ranking, come later in
that order and were never tried (see What it means).

**The tuning-only control** (random settings at the same 288 evaluations) adopted
`{max_variants 14, depth 3, blind ranking, four edge aggregates, 48 random senses, 4 exact repeats}`. That is, more
variants with blind ranking.

**Held out** (80 environments of the families H1 and H2, 50 defects):

| | v2 (= v1) | v1m (v1 + C_meta/80 units) | tune |
|---|---|---|---|
| Mean released gain on the 50 defects | 0.679 | 0.679 | 0.718 |
| Mean units per environment | 2,687 | 2,687 | 7,576 |

- P1, v2 − v1m: all 50 differences zero (n 0, p 1). With 2 variants, ARA_v1 spends about 2,700 units of its
  36,000-unit allowance and cannot use the extra 26,889.
- P2, v2 − tune: −0.039 (one-sided p 0.96; two-sided p 0.079). Tune was ahead on 16 defect environments and v2 on 8.
  Tune spent 2.8 times the units, so it is not a unit-matched comparison.
- **S: v2 released on 1 of the 30 held-out controls.** This was H2's NO_HEADROOM environment 62077: ARA diagnosed
  "evaluation", and the judge confirmed a sealed gain of 0.23 of the range. The Clopper–Pearson upper bound is 0.149,
  against a bar of 0.15, so S passes, narrowly. The tuning control released on the same environment and on one more
  (62045). A sealed gain on a NO_HEADROOM environment means H2's generator does not guarantee "no headroom" the way
  the base family's does. This is a defect of the held-out family's control, not a false release by the judge.
- **S5: ARA_v1's top-1 localisation on the held-out defects was 0.76** (38 of 50), against 0.84 on the base family in
  B20_R167. By class:
  - GLOBAL_ONLY and SEARCH_WEAK: 10 of 10;
  - EVAL_NOISY: 8;
  - SENSE_BLIND: 5;
  - FUSION_NEEDED: 5.
- Per family, v1's mean gain was lowest on H2's FUSION_NEEDED (0.13) and SENSE_BLIND (0.20).

## Against the expectation

The expectation gave NOT_SHOWN about 0.45 and NOTHING_ADOPTED about 0.3. It said the meta-ladder would "likely find
no term whose lower bound clears 0.02, or find localisation", and that S passes. NOTHING_ADOPTED happened.
- The ladder found nothing, as expected.
- That none of the six candidates changed a single released gain was not foreseen.
- S passed by a margin of 0.001.

## What it means

1. **Milestone 2 is not met.** ARA did not improve its own procedure here. The result is a calibration on the zoo.
2. **Why nothing was adopted, as measured.**
   - ARA_v1's headroom on the base family is small. The largest ladder term, localisation by an oracle hint, was
     +0.03.
   - With only 2 variants, most of ARA's settings do not change which variants it tries. Six one-step changes to the
     battery, the depth, the edge aggregates and the repeats left every released gain unchanged.
   - When the ladder locates nothing, `meta.neighbours` falls back to alphabetical order. That order put the number
     of variants and the ranking, the settings most likely to matter, seventh and later, so they were never tried.
     This is a design weakness of the meta-cycle's fall-back, found here, not a validity failure.
3. **What the tuning control shows.** Random settings with 14 variants and blind ranking released more on held-out
   defects (+0.039, not significant two-sided), at 2.8 times the units. That is B20_R150's and B20_R167's finding again:
   more tries buy gain at a price in units.
4. **Before B20_R145** (ARA over generations), which depends on this study:
   - the meta-cycle should order its fall-back candidates by measured sensitivity, or try every setting once,
     instead of alphabetically;
   - the held-out families' NO_HEADROOM control should be checked for real headroom, for example by the oracle key,
     before it is used as a control again.

## Looks at the study's data before it finished

The count of lines in `runs.jsonl` was read once (at about 08:23; 792) to estimate the time left. No run's content was read.
The summary and log were read after exit 0.

## Prior art

None is claimed. Algorithm configuration by search over a configuration space (SMAC, irace, ParamILS) is the
standard comparator for a tuning-only control.
