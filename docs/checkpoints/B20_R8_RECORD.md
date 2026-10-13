# B20_R8 record: replay contracts for exact, formal and DEV evidence (B14-OPEN-4, handoff s12.2)

- **Parent:** B20_R7 (commit `fc5bf4c`).
- **Run by:** the builder. Not independently reviewed.

## Problem

Before this batch, three levels could never be granted: `FINITE_CERTIFIED`, `THEOREM_CHECKED` and the DEV levels (utility `DEV_ONLY`, causality `CORRELATED`). The kernel failed closed on them because no trusted replay could re-derive them.

Handoff s12.2 asks for a contract per evidence family before promotion is enabled.

## Implementation

The contracts live in `kernel/replay_contracts.py` and are wired into `kernel/evidence.py`.

**exact_check → FINITE_CERTIFIED**

- Payload: `genesis-exact-check-v1` = {stored task, value, method}.
- The kernel re-runs the named method on the stored task. Methods form a closed set:
  - `graphs.exact_producer` (motif hitting set);
  - `graphs.exact_checker` (include/exclude branch and bound).
- A `SearchLimit` result counts as no value.
- Promotion needs two exact checks that replay, using *different methods*. Previously the rule counted distinct verifier labels.
- The claim must be the optimum of the same stored problem.
- Wording: at this level the optimum is stated with the qualifier "two exhaustive computations". The two methods are separate algorithms written by one author: independent computations, not independent institutions.

**formal_check → THEOREM_CHECKED**

- Payload: `genesis-formal-check-v1`, route `equational-custody-v1`.
- New claim form: a theorem claim, `{theorem_sha256, claim: 'theorem'}`.
  - It names a stored theorem `genesis-theorem-statement-v1`: the system, its exact pinned axioms, and the equation.
  - The statement is generated, never free text.
  - Its scope is `this equation under these axioms only`.
  - Its only math level is `THEOREM_CHECKED`.
- The kernel re-checks the custody of the proof's library and of the target record, then re-runs the Lean replay of the proof and its whole lemma chain.
- The replay route's identity is revocable like any verifier. Replays are cached per node, problem and revocation state.

**dev_comparison → DEV_ONLY, CORRELATED**

- Payload: `genesis-dev-comparison-v1` = {v2 plan, rows, result}.
- Every row must be marked `split: DEV`.
- The recorded result must equal the kernel's own `analysis.analyze` of the rows, and the decision must be SUPPORTED.
- The rows are producer data: this contract replays the analysis, not the executions.
- A DEV level never satisfies a confirmation.

**Still without a contract (fail closed):** ablation and placebo (causal), internal replication, and priority checks.

## Evidence

**`tests_genesis/test_replay_contracts.py`** (6 tests):

- **Finite certification**
  - Positive: two methods replay and the claim reaches FINITE_CERTIFIED.
  - Refused:
    - one method only, or a method name not in the closed set;
    - an inflated value;
    - a lower-bound claim;
    - a check made on another problem;
    - a host beyond the exhaustive limit.
- **DEV**
  - Positive: DEV_ONLY and CORRELATED are reached; CONFIRMED is still refused.
  - Refused:
    - a forged result;
    - non-DEV rows;
    - a result whose decision is not SUPPORTED.
- **Theorem**
  - Positive: a real lemma-using equational proof replays in Lean and reaches THEOREM_CHECKED. Its wording then asserts the equation, and finite-problem levels are refused for it.
  - Revoking the replay route lowers the claim.
  - Refused:
    - a claim about another statement;
    - an altered proof object;
    - a missing lemma proof;
    - a forged record;
    - wrong axioms.

**`tests_genesis/test_evidence_kernel.py`:** the B14 declared-verdict regression is kept for all six kinds. For the three new contracts it now asserts that a declared payload "is not replayable", in place of "has no replay contract". The guarantee itself is unchanged.

**Other suites:** the kernel, receipts, phase, custodian and red-team suites pass.

## Limitations

- Formal checks have one route, equational custody. Lean packages built on trusted statement modules (the B17 theory package, the CRPD-2a codegree package) have no route yet.
- A DEV row is not bound to its execution evidence.

## Consequence

B14-OPEN-4 is reduced to the causal, replication and priority contracts. GV2's formal evidence can now be promoted by the kernel itself, within its declared scope.
