# B20_R12: E1 host-family calibration under the rule `e1-hard-v1` (DEV)

- **Script:** `scripts/b20r12_e1_calibration.py`. It was committed as `02de690` before it ran; the rule and grid are in its docstring.
- **Run:** 13 Oct 2026. 1,546 s on the build host, with nothing else running.
- **Record:** `calibration_triangle_free_host_v1_e1.json`, SHA-256 `c7893f5b…92c6`. It passes `calibration.record_problems` and is adopted under `configs/dev_calibration.json` → `studies.e1.triangle_free_host_v1`.

## Why a separate rule

The user decided (13 Oct 2026) that E1's host family is chosen by a second, versioned rule, `calibration.SELECTION_RULE_E1_HARD`. The rule:
- takes the fixed DSL baselines' ceiling rate in [0, 0.25], target 0;
- keeps the same certification (≥ 0.9), headroom (≥ 0.02) and evaluator-speed (median ≤ 15 s) limits;
- keeps the same ordering and the same cap of 4 settings;
- never reads a candidate.

The domain rule and the domain adoption (n22 p0.35) are unchanged. A reviewer must still sign off the rule.

## Grid

The union of every triangle-free setting measured before: the round-2 domain grid (6 settings) plus the B20_RX4 cells (erdos n 26–38, p .25/.30/.35), 17 settings in all. Each setting had 8 fresh DEV hosts, seed 20261901, and the unchanged `calibration.calibrate`.

## Result: SELECTED (4 settings, in rule order)

| Order | Setting | Fixed-baseline ceiling rate | Mean headroom | Evaluator median |
|---|---|---|---|---|
| 1 | planted_cluster n20, p_in 0.7, p_out 0.3 | 0.00 | 0.044 | 0.34 s |
| 2 | erdos n18 p0.5 | 0.00 | 0.065 | 0.93 s |
| 3 | erdos n22 p0.35 | 0.125 | 0.026 | 0.62 s |
| 4 | erdos n26 p0.3 | 0.25 | 0.026 | 1.05 s |

Every larger setting failed the certification limit within the calibration's 30 s evaluator budget: n22 p0.5, n26 p0.35, n30 p0.3 and above. So did n34 and n38 (n38 p0.3 and p0.35 have more than 200 edges and are unsupported by the reference). Every setting tried, selected or not, is in the record with its reasons.

## Disclosure

The builder had seen DEV candidate results on some of these settings before fixing the grid (B20_R14, B20_RX4). The rule reads only the fixed baselines and the evaluator. The B20_RX4 cell the candidate did best on (n30 p0.35) is not certifiable under this calibration's evaluator budget and was not selected.

All hosts measured here are exposed DEV material. The E1 redo excludes them (`scripts/b20r12_e1_redo.py`).
