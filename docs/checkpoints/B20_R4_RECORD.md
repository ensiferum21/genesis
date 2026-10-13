# B20_R4 record: H08 generation lineage in campaigns and at the custodian (B20R-OPEN-2, B14-OPEN-3)

- **Parent:** B20_R3 (commits `147d613`, `5aa9774`); this batch is commit `f5c853d`.
- **Run by:** the builder. DEV only. Nothing here has been independently reviewed.

## Problem

The B20_R2 audit (`audit/lineage_b20r/report.json`) found that the stored DEV campaign export could not
support counting generations:

- SELECT totals were not exported;
- candidates were not bound to journal attempts;
- there was no per-run research account;
- the declared component change differed from the actual change.

Both sealed lineage kinds were therefore refused.

## Implementation

**`campaign.Campaign`**

- Every attempt is ledgered to the research run in progress, whether it is new or reused from the
  journal.
- Interrupted pre-freeze attempts are charged to that run on resume.
- Each generation commits a `lineage_run` record:
  - parent version, policies and permitted panels;
  - budget, and an account recomputable from receipts;
  - the ledger;
  - both policy candidates, with their SELECT scores and trial ids;
  - the declared selection rule.
- Each generation also commits a `lineage_transition` record: declared changes with their mechanisms,
  and the decision.
- `SystemVersion.generation` is now lineage depth; the round is carried by the freeze event.

**`lineage`**

- A native export is completed from the event log: positions, unledgered attempts, and the account and
  candidate scores recomputed from receipts.
- New selection rule: `max_score_then_greatest_policy`.
- New problem codes: `BUDGET_EXCEEDED` and `CANDIDATE_ATTEMPT_MISMATCH`.

**`custodian`**

- `sealed_generation_evaluation` is accepted only when all of the following hold:
  - the transition is in the export's qualifying chain (`lineage.accepted_chain`);
  - its arms are the child and parent versions' solvers;
  - the transition changes the program.
- `sealed_improver_evaluation` stays refused. It needs two research lineages evaluated jointly.
- `cli.generation_request_bundle` freezes one request per qualifying transition.

**`deployment/EXPECTED_RESULTS.json`**

- `restored_events` changes from 335 to 339 (two lineage entities per generation of the 2-generation
  reference campaign).
- Every other reference value is unchanged, including `generations_sha256`.

## Evidence

`tests_genesis/test_campaign_lineage.py` has 16 tests:

- the native records are clean;
- forged records and attempts hidden from the ledger are found;
- a crash during research charges the interrupted attempt;
- a crash after freeze keeps a clean lineage;
- qualifying and non-qualifying transitions are distinguished;
- the improver kind is still refused;
- a generation request registers and evaluates end to end under fixture keys.

`tests_genesis/test_generation_lineage.py` was updated to the new contract.

## Limitations

- The stored B20 DEV campaign is not re-run. Its export still yields no qualifying chain.
- No sealed generation evaluation has been run on real panels.
- Recovery, rollback and retention beyond crash/resume (handoff s20.6) are not implemented.

## Consequence

GV5 has its engineering path: three compounding generations can now be evaluated transition by
transition by an independent custodian. It still needs fresh panels per transition and an independent
operator.
