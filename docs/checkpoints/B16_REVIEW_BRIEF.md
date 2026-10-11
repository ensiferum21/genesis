# B16 review brief: custody, fairness and study design

The B16 phase exit is "custody, fairness and study design independently reviewed".
This brief names what to check and how to reproduce it. The builder wrote it, so it
is a map, not evidence. Every statement below should be checked against the code.

## Setup

```
unzip GENESIS_COMPLETION_CHECKPOINT_B16.zip -d b16 && cd b16/genesis
export PYTHONPATH=src PYTHONPYCACHEPREFIX=$(mktemp -d)
python3 -m unittest tests_genesis.test_domain_adapters tests_genesis.test_calibration \
  tests_genesis.test_analysis_v2 tests_genesis.test_evaluator_readiness \
  tests_genesis.test_resources tests_genesis.test_redteam_b16
```

The full matrix is `scripts/run_test_matrix.py --profile release`. To rehearse in a
clean room, run `deployment/reproduce.sh`.

## 1. Custody (W06)

| Question | Where to look |
|---|---|
| Can a requester escape multiplicity by naming its own hypothesis family? | `custody_records.custodian_family`, `registration_problems`; `test_redteam_b16.R1FamilyShopping` |
| Can a family exceed its declared size, or be re-declared with another size? | `registration_problems`; `test_evaluator_readiness.CustodianV2Flow` |
| Is an evaluation that never reported visible to everyone? | `family_state(...)['outstanding']`; `R5LegacyFamilies` |
| Does Holm use exactly the family results published before each evaluation, and does publication refuse if they changed meanwhile? | `custodian._publish`, `published_p_values_before`, `receipt_log_problems` |
| Is a rewritten log detected even when re-signed with the custodian key? | `chain_problems`; `R1FamilyShopping.test_r3_*` |
| Does the release preflight require the log and signed control declarations, and does it limit a claim when roles share control? | `custodian.release_preflight`, `custody_records.independence`; `ReleasePreflightV3` |

Known limits. These are not repaired, and the reviewer decides whether they are acceptable:

- **Scope is one custodian.** A researcher who uses several custodians is outside the family.
- **B16-OPEN-1.** There is no external time anchoring. The order of registration and
  publication is attested by the operator.
- **Same-operator custody.** Every role in this repository is a fixture key under
  one operator. A real deployment needs an independent custodian, auditor and
  release authority, and their control declarations.

## 2. Fairness (W05, W07)

| Question | Where to look |
|---|---|
| Does a candidate see anything beyond (domain, n, edges)? | `models.CandidateGraph`, `execution.execute`, `domains.*.candidate_view`; `test_domain_adapters` |
| Do both arms get the same tasks, limits and seed, exactly once each? | `resources.arm_fairness`; the judge reports it (`judge.recompute`) |
| Is ground truth kept off both arms' budgets, and is every attempt charged, including failures and interruptions? | `resources.account`; `test_resources` |
| Is the comparator the strongest fixed baseline, chosen without CONFIRM data? | `custodian.check_request_against_export` (the campaign's strongest conventional baseline, from DEV runs) |
| Are unsupported tasks explicit, and bounded by the plan? | `domains.Unsupported`, `analysis.analyze` (`max_unsupported_fraction`) |

Known limits:

- Human time is only declared, never measured.
- No model is used, so there is no model-call budget to compare.
- Cost is compared on CPU time only.

## 3. Study design (W07)

Read `evidence/study_design_b16/STUDY_DESIGN.md`. It ends with four questions:

1. Is the minimum useful effect meaningful?
2. Is the design effect a reasonable assumption?
3. Is the multiplicity scope right?
4. Are the floor, exclusion and cost rules acceptable?

Also check:

- **The analysis.** `kernel/analysis.py` should match the plan:
  - the exact or Monte Carlo sign-flip test;
  - a bootstrap interval at level 1 − 2α;
  - Holm with members that have not reported counted as p = 1;
  - the single-analysis rule.

  The kernel should reject a receipt whose recorded result does not re-derive
  (`decision_from_result`).
- **The judge.** `judge.recompute` rebuilds the store from its append-only export.
  It should refuse evidence that does not end at the signed root, recompute every
  analysis field and the resource account, and compare them with the signed values.
- **The power model.** The power model (`genesis.power`, B16-OPEN-2) is an
  assumption, so check whether its effect model and design floor are acceptable.
- **The calibration.** `genesis.calibration` used only DEV material, and the
  selection rule was fixed before any run. Every setting tried is recorded in
  `evidence/dev_calibration_b16/`.

## What B16 does not claim

- No sealed task exists and no candidate is frozen.
- The decision record is a DRAFT.
- No claim was promoted.
- R-04 and GV0 stay open.
