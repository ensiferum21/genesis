# B20_R136 record: a sense Genesis synthesised chooses the engine per graph, but not materially better than always running C0_1, and no better than the builder's degree feature (NOT_SHOWN; DEV)

**Run by:** the builder, on DEV. Experiment A of `docs/OMEGA_RECURSIVE_INVENTION.md` §15, the vertical slice. It
licenses nothing.

**Preregistration.** Preregistered at `6bb39ab` (29 Oct 2026). The script is `scripts/b20r136_sense_choice.py`, SHA-256
`357cd5ed202b8b79987668d081d408ad8fcbf32ef51cb5cae6d6fa3c979b2bcb`, unchanged. It ran from the clean worktree
`/home/claude/r136-wt` at that commit.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 07:24:51 to 07:38:30 SGT: 14 min, against "under 20
min". It made 760 measurements:
- 400 full 1 s engine runs, with median CPU 1.00 s;
- 240 charged runs, at 0.93–0.99 s;
- 120 sense timings.

It started 5 h 35 min late, because CPU 0 was left idle after B20_R173 (disclosed in `docs/checkpoints/
B20_R173_RECORD.md`).

**Evidence and checks.**
- `code_identity` `26a4b72b79cd83ba4a9f9639308fd379f5400a60c10eae830ff8a7bef2945bd5`. It was recomputed at recording
  from a temporary worktree of the run tree `6bb39ab`, and it matches.
- The evidence is in `evidence/sense_choice_b20r136/`:
  - `runs.jsonl`: every engine run and sense timing;
  - `search.json`: the sense search's result, the hand features' fit, and FIXED's choice;
  - `summary.json`;
  - `run.log`: the slice log.
- The record tests are `RecordB20R136` in `tests_genesis/test_sense_choice_study.py`. They were drafted before the
  study ran (`docs/handoff/RECORD_TEST_DRAFTS.md`, 29 Oct 2026, 23:30 SGT) and appended unchanged. They pass on the
  evidence (139 s). They check:
  - the script's digest;
  - the graphs, regenerated from the seed;
  - the sense search, re-run from the saved training runs, which finds the same sense with the same cross-validated
    value;
  - every test graph's sense value, choice and charged score, recomputed;
  - P1's test and the verdict.
- **One test was added at recording, disclosed.** `test_the_decision_recomputes_from_the_rows` recomputes P1 and P2,
  Holm, the material rule, S1's means and the verdict from the saved rows. The draft checked P1's p-value but took
  the pass flags from the summary.

## Result

**Verdict NOT_SHOWN, by the preregistered rule; valid.** Every validity check held: the CPU median, disjoint graph
sets, C0_1's key, B20_R151's digest, mcx3's pin, and the protected judge's source.

**What the search found.** FIXED, the engine with the better mean training score, is **C0_1**, not REX. Its +1.2% on
±1-weighted planar graphs outweighed its losses elsewhere. The sense search evaluated 300 candidates and chose
`m / q90(degree)`: the number of edges over the 90th percentile of the degrees. Its stump runs C0_1 below 620 and REX
above. Its cross-validated training value was 0.229%, against 0.224% for the better hand feature (degree CV) and the
oracle's 0.232%. Nothing about the families was given to the search.

Mean score per test graph (cut relative to REX at 1 s), over 60 graphs:

| Arm | Mean |
|---|---|
| ORACLE (the better engine per graph, by its 1 s runs) | +0.263% |
| HAND (degree CV > 1.157 → C0_1; charged) | +0.269% |
| SENSE (m / q90(deg) < 620 → C0_1; charged) | +0.216% |
| FIXED (C0_1 everywhere, 1 s) | +0.129% |

| Test | Mean difference | p | p_Holm | Material 0.1% | Passed |
|---|---|---|---|---|---|
| P1: SENSE − FIXED | +0.087% | 0.00045 | 0.0009 | no | **no** |
| P2: SENSE − HAND | −0.054% | 0.72 | 0.72 | no | **no** |
| S5: HAND − FIXED (secondary) | +0.141% | 4 × 10⁻⁵ | | | |

Per family (12 graphs each), how often each sense chose C0_1, and the mean scores:

| Family | SENSE chose C0_1 | HAND chose C0_1 | SENSE | HAND | FIXED | ORACLE |
|---|---|---|---|---|---|---|
| planar2 | 11 | 9 | +0.035% | +0.036% | +0.061% | +0.065% |
| planar2_pm1 | 9 | 12 | +0.863% | +1.165% | +1.230% | +1.230% |
| torus2d_pm1 | 0 | 0 | +0.089% | +0.101% | −0.190% | +0.018% |
| erdos | 0 | 0 | −0.004% | −0.012% | −0.098% | 0.000% |
| erdos_pm1 | 0 | 0 | +0.095% | +0.056% | −0.359% | 0.000% |

Both senses avoided C0_1's losses on tori and random graphs. The difference between them is on ±1-weighted planar
graphs:
- the synthesised sense sent 3 of 12 to REX, losing about 1.2% on each;
- the degree CV sent all 12 to C0_1.

The sense's threshold sat close to the planar graphs' values, so a few test graphs fell on the wrong side. Neither
sense separated the graphs by the sign of their weights, which is what decides C0_1's gain (it ties REX on unweighted
planar graphs). Telling planar graphs from the rest was enough.

**A noise floor, read from the rows.** On tori and random graphs every arm except FIXED ran REX, so ORACLE scores 0
there by definition. HAND and SENSE ran REX at a charged budget of 0.93–0.99 s, which seeds a different run, and they
scored between −0.01% and +0.10% per family. So run-to-run noise in a 12-graph family mean is about 0.1%, as large as
the material threshold. This is also why HAND's mean is above ORACLE's: ORACLE is defined on the 1 s runs, and HAND's
charged runs happened to score higher.

## Against the expectation

The expectation (low confidence) was BEATS_FIXED_ONLY, and the verdict is NOT_SHOWN.
- **FIXED is REX: wrong.** FIXED is C0_1, so the gain SENSE could add over FIXED is avoiding C0_1's losses (about
  0.13% on average), not adding its gain (about 0.25%). The mean difference was +0.087%. It is significant
  (p_Holm 0.0009), but below the material 0.1%.
- **HAND may come close to SENSE: right, and more than that.** The degree feature was ahead.

## What it means

1. **The vertical slice ran end to end, and the choice works.**
   - A sense was synthesised from the sense language with nothing about the families given.
   - Its computation was charged.
   - It chose per graph on fresh graphs, and it avoided C0_1's losses on three families.
2. **It does not beat the builder's feature, and its gain over always running C0_1 is below the material
   threshold.** The search's winning sense was chosen by 0.005% of training value over a feature the builder knew,
   on 40 training graphs. On test it generalised worse. With 8 graphs per family, the search's selection among 300
   senses mostly found a fragile cut of the same planar/non-planar split.
3. **What would test the idea better (candidates, not queued):**
   - more training graphs per family;
   - a family where the decisive property is not one the builder's degree statistics already carry. Here, for
     example, the sign of the weights would matter if C0_1 lost on unweighted planar graphs.
   - The charge and the 0.1% noise floor mean a choice must be worth well over 0.1% per graph to be seen at 60 test
     graphs.
4. **Queue.** `sense-invention` is not unlocked. B20_R142 (ARA on this workflow) depends on this study and on
   `ara-calibrated`. It can now be designed with this record in hand: the workflow's measured limitation is the sense's
   generalisation, not its expressiveness.

## Looks at the study's data before it finished

None. The study ran in one slice. Its log and summary were read after exit 0.

## Prior art

Algorithm selection per instance from instance features is Rice's framework (1976) and its descendants (SATzilla,
Xu et al. 2008; AutoFolio, Lindauer et al. 2015). Nothing about the method is claimed new. The point is that Genesis
synthesised the feature itself under a charged budget.
