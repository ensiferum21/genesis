# B20_R170 record (Foundry G2): the invented forecast-update rule raised coverage but not into the band, and did not pay (NOT_SHOWN; DEV)

**Run by:** the builder, on DEV. Foundry G2 (`docs/OMEGA_FOUNDRY.md`), from Daniel's Foundry proposal of 28 Oct 2026.
It is a calibration on planted worlds and licenses nothing.

**Preregistration.** Preregistered at `405741e` (29 Oct 2026). The script is `scripts/b20r170_forecast_calibration.py`,
SHA-256 `8aa46929e64a743b5eaba1eadde2dc285a6b445643486405e6eae5b691e2357d`, unchanged. It ran from the clean worktree
`/home/claude/r170-wt` at that commit, which holds the pinned engine modules.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 14:59:45 to 15:25:50 SGT: 26 min, against "under 1 h".
It started 11 s after B20_R163 ended.
- **CPU 0 idle time (disclosed):** B20_R172 started 79 s after this study ended (15:27:09).

**Evidence and checks.**
- `code_identity` `5796e12d8daba4d3ed2c27298f3559f0c15df8a42cade1ea04060d7dd481707f`. It was recomputed at recording
  from a temporary worktree of `405741e`, and it matches.
- The evidence is in `evidence/forecast_calibration_b20r170/`:
  - `meta.json`: the meta-search's record;
  - `rows.jsonl`: 90 evaluation runs, three arms on 30 worlds;
  - `summary.json`;
  - `run.log`, the slice log.
- The record tests are `RecordB20R170` in `tests_genesis/test_forecast_calibration_study.py`. They were drafted before
  the study ran (30 Oct 2026, 07:50 SGT) and appended unchanged. They pass on the evidence, and the whole suite
  passes (10 tests, 652 s). They check:
  - the script's digest;
  - the rows complete and the arms' budgets;
  - validity, the analysis and the verdict, recomputed in this tree;
  - at the preregistration commit: main re-run on the saved meta-search and rows to the same summary, the
    meta-search replayed to the same record, and the first and last worlds' runs re-executed to the same rows.

## Result

**Verdict NOT_SHOWN, by the preregistered rule; valid.**
- Every arm scored exactly 0 in all 6 null worlds.
- Every run spent its budget.
- The promoted rule lies on the grid.
- The pins held.

**The meta-search** (one sealed world of family Ga; 144,000 outer units; 21 branches, 13 distinct rules):
- Its best verified value, 2.721, was reached by outer spend 54,630 and never improved afterwards.
- C_meta was 83,483 units, so D got 3,470 more units per world (29% more).
- The promoted rule: signal hindcast, form both (scale and shift), sides both, conditioning global, update
  adaptive-conformal (ACI), rate 0.01. It differs from the identity in its signal, form and rate.

**Held out** (24 worlds of families Ja and Jb at a budget of 12,000):

| | P (promoted rule, 12,000) | D (identity, 15,470) | D0 (identity, 12,000) |
|---|---|---|---|
| Mean value | 2.133 | 2.313 | 2.150 |
| Mean per-world coverage of the 90% intervals | 0.737 | 0.631 | 0.655 |
| Ja: value, pooled coverage | 2.326, 0.721 | 2.535, 0.588 | 2.329, 0.613 |
| Jb: value, pooled coverage | 1.939, 0.749 | 2.090, 0.668 | 1.972, 0.686 |
| CPU per run | 11.8 s | 12.1 s | 8.6 s |

Every run had at least 633 checked forecasts, so all 24 worlds count for P2.

| Test | Result | Reading |
|---|---|---|
| P1: P − D on value, one-sided | −0.180; P ahead in 2 of 24 worlds; p 1.0 (Holm 1.0) | fails |
| P2: P − D0 on coverage, one-sided | +0.082; P ahead in 22 of 24; p 3 × 10⁻⁷ (Holm 6 × 10⁻⁷) | significant, but P's 95% interval [0.720, 0.757] is below the band [0.80, 0.97]: fails |
| S1: P − D0 on value, two-sided | −0.018; P ahead in 11 of 24; p 0.34 | TIE |
| S2: D − D0 on value, one-sided | +0.162; D ahead in 22 of 24; p 8 × 10⁻⁶ | the extra budget pays |
| S6: D − D0 on coverage, two-sided | −0.024; p 0.027 | more budget, slightly worse coverage |

P's per-world coverage ranged from 0.635 to 0.834; it was inside the band in 2 of the 24 worlds.

## Against the expectation

The expectation (moderate confidence) was CALIBRATION_INVENTED: P2 passes if a non-identity rule is promoted (the
development look: 0.83-0.90 for four hand-picked active rules), P1 NOT_SHOWN, S1 a TIE.
- **P2 wrong.** A non-identity rule was promoted and it raised coverage clearly, but to 0.737, not into the band. The
  development look used simpler worlds (four problems, the default types, no abstraction or branching out); its
  coverages did not carry over to the full engine on these families.
- P1 NOT_SHOWN and S1 a TIE, as expected.

## The meta-search and defect B20R163-META

This study uses F6's meta-search (`meta.MetaDomain`, the outer Frontier policy, the best verified artifact promoted),
so it inherits defect B20R163-META (`docs/BLOCKING_DEFECTS.md`): the rules were compared at unequal inner spends.
A diagnosis made at recording (`evidence/forecast_calibration_b20r170_diagnosis/`) repeated the meta-search exactly,
from a worktree of `405741e`, and kept each branch's inner spend. It reproduces the study's promoted rule, C_meta and
outer spend.
- **Two branches had nearly the whole inner budget:** the promoted rule (17,996 inner units, value 2.721) and the
  identity (17,407 units, 2.405). So the promoted rule was compared with the identity at nearly equal spend on the
  training world, and it was ahead there by 0.32 (one run each).
- **The other 19 branches had about 2,400 units each** (one 4,808), and were never compared at full spend. Eight of
  them ran the identity's behaviour with other engine seeds; their values at 2,400 ranged from 0.40 to 0.89, so one
  run is a noisy measure.
- **The promoted rule's branch was charged 78,000 outer units for its 17,996 inner ones**, as in F6.

So this study's defect is milder than F6's: the winner did beat the identity at about equal spend on the training
world. That one-run lead did not carry over to the held-out families (S1, a tie), which is what a single training
world and a single run each would predict. B20_R175's machinery (several training worlds, equal spend, a guard) is
the repair to use if G2 is repeated.

## What it means

1. **The engine found a forecast-update rule that partly repairs its own calibration.** On held-out families the
   rule raised the 90% intervals' coverage from 0.655 to 0.737, in 22 of 24 worlds. That is the first time a rule
   chosen by Genesis's own search moved the forecaster's calibration. It did not reach the forecaster's own
   acceptance band, so calibration is not repaired.
2. **The rule was not chosen for calibration.** The meta-search promoted by value, and the coverage gain came with
   the rule, not from the selection. A search scored on coverage, or on value and coverage together, is the obvious
   next design; so is the repaired comparison at equal spend (B20_R175's machinery).
3. **It does not pay.** At equal budget the rule ties the identity on value, and the meta-search's compute spent as
   extra budget is worth +0.18. Its hindcast signal also costs CPU (+38% per run), which the study reports but does
   not charge.
4. **Budget alone makes coverage slightly worse** (S6, −0.024): with more compute the forecasts extrapolate further,
   and the raw intervals cover less.

## Looks at the study's data before it finished

- At 15:02 the output directory was listed (it held no file) and an attempt to read a `run.log` there found none.
- At 15:13 the output directory's file names were listed (`meta.json`, `rows.jsonl`). No file was read.
- The summary was read after exit 0.

## Prior art

Adaptive conformal inference (Gibbs and Candès 2021) is the textbook rule among the grammar's points; the promoted
rule is an ACI update. Nothing about the method is claimed new.
