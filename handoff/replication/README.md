# Replication handoff package (W24; E6; gates GV7 and replication levels)

Prepared by the builder on 13 Oct 2026 (B20_R21). **Blocked.** There is no SUPPORTED sealed evaluation to replicate yet, and no independent operator. This package says exactly what an internal replicator or an external reproducer does once both exist. It is not evidence of anything.

## What the kernel accepts

| Level | Evidence kind | Signed by (registry v2 role) | The kernel also requires |
|---|---|---|---|
| replication INTERNAL_INDEPENDENT | `internal_replication` | `internal_replicator_key` | It repeats a supporting `sealed_evaluation` of the same claim: the same arms (candidate and baseline identities), the same analysis plan up to the family id the custodian assigns and the decision record each registration names, the same domain. It runs on another panel, under another operator identity, and is registered after the original completed. |
| replication EXTERNAL_REPRODUCTION | `external_reproduction` | `replicator_key` | The same repetition rule (B20_R21). It is a confirmation level, so the claim binding, eligible routes and sources, and unrevoked keys and evaluations all apply as for any confirmation. |

Distinct keys and operator identities are what code can check. Whether the people and machines are independent is for the release authority to judge. The registry must pin each role to a key that no other role uses (`kernel.roles`).

## Steps (once a sealed evaluation of claim C is SUPPORTED)

1. **Research operator.** Build the repetition request from the campaign's frozen request, with the replicator's own plan. The plan is identical except for `multiplicity.family_id`, which is `internal_replication:<domain>` or `external_reproduction:<domain>`, and the decision record it names:

       from genesis.cli import followup_request
       req = followup_request(campaign, 'external_reproduction', analysis=plan, task_count=n, seed=<new seed>)

   The request keeps the claim id, statement, scope, candidate and export binding. Hand it over together with the campaign export (`exports/campaign_export.zip`).

2. **Replicator, on its own machine, with its own keys and custodian store:**
   1. Build an exposure manifest that lists every DEV panel named in the evidence and every host the original custodian published. Include its registration log, and for E1 also `handoff/e1/exposure_hosts_all.json`.
   2. Draw a fresh CONFIRM pool from the same calibration with a private seed.
   3. Freeze the decision record (`decision_record.freeze`) and publish its hash.
   4. Register:

          register(root, req, prereg_key, '<operator id>', exposure_manifest=..., campaign_export=...,
                   pool=..., decision_record=frozen, accepted_selection_keys=[<original custodian public key>])

      `accepted_selection_keys` is needed only when the original used a custodian-selected comparator. The replicator then accepts that signed selection under the original custodian's registry key, and only for repetition kinds.
   5. Evaluate (`evaluate(...)`) with the key the registry pins for the role (`replicator_key` or `internal_replicator_key`), then publish the registration log.

3. **Judge.** Run `judge.recompute` on the replicator's raw evidence.

4. **Research operator.** Record both receipts (`kernel.record_signed`). Bind the claim to both requests (`receipts.binding_from_requests([original, repetition])`), then promote `replication`.

## Not supported, on purpose

- **A repetition by the same operator identity, on the same panel, or registered before the original completed.** Refused.
- **A repetition with another analysis.** Refused, unless the only differences are the custodian-assigned family id and the decision record.
- **A repetition that "replicates" a NOT_SUPPORTED or INCONCLUSIVE original.** There is nothing supporting to repeat.

## Tests

- `tests_genesis/test_b14_open4_contracts.py::Replication`: internal replication.
- `tests_genesis/test_b14_open4_contracts.py::ExternalReproduction`: external reproduction, with the original repeated, reproduction alone, same operator, and another plan.
- `tests_genesis/test_candidate_custody.py::CausalAndReplicationCustody`: the selection-key rule at registration.
