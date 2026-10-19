# E1b handoff package v2: an LP-guided construction pipeline on triangle-free hosts (GV3 path)

The builder regenerated this package on 14 October 2026 (B20_R24) with `scripts/b20r24_packages.py`. It is **not** registered with any custodian, and nothing here is an evaluation result.

**Status: READY_FOR_REVIEW on the `e1-hard-v2` family, triangle-free only.** A same-operator rehearsal of the whole custody path came out SUPPORTED, and the judge agrees.

## The claim

A frozen solver beats the strongest time-matched fixed DSL baseline on a CONFIRM panel held by a custodian, by at least the minimum useful effect of 0.5 edges per host. The exact claim is in `decision_record_DRAFT.json`.

The frozen solver is a `construct-pipeline-v1` descriptor:
- `{init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0, seed 0}`, that is, LP-ordered greedy followed by LP-perturbed restarts;
- the profile is 4 CPU s, 2048 MiB, 20 s wall and 1000 queries, the same for every arm.

**It is a builder-written method** (`discovery/construct.py`, B20_RX3). A supported E1b is a scoped better-solver statement (GV3). It is not evidence of research ability (GV4).

## Decisions (the user), still needing reviewers

| Decision | What |
|---|---|
| Family (14 Oct, B20R23-OPEN-1) | Study `e1b` under the versioned rule `e1-hard-v2`, the same calibration as E1's study `e1-v2`. It selected planted_cluster n30 p_in 0.6 p_out 0.2, erdos n26 p0.35 and erdos n30 p0.3. On C4 no setting is eligible: the small settings are at the time-matched ceiling, and erdos n30 p0.2 fails the certification limit. **E1b on C4 is therefore not pursued at this rule.** |
| Cost, comparator, power | As for E1 (time-matched; the custodian's SELECT step; the centred model). |

## Evidence (DEV, builder-run, every rule fixed before its run)

**B20_R23, on builder-chosen settings** (`evidence/e1b_readiness_b20r23/`, `evidence/e1b_causal_readiness_b20r23/`).
- Readiness: +1.79 per host on triangle-free hosts.
- Causal readiness: ablation +1.42 and placebo +2.53, both ready for review.

**Re-pilot on the `e1b` calibration** (`evidence/repilots_b20r24/`): 30 fresh hosts, all certified.

| Quantity | Value |
|---|---|
| Comparator | `multistart_tm` |
| Mean difference per host | **+2.63** (wins / ties / losses 29 / 1 / 0) |
| CPU ratio | 1.02 |
| Candidate at the optimum | 25 / 30 |
| DRAFT plan dry run | SUPPORTED, estimate 2.63 [2.27, 3.00] |
| Centred power | **10 per stratum, 30 in total (power 0.97)** |
| Verdict | **READY_FOR_REVIEW** |

**Rehearsals.**
- **First rehearsal: INVALID.** 2 of 30 hosts were unsupported, from the evaluator defect B20R24-OPEN-1, since repaired.
- **After the repair** (`evidence/rehearsal_rerun_b20r24/`): the custodian's SELECT chose `multistart_tm`. On 30 CONFIRM hosts, 29 were certified and 1 unsupported, within the 5% limit. Wins / losses / ties were 29 / 0 / 0. The estimate was **3.55** [3.03, 4.05] at a cost ratio of 1.019. Outcome **SUPPORTED**; `judge.recompute` agrees.

The rehearsals license nothing. One operator played every role, with fixture keys.

**Causal follow-ups, re-piloted on this family (B20_R28; `evidence/e1b_causal_repilot_b20r28/`).** The setup is 30 fresh hosts from the `e1b` calibration, with 28 certified (at least 8 of 10 per stratum). Every arm ran in the runc sandbox. The intervened descriptors are the registered ones in `interventions.json`.

| Contrast | Mean per host | W / T / L | CPU ratio | DRAFT dry run | Centred power | Verdict |
|---|---|---|---|---|---|---|
| candidate − ablation (`random_greedy`) | **+1.25** | 24 / 3 / 1 | 1.03 | SUPPORTED, 1.26 [1.02, 1.48] | 10 per stratum (30) | **READY_FOR_REVIEW** |
| candidate − placebo (`lp_shuffled_greedy`) | **+2.61** | 27 / 1 / 0 | 1.00 | SUPPORTED, 2.58 [2.23, 2.95] | 10 per stratum (30) | **READY_FOR_REVIEW** |

The placebo scores 1.36 per host *below* the ablation: shuffled LP values are worse than no LP order. On DEV, the LP signal is the active ingredient. A causal level still needs signed custodian ablation and placebo evaluations. The B20_R23 pilot on builder-chosen settings stays in the history.

**Certification limits on this family (B20_R30; `evidence/certification_budget_b20r30/`).** 90 fresh hosts were measured under both limits:

| Limit | Certified |
|---|---|
| Calibration, 60 s | 86/90 |
| Evaluator reference, 600 s | 90/90 (unsupported upper bound 3.27%) |

On this family the calibration's limit and the plan's 5% unsupported limit agree (LIMITS_CONSISTENT). How to align them in general is still the reviewer's choice (B20R24-OPEN-2).

**A strong-baseline question (B20_R32; B20R32-OPEN-2).** An off-the-shelf exact MILP solver (HiGHS, through the pinned scipy) found and proved the optimum of each of the 21 hardest `e1b` hosts tried in under 0.72 s wall. E1b's comparator is the time-matched fixed DSL programs. A reviewer should weigh whether "beyond strong baselines" needs a MIP comparator. B20_R33 measured it (`evidence/strong_baseline_audit_b20r33/`): on 60 fresh hosts the MIP proves every optimum within 0.36 CPU s, and this package's candidate is within 0.20 edges of it (NO_MATERIAL_DIFFERENCE, never above). A SUPPORTED outcome here would be a statement against time-matched DSL baselines only (B20R33-OPEN-1).

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json`, `time_matched_baselines.json` | The frozen candidate and its three baselines (2.0 CPU s each). |
| `interventions.json` | The registered ablation (`random_greedy`) and placebo (`lp_shuffled_greedy`), checked with `intervention_problems`. |
| `campaign_export.zip` | A fresh frozen DEV campaign with the candidate frozen in it. |
| `decision_record_DRAFT.json` | Names the `e1b` calibration and the re-pilot's power analysis. A frozen copy has no structural problems. |
| `power_analysis_centred_b20r24.json`, `pilot_summary_b20r24.json`, `rehearsal_summary_b20r24.json` | The re-pilot and both rehearsals. |
| `exposure_hosts_all.json` | Every host the builder named or generated (1,544). |
| `exposure_hosts_addendum_b20r28.json` | B20_R28: the 126 DEV hosts named after this package was frozen (B20_R26–R28). |
| `exposure_hosts_addendum_b20r31.json` | B20_R31: the 168 DEV hosts named after that, all in this package's settings: B20_R30's certification-budget hosts, B20_R31's study hosts and its six development-look hosts. A custodian lists **every** exposure file: `exposure_hosts_all.json` and each addendum. |
| `exposure_hosts_addendum_b20r32.json` | B20_R32: the 90 DEV hosts of the generated-row certification study, all in the `e1b` settings. |
| `exposure_hosts_addendum_b20r33.json` | B20_R33: the 60 DEV hosts of the strong-baseline audit, all in the `e1b` settings. |
| `exposure_hosts_addendum_b20r34.json` | B20_R34: the 104 DEV graphs named by the MIP-hard probe (56 run, plus the 48 never-run graphs of the listing regenerated on resume); none is in this package's settings. |
| `exposure_hosts_addendum_b20r35.json` | B20_R35: the 40 DEV hosts of the dense certification study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r36.json` | B20_R36: the 48 DEV hosts of the dense construction study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r37.json` | B20_R37: the 40 DEV hosts of the generator-v2 coverage study; none is in this package's settings. |
| `exposure_hosts_addendum_b20r38.json` | B20_R38: the 40 DEV hosts of the dense strong-baseline audit; none is in this package's settings. |
| `exposure_hosts_addendum_b20r41.json` | B20_R41: the 102 DEV hosts of the E1d readiness study (64 calibration, 30 pilot, 8 from a disclosed development look); none is in this package's settings. |
| `exposure_hosts_addendum_b20r43.json` | B20_R43: the 279 hosts of the E1d same-operator rehearsal (30 SELECT, 240 CONFIRM, 9 from a disclosed development look), all in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r44.json` | B20_R44: the 30 DEV hosts of the E1d ablation re-pilot, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r45.json` | B20_R45: the 45 CONFIRM hosts of the E1d ablation rehearsal, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r47.json` | B20_R47: the 40 DEV C4 hosts of the C4 certification study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. erdos n30 p0.2 is the C4 setting that failed this package's calibration. |
| `exposure_hosts_addendum_b20r48.json` | B20_R48: the 40 DEV C4 hosts of the C4 tree-certification study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. erdos n30 p0.2 is the C4 setting that failed this package's calibration. |
| `exposure_hosts_addendum_b20r49.json` | B20_R49: the 40 DEV C4 hosts of the C4 rows ablation study (c4_host_v2, erdos n30 p0.2 and n36 p0.17); none is in this package's settings. erdos n30 p0.2 is the C4 setting that failed this package's calibration. |
| `exposure_hosts_addendum_b20r50.json` | B20_R50: the 62 DEV C4 hosts of the E1b-C4 readiness study (32 calibration hosts in four erdos settings, 30 pilot hosts in erdos n30 p0.2 and n40 p0.15); none is in this package's adopted settings; they are the C4 settings of a DRAFT rule for this package's C4 arm. |
| `exposure_hosts_addendum_b20r52.json` | B20_R52: the C4 hosts of the E1b-C4 same-operator rehearsal (30 SELECT, 20 CONFIRM, 9 from a disclosed development look) in erdos n30 p0.2 and n40 p0.15; none is in this package's adopted settings; they are the C4 settings of the DRAFT E1b-C4 package (handoff/e1b_c4). |
| `exposure_hosts_addendum_b20r63.json` | B20_R63: the 30 DEV hosts of the E1d budget-crossover study, in the dense planted E1d settings; none is in this package's settings. |
| `exposure_hosts_addendum_b20r64.json` | B20_R64: the 30 DEV hosts of the E1d scaling pilot (planted (0.8, 0.06) at n40, n50, n60; n50/n60 drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r66.json` | B20_R66: the 20 DEV hosts of the E1d n60 replication (planted (0.8, 0.06) at n60, drawn beyond the registered family space); none is in this package's settings. |
| `exposure_hosts_addendum_b20r68.json` | B20_R68: the 50 DEV hosts of the E1d domain-heuristic comparison (30 on E1d's three calibrated planted settings, 20 planted (0.8, 0.06) at n60 drawn beyond the registered family space); none is in this package's settings. |
| `package_index.json` | Identities, the calibration and the outcomes. |

The B20_R23 version of this package (builder-chosen settings, both domains) is in the git history at `e7fad0e`.

## Steps for an independent run

The steps are E1's (`handoff/e1/README.md`), with `study='e1b'` and this package's files. The causal follow-ups, if E1b is SUPPORTED, use `cli.followup_request(campaign, 'ablation' | 'placebo', ...)` with the descriptors in `interventions.json`.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for triangle-free hosts from the `e1b` calibrated settings, on that panel only, against time-matched fixed DSL baselines. It would not establish a better improver, research ability, transfer, novelty, or anything about other families.

## Power analyses for the causal follow-ups (B20_R62)

The causal power analyses of B20_R28 are bound to the `sealed_evaluation` family. The custodian assigns `ablation:triangle_free_host_v1` and `placebo:triangle_free_host_v1` and refuses any other, so a freeze must use the rebound analyses in `evidence/power_rebind_b20r62/` (both still choose 10 per stratum; `docs/STATISTICIAN_BRIEF.md`, finding 2).
