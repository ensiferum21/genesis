# Completion batch log

## Batch 1 — solver speed, store scaling, known-answer ladder
- `dsl.solve` checks only motifs containing newly added edges. Output-identical
  to the frozen v1 interpreter (600 random cases + complete hosts); ~8x faster.
- `Store.recover_export` appends only new events. Before: write cost grew with
  history (2.9 s → 10.7 s per 250 attempts over 2,000 events). After: flat
  (~1.7 s). Full prefix checks still run on open, in `verify()` and on export.
- `genesis benchmark ladder`: preregistered known-answer ladder on complete
  hosts (OEIS A006855 for C4-free, Mantel for triangle-free), equal realized-CPU
  budgets, every invocation bounded and charged, frontier rungs (n = 41–49)
  classified without discovery claims. Transcribed A006855 values are
  cross-checked against the dual exact solvers for n ≤ 7.
- Pinned toolchain: Lean 4.34.1, CaDiCaL 3.0.1, drat-trim, E 3.5.1, zstd.

## Batch 2 — custodian trust holes (GI6-10, GI6-11)
See `docs/AUDIT_REMEDIATION.md` (GI6 section).

## Batch 3 — legacy trust paths (GI6-01/02/03/08)
- The current tree already carries the REV18 fixes for reused lemma IDs and
  pickle loading; the vulnerable code is in the old accepted archive. New
  tests reproduce each audit attack against this tree and fail closed.
- `eligibility.py`: only registered routes can feed confirmation-level claims.
  Legacy `gap_engine`, `legacy_batch42`, `custody_reference`, public campaigns
  and the ladder are ineligible; the accepted-base archive hash is revoked.

## Batch 4 — evidence kernel
- `genesis/kernel/evidence.py`: immutable evidence DAG; typed effects (unknown
  names refused); speculative taint resolved only by passing checks;
  promotion per axis requires the right kinds of checked artifacts (two
  distinct exact checkers for FINITE_CERTIFIED, gap-0 BoundState for
  OPTIMALITY_CHECKED, externally signed sealed evaluations for any
  confirmation); contamination, approximation, self-judgement and manual
  rescue block the levels they must; transitive revocation invalidates
  dependent claims; trust graph labels self- or mutually-validated verifiers
  CIRCULAR_JUSTIFICATION.
- `genesis/kernel/wording.py`: report linter for §21.2 forbidden
  transformations; campaign and ladder reports must pass it to be written.
- `genesis/kernel/signing.py`; architecture boundary test (kernel imports no
  research/campaign/DSL/IR code).
