# E1 handoff package: represent-and-repair (cross_2) on triangle-free hosts (GV3 path)

This package was prepared by the builder on 13 October 2026 (B20_R11). It is **not** registered with any custodian. Nothing here is an evaluation result. The rehearsal in `evidence/e1_readiness_b20r11/` was run by the same operator with fixture keys, so it licenses nothing.

## What is being tested

The B19 E1 claim is in `decision_record_DRAFT.json`, field `exact_claim`. It says that a frozen solver beats the strongest frozen fixed baseline on a CONFIRM panel held by a custodian, by at least the minimum useful effect of 0.5 edges per task.

The frozen solver is B18's represent-and-repair solver: the cut representation `cross_2`, greedy triangle-free repair, and 0.5 CPU seconds inside the solver.

## Contents

| File | What |
|---|---|
| `candidate_descriptor.json` | The candidate, as a `represent-and-repair-v1` descriptor. Its implementation digests are bound into the descriptor identity. |
| `campaign_export.zip` | A real frozen triangle-free campaign export, with the descriptor frozen in it (write-once). It is bound to the code identity of the commit that made it (see `readiness.json`). |
| `decision_record_DRAFT.json` | The B19 DRAFT decision record. It is unchanged and not frozen. |
| `b19_*.json` | The B19 pilot rows, its summary and both power analyses: the B16 model (INFEASIBLE) and the centred model (n = 25). |
| `exposure_hosts_to_exclude.json` | Every host the builder generated for E1 (B19 pilot, B20_R11 pilot and rehearsal). The custodian must exclude them. |

## Decisions a reviewer must make before anything is frozen

These are design choices. Each must be decided on design grounds, recorded, and fixed before any sealed panel exists. None may be set to whatever value produces a stronger label.

**1. Power model (B19-OPEN-4).**
- The B16 model reports INFEASIBLE.
- The centred-headroom correction gives 25 tasks: power 0.83 at the design effect and 0.23 at the minimum useful effect.

**2. Cost rule (new, B20R11-OPEN-1).** Under the custodian's equal sandbox metering (B20_R5), the candidate uses about 3.4 times the strongest baseline's CPU. Each arm costs about 0.21 s of interpreter start-up; the candidate adds its 0.5 s search. The DRAFT plan's `cost.max_ratio` is 3.0, so under the DRAFT every outcome is NOT_SUPPORTED, whatever the effect:

| Run | Opponent | Effect per task | CPU ratio | Result under the DRAFT |
|---|---|---|---|---|
| DEV pilot (30 hosts) | `low_cycle` | +1.33 | 3.38 | cost check fails |
| Rehearsal | `multistart` | +3.04 | 3.43 | NOT_SUPPORTED |

Options:
- time-matched baselines that receive the same CPU budget (for example restarts until the budget is spent);
- a smaller candidate budget;
- a different cost contract.

The choice, and the reason for it, belongs in the frozen record.

**3. Comparator (new, B20R11-OPEN-2).**
- The DRAFT names "the strongest fixed DSL baseline on the SELECT panel".
- The custodian currently requires the campaign's own strongest conventional baseline, which is recorded by the campaign's DEV panels. For this export that is `multistart`; the 30-host pilot's strongest is `low_cycle`.
- The reviewer fixes the rule, and the request and the custodian check must agree with it.

## Steps once the decisions are made

1. **Regenerate the package at the accepted commit.** The campaign export and the custodian check the evaluator's code identity, so the package must be rebuilt with the reviewed code:

       export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
       python3 scripts/b20r11_e1_readiness.py OUT_DIR

   If the reviewer changes the candidate budget or the comparator rule, the script and this README change first, in a reviewed commit.
2. **Reviewer:** amend the DRAFT with the decisions above, then freeze it with `genesis.decision_record.freeze(record)`. Publish the frozen record and its hash.
3. **Research operator:** build the v4 request with the frozen plan:
   - `cli.descriptor_request_bundle(campaign, task_count, analysis=plan_with_decision_record_hash)`;
   - the campaign is restored from the export with `store.rebuild_from_export`;
   - the request binds the export by hash.
4. **Independent custodian, on its own machine and with its own keys:**
   1. Build an exposure manifest covering every DEV panel named in the B16–B20 evidence, plus `exposure_hosts_to_exclude.json`.
   2. Draw a CONFIRM panel from the adopted triangle-free calibration with a private seed.
   3. Run `custodian.register(...)` with the frozen decision record.
   4. Run `custodian.evaluate(...)`, which uses the sandbox. Both arms run under one resource profile; the judge re-checks every witness.
   5. Publish the signed registration log.
5. **Judge and auditor:** run `judge.recompute` from the custodian's raw evidence, then `custodian.release_preflight` with the externally pinned trust root and control declarations.

## What a SUPPORTED outcome would and would not mean

It would support a scoped better-solver statement for triangle-free hosts from the calibrated family, on that panel only. Per the DRAFT's `allowed_conclusion`, it would not establish a better improver, transfer, or novelty.
