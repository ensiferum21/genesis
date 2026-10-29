# B20_R167 record: ARA is calibrated on the sealed Limitation Zoo (ARA_CALIBRATED; DEV)

**Run by:** the builder, on DEV. It is a calibration and licenses nothing. The protected judge was not asked.

**Preregistration.** Preregistered at `33e8905` (28 Oct 2026, 01:15 UTC). The script is
`scripts/b20r167_ara_zoo_rerun.py`, SHA-256 `233610d030b8a0af747834e2d0006e209348f3a52a590283f779d3a03eb1af81`,
unchanged. It is B20_R141's design with the freshness clause repaired, on a fresh sealed seed and fresh indices
(21000–21094). It ran from the clean worktree `/home/claude/r167-wt` at that commit.

**A lost first attempt (disclosed).** The second builder session started this study on 28 Oct 2026 at 02:16 UTC.
That attempt left nothing on the branch: nothing was pushed after 28 Oct 02:59 UTC, and its session ended. When the
third session became the writer again (29 Oct 2026, 21:30 SGT, at Daniel's instruction), the study was restarted from
scratch from its preregistered script, with a fresh output directory. No row, ledger entry or log line of the first
attempt was seen by anyone, and none was used. The verdict below is the restarted run's alone.

**This run.** Alone on CPU 0, in three slices of the study log (`/home/claude/logs/r167_slices.log`):
- the first, from 29 Oct 2026, 13:30 UTC, paused as designed after 6,603 s with 256 of 475 arm runs;
- the second, from 15:20 UTC, paused after 6,825 s with 470 arm runs (the slice check runs between arm runs, so a
  slice can overrun by one run);
- the third, from 17:15 UTC, ended with exit 0 after 41 s.

That is 3.7 h in all, against "about 3 h". The arms' own CPU was 3.7 h, of which the tuning sweep took 3.3 h.

**Evidence and checks.**
- `code_identity` `74f488ab28051405c375907ab78d7e11185a4e3c73c596cf560163e0e4934f7d`, recomputed at recording
  from a temporary worktree of the run tree `33e8905`: it matches.
- The evidence is in `evidence/ara_zoo_b20r167/`: the arm rows, the judge's ledger (275 submissions), the run log and
  `summary.json`.
- The record tests are `RecordB20R167` in `tests_genesis/test_ara_zoo_rerun_study.py`. They were drafted before the
  study ran (`docs/handoff/RECORD_TEST_DRAFTS.md`) and are unchanged. They pass on the evidence (4 tests, 71 s):
  - the script's digest;
  - the environments and the validity record, the freshness clause recomputed;
  - the analysis, experiment C and the verdict, recomputed from the saved rows, ledger and keys;
  - the 95 environments regenerate from the sealed seed with their keys, and every one of the 275 judged
    submissions re-judges, with the same oracle, range and sealed gain from re-executing its variant.
- B20_R141's record tests still pass.

## Result

**Verdict ARA_CALIBRATED, by the preregistered rule; failed [], valid.** Every validity check held: well formed,
within budget, the pinned judge, and fresh.

| Experiment | Result | Its bar |
|---|---|---|
| A1: ARA's top-1 localisation, 50 defect environments | 42 of 50 (chance 1/4), p 3.0 × 10⁻¹⁸ | p < 0.05 |
| A1 per class, Holm | GLOBAL_ONLY, SEARCH_WEAK, EVAL_NOISY 5 × 10⁻⁶; SENSE_BLIND 0.007; FUSION_NEEDED 0.078 | reported |
| A2: NONE on NULL and NO_HEADROOM | 30 of 30 | at least 0.8 |
| B: ara over tuning, per class, Holm | GLOBAL_ONLY 0.005; SENSE_BLIND, FUSION_NEEDED, EVAL_NOISY 0.016; SEARCH_WEAK 0.31 | some class < 0.05 |
| C: every promoted variant well formed and admissible | no failures (195 promotions) | none |
| D: ara2 over blind2 (2 tries each) | +0.408 of the range, p_Holm 2.7 × 10⁻⁶ (38 non-zero pairs) | both p < 0.05 and +0.05 |
| D: ara2 over tuning | +0.559, p_Holm 1.2 × 10⁻⁷ (39 non-zero pairs) | |
| S: releases on the 45 controls | ara 0, ara2 0 (upper bound 0.064 each); blind 1, blind2 0, tuning 0 | at most 0.10 for ara and ara2 |

**By class**, the mean released gain on the 10 environments of each class, in units of the attainable range:

| Class | ARA localised | ara | ara2 | blind (14 tries) | blind2 | tuning | oracle key |
|---|---|---|---|---|---|---|---|
| SENSE_BLIND | 7 of 10 (2 NONE) | 0.668 | 0.639 | 0.760 | 0.063 | 0.019 | 0.847 |
| GLOBAL_ONLY | 10 of 10 | 1.172 | 1.138 | 1.172 | 0.846 | 0.071 | 1.144 |
| FUSION_NEEDED | 5 of 10 (3 NONE) | 0.320 | 0.307 | 0.449 | 0.336 | 0.000 | 0.452 |
| SEARCH_WEAK | 10 of 10 | 1.012 | 1.003 | 1.012 | 0.520 | 0.831 | 1.223 |
| EVAL_NOISY | 10 of 10 | 1.200 | 1.200 | 1.200 | 0.482 | 0.572 | 1.187 |

Over the 50 defect environments the mean released gain was ara 0.874, ara2 0.857, blind 0.919, blind2 0.449 and
tuning 0.299.

On the controls:
- ARA diagnosed NONE on all 30 NULL and NO_HEADROOM environments.
- It diagnosed "expressiveness" on all 15 DECOY environments, as designed (a decoy is a defect on dev by
  construction). The judge refused every resulting submission.
- The one release on a control was blind's, on a NO_HEADROOM environment (index 21029).

Median units spent per environment:

| Arm | Median units |
|---|---|
| ara | 1,589 |
| ara2 | 1,570 |
| blind2 | 1,444 |
| tuning | 2,371 |
| blind | 9,897 |

## Against the expectation and against B20_R141

The expectation, written into the script before the run and informed by B20_R141's descriptive results, was
ARA_CALIBRATED with high confidence: A passes with FUSION_NEEDED the weakest class; B passes, but not on SEARCH_WEAK,
with FUSION_NEEDED borderline; C, D and S pass. That is what happened, with one difference: B is significant on
FUSION_NEEDED here (0.016; 0.063 in B20_R141).

The two runs agree closely on fresh environments: 42 of 50 localised in both; 30 of 30 NONE in both; ara2 over blind2
+0.408 here, +0.413 there; no release by ara or ara2 on any of 90 controls across the two. So B20_R141's environments
were not favourable.

## What it means

1. **ARA is calibrated on the zoo (`ara-calibrated`).** On planted limitations it has never seen, it says where the
   limitation is far above chance, says "nothing to fix" where there is nothing, and released nothing on 45 controls.
   With two tries it gets about twice the gain blind rewriting gets with two. With fourteen tries blind rewriting
   matches it, at about six times the units.
2. **Its limits, as measured.**
   - FUSION_NEEDED is its weak class: localised 5 of 10, NONE on 3, gain 0.32 against the oracle key's 0.45.
   - SENSE_BLIND is next: 7 of 10, NONE on 2.
   - SEARCH_WEAK is the class tuning repairs alone, so B is not significant there.
   - The zoo is planted by the builder. A calibrated ARA on the zoo is not evidence that ARA helps on a real
     workflow; that is B20_R142's question.
3. **What it unlocks.** `ara-calibrated`, which B20_R142 (ARA on the real engine-choice workflow) requires, and the
   expectation of B20_R144 (ARA applied to its own settings), whose script was drafted to wait for this verdict.
4. **For the protocol:** B20_R167's design tests ran `main` through the registered path (the lesson of B20_R141),
   and the repaired clause held in the registered run.

## Looks at the study's data before it finished

None. Progress was checked by the count of slice exits and the arm-run counts in the slice log's pause lines only.
The run log and the summary were read after exit 0.

## Prior art

None is claimed. Diagnosis by oracle substitution is ablation and its relatives (Meyes et al. 2019). The controls
follow `docs/OMEGA_EXPERIMENT_PROTOCOL.md`.
