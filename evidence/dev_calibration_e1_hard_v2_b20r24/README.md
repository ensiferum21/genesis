# e1-hard-v2 calibration (B20_R24, DEV)

**Script.** `scripts/b20r24_e1_hard_v2_calibration.py`, committed as `bf7c4c8` before it ran. Its SHA-256 (`6f2b53aa…1343`) was sent to the user in the conversation before the run, because GitHub was disconnected. The two domains ran in parallel on the workspace's 2 cores, as the docstring says.

**Decision behind it.** The user, 14 Oct 2026: a versioned rule that adds a candidate-independent headroom bound and a certification limit. One calibration picks the settings for both E1 and E1b, and both are then re-piloted on fresh hosts.

## The rule (`calibration.SELECTION_RULE_E1_HARD_V2`)

The rule keeps every `e1-hard-v1` limit:
- certified fraction ≥ 0.9;
- fixed-baseline ceiling rate in [0, 0.25];
- relative headroom ≥ 0.02;
- median evaluator time ≤ 15 s;
- the same order, and at most 4 settings.

It adds three things:

| Addition | What it does |
|---|---|
| Baselines measured as the studies run them | The three fixed DSL programs as `dsl-time-matched-v1` with 2.0 CPU s of restarts, in the OCI sandbox. That is E1b's budget; E1's baselines get 0.5 s, so this is conservative for E1. |
| A certification limit | `obstruction.certify`, seeded with the best baseline witness, with 60 s per host. |
| A headroom bound in edges | The mean of (certified optimum − best time-matched baseline) must be ≥ 1.0, the plan's design effect. |

The rule never reads a candidate.

## Result

**Triangle-free: 3 of 20 settings selected.** In selection order:

| Setting | Certified | Ceiling | Mean gap (edges) | Relative headroom | Median evaluator time |
|---|---|---|---|---|---|
| planted_cluster n30 p_in 0.6 p_out 0.2 | 1.0 | 0.0 | 2.875 | 0.031 | 1.3 s |
| erdos n26 p0.35 | 1.0 | 0.125 | 1.625 | 0.021 | 0.5 s |
| erdos n30 p0.3 (E1b's C1) | 1.0 | 0.125 | 2.0 | 0.021 | 0.9 s |

**C4: NO_ELIGIBLE_SETTING (0 of 14).**
- On every small setting, the 2.0 s time-matched baselines are at or near the optimum.
- erdos n30 p0.2 (E1b's C3) has headroom (gap 2.17), but only 6/8 hosts certify within 60 s, and the median evaluator time is 24 s.

Nothing was relaxed. E1b on C4 is therefore NOT_RUN in the re-pilots.

What the new limits changed, against `e1-hard-v1`:
- **E1's four v1 settings are all ineligible now.** planted_cluster n20 has a gap of 0.375; erdos n18 p0.5 has 0.75; n22 p0.35 has 0.125. erdos n26 p0.3 has a gap of 1.125, but a relative headroom of only 0.015 and a ceiling rate of 0.375. Measured against time-matched baselines, these settings are near the ceiling. This is what made E1 UNDERPOWERED (B20R12-OPEN-1).
- **erdos n40 p0.2 (E1b's C2) is ineligible:** ceiling rate 0.5, gap 0.625. The best of the three 2.0 s baselines per host often reaches the optimum there.
- **Larger and denser settings fail the certification limit:** n30 p0.35, n34 p0.3 and above, and n38 and above. erdos n22 p0.5 fails the evaluator-speed limit narrowly (median 16.0 s against 15 s).

## Adoption

`configs/dev_calibration.json` gains two studies that name the triangle-free record (SHA-256 `bc26782a…e633`) and the rule `e1-hard-v2`:
- `e1-v2`, for E1;
- `e1b`, for E1b on triangle-free hosts.

Study `e1` (`e1-hard-v1`, B20_R12) and the domain adoptions are unchanged. The rule needs a reviewer's sign-off.

## Files

- `calibration_<domain>_e1_hard_v2.json`: the full records. They hold every setting tried and per-host rows: certification, baseline values and baseline cgroup CPU.
- `summary.json`
- `console_<domain>.log`, `run_<domain>.log`

Every host measured here is DEV material and is exposed. The re-pilots regenerate the hosts from the records and exclude them.
