# Genesis Batch 35 — Terminal attempt ordering (DEV)
Date: 2026-10-09

## Scope
Repaired `prospective_accounting.audit` to select each arm's terminal event by the largest validated attempt number, rather than by its location in the input event array. The accounting gate already checks retry sequence continuity, duplicate attempts, post-success attempts, and per-arm budgets. This patch preserves those checks.

## Verification
`python -m unittest discover -q`: 187 tests pass (7 new regression tests). Tests cover candidate and baseline terminal states, interleaved tasks, permutation invariance for outcomes, and rejection of retry gaps and post-success retries.

## Evidence and limitations
The raw-event SHA-256 remains order-sensitive by design, while aggregate outcomes are now order-invariant. This does not establish independent evidence custody, genuine Lean proof replay, sealed dataset integrity, or a scientific claim. Promotion remains blocked.

## Next gate
Execute genuine Lean proofs with a trusted pinned toolchain and independently verify the raw receipts. Without external execution and custody, further DEV tests cannot establish scientific success.
