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
| 17 | Formal research | W08, first TheoryPackage path | Real generated reusable Lean artifacts replay (B17: replayed by the builder from the package sources; independent replay outstanding) |
| 18 | Concept invention | W09–W12 | Typed concepts, explicit worlds and checked semantics (B18: built and replayed by the builder on DEV; independent review outstanding) |
| 19 | Useful discovery | W13–W17; E1/E2 readiness | Prospective usefulness accepted or branch rejected (B19: DEV evidence for W13–W15, W16 decided on DEV, W17 records, E1/E2 drafts; acceptance needs independent review and a custodian) |
| 20 | Learned research | W18–W20; E3 | Better-improver claim supported or explicitly unestablished (B20: explicitly UNESTABLISHED on DEV; macros, policies, memory and curriculum built and tested) |
| 20_R1 | Review repairs | B20-REVIEW-01..04 (handoff H01–H03) | Findings reproduced from stored evidence; global partition, budget authority, successor proof custody and obstruction certificate custody repaired with regressions; custody-complete re-run (B20_R1: builder-run, independent review outstanding; B20 comparison stays contaminated) |
| 20_R2 | CRPD subset, H02 exit, H05/H08 parts | CRPD-1..3; H02; H05/H08 (handoff) | Soundness modes; Lean-checked codegree (first EQ abstraction); orbit probe NOT_DETECTED; fresh DEV E3 on the repaired harness: learned vs fixed 0W/2T/6L with all runs within cap; lineage validator (stored campaign export yields no qualifying chain); trusted candidate runner (not wired). Builder-run, DEV only |
| 20_R3 | Redesigned research policy, new frozen DEV study | B20R-OPEN-1 (handoff H07, moved first) | Headroom pilot: ORACLE − fixed ≤ 1/12 on six systems; cost-aware policy INFERIOR_DEV (2W/3T/3L), material NOT_DISCRIMINATING; libraries are not monotone for E (one true lemma: 7/8 → 0/8); Lean 153/208 CHECKED, failures traced to tactic-cascade steps. Builder-run, DEV only |
| 20_R4 | Generation lineage in campaigns | H08; B20R-OPEN-2, B14-OPEN-3 | Campaigns write native lineage records (ledgered attempts, recomputable accounts, scored candidates, declared changes); custodian accepts generation requests only for qualifying transitions; improver kind still refused. Builder-run |
| 20_R5 | Executable candidates through the custodian | H05; B19-OPEN-3, B20R-OPEN-4 | Request v4 / receipt v4 / claim binding v2; descriptors rebuilt from the frozen export; every arm in the OCI sandbox; judge re-checks every witness; s13.3 acceptance list end to end (21 tests). Builder-run, fixture keys |
| 20_R6 | Family search for selection headroom | B20R3-OPEN-1 | Robbins' basis (floor) and Boolean rings (near ceiling) both NO_HEADROOM; lemma interference replicated (34 lemmas 11/12 vs 132 lemmas 8/12). DEV design diagnostic |
| 20_R7 | Sealed statement panels, formal successors through the custodian | H05; B20R5-OPEN-1 | Custodian-side panel generation after freeze from a private seed with full screening; frozen research exports; kind formal-research-successor-v1 in the sandbox; Lean replay of every claim by custodian and judge; 12 tests. Builder-run, fixture keys |
| 20_R8 | Replay contracts | B14-OPEN-4 (handoff s12.2) | Kernel-replayed exact checks (FINITE_CERTIFIED, two methods), theorem claims with Lean replay from equational custody (THEOREM_CHECKED) and DEV analysis recomputation (DEV_ONLY, CORRELATED); causal, replication and priority still fail closed; 6 tests. Builder-run |
| 20_R9 | Library curation pilot | B20R3-OPEN-1/2 | Curating which lemmas to keep: NO_CURATION_HEADROOM on four variants (at most +1/12); across B20_R3/R6/R9 no research-policy dimension reaches 2/12 on the equational domain. DEV design diagnostic |
| 20_R10 | Small open items | B20R7-OPEN-1/2, B20R3-OPEN-3 | Custodian statement screen for research (signed, fails closed); checker CPU metered; error lines kept in checker logs |
| 20_R11 | E1 readiness through the custodian runner | GV3 path; B19-OPEN-3/4 | E1 effect replicates under equal sandbox metering (+1.33/task, 24W/5T/1L) but the DRAFT cost rule fails (CPU ratio 3.38 > 3.0); handoff/e1 package; same-operator rehearsal end to end (NOT_SUPPORTED on cost, judge agrees). Builder-run, fixture keys |
| 20_R12–R24, RX1–RX5 | Recorded in `NEXT_ACTIONS.md` and `docs/checkpoints/` | — | — |
| 20_R25 | Lean replay hint generator v2 | B21 side-branch port; W16 | Wolfram-axiom chains 0/19 → 19/19 on identical proof objects; no regression on Sheffer (11/11) |
| 20_R26 | Quotient representations | s15.3 / W10 (GV4) | Parametric Lean transport theorem CHECKED; DEV NO_UTILITY_AFTER_COST (attempt 1) |
| 20_R27 | Decompositions | s15.3 / W10 (GV4) | Lean composition theorem CHECKED; DEV NO_UTILITY_AFTER_COST, −2.53 vs the same components on the whole host (attempt 1) |
| 20_R28 | E1b causal re-pilot on the e1b family | GV3 path | Ablation +1.25 and placebo +2.61, both READY_FOR_REVIEW; handoff exposure addenda |
| 20_R29 | Second-machine reference repaired | R-04 driver; found by the B20_R28 rehearsal | `restored_events` 339 → 345 (B20_R16 drift, bisected); drift test in the matrix |
| 20_R30 | Certification at 60 s and at 600 s | B20R24-OPEN-2 (GV3 path) | 90 fresh e1b hosts: 86/90 at 60 s, 90/90 at 600 s; LIMITS_CONSISTENT (upper bound 3.27%); decision stays with the reviewer |

Later phases (B17–B23+) follow the roadmap and its gates; numbers are labels,
not estimates.

## Never done by these batches

- Acting as the independent custodian, auditor or release authority.
- Creating sealed tasks, running sealed comparisons, or promoting any claim.
- Rewriting historical evidence. Old runs and audits stay as they are.
