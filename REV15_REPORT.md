# Genesis revision 15 — downstream premise and theory-boundary red-team repair

**Classification:** DEVELOPMENT ONLY. No promotion, no independent release acceptance, no external Lean or sealed jobs. The accepted base is unchanged.

## Reproduced vulnerabilities

**GEN-AUD-023 (CRITICAL; false task-solved acknowledgement):** In REV14, `LemmaStore.verify` correctly detected a caller's mutation of public `store.lemmas`, but `InductionWorld._library()` still copied those untrusted public values into `Prover` and `check_proof`. A legitimate admitted `L: Z=Z` was changed in the public dictionary to `L: Z=S Z`. The synthetic DEV task `Z=S Z` then changed from `solved=[0]` to `solved=[1]`. This is a concrete downstream false mathematical success, not a proof admitted to the LemmaStore. The raw `check_proof(theory, caller_lemmas,...)` API remains conditional on the supplied premises; it must not be used as a standalone certificate.

**GEN-AUD-024 (CRITICAL; detached mutable theory):** A world was constructed with an initially matched trusted theory/store. Later the public `world.theory` was replaced by a copied theory with `plus Z y = S y` while the store retained its original pinned theory. `store.replay_all()` still passed, yet a DEV task `plus Z Z = S Z` changed from `solved=[0]` to `solved=[1]`. A proof relative to a modified counterfactual theory is not a proof about the original Peano arithmetic theory. This demonstrates missing cross-component binding, not a failure of the pinned store's internal mutation detector.

## Integrated DEV mitigation

- `LemmaStore.verified_subset(ids)` checks pinned theory, complete public/private registry consistency and proof admission digests, then returns deep copies of admitted premises; missing IDs fail closed.
- `LemmaStore.assert_theory_matches(world.theory)` binds the solver's actual theory to the store's pinned theory digest before any use.
- `InductionWorld._library()` and `solve()` reject unverified/caller-substituted premises and detached theories; `ResearchContext.lib()` similarly validates both.
- Removed all direct `store.lemmas` reads from the source modules for adapter construction, U3 harvesting/experience/dreaming, U4 research, U5 funnel, task-suite construction and cascade evaluation.
- Clarified the low-level `check_proof` contract: its result is conditional on trusted axioms and premises, **not independent mathematical certification**.

## Reproduction evidence

`audit/REV15_BEFORE.json` is from a fresh extraction of REV14; `audit/REV15_AFTER.json` is from the patched integrated repository. The benign reproducer has no sealed task access or external calls.

Before: `{"baseline":[0],"forged_public_lemma":[1],"detached_theory":[1]}`.

After: `{"baseline":[0],"forged_public_lemma":{"blocked":"CheckError"},"detached_theory":{"blocked":"CheckError"}}` (full reasons in JSON).

Nine new adversarial tests cover the two exploits, direct solver/library injection, research context, unrelated registry mutation, low-level checker premise boundary, and valid replay. Test transcript, source hash manifest and all attempts are retained. Full-suite results are recorded in `audit/REV15_REGRESSION_RUN.json` and `audit/REGRESSION.stderr`.

## Explicit limitations and hard blockers

This is a **local red-team reproduction and builder patch**, not an independent re-audit or independent release decision. Python-private snapshots are not a hostile-process security boundary. The theorem definitions and Lean axioms still require an independent trusted checker and external pinned provenance; arbitrary counterfactual theories can support different theorems relative to their axioms. No external Lean executable or Docker runtime was available in this environment. No external custodian, independent key, operational isolation audit or immutable external preregistration timestamp was provisioned. No 300 independently checked genuinely fresh theorems exist. No new sealed experiments were run; no historical sealed jobs were rerun. Historical 11/20 missing raw jobs remain unresolved and must not be counted as verified. All previous negative evidence, failed attempts and alpha=0.05 remain unchanged.

**Campaign:** Batch 1 `FAILED_REPAIR_REQUIRED`; completed batches 0; accepted base unchanged; promotion false. Next: independent red-team review of REV15 source and custody architecture, external sealed custodian, pinned Lean theorem/axiom audit, fresh semantic task pool, then new preregistered equal-budget D/U/V2n/V2p comparisons. On 15 October Singapore time, close out based on independent prospective evidence only.
