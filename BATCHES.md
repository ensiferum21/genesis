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
| 20_R31 | Generated valid inequalities | s15.3 / W10 (GV4) | K5 and W5 bounds Lean-CHECKED; DEV NO_UTILITY_AFTER_COST in construction (+0.19 vs the plain LP greedy); certification diagnostic 72 → 82 of 90 LP-floor certifiable (attempt 1) |
| 20_R32 | Exact certification over generated rows | W13, s15.3 (GV4); GV3 path | Sound; NO_CERTIFICATION_UTILITY on a fresh sample (2 of its 3 SAT-needing hosts closed; McNemar p 0.25); post-hoc MILP cross-check confirms all SAT-certified optima and raises a strong-baseline question |
| 20_R33 | Strong-baseline audit of E1/E1b | GV3 path (B20R32-OPEN-2) | Exact MIP proves every optimum ≤ 0.36 CPU s; E1 MIP_DOMINATES (+0.75), E1b NO_MATERIAL_DIFFERENCE (+0.20); both +~2 over DSL baselines |
| 20_R34 | MIP-hard certifiable settings probe | GV3 path (B20R33-OPEN-1) | NO_MIP_HARD_CERTIFIABLE_SETTING: where the evaluator certifies, the MIP is optimal; dense planted regime uncertifiable (candidate beats MIP incumbent there, exploratory); resume defect repaired in the record |
| 20_R35 | Generated-row certification, enriched | W13, s15.3 (GV4); GV3 path | CERTIFICATION_UTILITY: 27/40 vs 7/40 certified at 60 s, McNemar p ≈ 1e-6, +18.5 s saved per host; sound |
| 20_R36 | K5 rows for construction, dense regime | s15.3 / W10 (GV4) | NO_UTILITY_AFTER_COST: +3.94 vs plain LP greedy, +4.31 vs MIP, −2.97 vs menu `cross_2` (attempt 2) |
| 20_R37 | Generator v2 (≤ 7 vertices) | s15.3 / W10, W13 | 9 patterns, 12 obligations Lean-CHECKED (K7, K7−e with a hoisted heartbeat option); NO_COVERAGE_GAIN at 60 s (33 vs 30 of 40); dense planted 19/20 |
| 20_R38 | Frozen E1/E1b vs exact MIP, dense regime | GV3 path (B20R33-OPEN-1) | E1 optimal 19/20 per setting; +14.6 vs HiGHS at 4× budget on planted; E1b beyond MIP on planted, dominated on erdos; all 40 hosts certified by generated rows |
| 20_R39 | Custody for generated-row certificates; generated-rows reference | W03, W13; B20R35-OPEN-1 | Built and tested, not wired; adoption steps documented for a reviewer |
| 20_R40 | Candidate registry v2; exact-MIP baseline kind | W06; NEXT_ACTIONS item 2; GV3 comparator | Built and tested, not wired; frozen E1/E1b descriptors unchanged |
| 20_R41 | E1d readiness: DRAFT dense rule, candidate-blind calibration, re-pilot vs exact MIP | GV3 path (B20R33-OPEN-1, B20R41-OPEN-1) | 3 planted settings selected; 30/30 certified; comparator HiGHS at 4× budget; candidate optimal 30/30, +10.6 [9.1, 12.1]; READY_FOR_REVIEW |
| 20_R42 | Registry v2 and the generated-rows reference wired into the custodian path, opt-in (request v5) | W06, W03; B20R40-OPEN-1, B20R35-OPEN-1 | Built and tested (11 new tests; full tests_genesis passes); v3/v4 requests, receipts, adopted rules and frozen ids unchanged; not adopted |
| 20_R43 | E1d DRAFT package; same-operator rehearsal through the v5 path | GV3 path (B20R41-OPEN-1) | Custodian SELECT chose HiGHS at 4x budget; 240-host CONFIRM, 237 certified; W/L/T 198/0/39, +9.80 [9.30, 10.35], cost ratio 0.34: **SUPPORTED**, judge agrees; package `handoff/e1d` |
| 20_R44 | Registered ablation of E1's discovered representation (cross_2 -> ordered_2, Lean-weaker decoder); E1d ablation re-pilot with a Lean-certified null control | GV3 path, causal control (B20R41-OPEN-1, B20R44-OPEN-1) | Candidate − ablation +7.07 [6.47, 7.70], 30/0/0, cost ratio 1.00: **READY_FOR_REVIEW** (45 hosts for power 0.86); null control (adjacent_2, Lean-equal) +0.03: NULL_CONTROL_CLEAN |
| 20_R45 | Same-operator rehearsal of the E1d ablation evaluation through the v5 path | GV3 path, causal control (B20R41-OPEN-1) | v5 ablation request, custodian re-checked the intervention; 45-host CONFIRM, 44 certified; 44/0/0, +6.64 [6.03, 7.29], cost ratio 1.00: **SUPPORTED**, judge agrees |
| 20_R46 | The row-invention procedure transferred to C4-free subgraphs: generator, Lean obligations, recipes | GV6 path, transfer (B20R46-OPEN-1) | 34 patterns kept from 201 graphs on 4–6 vertices (K6: 4-cycle LP 11.25 → 7.5, ex 7); **37/37 obligations Lean-CHECKED** (34 bounds by integer rounding certificates); procedural transfer only, utility is B20_R47 |
| 20_R47 | Exact checker and route for generated C4 rows; preregistered C4 certification-coverage study | GV6 path, transfer utility (B20R46-OPEN-1, B20R47-OPEN-1) | 40 fresh C4 hosts at 60 s: certified 22 vs 22, no discordant host (McNemar p 1.0): **NO_CERTIFICATION_UTILITY**; the rows are sound, close 80% of the LP gap, certify 10 hosts by LP alone and save 2.24 s per host [0.23, 4.74]; diagnostics: the open gap is global, a certified branch-and-bound prototype closes 10 of 13 open hosts (B20_R48) |
| 20_R48 | Certified branch and bound over the transferred C4 rows (exact tree checker); preregistered coverage study | GV6 path, transfer utility (B20R48-OPEN-1) | 40 fresh C4 hosts at 60 s: tree route 38 vs evaluator 26, 12/0 discordant, McNemar p 0.00024, wall saving +27.8 s [20.7, 35.6], every certificate VALID: **CERTIFICATION_UTILITY**; both settings meet the 90% calibration limit under the tree route (n36: 90% vs 35%) |
| 20_R49 | Registered ablation of the transferred rows in the tree route (empty registry: 4-cycle rows only) | GV6 path, attribution (B20R46-OPEN-1, B20R48-OPEN-1) | 40 fresh C4 hosts at 60 s: with the rows 36, without 24, 12/0 discordant, McNemar p 0.00024, 14x fewer nodes, +19.6 s per host: **ROWS_RESPONSIBLE** |
| 20_R50 | E1b's C4 arm under a DRAFT rule whose reference is the tree route: calibration and readiness/causal re-pilot | GV3 path in C4 (B20R50-OPEN-1, B20R48-OPEN-1) | Calibration selects erdos n40 p0.15 and n30 p0.2 (8/8 certified each; the first eligible C4 settings); 30-host re-pilot all certified: readiness +1.17, ablation +1.43, placebo +2.73, all **READY_FOR_REVIEW**; exact C4 MIP at 2 s optimal 30/30, E1b −0.93 below it (MIP dominates) |
| 20_R51 | C4 tree route wired as an opt-in v5 reference with custody (`certificates_tree_c4`, route `generated-rows-tree-c4-v1`, adapter `ROWS_ROUTES`, DRAFT C4 rule listed) | W03, W06; B20R48-OPEN-1, B20R50-OPEN-1 | Built and tested (9 new tests; full tests_genesis passes); triangle-free route, v3/v4 requests, receipts, adopted rules and frozen ids unchanged; not adopted |
| 20_R52 | E1b-C4 DRAFT package; same-operator rehearsal through the v5 C4 tree route | GV3 path in C4 (B20R50-OPEN-1) | Custodian SELECT chose low_cycle_tm; 20-host CONFIRM, all certified by the tree reference at 600 s; +1.15 [0.70, 1.65], 12/1/7, cost ratio 0.92: **SUPPORTED**, judge agrees; package `handoff/e1b_c4` |
| 20_R53 | Research-selection headroom on Wolfram's axiom at B20's hard settings (design pilot) | GV4 / GV6 equational target (B20R9-OPEN-1) | 4 fresh seeds: ORACLE@cap − FIXED@cap 1, 0, 1, 0 (caps non-binding: the pool exhausts in 4.9–9.1 s), noise 0: **NO_HEADROOM**; the ceiling (3–8 of 15 unproved by any pool library) is the limit. Descriptive GAP (transferred keep rule) equals ORACLE on every seed with 1–3 lemmas |
| 20_R54 | Does research beyond the pool reach Wolfram's ceiling? (design pilot; POOL6, up to 6 nodes, 233 true equations) | GV4 / GV6 equational target (B20R9-OPEN-1, B20R46-OPEN-1) | 4 fresh seeds, targets screened against all research material: ORACLE6 − ORACLE5 0, 0, 0, 0, noise 0: **NO_CEILING_HEADROOM**; EXHAUST6 (174–183 lemmas, 523–615 s) − EXHAUST5 −1, 0, 0, 0; GAP6 (1–5 lemmas) = EXHAUST6. The equational target has no research headroom at these scales |
| 20_R55 | The row-invention procedure transferred to sum-free sets of integers (`invention/cuts_sf.py`, new trusted `SFDefs`) | GV6 second target, a different theorem family (B20R46-OPEN-1) | 17 patterns (sets ⊆ {1..8}) kept from 214 candidates; **all 20 obligations Lean-CHECKED**; package replays. Procedural transfer only; utility on hosts is B20_R56; structural caveat stated |
| 20_R56 | Certified branch and bound over the transferred sum-free rows vs the same tree over Schur rows only (the conventional route and the registered ablation); exact checker `lp_dual_tree_sf`, producer `generated_bnb_sf` | GV6 second target: utility and attribution (B20R46-OPEN-1) | 40 fresh hosts (300/0.6, 360/0.6), 60 s: 28 vs 26 certified (2/0, p 0.25), wall saving −1.61 s [−4.14, +1.37], all sound: **NO_CERTIFICATION_UTILITY**; root bound 5–10 lower, nodes 85 vs 278, slower on easy hosts |
| 20_R57 | The transferred sum-free rows on hosts hard for the conventional route (screen: route a alone does not certify in 20 s; 40 of 72 fresh candidates) | GV6 second target: utility and attribution (B20R46-OPEN-1) | 22 vs 14 certified (8/0, p 0.0039), wall saving +6.02 s [2.50, 9.88], all sound: **CERTIFICATION_UTILITY**; certified bound +6.875 [5.375, 8.475]: **BOUND_UTILITY** |
| 20_R58 | Pattern-selection headroom in sum-free certification (design pilot): NONE, ALL and TOP-k by development score on 16 fresh hosts at 30 s | GV4 headroom (B20R9-OPEN-1) | ALL 13, NONE 10, TOP-1/2/4/8 9/10/10/11: **NO_HEADROOM** (H −2); the patterns' value is joint (alone 0.1–0.6 of root bound, together 7) |
| 20_R59 | Internal replication of B20_R57 (same protocol, fresh seeds; interrupted once by disk exhaustion and resumed) | GV6 second target, replication | a 21 vs c 23 (0/2, p 0.25), wall saving +2.76 [0.04, 5.37]: primary NO_CERTIFICATION_UTILITY, **NOT_REPLICATED**; certified bound +3.875 [2.675, 5.125]: **BOUND_UTILITY replicates** |

Later phases (B17–B23+) follow the roadmap and its gates; numbers are labels,
not estimates.

## Never done by these batches

- Acting as the independent custodian, auditor or release authority.
- Creating sealed tasks, running sealed comparisons, or promoting any claim.
- Rewriting historical evidence. Old runs and audits stay as they are.
