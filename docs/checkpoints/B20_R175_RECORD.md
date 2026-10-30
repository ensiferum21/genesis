# B20_R175 record (F6b): the repaired meta-search found nothing better than the defaults and kept them; F6's procedure would have promoted a harmful configuration (NOT_SHOWN, NOTHING_PROMOTED; DEV)

**Run by:** the builder, on DEV. F6 repeated with its meta-search repaired (defect B20R163-META). It is a calibration on
planted worlds and licenses nothing.

**Preregistration.** Preregistered at `7878cdb` (30 Oct 2026). The script is `scripts/b20r175_meta_repaired.py`,
SHA-256 `b5c957f6669b078b3dc1a4bf19ef4a38fe1b16d31b5b8fa54bb5096fade178ba`, unchanged. It ran from the clean worktree
`/home/claude/r175-wt` at that commit, which holds the pinned engine modules.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 19:50:17 to 20:23:05 SGT: 33 min, against "about
1 h".
- **CPU 0 idle time (disclosed):** 31 s before it (after PT-1; disclosed in PT-1's record), and 4 s after it (PT-2
  started at 20:23:09).

**Evidence and checks.**
- `code_identity` `2ef674b3832f8b1b17c1046dc9113b9312cfdfd15135c7c7fc51c0933bd39888`. It was recomputed at recording
  from a temporary worktree of `7878cdb`, and it matches.
- The evidence is in `evidence/meta_repaired_b20r175/`:
  - `search.json`: the bracket (every configuration, its spend and its value on the training suite), the guard's
    runs, the promotion and C_K;
  - `f6.json`: F6's procedure repeated on the first training world;
  - `rows.jsonl`: 120 evaluation runs, four arms on 30 worlds;
  - `summary.json`;
  - `run.log`, the slice log.
- The record tests are `RecordB20R175` in `tests_genesis/test_meta_repaired_study.py`. They were drafted before the
  study ran (30 Oct 2026) and dry-run on a rehearsal at `7878cdb`, and are appended unchanged. They pass on the evidence, and the whole suite passes (12 tests, 588 s). They check:
  - the script's digest;
  - the bracket's schedule, the guard and the promotion;
  - the rows complete, the arms' budgets, validity, the analysis and the verdict, recomputed in this tree;
  - at the preregistration commit: main re-run to the same summary; the bracket, the guard and F6's procedure
    replayed to the same records; the first and last worlds' runs re-executed to the same rows.

## Result

**Verdict NOT_SHOWN (NOTHING_PROMOTED), by the preregistered rule; valid.**
- Every arm scored exactly 0 in all 6 null worlds.
- Every run spent its budget, the guard's included.
- The bracket ran as scheduled: 27 distinct configurations, stages of 27, 9, 3 and 1, the survivor's four members
  each to 12,000.
- Both promoted configurations lie on the grid, and the pins held.

**The repaired search** (four sealed training worlds of family Ma; one successive-halving bracket; C_search 161,320):
- The survivor: eps 0.4 and lam_con 0, the other four settings at their defaults. Its suite value was 2.163 at full
  budget; the two other finalists stopped at 4,200 per member with 0.709 and 0.922.
- **The guard kept the defaults.** Run once more on each training world with fresh seeds, the survivor scored 1.939
  and the defaults 1.952 (the survivor behind on three of the four worlds). C_guard was 95,954.
- So PK is the defaults. Its runs are identical to D0's, and P1 has no non-zero difference.
- C_K was 257,274 units: D24 got 10,710 more per world (89% more).

**F6's procedure** (on the first training world, unchanged code) promoted **the same configuration as in F6**: eps
0.1, lam_lp 3, lam_con 0, k_imagine 32, patience 2, stall 80. That is the first configuration its outer engine opens
from seed 0, whatever the world, as the diagnosis of B20R163-META predicts.

**Held out** (24 worlds of families Ha and Hb at a budget of 12,000):

| | PK (= defaults) | P1 (F6's procedure) | D0 (defaults) | D24 (defaults, 22,710) |
|---|---|---|---|---|
| Mean value | 2.573 | 2.117 | 2.573 | 2.868 |
| Ha | 2.952 | 2.477 | 2.952 | 3.262 |
| Hb | 2.194 | 1.756 | 2.194 | 2.474 |

| Test | Mean difference | p | Reading |
|---|---|---|---|
| P1: PK − D0, one-sided | 0 (no non-zero pair) | 1.0 | NOT_SHOWN (NOTHING_PROMOTED) |
| S1: PK − D24, one-sided | −0.295 | 1.0 | DOES_NOT_PAY |
| S2: PK − P1, two-sided | +0.456 | 0.002 | REPAIR_BETTER |
| S3: P1 − D0, two-sided | −0.456 (P1 behind on 18 of 24) | 0.002 | CONFIG_WORSE |
| S4: D24 − D0, one-sided | +0.295 (19 of 24) | 4 × 10⁻⁵ | the extra budget pays |
| S7: break-even | none (no gain) | | |

## Against the expectation

The expectation (low confidence) said: P1 NOT_SHOWN more likely than CONFIG_TRANSFERS (0.65 against 0.35), with the
guard keeping the defaults about one time in three. **Right**, by way of the guard. S1, not PAYS: right. S2, a TIE or
a small REPAIR_BETTER: the repair was better by much more than expected, because F6's configuration was harmful here.
**S3, a TIE as in F6: wrong.** F6's configuration lost to the defaults by 0.456.

## What it means

1. **With the comparison made fair, the engine found no configuration of its own better than its defaults.** The best
   of 27 configurations, chosen at equal spend on four training worlds, did not beat the defaults when both were
   run again on those worlds, and the guard kept the defaults. That is the guard doing its job; nothing was promoted
   that would have done harm.
2. **F6's procedure is worse than useless.** It promotes whatever its outer engine opens first, and here that
   configuration cost 0.456 of value on held-out worlds (in F6 it happened to tie). B20R163-META was a real defect,
   and the repair removes a real risk.
3. **The defaults are hard to beat on these planted worlds.** They were shaped by F1's development look; a search over
   the six settings at this scale finds nothing better. Self-configuration may pay where the defaults are poorly
   matched to the domain, which these worlds do not test.
4. **For G3 (B20_R171):** the policy stage now has a measured, negative answer at equal spend; a joint search must
   add something the policy alone does not.

## Looks at the study's data before it finished

None. The study ran in one slice; its summary was read after exit 0.

**A disclosure about the development look.** The bracket's 27 configurations are drawn by the outer engine from seed
0, independently of the worlds, so the development look (seeds 990001-990004) evaluated the same 27 configurations,
and its survivor (eps 0.4, lam_con 0) is the study's survivor. The look's values on development worlds were not
compared with anything held out, and the guard's decision here was made on the study's own training worlds.

## Prior art

Successive halving (Jamieson and Talwalkar 2016; Hyperband, Li et al. 2017) and algorithm configuration with a
held-out check (SMAC, irace). Nothing about the method is claimed new.
