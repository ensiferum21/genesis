# B20_R103 evidence: the feedback contract and the zero-signal battery: CONTRACT_LEAKS (by the rule), TOO_STRICT, CALIBRATED

Builder-run on DEV (Daniel's research alert of 22 Oct 2026, `docs/RESEARCH_ALERTS.md`). It licenses nothing.
- **Script:** `scripts/b20r103_zero_signal.py`, preregistered at `cc7f4bb` (SHA-256 `335669c5…`).
- **The contract:** `src/genesis/autonomy/feedback.py` (SHA-256 `312e9c5e…`).
- **Run:** alone on CPU 0, 213 s, on 23 Oct 2026 (09:25–09:29 SGT). `code_identity` `2e84acdb…`, the committed tree
  (`ff08000`).

| File | What |
|---|---|
| `searches.jsonl` | 720 searches: signal (none, planted) x quirk sd (0, 1, 2 x sigma_e) x protocol (open, contract) x 60 replicates; each with its claimed gain, final number, final optimism, true gain and, for the contract, the judge's tau, releases and stop |
| `summary.json` | sigma_e, the table per condition, the L2 rates, the labels |

sigma_e (one evaluation's noise in Genesis's recorded program searches) = 0.149 edges.

## Result

**L1 with no signal** (every program equally good; 60 searches per row; values in edges, and in sigma_e):

| Quirk sd | Open: claimed gain | Open: final optimism | Contract: claimed gain | Contract: final optimism (held-out) | Contract: releases | Contract: evaluations used |
|---|---|---|---|---|---|---|
| 0 | -0.18 (-1.2) | +0.08 (+0.5) | +0.01 (+0.07) | -0.01 | 1 in 60 | 513 of 1,500 |
| 1 sigma_e | +0.14 (+0.9) | +0.50 (+3.4) | 0 | -0.02 | 0 | 492 |
| 2 sigma_e | +0.39 (+2.6) | +0.99 (+6.6) | 0 | +0.03 | 0 | 486 |

- **Without the contract**, the number a search reports overstates the truth more and more as the evaluation data's
  quirks grow: by about 1 edge (6.6 sigma_e) at the largest quirk. That is the alert's effect, inside Genesis's own
  program search.
- **With the contract**, every no-signal search stopped early (about a third of the budget). It released noise once
  in 180 searches, and its held-out final numbers are unbiased (within 0.03 edges).

**L1 with a planted signal** (a real effect of up to 8 sigma_e, built step by step):

| Quirk sd | Open: true gain | Contract: true gain | Ratio | Open: final optimism | Contract: final optimism |
|---|---|---|---|---|---|
| 0 | 0.49 | 0.34 | 69% | +0.07 | -0.02 |
| 1 sigma_e | 0.42 | 0.21 | 51% | +0.50 | +0.00 |
| 2 sigma_e | 0.55 | 0.07 | 13% | +0.99 | +0.01 |

The contract's fixed threshold averages 5.1, 7.2 and 11.4 sigma_e at the three quirk levels; at the largest it
exceeds the whole planted effect (8 sigma_e), so it keeps 13% of the open protocol's true gain: TOO_STRICT, as expected. Its reports
stay honest at every quirk; the open protocol's do not.

**L2, the research loop's analyses with identical arms:** false "better" rate 0 of 400 quality-at-equal-time studies
and 0 of 400 time-to-target comparisons: CALIBRATED.

## The headline label, and why it reads CONTRACT_LEAKS

The preregistered rule calls the contract HOLDS only if, at every quirk, its mean claimed gain is at most a quarter of
the open protocol's *and* below sigma_e. At quirk 0 the open protocol's mean claimed gain is negative (-0.18 edges).
Its reported fresh re-evaluations fall below the initial incumbent's first score, which was the best of 16 noisy
draws. A quarter of a negative number is negative. The contract's one false release among 60 searches gives it a
mean claimed gain of +0.01 (0.07 sigma_e), so the rule fails at quirk 0 and the headline is **CONTRACT_LEAKS**.

The verdict stands as preregistered. What the leak is, measured:
- **False releases:** one in 180 no-signal searches (0.6%; the design allows about 5% per stalled search).
- **Effect on the final numbers:** none; they are held out and unbiased.

The rule was written for a positive open-protocol gain and is mis-specified when that is negative. A later study
should compare claimed gains with the truth (zero), not with a fraction of the open protocol's.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| Open: a claimed gain of 2–6 sigma_e with no signal, growing with the quirks | It grows with the quirks: -1.2, +0.9 and +2.6 sigma_e, below the forecast. The final optimism (+0.5, +3.4, +6.6 sigma_e) shows the forecast effect |
| Contract: claimed gain near zero, final optimism near zero, early stops in most no-signal runs | Yes; all 180 stopped early |
| Power kept at quirk 0; CONTRACT_TOO_STRICT expected | Power kept at quirk 0 (69%) and 1 (51%), lost at 2 (13%): TOO_STRICT. The headline is CONTRACT_LEAKS by the ratio rule above, not CONTRACT_TOO_STRICT |
| L2 CALIBRATED | Yes, 0 false verdicts in 800 |

## What it means

- **What Genesis now has.** The contract gives a self-improving search a way to tell progress from noise: with it,
  a search on a problem without signal stops and reports nothing. Without it, Genesis's own search reports up to a
  whole edge of progress that is not there.
- **What the contract costs.** Real effects smaller than one confirmation's noise are missed. The remedy the battery
  points to is larger confirmation data, which shrinks the quirks.
- **The research loop's analyses are already calibrated.** Their sequential tests and quantile labels never called
  identical arms different.
