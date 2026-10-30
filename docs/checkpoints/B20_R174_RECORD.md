# B20_R174 record: Genesis's search did no better than random sampling of the same language (NOT_SHOWN, RANDOM_MATCHES_SEARCH; DEV)

**Run by:** the builder, on DEV. The control B20_R173's release lacked (`docs/checkpoints/B20_R173_RECORD.md`,
"Against random engines"). It licenses nothing.

**Preregistration.** Preregistered at `bc57958` (30 Oct 2026). The script is `scripts/b20r174_search_vs_random.py`,
SHA-256 `842a9d730182a23b5c94790c81b858f1b3e70704b0b9a09d8f2e4122e5302924`, unchanged. It ran from the clean
worktree `/home/claude/r174-wt` at that commit.

**This run.** Alone on CPU 0, in two slices, on 30 Oct 2026: 15:48:21 to 17:38:23 SGT (paused, exit 3), then 17:38:26
to 19:24:28 (exit 0). 3 h 36 min in all, against "about 3.5 h".
- **CPU 0 idle time (disclosed):** 3 min 6 s before it (after B20_R172; disclosed in that record), 3 s between the
  slices, and 5 s after it (PT-1 started at 19:24:33).

**Evidence and checks.**
- `code_identity` `5d6b046bb6100c270527cb811d957009f003fdd199b4a4c674f00fbcab9df0f0`. It was recomputed at recording
  from a temporary worktree of `bc57958`, and it matches.
- The evidence is in `evidence/search_vs_random_b20r174/`:
  - `runs.jsonl`: all 12,432 engine runs, each with its key, cut and CPU;
  - `summary.json`;
  - `run.log`, the slice log.
- The record tests are `RecordB20R174` in `tests_genesis/test_search_vs_random_study.py`. They were drafted before the
  study ran (30 Oct 2026, 08:20 SGT) and appended unchanged. They pass on the evidence, and the whole suite passes (9 tests, 117 s). They check:
  - the script's digest;
  - the CPU median and the verdict;
  - the whole study replayed from the saved runs, with every engine run forbidden: the graphs regenerated, the
    random arms' samples, finalists and winners re-derived, the truth, validity, P1 and the verdict, to the same
    summary.

## Result

**Verdict NOT_SHOWN, read as RANDOM_MATCHES_SEARCH, by the preregistered rule; valid.**
- The median CPU of the 1 s runs was 1.0008 s.
- The graph sets are disjoint from each other and from everything excluded.
- The three search winners hash to their recorded keys, and B20_R151's summary has its recorded digest.
- Each random arm made exactly 496 evaluations of 8 graphs.
- mcx3's pin and the protected judge's source are unchanged.

**The random arms** (REX, then 480 distinct random L0 engines each, then the search's final rule):
- 161, 244 and 279 of each arm's 480 random engines scored above REX on their training split.
- Their winners scored 1.0057, 1.0054 and 1.0051 on the final re-evaluations (REX about 1.00).

**On the 24 fresh ±1-weighted planar graphs (T)**, each engine's mean gain over REX at 1 s:

| Search winners (B20_R151) | T-gain | Random winners (here) | T-gain |
|---|---|---|---|
| C0_0 | +1.343% | RANDOM_0 | +1.118% |
| C0_1 (released by B20_R173) | +0.878% | RANDOM_1 | +1.020% |
| C0_2 | +1.055% | RANDOM_2 | +1.152% |
| mean | +1.092% | mean | +1.097% |

Every one of the six beats REX on T (each p 6 × 10⁻⁸ or 1 × 10⁻⁷, one-sided).

| Test | Result | Reading |
|---|---|---|
| P1: per graph, the search winners' mean T-gain minus the random winners' | −0.005 percentage points; the search ahead on 14 of 23 graphs (1 tie); Wilcoxon p 0.40; permutation p 0.55 | NOT_SHOWN; \|mean\| < 0.1%: RANDOM_MATCHES_SEARCH |
| S1: C0_1 against the best random winner (RANDOM_2) | −0.27 points; C0_1 ahead on 5 of 24; p 0.0004 (two-sided) | the released engine is worse |
| S4: P1 on the 12 unweighted planar graphs (T2) | +0.01 points; p 0.28 | everything near REX (gains 0.02-0.12%) |

## Against the expectation

The expectation (moderate confidence) said NOT_SHOWN, read RANDOM_MATCHES_SEARCH: right. S4, everything near REX on
planar2: right. S1, C0_1 within ±0.2% of the best random winner: **wrong**. The best random winner beat it by 0.27%,
and C0_1 was the weakest of the six winners on these graphs.

## What it means

1. **On this family, Genesis's search found nothing that random sampling of the same language does not.** At
   matched evaluations and with the same final selection, three random arms found engines as good as the three
   search winners: +1.10% against +1.09% over REX. The ~1% gain over REX belongs to the builder's L0 language, not
   to the search.
2. **B20_R173's release says less than it seemed.** The judge released C0_1 by its rules, and C0_1 does beat REX
   (+0.88% here, a fourth fresh set). But C0_1 was the weakest of the six winners on fresh graphs, and the best
   random winner beat it significantly. A cross-reference is added to B20_R173's record.
3. **The search is not useless; it is unmeasured where it might matter.** Here the language is dense with good
   engines (a third to over half of random engines beat REX on their training split), so selection among 480 is
   enough. A search earns its keep only where good engines are rare; that would need a family or a language where
   random sampling fails, and no study has found one yet.

## Looks at the study's data before it finished

None. The slice log was read at 16:12 and 17:31 (empty). The summary was read after exit 0.

## Prior art

Random search as the baseline for configuration and architecture search (Bergstra and Bengio 2012; Li and Talwalkar
2019, for neural architecture search) is the standard control; random baselines often match more elaborate search.
Nothing about the method is claimed new.
