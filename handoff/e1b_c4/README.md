# E1b-C4 handoff package (DRAFT): E1b's LP-guided candidate on C4 hosts, scored by the tree reference over the transferred rows (GV3 path in C4)

The builder wrote this package on 17 October 2026 (B20_R52) with `scripts/b20r52_e1b_c4_package.py`.
- It is **not registered with any custodian**, and nothing here is an evaluation result.
- **Nothing is adopted.** The rule and the reference route await a reviewer (B20R50-OPEN-1,
  B20R48-OPEN-1).

**Status: READY_FOR_REVIEW (DEV), scoped to the DSL baselines.**
- **Re-pilot (B20_R50):** READY_FOR_REVIEW in readiness and in both causal contrasts.
- **Same-operator rehearsal of the whole custody path (B20_R52):** SUPPORTED, and the judge agrees.

## Evidence card (five dimensions, never collapsed into one score)

| Dimension | Status | Evidence |
|---|---|---|
| **Validity** | Every witness is re-checked by the domain checker. Every optimum is certified by an exact branch-and-bound certificate. Its leaves are LP duals over the host's 4-cycles and over C4 pattern rows that the system generated and Lean-checked (B20_R46). The tree checker uses exact arithmetic, and each certificate is held in custody with checker-only replay (B20_R51). | B20_R46–R51; the rehearsal re-checked 40 witnesses |
| **Utility, fresh DEV hosts** | +1.17 per host [0.83, 1.50] over the strongest time-matched DSL baseline, low_cycle_tm; 22/6/2; cost ratio 0.94 | B20_R50 (`pilot_summary_b20r50.json`) |
| **Utility, rehearsal panel, same operator** | +1.15 per host [0.70, 1.65]; W/L/T 12/1/7 on 20 certified hosts; cost ratio 0.92. Comparator low_cycle_tm, selected by the custodian's SELECT | B20_R52 (`rehearsal_summary_b20r52.json`) |
| **Causal contribution** | **DEV: READY_FOR_REVIEW.** Removing the LP ordering (the registered ablation, random_greedy) costs +1.43 per host [1.20, 1.63], 24/6/0. Permuting the LP values (the registered placebo, lp_shuffled_greedy) costs +2.73 per host [2.30, 3.17], 25/5/0. As on triangle-free (B20_R28), the LP signal is the active ingredient. Licensing a causal level needs custodian-signed follow-up evaluations | B20_R50 |
| **Strong baselines** | **An exact C4 MIP dominates.** HiGHS over the 4-cycle rows at 2 s is optimal on 30/30 pilot hosts and 0.93 per host above the candidate (0/11/19). The claim is therefore scoped to time-matched DSL baselines, as for E1b on triangle-free (B20R33-OPEN-1) | B20_R50 (descriptive) |
| **Improver capability, novelty, replication** | None claimed. The candidate is a builder-written method. There is no independent replication | n/a |

## The claim

The exact wording is in `decision_record_DRAFT.json`, field `exact_claim`. In short: E1b's frozen
parameters, as a construct-pipeline-v1 descriptor for c4_host_v2, score more edges than the strongest
time-matched fixed DSL baseline, by at least 0.5 edges per host.
- **Panel:** a custodian-held CONFIRM panel from the two settings that the DRAFT rule
  `e1-hard-v2-c4tree-draft` calibrated candidate-blind: erdos n40 p0.15 and erdos n30 p0.2.
- **Comparator:** selected by the custodian.
- **Reference:** optima certified by the tree reference (`reference_route.json`: route
  `generated-rows-tree-c4-v1`, B20_R46's package, 600 s).

## Why this package exists

C4 was the domain where E1b could not be scored:
- no e1-hard-v2 setting was eligible (B20_R24);
- the causal pilot was UNSETTLED_REFERENCE (B20_R23).

The rows that made it scorable were invented by the system's own procedure in the triangle-free
domain, transferred to C4, and checked in Lean (B20_R46). Their certification utility is preregistered
and causally attributed (B20_R48, R49).

## Files

| File | What it is |
|---|---|
| `candidate_descriptor.json` | construct-pipeline-v1 for c4_host_v2 with E1b's frozen parameters (B20_R23/R50's descriptor) |
| `baselines.json` | the three time-matched DSL baselines under the same profile |
| `campaign_export.zip` | a fresh frozen DEV campaign with the candidate frozen in it (no selection recorded) |
| `decision_record_DRAFT.json` | the DRAFT decision record (frozen, it has no problems) |
| `reference_route.json` | the v5 reference route |
| `pilot_summary_b20r50.json`, `power_analysis_centred_*_b20r50.json` | B20_R50's re-pilot and power analyses |
| `rehearsal_summary_b20r52.json` | the same-operator rehearsal (SUPPORTED, judge agrees) |
| `exposure_hosts_all_part_01..06.json` | every host the builder named, 2,957 in all, in files of at most 500 |
| `package_index.json` | index and identities |

## What a real run needs

1. **Rule.** A reviewer adopts the DRAFT rule `e1-hard-v2-c4tree-draft` (B20R50-OPEN-1).
2. **Reference.** A reviewer adopts the tree route as a c4_host_v2 reference, with its custody
   (B20R48-OPEN-1; `docs/GENERATED_ROWS_REFERENCE.md`).
3. **Strong baselines.** A reviewer decides B20R33-OPEN-1, the scope of "strong baselines", given
   that the exact MIP dominates here.
4. **People.** A statistician, and an independent custodian on its own machine.
