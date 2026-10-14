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

**Causal follow-ups on this family (B20_R25, `evidence/e1b_causal_b20r25/`).** The re-pilot on 30 fresh `e1b` hosts gives:
- ablation (`random_greedy`): +1.80 per host, 27 / 3 / 0, power 0.996 at 30 hosts, **READY_FOR_REVIEW**;
- placebo (`lp_shuffled_greedy`): +3.70 per host, 28 / 2 / 0, power 0.865 at 36 hosts, **READY_FOR_REVIEW**.

A same-operator rehearsal of the whole causal path, with fixture keys, then ran in one campaign:
- the custodian's SELECT chose `multistart_tm`;
- the main evaluation was **SUPPORTED** (30 / 0 / 0, 3.03);
- the ablation follow-up was **SUPPORTED** (28 / 0 / 2, 1.97);
- the placebo follow-up was **SUPPORTED** (35 / 0 / 1, 3.19);
- the judge agreed on all three.

The evidence kernel, under a FIXTURE registry, promoted the claim to utility CONFIRMED_SAME_DOMAIN and causality PLACEBO_CONTROLLED. Fixture grants never reach a release path. The follow-up DRAFTs are `decision_record_DRAFT_ablation.json` and `decision_record_DRAFT_placebo.json`.

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json`, `time_matched_baselines.json` | The frozen candidate and its three baselines (2.0 CPU s each). |
| `interventions.json` | The registered ablation (`random_greedy`) and placebo (`lp_shuffled_greedy`), checked with `intervention_problems`. |
| `campaign_export.zip` | A fresh frozen DEV campaign with the candidate frozen in it. |
| `decision_record_DRAFT.json` | Names the `e1b` calibration and the re-pilot's power analysis. A frozen copy has no structural problems. |
| `power_analysis_centred_b20r24.json`, `pilot_summary_b20r24.json`, `rehearsal_summary_b20r24.json` | The re-pilot and both rehearsals. |
| `decision_record_DRAFT_ablation.json`, `decision_record_DRAFT_placebo.json`, `power_analysis_centred_<contrast>_b20r25.json` | The causal follow-ups (B20_R25). |
| `exposure_hosts_part_NN.json`, `exposure_sources.json` | Every host the builder named or generated, as of B20_R25 (1,760), in files of at most 400 hosts, with a manifest fragment. |
| `package_index.json` | Identities, the calibration and the outcomes. |

The B20_R23 version of this package (builder-chosen settings, both domains) is in the git history at `e7fad0e`.

## Steps for an independent run

The steps are E1's (`handoff/e1/README.md`), with `study='e1b'` and this package's files. The causal follow-ups, if E1b is SUPPORTED, use `cli.followup_request(campaign, 'ablation' | 'placebo', ...)` with the descriptors in `interventions.json`.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for triangle-free hosts from the `e1b` calibrated settings, on that panel only, against time-matched fixed DSL baselines. It would not establish a better improver, research ability, transfer, novelty, or anything about other families.
