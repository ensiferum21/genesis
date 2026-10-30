# B20_R172 record (Foundry G4): the engine found a state feature its index lacked, and it generalised, but did not pay (NOT_SHOWN; DEV)

**Run by:** the builder, on DEV. Foundry G4 (`docs/OMEGA_FOUNDRY.md`), from Daniel's Foundry proposal of 28 Oct 2026.
It is a calibration on planted worlds and licenses nothing.

**Preregistration.** Preregistered at `73f8ad4` (29 Oct 2026). The script is `scripts/b20r172_state_features.py`,
SHA-256 `46e571f4f763ace626a8962bd6e21c103b91f99c2e095e299ee3571677739b33`, unchanged. It ran from the clean
worktree `/home/claude/r172-wt` at that commit, which holds the pinned engine modules.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 15:27:09 to 15:45:15 SGT: 18 min, against "under
1 h".
- **CPU 0 idle time (disclosed):** 79 s before it (B20_R170 ended at 15:25:50), and 3 min 6 s after it (B20_R174
  started at 15:48:21). The second gap: the builder was waiting in the foreground on a diagnosis running on CPU 1
  when this study ended.

**Evidence and checks.**
- `code_identity` `508a6f96ab557d887c2f577f676a2a4b113959e843a22d71dc69288ec734d08e`. It was recomputed at recording
  from a temporary worktree of `73f8ad4`, and it matches.
- The evidence is in `evidence/state_features_b20r172/`:
  - `search.json`: the counterexample search's record;
  - `rows.jsonl`: 90 evaluation runs, three arms on 30 worlds;
  - `summary.json`;
  - `run.log`, the slice log.
- The record tests are `RecordB20R172` in `tests_genesis/test_state_features_study.py`. They were drafted before the
  study ran (30 Oct 2026, 07:55 SGT) and appended unchanged. They pass on the evidence, and the whole suite passes (9 tests, 117 s). They check:
  - the script's digest;
  - the rows complete and the arms' budgets;
  - validity, the analysis and the verdict, recomputed in this tree;
  - at the preregistration commit: main re-run on the saved search and rows to the same summary, the feature
    search replayed to the same record, and the first and last worlds' runs re-executed to the same rows (S7
    included).

## Result

**Verdict NOT_SHOWN, by the preregistered rule; valid.**
- Every arm scored exactly 0 in all 6 null worlds.
- Every run spent its budget.
- The proposed feature is in the feature language.
- The pins held.

**The search** (two sealed training worlds of family Ka, each run once at 12,000 with decision logging; 120 decisions
each replayed for 10 quanta per candidate):
- The index agreed with the replays on 0.698 of the weighted pairs (0.732 and 0.657 on the two worlds).
- Of 697 expressions, the search proposed **slope4 / hi**: the least-squares slope of the branch's last four points,
  over the upper end of its 95% forecast. Its held-out agreement was 0.825 against the index's 0.695 (z 2.75); its weight in the
  index is 23.0. The two folds had found slope4 / level and curv × noise.
- C_search was 71,988 units (the two training runs and 48,000 of replay), so D got 2,990 more units per world (25%
  more).

**Held out** (24 worlds of families La and Lb at a budget of 12,000):

| | P (feature, 12,000) | D (defaults, 14,990) | D0 (defaults, 12,000) |
|---|---|---|---|
| Mean value | 1.957 | 1.978 | 1.908 |
| La | 2.066 | 2.024 | 1.945 |
| Lb | 1.847 | 1.933 | 1.871 |
| CPU per run | 10.9 s | 11.7 s | 10.8 s |

| Test | Mean difference | Worlds where the first arm is ahead | p | Reading |
|---|---|---|---|---|
| P1: P − D, one-sided | −0.022 | 8 of 24 | 0.77 | NOT_SHOWN |
| S1: P − D0, two-sided | +0.048 | 13 of 24 | 0.51 | TIE |
| S2: D − D0, one-sided | +0.070 | 16 of 24 | 0.048 | the extra budget pays a little |
| S7: on D0's decisions in the held-out worlds, the index with the feature against the index alone, one-sided | +0.066 (0.768 against 0.702) | | 0.001 (24 worlds) | FEATURE_GENERALISES |

## Against the expectation

The expectation (informed by the development look) said: a feature is proposed; P1 NOT_SHOWN; S1 a TIE; S7
FEATURE_GENERALISES (low confidence). All four held. The index agreed with the replays less often here (0.70) than in
the development look (0.82-0.92), so there was more room than expected, and the feature took some of it.

## What it means

1. **Genesis found a distinction its own controller was missing, and the distinction is real.** Replaying its own
   decisions, it found that the index should weigh a branch's recent slope against its forecast ceiling; on 24 new
   worlds' decisions that feature agreed with what replays showed better than the index alone (0.768 against 0.702).
   This is the first state feature the engine has proposed for itself that held up out of sample.
2. **Knowing better which branch to advance did not buy measurable value.** At equal budget the feature's arm was
   ahead by +0.048, not significantly, with the gain on family La (+0.12) and a small loss on Lb (−0.02); given the
   search's compute as extra budget, the defaults were slightly ahead. One reading, not tested here: better choices
   between the two leading branches are worth little when the index already ranks most pairs correctly and the
   pairs it gets wrong are close in value.
3. **Next:** the distinction is now measured and the value is not. A study with more worlds (the S1 effect, +0.048
   with this variance, would need several times as many to resolve), or a feature search scored on value rather than
   pairwise agreement, would say whether it can pay. Nothing is adopted.

## Looks at the study's data before it finished

None. The summary was read after exit 0.

## Prior art

Counterexample-guided abstraction refinement (Clarke et al. 2000) and learned value features for search control are
the comparators. Nothing about the method is claimed new.
