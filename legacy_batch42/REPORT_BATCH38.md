# Genesis Batch 38 — C4 exact solver vs multistart greedy (DEV)

## Implemented
- Reproducible public development graph suite (24 instances, 5–7 vertices, at most 20 edges).
- Stronger multistart greedy baseline: one deterministic order plus 32 independently shuffled orders per case.
- Exact branch-and-bound candidate checked against a separate minimum C4 cycle-hitting-set recurrence.
- Reproducible per-case baseline randomization, result suite hash, per-case optimum and search costs.
- Twelve regression tests; 225 cumulative tests passing.

## Observed development results
See `C4_DEV_BENCHMARK_RESULTS.json` for the full per-case record. All exact optima agree with the independent algorithm. This is **not** a sealed prospective experiment: generator, benchmark, and evaluation code are research-visible, and candidate uses more computation than the greedy baseline. Results therefore cannot support a fair efficiency claim or a new mathematics claim.

## Remaining blockers
- Matched compute budgets, preregistered sealed external graph tasks, independent custody, real Lean proof checking, and independent replication.
- The current exact solver is limited to 20 host edges and does not support general n<=63 optimization.
- No discovery of new theorem, no learned research policy, no multigeneration self-improvement.
