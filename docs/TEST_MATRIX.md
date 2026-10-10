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

Run: `python3 scripts/run_test_matrix.py --profile commit|nightly|release --report out.json`.
pytest/Hypothesis are not used because they were not installable in the build
environment; property tests use seeded random generation and run under
`unittest`. Both remain compatible with a pytest runner.
