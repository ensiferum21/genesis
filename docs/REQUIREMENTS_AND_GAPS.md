# Requirements and honest scope (section summary; updated in batch 14)

**Superseded for row-level status by `docs/REQUIREMENTS_LEDGER.md` (W01),**
which gives every specification section, roadmap item and catalogue entry one
disposition with resolvable tests and separates implementation, local
execution, independent verification and efficacy. This page keeps the
section-level summary. The previous version (10 October checkpoint) is in git
history at `c2d53a9`. Status words:

- **DONE_BOUNDED** — implemented, tested in this repository's test matrix, narrow scope stated.
- **PARTIAL** — real implementation with a stated missing piece.
- **EXTERNAL_REQUIRED** — the code path exists; what is missing is a person, organisation,
  machine or fresh evidence that code cannot supply.
- **NOT_IMPLEMENTED** — absent by design or out of scope here.
- **RESEARCH_UNESTABLISHED** — mechanism exists; no supported effect.

| § | Requirement | Status | Where / what remains |
|---|---|---|---|
| 1–2 | Goals, SystemVersion, research state, authority invariant | DONE_BOUNDED | `kernel/version.py` (all §2.1 fields), `kernel/authority.py` (leased grants; children cannot gain budget or permissions; network/release/provider need external authorization). |
| 3.1 | Microkernel services: identity, CAS, event ledger, receipts, authority, certificate replay, evaluator isolation, release gate, rollback | DONE_BOUNDED | `store.py`, `kernel/*`, `custodian.py`, `sandbox.py`. Rollback = predecessor version + lineage; destructive ops absent. |
| 3.2 / 15 | Trust root, CIRCULAR_JUSTIFICATION, no self-certification | DONE_BOUNDED / EXTERNAL_REQUIRED | `kernel/evidence.verifier_trust`, `kernel/roles.py` (root-signed registry the research account cannot write). The root key holder must be external. Foundation lifting NOT_IMPLEMENTED. |
| 4.1 / 32 | 16 primitives with contracts | DONE_BOUNDED | `ir.py` typed overloads, traces, replay. Graph-wedge scope only. |
| 4.3 | Epistemic type and effect system | DONE_BOUNDED | `kernel/evidence.py` Effect enum, propagation, speculative taint resolved only by passing checks. |
| 4.4 | MRDL | DONE_BOUNDED | `mrdl.py` (unchanged). |
| 5 | Discovery loop A–G | DONE_BOUNDED (A–F) / EXTERNAL_REQUIRED (G) | Campaign + world loop + macros; G (fresh sealed confirmation) needs an independent custodian. Walkthrough: `evidence/e2e_walkthrough/`. |
| 6 / App. A | Macro engines | PARTIAL | 5 engines IMPLEMENTED_BOUNDED (Ghost Census, Barrier & Escape, Local-to-Global, Gap Engine, Cognitive Compilation), 16 INFRASTRUCTURE_BOUNDED, 116 recorded as composition hypotheses (`registry.py`). No stubs. |
| 7 | Orthogonal evidence axes, ghost and BoundState semantics, wording gate | DONE_BOUNDED | `kernel/evidence.py`, `kernel/wording.py`; reports must pass the linter to be written. |
| 8 | c4_host_v2, triangle_free_host_v1, dual checkers, construction + obstruction | DONE_BOUNDED | Exhaustive dual solvers ≤ 24 edges; SAT/DRAT upper certificates beyond (`verification/sat.py`). Complete hosts above ~9 vertices are hard to certify (symmetry). |
| 9 | Worlds, Pareto, retirement, irreversibility | DONE_BOUNDED | `research.Ecology`, `worldstep.py`. Irreversibility weighting is the market's risk term. |
| 10 | Local-to-global, continuation, tractability, approximation | PARTIAL | Local-to-global and approximation→exact done; continuation and FPT/kernelization NOT_IMPLEMENTED. |
| 11 | Fault-tolerant cognition | PARTIAL | Heterogeneous checks (dual predicates, SAT vs exhaustive, model finder vs evaluator, Lean comparator); semantic parity syndromes NOT_IMPLEMENTED. |
| 12 | Causal self-improvement | PARTIAL / RESEARCH_UNESTABLISHED | Modification records, DEV ablation/placebo, market calibration; no supported causal gain. |
| 13–14 | Experience synthesis, crystallization, kernel minimization | NOT_IMPLEMENTED / RESEARCH_UNESTABLISHED | Trace compilation only. No neural training. |
| 16 | Architecture, tables, envelope, single writer | DONE_BOUNDED | Kernel/research boundary enforced by test; §16.4 tables as a derived index (`kernel/index.py`). |
| 17 | Execution, containment, profiles, resource fairness | DONE_BOUNDED | Fixed DSL executor + runc/OCI sandbox (executed escape suite); realized-CPU matching in the ladder. Container base image digest not pinned (no registry access). |
| 18 / 35 | Splits, leak screening, contamination firewall | DONE_BOUNDED | `exposure.py` (custodian-built registry), `kernel/leakscan.py` (exact/structural/Lean-elaborated/near-duplicate, oracle, query budget), `kernel/memory.py` (§37.3). Old Lean round-2 contamination remains historical. |
| 19A | Microkernel and replay (L0) | DONE_BOUNDED | Corruption, mutation, rebuild, bundle verification, escape suite. Independent audit still required. |
| 19B | Ghost Census kill gate | DONE_BOUNDED (harness) | `experiment_b.py`; DEV run decision KILL (family too easy). |
| 19C–F | Clean Lean study, transfer, better improver, multi-generation | EXTERNAL_REQUIRED | Harnesses exist (campaign generations, transfer panel, custodian, signed phases); sealed evidence and independent operators do not. |
| 20 | Baselines and ablations | DONE_BOUNDED | DSL baselines, CaDiCaL specialist arm under equal CPU, exact reference, ablation/placebo. No frontier-model baseline (no model is used). |
| 21 | Reporting | DONE_BOUNDED | Evidence-derived reports + wording linter; release bundle includes limitations. |
| 22 / 45 | Red team / threat model | PARTIAL | Audit reproductions GI6-01/02/03/08/10/11 fail closed; sandbox escape suite; independent red team EXTERNAL_REQUIRED. |
| 23 / 31 / 48 | Phases, checklist, completion | see below | |
| 26 | Reference APIs | DONE_BOUNDED | run_trial ≈ `campaign.trial`; promote_claim = `kernel/evidence.promote`; world step = `worldstep.py`; modification contract with authority_delta = 0. |
| 27 | Verification adapters | DONE_BOUNDED / PARTIAL | Lean (pinned, sandboxed comparator, axiom audit, leanchecker), SAT/DRAT, exact, differential, property harness; interval/numerical certificates NOT_IMPLEMENTED; human adjudication records for near duplicates. E proofs are prover claims (not replayed). |
| 28 | Literature compiler | NOT_IMPLEMENTED | Novelty axis requires an external priority check record. |
| 29 / 47 | Software, empirical science, ML research | NOT_IMPLEMENTED | Out of scope for this branch. |
| 30 | Security boundary | DONE_BOUNDED | No network in generated code; credentials only outside the sandbox; external permissions need authorization. |
| 33 | Coordinator state machine, transaction boundary, crash recovery | DONE_BOUNDED | `kernel/phases.py` (signed scientific transitions), `store.rebuild_from_export` (recovered the 10 Oct malformed run). |
| 34 | Research market, stop rule | DONE_BOUNDED | `market.py`. |
| 36 | Domain adapter | PARTIAL | Graph adapter functions exist; a formal `DomainAdapter` protocol class is not extracted. |
| 37 | Lean contract | DONE_BOUNDED | Finite witness obligations only; no Mathlib; no optimality theorems formalized. |
| 38 | Test and CI matrix | DONE_BOUNDED | `docs/TEST_MATRIX.md`, `scripts/run_test_matrix.py`, `.github/workflows/ci.yml`. pytest/Hypothesis not installable here; seeded property loops under unittest. |
| 39 | Config and CLI | DONE_BOUNDED | `genesis init/doctor/smoke/campaign/world/trial/artifact/evidence/freeze/report/export/verify-bundle/benchmark/research/experiment/registry/store/formal`. |
| 40 | End-to-end walkthrough | DONE_BOUNDED | `scripts/e2e_walkthrough.py`; steps 11–13 with fixture roles; step 14 not performed. |
| 41–42 | Meta-gap discovery, kernel minimization | RESEARCH_UNESTABLISHED | Meta-gap candidates recorded as hypotheses; no primitive invention. |
| 43 | Replication bundle | DONE_BOUNDED | `release_bundle.py` + independent `verify_bundle`. |
| 44 | Human/expert interaction | PARTIAL | Signed adjudication records for near duplicates; expert-query optimizer NOT_IMPLEMENTED. |
| 46 | Deployment | PARTIAL | B15: supported platform spec and host check, Python 3.13 lock, reproducible toolchain with pin-revision protocol, root launcher / unprivileged worker, crash-tested recovery, backup/restore and a second-machine reproduction driver (`deployment/DEPLOYMENT.md`). Container digest still unpinned (no registry); no second machine; compute sizing not measured. |

## §31 acceptance checklist

| Area | Status |
|---|---|
| Architecture boundaries explicit; workers cannot write evaluator state | Met in code and tests (kernel import boundary, sandbox, custodian private root, role registry). |
| Provenance: every artifact/claim → hashes, producer attempt, version | Met (CAS, events, evidence DAG, SystemVersion). |
| Execution limits enforced, failures retained | Met (DSL executor + OCI sandbox, executed escape suite). |
| Evidence axes separate; no-ghost ≠ proof; checker errors ≠ outcomes | Met. |
| Formalization: ambiguity and NL↔formal mappings versioned and testable | Partial: trusted Lean spec generation for finite witnesses only. |
| World ecology | Met (bounded). |
| Construction/obstruction; exactness needs gap zero | Met. |
| Sealed evaluator isolated; screening before exposure | Mechanism met; independent operation EXTERNAL_REQUIRED. |
| Strong baselines under matched information/budget | Met for the graph wedge (DSL + CaDiCaL arms, equal realized CPU). |
| Modifications: hypotheses, predictions, invariants, rollback, causal plans | Met (Modification records, authority_delta = 0). |
| Compilation: promotion and later demotion by evidence | Partial (compilation and revocation exist; demotion policy not exercised). |
| Reporting from evidence with limitations | Met. |
| Reproduction on an independent machine without hidden state | Bundle + verifier met; actual external reproduction EXTERNAL_REQUIRED. |
| Design freeze for new primitives | Met (registry; no new primitives). |

## §48 completion labels (builder's assessment, not an accepted release)

The reviewer reproduced two evidence-integrity defects (R-01, R-02) against
B13 and raised R-03 and R-04. B14 repaired R-01..R-03 (and eleven further
internal red-team findings), but **every label below is pending independent
acceptance**, and P0 cannot be accepted while R-04 (supported deployment) is open.
B15 built and tested on one host everything R-04 asks for that does not need a
registry, PyPI or a second machine; those three remain. B16 built the evaluator
side (domain contracts, DEV calibration, preregistered statistics, resource
accounting, custody records); its exit requires independent review of custody,
fairness and study design. B17 built the Lean/Mathlib research workspace and the
first theory package. The package replays from its sources, but only the builder has
replayed it. B18 built concept invention: a representation grammar, worlds with checked
transport, and concept recovery. All of it is DEV-only and replayed by the builder. B19
built useful discovery on DEV:
- certified reductions with exact LP dual certificates (W13);
- active selection with honest identifiability (W14);
- catalysis controls (W15);
- a Ghost Census diagnostic with Lean replay of E proofs (W16);
- literature and priority records (W17);
- E1/E2 drafts.
Acceptance needs independent review and a custodian. B20 built learning to research on
an equational domain with exact deciders: research policies, replayable macros, screened
memory and curriculum, and Lean-checked lemma chains. The better-improver claim (E3, GV4)
is explicitly unestablished.
B21 built repeated improvement on the same domain: a generation controller with frozen,
content-addressed generations and a predeclared acceptance rule; a primitive proposed by an
operator-completeness adversary, with a definitional contract and a Lean bridge to the
base language; and heterogeneous routes with fault injection and a simulated expert under
an intervention budget. One transition was accepted and then the domain saturated, so
compounding (E4, GV5) is not established.

- **ENGINEERING_COMPLETE_P0** — builder's assessment only. Blocked on R-04's
  outstanding parts (second-machine run of `deployment/reproduce.sh`, image
  digest, wheel hashes) and on independent review of the B14/B15 work (gate GV0).
- **DOMAIN_COMPLETE_P1** — c4_host_v2 runs end to end with strong conventional
  baselines and exact checking; optimality now needs a custody-held certificate
  replayed with the solver disabled. Pending audit.
- **RESEARCH_IR_COMPLETE_P2** — typed IR execution, world ecology and evidence
  promotion run in public DEV campaigns; only 5 of 137 engines are concrete
  macros (15 more are shared mechanisms, 117 not implemented; see the ledger).
  Pending audit.
- **P3–P7** — not claimed. They need independent custody, fresh sealed panels,
  external timestamps, independent audit and replication (gates GV2–GV7).
