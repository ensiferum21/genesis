# E1b handoff package: an LP-guided construction pipeline (GV3 path), DRAFT

The builder prepared this package on 14 October 2026 (B20_R23) with `scripts/b20r23_e1b_package.py`. It is **not** registered with any custodian, and nothing here is an evaluation result.

**Status: READY_FOR_REVIEW on DEV.** The host family needs a decision before the custodian's SELECT step can run.

## The claim

E1b claims that a frozen solver beats the strongest time-matched fixed DSL baseline on a CONFIRM panel held by a custodian, by at least the minimum useful effect of 0.5 edges per host. The exact claim, per domain, is in `decision_record_DRAFT_<domain>.json`, field `exact_claim`.

The frozen solver is a `construct-pipeline-v1` descriptor:
- `{init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0, seed 0}`;
- that is, LP-ordered greedy followed by LP-perturbed restarts, with 2.0 CPU s of search;
- the profile is 4 CPU s, 2048 MiB, 20 s wall and 1000 queries, the same for every arm;
- the custodian runs it in the OCI sandbox through the trusted runner.

**It is a builder-written method** (`discovery/construct.py`, B20_RX3). A supported E1b would therefore be a scoped better-solver statement (GV3). It would say nothing about research ability (GV4).

## Evidence (DEV, builder-run, rules fixed before each run)

| Pilot | Triangle-free (C1 erdos n30 p0.3 + C2 erdos n40 p0.2) | C4 (C3 erdos n30 p0.2) |
|---|---|---|
| Readiness, `evidence/e1b_readiness_b20r23/`: candidate − strongest time-matched baseline (`low_cycle_tm`) | +1.79 per host, 18 / 6 / 0, CPU ratio 1.02; candidate at the certified optimum on 22/24; centred power: 12 per stratum (0.88). **READY_FOR_REVIEW** | +1.00, 4 / 5 / 0, ratio 0.99, 9/12 certified (at the threshold); power: 20 (0.92). **READY_FOR_REVIEW** |
| Causal readiness, `evidence/e1b_causal_readiness_b20r23/`: candidate − ablation (`random_greedy`) | +1.42, 15 / 4 / 0, power: 10 per stratum (0.99). **READY_FOR_REVIEW** | 7/10 certified. **UNSETTLED_REFERENCE** |
| Causal readiness: candidate − placebo (`lp_shuffled_greedy`) | +2.53, 19 / 0 / 0, power: 10 per stratum (0.85). **READY_FOR_REVIEW** | **UNSETTLED_REFERENCE** |

The basis is the same as E1's: B20_RX3 and RX3b (capability headroom, replicated), and B20_R14 (room to the optimum on these settings).

**Descriptor identity.** The candidate's identity binds the reviewed source files. It changed once during B20_R23, when `candidates.py` gained the placebo component. The readiness pilot ran under the earlier identity (`ac8f1fcb…` triangle-free, `74861eea…` C4). The causal pilot and this package use the current identity (`f5a3d7ff…`, `64a9890b…`), and the `lp_greedy` code path did not change between them.

## Decisions needed (before any panel exists; on design grounds only)

1. **The host family (new: B20R23-OPEN-1).** The custodian's SELECT step draws from a study calibration (`calibration.load(domain, study='e1b')`), and none exists. `e1-hard-v1` applies to E1 only, by the user's decision of 13 Oct 2026. The options are:
   - extend `e1-hard-v1` to E1b, or register a new versioned rule. Either way the rule must not read the candidate. A calibration run then selects the settings, and the pilot is repeated on them if they differ from C1–C3;
   - adopt C1/C2 (and C3) as builder-chosen settings, recorded as such, with a reviewer's approval;
   - do not proceed with E1b.
2. **C4.** Keep C4 only with a certification budget fixed in advance (120 s certified 9/12 and 7/10). Otherwise run E1b on triangle-free hosts only.
3. **Reviewer and statistician sign-off.** The same decisions as for E1: time-matched cost, the SELECT comparator, the centred power model (B19-OPEN-4), and the Holm family (family_size 3, family_id per domain).

## Contents

| File | What |
|---|---|
| `candidate_descriptor_<domain>.json` | The frozen candidate. |
| `time_matched_baselines_<domain>.json` | The three `dsl-time-matched-v1` baselines (2.0 CPU s of restarts). |
| `interventions_<domain>.json` | The registered ablation and placebo descriptors, checked with `intervention_problems`. |
| `campaign_export_<domain>.zip` | A real frozen DEV campaign (1 generation) with the candidate descriptor frozen in it. |
| `decision_record_DRAFT_<domain>.json` | The DRAFT: the B19 plan core with a per-domain family_id, and the readiness pilot's centred power analysis. A frozen copy has no structural problems (`package_index.json`). It still names an undecided family. |
| `power_analysis_centred_<domain>.json` | From the readiness pilot. |
| `exposure_hosts_all.json` | 1,084 hosts, as tasks: every graph host named in `evidence/` and `handoff/` (both E1b pilots included) plus the regenerated E1 exposure set. A custodian lists it as a `json` source in its exposure manifest. |
| `package_index.json` | Descriptor ids, the problems a frozen copy would have, the SELECT step's state (BLOCKED: no study calibration), and the pilot summaries' hashes. |

## Steps once the family is decided

1. **Builder.** Make the calibration under the decided rule, in a reviewed commit, and adopt it as study `e1b` in `configs/dev_calibration.json`. If its settings differ from C1–C3, repeat the readiness pilot on fresh hosts (the template is `scripts/b20r23_e1b_readiness.py`). Then regenerate this package.
2. **Reviewer.** Freeze the record (`decision_record.freeze`), then publish it and its hash.
3. **Independent custodian, on its own machine and with its own keys:**
   1. Run `select_comparator(..., study='e1b')`.
   2. The research operator records the signed selection in the campaign (`cli.record_comparator_selection`) and builds the v4 request (`cli.descriptor_request_bundle`).
   3. The custodian runs `register`, then `evaluate`, and publishes the registration log.
4. **Judge.** Run `judge.recompute`.
5. **Causal follow-ups, if E1b is SUPPORTED.** `cli.followup_request(campaign, 'ablation' | 'placebo', ...)` with the descriptors in `interventions_<domain>.json`. The custodian re-checks the intervention at registration, and the kernel replays it before ABLATION_SUPPORTED or PLACEBO_CONTROLLED.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for the decided family, on that panel only, against time-matched fixed DSL baselines. It would not establish a better improver, research ability, transfer, novelty, or anything about other families. The placebo used here falls below random order on DEV, so PLACEBO_CONTROLLED would show that this placebo does not reproduce the effect, not that every cost-matched procedure falls short.
