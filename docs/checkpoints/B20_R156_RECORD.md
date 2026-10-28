# B20_R156 record (F3): the Frontier's allocation beats successive halving, UCB1 and uniform on sealed planted worlds (FRONTIER_BETTER; DEV, a calibration)

**Run by:** the builder, on DEV. It is a calibration of the machinery on planted worlds: **nothing here is evidence
about real problems.** It licenses nothing, and the protected judge was not asked.

**Preregistration.** Preregistered at `5c3e236` and amended once before it ran, at `4a7e193` (cached forecasts on a
geometric horizon grid), as disclosed in the script. The script that ran is `scripts/b20r156_frontier_worlds.py`,
SHA-256 `9ae034dbf8bde4cd9d2eba75807c16ef869917568cf4ffd5a8d2b2f20566353a`. It ran from the clean worktree
`/home/claude/f3-wt` at `4a7e193`.

**This run.** Alone on CPU 0, in one slice, from 28 Oct 2026, 00:58 UTC, to 01:07 UTC, with exit 0. It took 9 min,
against "under 1 h".

**Evidence and checks.** `code_identity` `f864a4c1…e71e`. The evidence is in `evidence/frontier_worlds_b20r156/`:
180 rows (30 worlds × 6 arms) and `summary.json`. The record tests are `RecordB20R156` in
`tests_genesis/test_frontier_worlds_study.py`. They were written before the study ran
(`docs/handoff/RECORD_TEST_DRAFTS.md`, 28 Oct 2026, 02:55 SGT) and pass unchanged:
- the script's digest;
- the worlds regenerate from the sealed seed;
- validity is recomputed from the rows;
- the analysis and the verdict are recomputed;
- one world, re-run at the branch head, gives the same row. The engine has moved on since `4a7e193`, with the
  derive action, procedures, the meta level and multi-domain; at its defaults it is unchanged here.

**Validity held:**
- every arm scored exactly 0 in all 6 null worlds;
- every run spent its budget;
- the module pins matched.

## Result

**Verdict FRONTIER_BETTER, which was one of the two outcomes expected before running** ("FRONTIER_BETTER or
PARTIAL (halving, uniform)").

| P1: F (the Frontier's allocation alone) against | Mean gain, of the reference | Worlds where F is higher | p_Holm |
|---|---|---|---|
| successive halving | +0.193 | 23 of 24 | 1.7 × 10⁻⁶: BEATEN |
| UCB1 | +0.108 | 18 of 24 | 6.2 × 10⁻⁴: BEATEN |
| uniform | +0.317 | 24 of 24 | 1.8 × 10⁻⁷: BEATEN |

Mean value by arm, as a fraction of the world's reference (each initial problem's best planted curve at an equal
share of the budget):

| F+ | F | UCB1 | halving | uniform | random |
|---|---|---|---|---|---|
| **2.314** | 0.810 | 0.701 | 0.617 | 0.492 | 0.445 |

The family means agree; F is ahead of every comparator in each of the three held-out families.

**Secondary results:**
- **S1, abstraction and branching out (F+ against F): +1.505, higher in 24 of 24 worlds, p 1.2 × 10⁻⁷.** F+ abstracts
  a median of 6 templates per world and reveals a median of 2.5 successor problems. It ends at 2.3 times the
  reference, which counts only the initial problems. Most of its value comes from problems it opened itself.
- **S2, the calibration of F's forecasts: coverage 0.661 (Wilson 95% [0.654, 0.667]) of 19,720 forecasts, against a
  nominal 0.90.** The intervals are too narrow. The expectation, "near or above 0.9", was wrong. The allocation wins
  anyway, so the forecasts rank the branches better than they size them.
- **S3, recombination veins:** F opened 53 of the 57 planted pairs and UCB1 47.
- **S4:** F against random, +0.364, p 6 × 10⁻⁸.

## What it means

1. **On worlds nothing had seen, the engine's allocation beats the standard allocators.** This confirms the
   development look of B20_R160 (0.774 against UCB1 0.652 there; 0.810 against 0.701 here). UCB1 is the closest, as
   expected, and still loses in 18 of 24 worlds.
2. **The divergent part is where most of the value is in these worlds.** Abstraction and branching out nearly triple
   what allocation alone achieves. It is a planted world built to reward that, so this calibrates the machinery
   rather than measuring anything real. F4 (B20_R157, on the sealed Laplacian bounds, running now) and F5 are the
   first tests on real mathematics.
3. **The forecasts' intervals are overconfident**, about 66% coverage at a nominal 90%. That is a repair candidate
   (a calibrated widening, for example conformal over the observed residuals). It would not change what was tested
   here. It is not preregistered, and the engine is not changed now, because F4–F6 are pinned to it.

## Looks at the study's data before it finished

None. The study finished within one slice. The log and the summary were read after exit 0.

## Prior art

None is claimed. Successive halving (Karnin et al. 2013; Jamieson and Talwalkar 2016) and UCB1 (Auer et al. 2002)
are the comparators. Learning-curve extrapolation for allocation follows Domhan et al. (2015) and Klein et al.
(2017).
