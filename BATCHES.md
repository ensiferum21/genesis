# Engineering completion batches (P0–P2)

Branch: `completion-p0-p2`, started 2026-10-10 from commit `c2d53a9`
(the 10 October integrated DEV checkpoint, SHA-256 `73fd33a4…bbf34`).

Goal: finish the engineering scope of the Genesis specification
(ENGINEERING_COMPLETE_P0, DOMAIN_COMPLETE_P1, RESEARCH_IR_COMPLETE_P2 in §48)
plus a known-answer benchmark. Scientific labels P3–P7 need independent
operators and fresh sealed evidence; no batch here claims them.

Each batch ends with: all suites passing, a git commit, and a checkpoint ZIP
(`scripts/make_checkpoint.py`) containing the source, a git bundle, a test
report and a SHA-256 manifest. `batch_state.json` records progress, so a new
session can resume from the latest checkpoint (see `RESUME.md`).

| # | Batch | Spec | Exit test |
|---|---|---|---|
| 1 | Incremental motif checking in the solver DSL; known-answer ladder benchmark (ex(n,C4), Mantel) with preregistration and matched realized CPU | §8, §19C, §20, W05 | Old/new solver outputs identical; ladder runs end to end through bounded execution |
| 2 | Custodian builds its own cumulative exposure registry; release roles come from an externally rooted registry | GI6-10, GI6-11, §18, §45 | Both audit attacks reproduced as tests and now BLOCK |
| 3 | Legacy trust paths: reused-ID proof acceptance, pickle loading, semantic replay identity, legacy scorer retired from promotion | GI6-01/02/03/08 | Audit reproductions fail closed |
| 4 | Evidence kernel: typed effects, dependency DAG, claim promotion, transitive revocation, trust graph with CIRCULAR_JUSTIFICATION | §3.2, §4.3, §7, §26.2, §37.3 | Illegal promotion fixtures all rejected |
| 5 | Coordinator: post-freeze phases driven by verified signed receipts; crash recovery; relational tables; full SystemVersion | §2.1, §16.4, §33 | State machine reaches JUDGED/RELEASED/INVALIDATED only via valid receipts |
| 6 | Container sandbox (runc/OCI) for arbitrary generated code; executed escape suite | §17, §30, §38, §45 | Network, filesystem, credential, evaluator, resource escapes denied |
| 7 | SAT upper-bound certificates (CaDiCaL + DRAT, checked by drat-trim); harder task generator | §5.6, §8, §27 | Certified BoundState beyond exhaustive range; corrupted proofs rejected |
| 8 | Lean checker: pinned toolchain, clean environment, axiom audit, outcome classes, environment hash | §27, §37 | Generated obligations actually kernel-checked; bad proofs classified |
| 9 | Leak firewall: exact, structural and near-duplicate screening with quarantine for tasks, Lean statements, lemmas and memory | §18.2, §35, §37.3 | Known exact/alpha/near duplicates blocked |
| 10 | Research IR macros as replayable programs; research market with value-of-computation and stop rule | §4, §6, §26.3, §34 | Macros replay byte-identically from IR |
| 11 | Experiment B harness: FOF subset, finite model finder, independent model checker, prover baseline | §19.2 | PROVED / GHOST_FOUND / UNSETTLED / HARNESS_ERROR kept distinct |
| 12 | Reproducibility: environment digest, container build, CI workflow, §38 test matrix runner, §43 replication bundle | §38, §43, W07 | Matrix runner green; bundle verifies |
| 13 | End-to-end integration, smoke under 600 s, honest requirements map, final checkpoint | §31, §40, §48 | Full matrix green |

## Continuation phases (reviewer roadmap, B14 onward)

| # | Phase | Roadmap | Exit |
|---|---|---|---|
| 14 | Repair acceptance | W01–W03; R-01/R-02 regressions; certificate custody | Unsupported labels and stale exports rejected (internal red team included); independent review pending |
| 15 | Independent execution | W04, R-04 | Supported host and mandatory matrix verified on a second machine (B15 built everything checkable on one host; the second-machine run is outstanding) |
| 16 | Evaluator readiness | W05–W07 | Custody, fairness and study design independently reviewed (B16 built and tested them; the independent review is outstanding) |

Later phases (B17–B23+) follow the roadmap and its gates; numbers are labels,
not estimates.

## Never done by these batches

- Acting as the independent custodian, auditor or release authority.
- Creating sealed tasks, running sealed comparisons, or promoting any claim.
- Rewriting historical evidence. Old runs and audits stay as they are.
