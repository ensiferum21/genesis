# E1 handoff package v2: represent-and-repair (cross_2) on triangle-free hosts (GV3 path)

The builder regenerated this package on 13 October 2026 (B20_R12, redone on the canonical line). It is **not** registered with any custodian, and nothing here is an evaluation result.

**Status: the decided design is UNDERPOWERED. No sealed E1 run should be registered under it.**

## The claim

E1 claims that a frozen solver beats the strongest time-matched fixed baseline on a CONFIRM panel held by a custodian, by at least the minimum useful effect of 0.5 edges per task. The exact claim is in `decision_record_DRAFT_v2.json`, field `exact_claim`.

The frozen solver is B18's represent-and-repair solver:
- the cut representation `cross_2`;
- greedy triangle-free repair;
- 0.5 CPU seconds inside the solver.

## Decisions already made (the user, 13 Oct 2026), still needing reviewers

| Decision | What | Who must still sign off |
|---|---|---|
| Cost (B20R11-OPEN-1) | Conventional baselines get the candidate's search budget. `dsl-time-matched-v1` restarts the fixed program until 0.5 CPU s are spent. The plan's cost rule (max ratio 3.0) is unchanged. | reviewer |
| Comparator (B20R11-OPEN-2) | The custodian selects the strongest time-matched baseline on its own private SELECT panel (`custodian.select_comparator`). `register` refuses any other baseline. | reviewer |
| Power model (B19-OPEN-4) | Centred-headroom model, at least 10 tasks per stratum. | independent statistician |
| Host family | E1's hosts come from a study calibration made under a separately versioned rule, `e1-hard-v1`: fixed-baseline ceiling rate at most 0.25, with the other limits unchanged and no candidate input. The rule selected four settings: planted_cluster n20, erdos n18 p0.5, erdos n22 p0.35 and erdos n26 p0.3 (`evidence/dev_calibration_e1_b20r12/`). | reviewer (the rule) |

## What the B20_R12 pilot found (DEV, 30 fresh hosts, `evidence/e1_redo_b20r12/`)

| Quantity | Value |
|---|---|
| Comparator (strongest time-matched baseline on the pilot) | `multistart_tm` |
| Mean difference per host | +0.97 (wins / ties / losses 19 / 9 / 2) |
| CPU ratio, candidate to comparator | 1.00 (the cost rule now holds) |
| DRAFT plan dry run on the pilot | SUPPORTED (estimate 0.95, 90% interval [0.69, 1.21]) |
| Centred power model | INFEASIBLE |
| **Verdict (rule fixed before running)** | **UNDERPOWERED** |

Why INFEASIBLE: the power model gives each host with headroom whole extra edges, enough to make each stratum's expected gain equal the design effect of 1.0 edge. Two strata cannot carry that, so no panel size reaches the power target:
- planted_cluster: the candidate already reaches the certified optimum on 7 of 8 hosts, and the remaining host has 1 edge of headroom;
- erdos n22 p0.35: 5 of 7 hosts have 1 edge of headroom each, at most 0.71 per host.

The dry-run SUPPORTED on the pilot is not evidence: it is DEV material, and it was looked at only after the verdict rule was fixed.

The custodian's SELECT rehearsal also chose `multistart_tm` (totals over 30 private hosts: exchange_tm 1538, low_cycle_tm 1535, multistart_tm 1582). Because no panel size was chosen, the amended DRAFT cannot pass the decision-record check, and the rehearsal stopped there, as its rule said it would.

## What a reviewer could decide (design grounds only, before any panel exists)

Nothing here may be chosen because it produces a stronger label.

1. **Power model.** Whether a single design effect per stratum is the right model when strata differ in headroom. Alternatives are a design effect set per stratum from the design rather than from this pilot, or an estimand over strata with headroom. The statistician decides.
2. **Calibration rule.** Whether `e1-hard-v1` should also bound a candidate-independent headroom, so that strata like planted_cluster and n22 p0.35 are not selected. In those strata the fixed baselines miss the optimum by little, and the optimum is easy for a stronger solver to reach. Any change is a new rule version (`e1-hard-v2`), registered before a new calibration run.
3. **Retire E1 at this design.** The decided design cannot be powered on the selected family. That is a fair result, and it stays recorded.

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json` | The candidate as a `represent-and-repair-v1` descriptor. Its identity binds the reviewed source files, so it changed with this commit's `candidates.py`. |
| `time_matched_baselines.json` | The three `dsl-time-matched-v1` baselines (0.5 CPU s of restarts each). |
| `campaign_export.zip` | A real frozen triangle-free campaign export, with the candidate descriptor frozen in it. |
| `decision_record_DRAFT_v2.json` | The amended DRAFT. It names the E1 calibration, the time-matched comparator rule and the B20_R12 power analysis (INFEASIBLE). It is not frozen. |
| `decision_record_DRAFT.json` | The B19 DRAFT, unchanged. |
| `pilot_summary_b20r12.json`, `power_analysis_centred_b20r12.json` | The B20_R12 pilot and its power analysis. |
| `b19_*.json` | The B19 pilot, its summary and both B19 power analyses. |
| `exposure_hosts_to_exclude.json` | Every host the builder generated for E1, by seed or as tasks: the B19 and B20_R11 pilots, the B20_R11 rehearsal, the lost B20_R12 run (its SELECT hosts cannot be named), the E1 calibration, the B20_R12 pilot and its SELECT rehearsal. |
| `exposure_hosts_all.json` | The same hosts plus every triangle-free DEV host in the B20_R13, RX3, RX3b, RX4 and RX5 evidence, as tasks: 771 in all. A custodian can list this file as a `json` source in its exposure manifest. |

## Steps if a reviewer accepts a powered design

1. **Change the design first.** Change the plan and/or the rule in a reviewed commit, re-run the pilot on fresh DEV hosts (`scripts/b20r12_e1_redo.py` is the template), and regenerate this package at that commit.
2. **Reviewer:** freeze the amended record (`decision_record.freeze`), then publish it and its hash.
3. **Research operator:** record the custodian's signed comparator selection in the campaign (`cli.record_comparator_selection`). Then build the v4 request (`cli.descriptor_request_bundle`) with the frozen plan.
4. **Independent custodian, on its own machine and with its own keys:**
   1. Write an exposure manifest that lists every DEV panel named in the B16–B20 evidence and `exposure_hosts_all.json`.
   2. Run `select_comparator(..., study='e1')`.
   3. Draw the CONFIRM pool from the E1 study calibration with a private seed.
   4. Run `register`, then `evaluate`.
   5. Publish the registration log.
5. **Judge and auditor:** run `judge.recompute`, then `custodian.release_preflight` against the externally pinned trust root.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for triangle-free hosts from the E1 calibrated settings, on that panel only, against time-matched fixed baselines. It would not establish a better improver, transfer, novelty, or anything about the domain-adopted family.
