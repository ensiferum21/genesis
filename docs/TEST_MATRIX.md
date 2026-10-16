# Spec §38 test matrix → where each class lives

| Class | Examples in this repo | Profile | Release consequence |
|---|---|---|---|
| Unit | hashing, schemas, bound ordering, status transitions (`tests_genesis/test_store*.py`, `test_evidence_kernel.py`, `test_phase_receipts.py`) | commit | must pass |
| Property | relabel invariance, canonicalization, rebuild = online state over random histories, IR equivalence over 600 random cases (`test_store_recovery.py`, `test_dsl_equivalence.py`, `test_leak_firewall.py`) | commit | must pass |
| Differential | dual graph predicates, SAT vs exhaustive optima, SAT model vs independent FOL evaluator, encoding vs brute force (`tests_certificates/`, `tests_formal/test_fol_ghosts.py`) | nightly | disagreement blocks the adapter |
| Mutation | corrupted receipts, objects, event bodies, derived state, DRAT proofs, certificates, bundles (`test_matrix_classes.py`, `tests_certificates/`) | commit | kernel must detect corruption |
| Sandbox escape | network, filesystem, credentials, evaluator paths, privilege, seccomp, resources (`tests_sandbox/`) | release | failure **or skip** blocks release |
| Replay | macro IR replay, trial replay, store rebuild, bundle verification (`test_macros_market.py`, `test_research_runtime.py`, `test_matrix_classes.py`) | commit | failure marks a reproducibility defect |
| Leak firewall | exact / alpha / elaborated / near duplicates, oracle, theorem-memory audit (`test_leak_firewall.py`, `test_custodian_registry.py`) | commit | failure blocks sealed use |
| Baseline regression | golden baselines + exact optima (`test_matrix_classes.py`, `golden/baselines.json`) | commit | unexpected change requires adjudication |
| Evidence wording | illegal promotions and prose (`test_evidence_kernel.py`) | commit | must reject all fixtures |
| Load/resource | single writer, concurrent worker returns, CPU/output/OOM receipts (`test_matrix_classes.py`, `tests_sandbox/`) | commit / release | must retain truthful receipts |
| End-to-end smoke | one campaign through report under 600 s (`test_matrix_classes.py`) | commit | must pass under the cap |
| Formal | Lean canaries and defence in depth (`tests_formal/`) | nightly | failure blocks formal claims |
| Acceptance regressions (B14) | R-01 reproduced attacks + every forged-receipt case (`test_acceptance_regressions.py`), R-02 export revocation (`test_export_revocation.py`), R-03 checker-only replay (`tests_certificates/test_certificate_custody.py`), internal red-team F1–F11 (`test_redteam_b14.py`) | commit / nightly | any failure re-opens GV0 |
| Deployment and recovery (B15) | platform/lock checks (`test_deployment.py`), real-process crash injection at 14 points (`test_crash_consistency.py`), backup/restore (`test_backup_restore.py`), pin revision protocol (`test_toolchain_revision.py`), reproduction driver (`test_reproduce.py`), red team (`test_redteam_b15.py`) | commit | failure blocks R-04 |
| Role separation (B15) | root launcher serving an unprivileged worker: peer UID, ceilings, allowlists, budget, anchored log, Lean from UID 65534 (`tests_sandbox/test_launcher.py`) | release | failure **or skip** blocks release |
| Toolchain behaviour (B15) | 10 known-answer cases on the installed pinned tools (`tests_certificates/test_known_answers.py`) | nightly | failure blocks release |
| Evaluator readiness (B16) | domain adapter conformance (`test_domain_adapters.py`), DEV calibration (`test_calibration.py`), analysis plan v2 and power (`test_analysis_v2.py`), custody flow with v3 receipts, judge, registration log and preflight (`test_evaluator_readiness.py`), resource accounting and arm fairness (`test_resources.py`), red team (`test_redteam_b16.py`) | commit | failure blocks sealed use |
| Formal research (B17) | workspace pins and artifact audit, adversarial proof modules (sorryAx, weakened statement, shadowed names, axioms, `Lean` imports, options), search never accepting, Lean statement adapter, committed package contract, tamper detection and replay from sources (`tests_formal/test_formal_research.py`) | nightly / release | failure **or skip** blocks release |
| Concept invention (B18) | representation grammar typing and screening, loss witnesses, method validity, world judgement rules, typed anti-unification and leakage check, fresh-family screening, evidence contract and a replay (`tests_formal/test_invention.py`) | nightly / release | failure **or skip** blocks release |
| Useful discovery (B19) | LP dual certificates (exactness, tampering, motif check), joint certification, active selection and identifiability (EIG, KG*, top-two, classes), catalysis and active evidence (`tests_formal/test_discovery.py`); E proof objects replayed step by step in Lean, translation faithfulness (`decide` vs the independent evaluator), model-finder budget regression, the W16 decision rule and evidence (`tests_formal/test_ghost_census.py`) | nightly / release | failure **or skip** blocks release |
| Literature and readiness (B19) | exact quotes, quarantine of instruction-like retrieved text, verdicts independent of text, ambiguity and adjudication records, novelty never 'novel' (`tests_genesis/test_literature.py`); E1/E2 drafts consistent and unfrozen (`tests_genesis/test_readiness.py`); centred-headroom power option (`tests_genesis/test_analysis_v2.py`) | commit | failure blocks release |
| Learning to research (B20) | exact deciders, pools and targets, policies and the logistic fit, macros (induction, faithful replay, revocation, preconditions), memory screening and curriculum, research runs, Lean replay of lemma chains including a tampered chain, and the evidence contract (`tests_formal/test_learning.py`) | nightly / release | failure **or skip** blocks release |
| Representation families and replay (B20_R25–R28) | hint generator versions (v1 verbatim, v2 default; v2 finds refuting instances v1 misses) and the paired A/B evidence (`tests_formal/test_hint_versions.py`); quotient patterns exact against brute force, transport model, witnesses (`tests_genesis/test_quotients.py`); decomposition partition, composition model, witnesses (`tests_genesis/test_decompositions.py`); both families' packages replay and their verdicts follow from the rows (`tests_formal/test_quotient_invention.py`, `tests_formal/test_decomposition_invention.py`); the E1b causal re-pilot record (`tests_genesis/test_e1b_causal_repilot.py`) | nightly / release | failure **or skip** blocks release |
| Certification limits and the relaxation family (B20_R30–R31) | B20_R30's certification-budget record: summary from the rows, the preregistered verdict rule, the one-sided Clopper–Pearson bound, hosts in the exposure addenda (`tests_genesis/test_certification_budget.py`); the pattern generator's kept and rejected patterns, bounds on random triangle-free sets, copies, the component's budget and witnesses (`tests_genesis/test_cuts.py`); the relaxation package replays, the verdict and the Part C tallies follow from the rows, fresh hosts, addenda (`tests_formal/test_relaxation_invention.py`) | nightly / release | failure **or skip** blocks release |
| Requirements ledger | every spec section, roadmap item and catalogue entry has a disposition with resolvable tests (`test_ledger.py`) | commit | must pass |

Run: `python3 scripts/run_test_matrix.py --profile commit|nightly|release --report out.json`.
pytest/Hypothesis are not used because they were not installable in the build
environment; property tests use seeded random generation and run under
`unittest`. Both remain compatible with a pytest runner.

Skips: release-blocking suites (sandbox, certificates, formal) accept no skips.
In every other suite a skip fails the matrix unless it is declared, with a
reason, in `docs/NONMANDATORY_SKIPS.json` (currently one legacy test that needs
cached historical worlds). Missing tools therefore surface as failures, never
as silent passes.
