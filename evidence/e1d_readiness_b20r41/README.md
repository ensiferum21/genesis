# B20_R41 evidence: E1d readiness, a dense family scored against an exact MIP (DEV, DRAFT rule)

Builder-run on DEV. Nothing here is independently reviewed, and nothing licenses a claim. The rule
is a DRAFT and is not in `calibration.RULES`. No package, comparator, evaluator or rule was
adopted.

- **Script:** `scripts/b20r41_e1d_readiness.py`. It was committed before the run in `39b0999`, and
  its SHA-256 (`306ff409…7862`) was sent to the user beforehand. The same commit added
  `lp_rounding_seconds` (off by default) to `discovery/generated_certify.py`.
- **Log:** `run.log`. 2,591 s in one go, on one pinned core. A checkpoint rehearsal ran on the
  other core.
- **Development looks:** all disclosed in `development_looks.json`.
  - A smoke run on a tiny grid with other seeds, which created 8 new hosts. They are in
    `development_look_hosts.json`.
  - Two looks on hosts already exposed in B20_R38. The rounding option came from the second.

## Design (fixed before running; the details are in the script's docstring)

**Draft rule `e1-hard-v3-draft`.** It uses e1-hard-v2's thresholds, with three changes:
- **Baselines.** E1's three frozen time-matched DSL programs at 0.5 s, plus `milp-highs-v1`
  (registry v2, exact HiGHS on one core) at 0.5 s and at 2.0 s. The strongest baseline on a host
  is the best of the five.
- **Reference.** The generated-rows route (B20_R37 registry and limits), seeded by the
  evaluator's own seed witness and the best baseline witness. It rounds its own LP for 1 CPU s,
  then runs SAT/DRAT, all within 60 s. The candidate is never an input.
- **Median reference time limit:** 30 s, not 15 s. The route's separation step alone is capped at
  15 s.

**Part A** is a candidate-blind calibration: 8 dense settings × 8 fresh hosts.

**Part B** runs on the selected settings: 30 fresh hosts and six arms, all in runc.
- The arms: E1's frozen candidate, its three frozen DSL baselines, and the MIP at 0.5 s and at
  2.0 s.
- The reference is seeded with the best arm witness, at 120 s.
- The analysis is B20_R24's, with the comparator chosen from all five baselines: the B19 DRAFT
  plan core, a dry run and the centred power model.

## Part A: calibration (`calibration_record.json`, `calibration_rows.jsonl`, `calibration_hosts.json`)

| # | Setting | Certified | Ceiling rate | Mean gap (edges) | Median reference time | MIP at 2 s at optimum | Eligible |
|---|---|---|---|---|---|---|---|
| 0 | planted n36 (0.8, 0.08) | 8/8 | 0.50 | 3.0 | 15.4 s | 4/8 | no: ceiling rate |
| **1** | **planted n38 (0.8, 0.07)** | 8/8 | **0.00** | 10.0 | 18.8 s | 0/8 | **yes** |
| **2** | **planted n40 (0.8, 0.06)** | 8/8 | **0.00** | 13.0 | 20.0 s | 0/8 | **yes** |
| **3** | **planted n40 (0.7, 0.06)** | 8/8 | **0.25** | 4.6 | 15.4 s | 2/8 | **yes** |
| 4 | planted n40 (0.9, 0.05) | 6/8 | 0.00 | 8.3 | 30.2 s | 0/8 | no: certification, speed |
| 5 | erdos n28 p0.45 | 8/8 | 0.88 | 0.1 | 11.9 s | 7/8 | no: ceiling rate, headroom |
| 6 | erdos n30 p0.42 | 7/8 | 1.00 | 0.0 | 12.2 s | 7/7 | no: certification, ceiling rate, headroom |
| 7 | erdos n32 p0.38 | 6/8 | 1.00 | 0.0 | 10.8 s | 6/6 | no: certification, ceiling rate, headroom |

**Selected:** settings 1, 2 and 3, in the rule's order.

**The candidate-blind reference works here.** On all 38 certified planted hosts, rounding the
route's own LP reached the optimum, and no SAT step was needed. SAT ran only on the 5 hosts left
uncertified. The LP was fully integral on 25 of
32 hosts in the four lower-density planted settings. The five uncertified hosts each kept a gap of
1–2 edges.

**On dense random graphs the exact MIP is enough.** HiGHS at four times E1's budget is at the
certified optimum on 20 of 21 certified erdos hosts. No "beyond strong baselines" headroom is
left there.

## Part B: re-pilot (`pilot_summary.json`, `pilot_rows.jsonl`, `pilot_hosts.json`, `power_analysis_centred.json`)

30 fresh hosts, 10 per selected setting. All 30 were certified, with reference wall times of
median 20.5 s and max 27.5 s. No run failed.

| Arm (all in runc) | Total | At optimum | Mean gap to optimum | Median cgroup CPU |
|---|---|---|---|---|
| **E1 frozen candidate** (`cross_2`, 0.5 s) | **3,546** | **30/30** | **0.0** | 0.73 s |
| `milp-highs-v1` at 2.0 s (4× budget) | 3,228 | 6/30 | 10.6 | 2.24 s |
| `low_cycle` (DSL, time-matched) | 3,150 | 0/30 | 13.2 | 0.73 s |
| `multistart` (DSL, time-matched) | 3,023 | 0/30 | 17.4 | 0.72 s |
| `exchange` (DSL, time-matched) | 2,958 | 0/30 | 19.6 | 0.72 s |
| `milp-highs-v1` at 0.5 s | 977 | 0/30 | 85.6 | 0.80 s |

**Comparator.** The strongest baseline by pilot total is **the exact MIP at four times the
candidate's budget**.

| Check (B19 DRAFT plan core, dry run) | Result |
|---|---|
| Candidate − comparator | **+10.6 per host**, interval [9.1, 12.1], p = 5 × 10⁻⁵ |
| W / T / L | 24 / 6 / 0 |
| By stratum | +10.9 (n38, 0.8, 0.07), +16.4 (n40, 0.8, 0.06), +4.5 (n40, 0.7, 0.06) |
| Cost ratio, candidate / comparator (cgroup CPU) | 0.34; the limit is 3.0 |
| Dry-run decision | SUPPORTED: every check passes, with no stratum regression |
| Centred power at the minimum useful effect (0.5) | 80 hosts per stratum (240 in all) for power 0.81; false-positive rate 0.012 at zero effect; approximation agreement 1.0 |

**Verdict: READY_FOR_REVIEW.**

## What it means

1. **This is the first DEV pilot whose comparator is an exact solver given more compute, and the
   frozen candidate is beyond it.** B20_R38 showed the same pattern, but only descriptively. E1's
   frozen 0.5 s candidate reached the certified optimum on all 30 fresh hosts.
   The strongest baseline, HiGHS given four times the CPU, did so on 6. The calibration that
   picked the settings never ran the candidate.
2. **The reference is candidate-blind and fast enough.** The generated-rows LP, with rounding of
   its own solution, certified every selected host in at most 27.5 s. This is the evaluator path a
   real run would need (`docs/GENERATED_ROWS_REFERENCE.md`).
3. **The headroom is specific to the planted regime.** On dense random graphs the MIP closes the
   gap, so a statement would be scoped to the three planted settings.

## Limits (for the reviewer)

- **DEV, builder-run, DRAFT rule.** The planted regime came from earlier DEV exploration
  (B20_R34, B20_R36, B20_R38). The time limit of 30 s and the LP rounding were fixed before this
  run. The reasons and the looks behind them are disclosed.
- **A stronger, slower method exists.** The reference itself, the generated-rows LP plus
  rounding, solves these hosts exactly in about 20 s of wall time. The plan treats it as ground
  truth, not as a competitor. A reviewer may want the claim to say this.
- **What a real E1d run needs.** All of these are reviewer decisions:
  - adopt `e1-hard-v3-draft`;
  - adopt the generated-rows reference and its custody (B20R35-OPEN-1, B20_R39);
  - wire registry v2, so that the custodian can run and select a MIP comparator (B20R40-OPEN-1);
  - a statistician;
  - an independent custodian.
- **Exposure.** The 102 hosts (64 calibration, 30 pilot, 8 development) are in the handoff
  addenda `exposure_hosts_addendum_b20r41.json`.
