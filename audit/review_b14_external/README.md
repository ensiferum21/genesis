# External review of the B14 checkpoint

`GENESIS_B14_REVIEW.md` is the reviewer's report, verbatim. It confirmed the
checkpoint's integrity (archive hash, 578 manifest entries, restored commit
`30a61fc`, 576 tracked files) and ran 88 existing tests. It found one defect,
F-01, and kept GV0 open. The reviewer's local run was blocked by a missing
`networkx`; the full release matrix was not reproduced there.

## F-01: a false optimum statement survived bundle verification

- `f01_false_optimum.py` reproduces the reviewer's case with the production API.
- `logs/before_fix_30a61fc.log`: on B14, "the optimum … is 0 edges" (the true
  optimum is 3) was exported as the claim's statement, and the bundle verified.
- `logs/after_fix.log`: on the repaired tree, the exported wording is the
  supported lower bound ("has a valid subgraph with 0 edges"); the optimum
  appears only as `NOT ESTABLISHED (requested, unproved): …`.

### Repair

- The requested proposition is now kept separate from what the evidence
  establishes. `EvidenceKernel.current_wording` derives each claim's assertable
  wording from its own effective levels:
  - **Mathematical claims** (`GENERATED_FROM_PROBLEM`): lower-bound text at
    WITNESS_VALID; optimum text only at OPTIMALITY_CHECKED with matching
    checked bounds.
  - **Bound claims** (`COMMITTED_BEFORE_EVALUATION`): the committed statement,
    only while a confirmation level is effective.
  - **Free text** (`FREE_TEXT_NOT_ASSERTED`): never asserted.
  - Anything requested but not established is exported only as a marked
    conjecture.
- CLAIMS.json carries `current_statement`, `conjecture`, `statement_contract`
  and `requested_statement`. The unconditional math exemption is removed: each
  claim's current statement and scope are checked against that claim's own
  levels.
- Mathematical scope is fixed to the checked problem.
- `report.md` is generated from the per-claim wording and checked byte for
  byte. Caller prose goes to `operator_notes.md`, checked at the floor, so it
  cannot carry a claim. This closes B14-OPEN-5.
- The relational index shows current wording, never requested text as if it
  were established.

### Regressions

`tests_genesis/test_external_review_b14.py` covers the reviewer's six
acceptance cases, plus free-text and bound-claim cases.
