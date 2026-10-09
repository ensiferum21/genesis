# Genesis Batch 34 — Prospective statistics correctness repair (DEV)
Date: 2026-10-09

## Changes
- `prospective_statistics._pvalue`: replace `math.fsum` over large binomial coefficients with integer numerator and power-of-two denominator; avoid float overflow at large n. The returned binary64 value can underflow to 0 for extremely small positive probabilities and is not an exact rational representation.
- `prospective_statistics.analyze_frozen_trial`: select terminal attempt by numeric attempt ID, independent of input event order. The frozen accounting gate continues to reject missing attempts and post-success retries.
- Six regression tests in `test_batch34_regressions.py`.

## Validation
`python -m unittest discover -q`: 180 tests, OK.

## Evidence and limitations
All tests are local development checks. No Lean executable is available; no mathematical proof was checked; no external sealed dataset or independent checker was provided. Scientific promotion remains BLOCKED. Large-sample p-values are float approximations and may underflow to zero; exact significance decisions should use integer comparisons in a future release.
