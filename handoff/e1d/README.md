# E1d handoff package (DRAFT): E1's frozen candidate on dense planted hosts, against an exact MIP at four times its budget (GV3 path)

The builder wrote this package on 16 October 2026 (B20_R43) with `scripts/b20r43_e1d_package.py`.
- It is **not registered with any custodian**, and nothing here is an evaluation result.
- **Nothing is adopted.** The rule, the reference route and the registry-v2 wiring it relies on all
  await a reviewer (B20R41-OPEN-1, B20R35-OPEN-1, B20R40-OPEN-1).

**Status: READY_FOR_REVIEW (DEV).**
- **Re-pilot (B20_R41):** READY_FOR_REVIEW.
- **Same-operator rehearsal of the whole custody path (B20_R43):** SUPPORTED, and the judge agrees.

## Evidence card (five dimensions, never collapsed into one score)

| Dimension | Status | Evidence |
|---|---|---|
| **Validity** | Every witness is re-checked by the domain checker. Every optimum is certified: an exact LP certificate over Lean-checked generated inequalities, checked by an exact checker; or SAT/DRAT. | B20_R35/R37/R39; the rehearsal re-checked 474 witnesses |
| **Utility, fresh DEV hosts** | +10.6 per host [9.1, 12.1] over the strongest of five baselines, which was HiGHS at 4× budget. Candidate optimal on 30/30. | B20_R41 (`pilot_summary_b20r41.json`) |
| **Utility, rehearsal panel, same operator** | +9.80 per host [9.30, 10.35]; W/L/T 198/0/39 on 237 certified hosts. Comparator HiGHS at 4× budget, selected by the custodian's SELECT. | B20_R43 (`rehearsal_summary_b20r43.json`) |
| **Causal contribution** | **DEV: READY_FOR_REVIEW.** Weakening only the discovered representation's decoder (`cross_2` → `ordered_2`, which Lean shows is strictly weaker) costs **+7.07 per host [6.47, 7.70], 30/0/0**. A Lean-certified *equal* decoder (`adjacent_2`, the null control) shows +0.03 [−0.02, +0.09]: NULL_CONTROL_CLEAN. The same-operator rehearsal of the custodian-signed ablation evaluation through v5 is **SUPPORTED, judge agrees: +6.64 [6.03, 7.29], 44/0/0** (B20_R45). Licensing ABLATION_SUPPORTED needs an independent custodian. | B20_R44, B20_R45 (`evidence/e1d_ablation_b20r44/`, `evidence/e1d_ablation_rehearsal_b20r45/`) |
| **Comparator budget** | **Budget crossover (B20_R63): CROSSOVER_AT_8S.** On 30 fresh hosts the candidate again beats HiGHS at 2 s (4×): +10.30 [8.77, 11.83]. It also beats it at 4 s (8×): +6.37. At 8 s (16×) the advantage is +0.43, no longer material, and at 16 s and 32 s HiGHS ties, proving all 30 optima in about 6 CPU s per host (median). The advantage is speed, about an order of magnitude, not quality at any budget; a claim must state the crossover. | B20_R63 (`evidence/e1d_crossover_b20r63/`) |
| **Host size** | **Host size (B20_R64, DEV pilot outside the calibrated settings): ADVANTAGE_GROWS.** On planted (0.8, 0.06) hosts, the crossover is 8 s (16×) at n40, 32 s (64×) at n50, and beyond 64× at n60 (about 430 edges): there the candidate leads HiGHS at 32 s by +17.6 [8.1, 28.8], 10/0/0, within about one edge of a proven upper bound. A first run was invalid (HiGHS CPU-starved by a concurrent job) and was re-run alone. Claiming it needs a family-space extension and the 200-edge certificate bound lifted for the LP-dual route. | B20_R64 (`evidence/e1d_scaling_b20r64/`) |
| **Improver capability** | None claimed. This is a better-*solver* package. | n/a |
| **Novelty / replication** | None claimed: the representation is a cut decoder, and the bounds are classical. **No independent replication.** | needs an independent custodian (GV7) |

## The claim

The exact wording is in `decision_record_DRAFT.json`, field `exact_claim`. In short: a frozen solver
scores more edges than the strongest of five registered baselines, on a CONFIRM panel held by a
custodian, by at least 0.5 edges per host.
- **The frozen solver:** E1's represent-and-repair, with the `cross_2` cut representation, greedy
  repair and 0.5 CPU s of search. Its descriptor is the same frozen descriptor as package E1:
  `f4c7f4b0…95b1`.
- **The five baselines:**
  - three fixed DSL programs, time-matched at 0.5 CPU s;
  - the exact MILP `milp-highs-v1` (HiGHS, one core) at 0.5 CPU s;
  - the same MILP at **2.0 CPU s**, four times the candidate's budget.

**Setting.** The hosts are triangle-free host graphs from three dense planted-cluster settings,
calibrated candidate-blind under the DRAFT rule `e1-hard-v3-draft`:
- n38 (0.8, 0.07);
- n40 (0.8, 0.06);
- n40 (0.7, 0.06).

**Scoring.** Optima are certified by the generated-rows reference (`reference_route.json`): LP over the
B20_R37 Lean-checked rows, rounding of its own LP, then SAT/DRAT, at 120 s.

**What the claim must also say.** The reference itself, an exact method, solves these hosts in about
20 s of wall time. The plan treats it as ground truth, not as a competitor. The claim is therefore "a
0.5 s solver beats an exact MIP at 2 s", not "beats every exact method".

## Evidence (DEV, builder-run, every rule fixed before its run)

**Calibration (B20_R41 Part A; record `evidence/e1d_package_b20r43/calibration_triangle_free_host_v1_e1_hard_v3_draft.json`).**
- 8 dense settings × 8 hosts, run candidate-blind.
- The three planted settings above were selected.
- The dense erdos settings fail: HiGHS at 2 s is optimal on 20/21 certified hosts.

**Re-pilot (B20_R41 Part B):** 30 fresh hosts, all certified.

| Quantity | Value |
|---|---|
| Comparator | `milp_highs_4x` (HiGHS at 2.0 s) |
| Mean difference per host | **+10.6** [9.1, 12.1]; W/T/L 24/6/0 |
| Candidate / MIP-4× / best DSL at the optimum | 30/30, 6/30, 0/30 |
| CPU ratio, candidate to comparator | 0.34 |
| DRAFT plan dry run | SUPPORTED |
| Centred power | **80 per stratum, 240 in total** (power 0.81 at the minimum useful effect) |

**Rehearsal (B20_R43, same operator, fixture keys).**
- **Where it ran.** In a throwaway copy of the code at the B20_R43 setup commit. There, and only
  there, study `e1d` adopted the record, standing in for a reviewer's adoption.
- **The path.** Evaluation request v5, with registry-v2 arms and the reference route named in it.

| Step | Result |
|---|---|
| Custodian SELECT on 30 private hosts | **`milp_highs_4x`**. SELECT totals: MIP-4× 3,123, low_cycle 3,053, multistart 2,986, exchange 2,899, MIP-0.5 s 987. |
| CONFIRM panel | 240 hosts. 237 certified by the LP over generated rows; 3 unsupported (1.25%, within the plan's 5%). |
| Wins / losses / ties | **198 / 0 / 39** |
| Estimate | **+9.80** [9.30, 10.35], p = 5 × 10⁻⁵, Holm rejects |
| By stratum | n38 (0.8, 0.07): +10.83; n40 (0.7, 0.06): +4.59; n40 (0.8, 0.06): +14.00. No stratum regresses. |
| Cost ratio | 0.338 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | agrees; 474 witnesses re-checked; fairness has no problems |

The rehearsal licenses nothing. One operator played every role, and the builder froze the record.

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json` | The candidate: E1's frozen descriptor, unchanged. |
| `baselines.json` | The five baselines under the candidate's profile (2 CPU s, 2048 MiB, 10 s wall, 1000 queries). Two are registry-v2 descriptors (`milp-highs-v1`). |
| `reference_route.json` | The v5 reference route: `generated-rows-v1`, the B20_R37 package by digest, and every limit. |
| `campaign_export.zip` | A fresh frozen DEV campaign with the candidate frozen in it. It has no comparator selection; a real custodian's selection goes there. |
| `decision_record_DRAFT.json` | The DRAFT. It names the calibration record (by SHA-256 in `package_index.json`), the reference route and the B20_R41 power analysis. A frozen copy has no structural problems. |
| `pilot_summary_b20r41.json`, `power_analysis_centred_b20r41.json` | The re-pilot. |
| `rehearsal_summary_b20r43.json` | The rehearsal: selection, payload, judge, fairness, resource account and reference methods. |
| `exposure_hosts_all_part_01.json` … `_06.json` | Every host the builder named or generated (2,641), as tasks, in files of at most 500. One file would exceed the exposure screener's 10⁶-node limit. A custodian lists each as a `json` source. |
| `package_index.json` | Identities: candidate, baselines, calibration, reference route, decision record, code and rehearsal. |

## What a real E1d run needs (reviewer decisions)

1. Adopt the rule `e1-hard-v3-draft` and the study `e1d` in `configs/dev_calibration.json`.
2. Adopt the generated-rows reference: the theory package, the checker identities, and the route in
   request v5 (B20R35-OPEN-1; `docs/GENERATED_ROWS_REFERENCE.md`).
3. Adopt the registry-v2 wiring and the MIP as a comparator (B20R40-OPEN-1;
   `docs/CANDIDATE_REGISTRY_V2.md`).
4. A statistician signs off the centred power model (B19-OPEN-4).
5. An independent custodian runs SELECT, register and evaluate on its own machine, for 240 hosts.
6. For a causal level: the registered transform reviewed (B20R44-OPEN-1), then a custodian-signed ablation evaluation; the B20_R44 re-pilot is READY_FOR_REVIEW.
