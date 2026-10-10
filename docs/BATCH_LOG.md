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
