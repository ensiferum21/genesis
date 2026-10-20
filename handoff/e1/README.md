# E1 handoff package v3: represent-and-repair (cross_2) on triangle-free hosts (GV3 path)

The builder regenerated this package on 14 October 2026 (B20_R24) with `scripts/b20r24_packages.py`. It is **not** registered with any custodian, and nothing here is an evaluation result.

**Status: READY_FOR_REVIEW on the `e1-hard-v2` family.** B20_R12's design was UNDERPOWERED on the `e1-hard-v1` family (B20R12-OPEN-1). The user's decision of 14 Oct 2026 replaced the family rule, and the re-pilot is now powerable. A same-operator rehearsal of the whole custody path came out SUPPORTED, and the judge agrees.

## The claim

A frozen solver beats the strongest time-matched fixed baseline on a CONFIRM panel held by a custodian, by at least the minimum useful effect of 0.5 edges per host. The exact claim is in `decision_record_DRAFT_v3.json`, field `exact_claim`.

The frozen solver is B18's represent-and-repair solver:
- the cut representation `cross_2`;
- greedy triangle-free repair;
- 0.5 CPU s of search.

Its baselines are the three fixed DSL programs, restarted for 0.5 CPU s (`dsl-time-matched-v1`). Every arm runs in the custodian's OCI sandbox under one profile: 2 CPU s, 2048 MiB, 10 s wall, 1000 queries.

## Decisions (the user), still needing reviewers

| Decision | What | Who must still sign off |
|---|---|---|
| Cost (13 Oct) | Time-matched baselines. The plan's cost rule (max ratio 3.0) is unchanged. | reviewer |
| Comparator (13 Oct) | The custodian's SELECT step on its own private panel; `register` enforces it. | reviewer |
| Power (13 Oct) | Centred-headroom model, at least 10 per stratum. | independent statistician (B19-OPEN-4) |
| Family (14 Oct) | Study `e1-v2` under the versioned rule `e1-hard-v2`. It adds three things to `e1-hard-v1`, and never reads a candidate: <br>• time-matched baselines measured in the sandbox; <br>• a certification limit (`obstruction.certify`, 60 s; at least 90% certified); <br>• a headroom bound of mean (optimum − best baseline) ≥ 1.0 edge, the design effect. <br>It selected planted_cluster n30 p_in 0.6 p_out 0.2, erdos n26 p0.35 and erdos n30 p0.3 (`evidence/dev_calibration_e1_hard_v2_b20r24/`). | reviewer (the rule) |

## Evidence (DEV, builder-run, every rule fixed before its run)

**Re-pilot** (`evidence/repilots_b20r24/`): 30 fresh hosts, 10 per setting, all certified.

| Quantity | Value |
|---|---|
| Comparator | `low_cycle_tm` |
| Mean difference per host | +2.57 (wins / ties / losses 26 / 3 / 1) |
| CPU ratio, candidate to comparator | 1.00 |
| DRAFT plan dry run | SUPPORTED, estimate 2.57 [2.10, 3.03] |
| Centred power | **10 per stratum, 30 in total (power 0.88)** |
| Verdict | **READY_FOR_REVIEW** |

**First rehearsal: INVALID.** 4 of 30 CONFIRM hosts were unsupported, against the plan's limit of 5%. The cause was an evaluator defect, B20R24-OPEN-1: the SAT-only reference gave up after one 60 s timeout. It was repaired with the joint LP/SAT reference for v4 evaluations. The plan was not changed.

**Rehearsal after the repair** (`evidence/rehearsal_rerun_b20r24/`): same operator, fixture keys, new hosts.

| Step | Result |
|---|---|
| Custodian SELECT on 30 private hosts | `multistart_tm` |
| CONFIRM panel | 30 hosts, all certified |
| Wins / losses / ties | 29 / 0 / 1 |
| Estimate | **3.00** [2.53, 3.47] |
| Cost ratio | 1.003 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | agrees |

The rehearsal licenses nothing. Every role was played by one operator, and the builder froze the record.

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json` | The candidate, as built by this commit's reviewed code. Its identity changed because `candidates.py` changed in B20_R23. |
| `time_matched_baselines.json` | The three baselines, 0.5 CPU s each. |
| `campaign_export.zip` | A fresh frozen DEV campaign with the candidate frozen in it. It has no comparator selection recorded; a real custodian's selection goes there. |
| `decision_record_DRAFT_v3.json` | The DRAFT. It names the `e1-v2` calibration (record SHA-256 in `package_index.json`) and the re-pilot's power analysis. A frozen copy has no structural problems. |
| `power_analysis_centred_b20r24.json`, `pilot_summary_b20r24.json` | The re-pilot. |
| `rehearsal_summary_b20r24.json` | Both rehearsals: the payload, the judge, fairness and the SELECT totals. |
| `exposure_hosts_all.json` | Every host the builder named or generated, as tasks: 1,544 hosts. This covers both domains, the E1 history, both calibrations, the pilots and both rounds of rehearsals. A custodian lists it as a `json` source in its exposure manifest. |
| `exposure_hosts_addendum_b20r28.json` | B20_R28: the 126 DEV hosts named after this package was frozen (B20_R26–R28, some in the e1-v2 setting erdos n30 p0.3). A custodian lists it as a second `json` source. |
| `exposure_hosts_addendum_b20r31.json` | B20_R31: the 168 DEV hosts named after that, all in the `e1b` settings, one of which (erdos n30 p0.3) is the e1-v2 setting: B20_R30's certification-budget hosts, B20_R31's study hosts and its six development-look hosts. Written by `scripts/exposure_addendum.py`. A custodian lists it as a further `json` source. |
| `exposure_hosts_addendum_b20r32.json` | B20_R32: the 90 DEV hosts of the generated-row certification study, all in the `e1b` settings (one setting, erdos n30 p0.3, is the e1-v2 setting). |
| `exposure_hosts_addendum_b20r33.json` | B20_R33: the 60 DEV hosts of the strong-baseline audit, all in the `e1b` settings (one setting, erdos n30 p0.3, is the e1-v2 setting). |
| `exposure_hosts_addendum_b20r34.json` | B20_R34: the 104 DEV graphs named by the MIP-hard probe (56 run, plus the 48 never-run graphs of the listing regenerated on resume); none is in this package's settings. |
| `exposure_hosts_addendum_b20r35.json` | B20_R35: the 40 DEV hosts of the dense certification study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r36.json` | B20_R36: the 48 DEV hosts of the dense construction study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r37.json` | B20_R37: the 40 DEV hosts of the generator-v2 coverage study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r38.json` | B20_R38: the 40 DEV hosts of the dense strong-baseline audit; none is in this package's settings. |
| `exposure_hosts_addendum_b20r41.json` | B20_R41: the 102 DEV hosts of the E1d readiness study (64 calibration, 30 pilot, 8 from a disclosed development look); none is in this package's settings. |
| `exposure_hosts_addendum_b20r43.json` | B20_R43: the 279 hosts of the E1d same-operator rehearsal (30 SELECT, 240 CONFIRM, 9 from a disclosed development look), all in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r44.json` | B20_R44: the 30 DEV hosts of the E1d ablation re-pilot, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r45.json` | B20_R45: the 45 CONFIRM hosts of the E1d ablation rehearsal, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r47.json` | B20_R47: the 40 DEV C4 hosts of the C4 certification study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. |
| `exposure_hosts_addendum_b20r48.json` | B20_R48: the 40 DEV C4 hosts of the C4 tree-certification study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. |
| `exposure_hosts_addendum_b20r49.json` | B20_R49: the 40 DEV C4 hosts of the C4 rows ablation study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. |
| `exposure_hosts_addendum_b20r50.json` | B20_R50: the 62 DEV C4 hosts of the E1b-C4 readiness study (32 calibration hosts in four erdos settings, 30 pilot hosts in erdos n30 p0.2 and n40 p0.15); none is in this package's settings. |
| `exposure_hosts_addendum_b20r52.json` | B20_R52: the C4 hosts of the E1b-C4 same-operator rehearsal (30 SELECT, 20 CONFIRM, 9 from a disclosed development look) in erdos n30 p0.2 and n40 p0.15; none is in this package's settings. |
| `exposure_hosts_addendum_b20r63.json` | B20_R63: the 30 DEV hosts of the E1d budget-crossover study, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r64.json` | B20_R64: the 30 DEV hosts of the E1d scaling pilot (planted (0.8, 0.06) at n40, n50, n60; n50/n60 drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r66.json` | B20_R66: the 20 DEV hosts of the E1d n60 replication (planted (0.8, 0.06) at n60, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r68.json` | B20_R68: the 50 DEV hosts of the E1d domain-heuristic comparison (30 on E1d's three calibrated planted settings, 20 planted (0.8, 0.06) at n60 drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r70.json` | B20_R70: the 24 DEV hosts of the E1d time-to-solution scaling study (planted (0.8, 0.06) at n40, n50, n60; n50/n60 drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r72.json` | B20_R72: the 20 DEV hosts of the representation-engine move-rule study (planted (0.8, 0.06) at n60, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r75.json` | B20_R75: the 12 DEV hosts of the state-of-the-art comparison (planted (0.8, 0.06) at n60 and n63, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r76.json` | B20_R76: the 12 DEV hosts of the state-of-the-art comparison with CP-SAT (planted (0.8, 0.06) at n60 and n63, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r77.json` | B20_R77: the 24 DEV hosts of the engine's comparison with CP-SAT and BURER2002 (planted (0.8, 0.06) at n63, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r79.json` | B20_R79: the 16 DEV training hosts of the system's program search (planted (0.8, 0.06) at n63, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r81.json` | B20_R81: the 24 DEV hosts of the self-found-solver test (planted (0.8, 0.06) at n63, drawn beyond the registered family space); none is in this package's settings. |
| `package_index.json` | Identities, the calibration, the verdicts and the rehearsal outcomes. |
| `decision_record_DRAFT_v2.json`, `pilot_summary_b20r12.json`, `power_analysis_centred_b20r12.json` | B20_R12 (`e1-hard-v1`: UNDERPOWERED). Kept. |
| `decision_record_DRAFT.json`, `b19_*.json`, `exposure_hosts_to_exclude.json` | B19 and the earlier exposure list. Kept. |

**A strong-baseline caveat (B20_R33; B20R33-OPEN-1).** On 60 fresh hosts of these settings an exact MIP solver (HiGHS, through the pinned scipy) proves every optimum within 0.36 CPU s. At this package's 0.5 s budget it dominates the candidate by +0.75 edges per host (`evidence/strong_baseline_audit_b20r33/`). A SUPPORTED outcome here would be a statement against time-matched DSL baselines only; the reviewer decides whether that scope is worth running. In a dense regime outside this package's settings, B20_R38 found this candidate optimal on 19/20 fresh hosts and +14.6 per host above HiGHS at four times its budget (planted clusters); using that regime would need a new package version, a versioned rule and the generated-rows reference (`docs/GENERATED_ROWS_REFERENCE.md`). B20_R41 ran that preparation on DEV under a DRAFT rule (`e1-hard-v3-draft`): calibration selected three planted settings, and a 30-host re-pilot against the strongest baseline, which was HiGHS at four times the budget, is READY_FOR_REVIEW (+10.6 per host [9.1, 12.1], candidate optimal on 30/30; `evidence/e1d_readiness_b20r41/`). Nothing in this package changes.

## Steps for an independent run

1. **Reviewer.** Sign off the rule `e1-hard-v2` and the three earlier decisions, then freeze `decision_record_DRAFT_v3.json` (`decision_record.freeze`). Publish the record and its hash.
2. **Statistician.** Sign off the centred power model (B19-OPEN-4).
3. **Independent custodian, on its own machine and with its own keys:**
   1. Write an exposure manifest that includes `exposure_hosts_all.json` and every `exposure_hosts_addendum_*.json` (B20_R28, B20_R31).
   2. Run `select_comparator(..., study='e1-v2')`.
   3. The research operator records the signed selection (`cli.record_comparator_selection`) and builds the v4 request (`cli.descriptor_request_bundle`, 30 hosts).
   4. The custodian runs `register`, then `evaluate` on a CONFIRM pool drawn from study `e1-v2` with a private seed, and publishes the registration log.
4. **Judge and auditor.** Run `judge.recompute`, then `custodian.release_preflight` against the externally pinned trust root.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for triangle-free hosts from the `e1-v2` calibrated settings, on that panel only, against time-matched fixed baselines. It would not establish a better improver, transfer, novelty, or anything about other families.
