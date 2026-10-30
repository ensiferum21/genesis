# B20_R163 record (F6): the configuration the Frontier found for itself did not beat its defaults (NOT_SHOWN; DEV)

**Run by:** the builder, on DEV. F6 of Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md` §4.8). It is
a calibration on planted worlds and licenses nothing.

**Preregistration.** Preregistered at `77d725d` (28 Oct 2026). The script is `scripts/b20r163_frontier_meta.py`,
SHA-256 `e71bfb69365bb5fa4a1129e59c13637ce048ab0cc15dbdaa4ddd8878a620777f`, unchanged. It ran from the clean worktree
`/home/claude/f6-wt` at that commit, which holds the pinned engine modules.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 14:38:25 to 14:59:34 SGT: 21 min, against "under 1 h".
It started 7 s after the checkpoint B20_R169 was made, and B20_R170 started 11 s after it ended.

**Evidence and checks.**
- `code_identity` `d3a9866123e24d987459e66e304bda62643ac14880bb2b233dd72af1aa84b228`. It was recomputed at recording
  from a temporary worktree of `77d725d`, and it matches.
- The evidence is in `evidence/frontier_meta_b20r163/`:
  - `meta.json`: the meta-search's record;
  - `rows.jsonl`: 90 evaluation runs, three arms on 30 worlds;
  - `summary.json`;
  - `run.log`.
- The record tests are `RecordB20R163` in `tests_genesis/test_frontier_meta_study.py`. They were drafted before the
  study ran (28 Oct 2026, 02:55 SGT) and appended unchanged. They pass on the evidence, and the whole suite passes
  (8 tests). They check:
  - the script's digest;
  - the meta-search's record and the matched budgets;
  - validity and the analysis, recomputed from the rows;
  - one evaluation, re-run to the same row.
- The re-run uses the branch's engine modules, in which `frontier/allocate.py` has since gained G2's and G4's
  options, off by default. It gives the same row, as the identity tests claimed.

## Result

**Verdict NOT_SHOWN, by the preregistered rule; valid.**
- Every arm scored exactly 0 in all 6 null worlds.
- Every run spent its budget.
- The promoted configuration lies on the grid.
- The pins held.

**The meta-search** (one sealed world of family Ma; 144,000 outer units; 21 configurations opened):
- Its best verified value, 2.119, was reached by outer spend 18,628 and never improved afterwards.
- C_meta, the inner compute counted once per run, was 76,886 units, so D got 3,200 more units per world (27% more,
  against the expectation's "about 50%").
- The promoted configuration changed all six settings from the defaults:
  - eps 0.25 → 0.1;
  - lam_lp 1 → 3;
  - lam_con 0.02 → 0;
  - k_imagine 8 → 32;
  - patience 4 → 2 quanta;
  - stall 40 → 80.

**Held out** (24 worlds of families Ha and Hb at a budget of 12,000; values relative to each world's reference):

| | P (promoted, 12,000) | D (defaults, 15,200) | D0 (defaults, 12,000) |
|---|---|---|---|
| Mean value | 2.237 | 2.457 | 2.310 |
| Ha | 2.406 | 2.606 | 2.471 |
| Hb | 2.067 | 2.308 | 2.149 |

| Test | Mean difference | Worlds where the first arm is ahead | p | Reading |
|---|---|---|---|---|
| P1: P − D, one-sided | −0.221 | 6 of 24 | 0.99 | NOT_SHOWN |
| S1: P − D0, two-sided | −0.073 | 11 of 24 | 0.56 | TIE |
| S2: D − D0, one-sided | +0.148 | 21 of 24 | 8 × 10⁻⁶ | the extra budget pays |

## Against the expectation

The expectation (moderate confidence) said: P1 NOT_SHOWN; S1 a TIE or a small CONFIG_BETTER; S2 clearly positive.
All three held, with S1 a tie leaning negative.

## What it means

1. **The Frontier's self-configuration did not pay for itself here.**
   - On held-out families, the configuration it found on one meta-training world was no better than its defaults at
     equal budget.
   - Spending the meta-search's compute as extra budget on the defaults was clearly better.
2. **The meta-search over-fitted its one world.** It stopped improving after a fraction of its budget, and its winner
   changed every setting at once, toward much less exploration (eps 0.1, lam_con 0) and more imagination
   (k_imagine 32). Those choices fit one world of family Ma and did not transfer.
3. **For G3 (B20_R171, joint against separate discovery):** the policy-only point of that design is now measured, and
   it is negative. A joint search must beat both this and the extra-budget baseline. Meta-searching over more than
   one training world would be the first design change worth testing.

## Looks at the study's data before it finished

The output directory's file names were listed once, at 14:46. No file was read. The summary and log were read after
exit 0.

## Prior art

Algorithm configuration with held-out evaluation and its cost counted (SMAC, irace) is the standard comparator. Nothing
about the method is claimed new.
