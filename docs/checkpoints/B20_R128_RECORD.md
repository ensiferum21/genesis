# B20_R128 record: improving the process of invention: NOT_SHOWN, and no inner search released anything (DEV)

- **Run by:** the builder, on DEV; licenses nothing. Preregistered at `70a590d` and amended before any run at
  `bc7e424` (`scripts/b20r128_improve_the_improver.py`, SHA-256
  `59df2af9ae09b2038b8b7d95476d4b6dea43adc6997439dc24f8c5ece27ab0ee`). Run as preregistered (directive item 1),
  unchanged.
- **Code since `bc7e424`.** None of the code it uses changed, with one exception: `gset.best_known` gained an
  `as_of` argument (`8d7e402`). The study only calls `gset.tasks()`, to exclude Gset's identities, so the change has
  no effect here.
- **The run.** Alone on CPU 0, from a clean worktree of `295b634`, 27 Oct 2026, 06:07–09:19 SGT, in two slices:
  6,847 s (paused as designed, at the first search boundary after 6,600 s) and 4,635 s. Total 11,482 s (3.2 h)
  against 3.3 h estimated. `code_identity` is in `summary.json`.
- **Evidence.** `evidence/improve_the_improver_b20r128/`: 30 inner searches. Recomputed independently: the
  meta-search was re-derived from the preregistered seed, and every value matches.

## Result

**Verdict NOT_SHOWN.** On 8 fresh graph sets, the process the meta-search chose (EVOLVED) and Genesis's original
inventor process (ORIGINAL) produce engines of the same quality.

| | ORIGINAL | EVOLVED |
|---|---|---|
| process | steady search, pop 16, 8 children, tournament 3, crossover 0.25, 16 extra calibration engines, equal mutation weights, no adaptation | steady search, pop 12, 16 children, tournament 2, crossover 0.5, 8 extra calibration engines, weights favouring replace and duplicate (4), adaptation on |
| yield on the 8 fresh sets (mean of D / REX at 0.5 s) | 1.00039 | 1.00062 |
| engines beating REX on held-out graphs | 7 of 8 | 6 of 8 |

The test: EVOLVED − ORIGINAL by set = −0.00029, +0.00121, +0.00139, +0.00127, −0.00083, +0.00034, −0.00139,
+0.00017. That is 5–3, with a mean of +0.00023. The two-sided Wilcoxon over the 8 sets (8 non-zero) gives p 0.547:
**NO_DIFFERENCE**.

**The meta-search** (on its own graph set):
- Generation 0 was ORIGINAL plus 5 random processes, best yield 1.00107. ORIGINAL itself scored 1.00036.
- Generation 1 reached 1.00045 at best; generation 2 reached 1.00152.
- EVOLVED is generation 2's process 10. The 14 yields span 0.99278–1.00152 (standard deviation 0.0022).

**The main finding: no inner search released anything.** All 30 searches went the same way:
- Each ran 120 split evaluations, made 1–4 submissions to its judge (the protected contract version 2), and had
  none released.
- The judge's thresholds were 0.76–2.84% (median 1.63%).
- Each search's answer is therefore its judge's first incumbent: the engine of its initial random population with
  the best score on the training split A. That is the protected search's rule.

So both the meta-search and the final test compared how processes draw and rank their first population. They did not
compare what their judges let through. **No improvement of the process of invention could have been measured.**
Selection among 14 processes on one graph set picked whichever drew the luckiest first population, and that advantage
did not carry to fresh sets. This is B20_R132's finding seen from one level up. At these gains (final yields 0.9991–1.0022
of REX) the protected judge, whose threshold is around 1.6%, releases nothing, so a level-2 search over processes
has no level-1 signal to select on.

**Validity.**
- Every engine passes `mcx2.check_config` (re-checked on all 30).
- Every run's cut is computed from the returned partition (`mcx2.solve`).
- The REX references were computed once per graph and kept (`references.json`), so the resumed slice used the same
  ones.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| the meta-search finds a process with a higher yield on its own set (selection on noise would do that) | yes: 1.00152 against ORIGINAL's 1.00036 |
| most likely one that spends less of its budget calibrating the judge | yes: 8 extra calibration engines instead of 16, and a population of 12 instead of 16 |
| NO_DIFFERENCE on fresh sets | yes (p 0.55) |
| the engines of both processes beat REX on held-out graphs in most repetitions | yes: 7 and 6 of 8 |
| by about 0.1–0.5% | **smaller**: mean +0.04% and +0.06% |
| NOT_SHOWN | yes |

The expectation did not foresee that no inner search would release anything. B20_R127's nine searches had already
released nothing, but this study was designed before that was analysed.

## Limits

- DEV, builder-run, one machine. One inner search per process and graph set, 8 repetitions, 0.5 s per run.
- The yields measure first incumbents, not invention (above). A test of process improvement needs a level 1 that
  releases. That could come from a finer judge (B20_R132's version 3 was not validated), a regime with more
  headroom, or a richer language: the questions B20_R132 leaves to Daniel.
- No independent replication.

## Tests

`tests_genesis/test_improve_the_improver.py::RecordB20R128` (5), on the evidence:
- the preregistered script unchanged;
- one row per search, every engine valid, 120 evaluations each;
- the meta-search re-derived from the preregistered seed with `selfimprove`'s operators;
- the final rows, test, verdict and measures recomputed by `analyse`;
- no release in any search.

The 5 design tests are unchanged.
