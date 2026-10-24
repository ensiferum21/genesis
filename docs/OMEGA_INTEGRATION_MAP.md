# Genesis Ω: integration map (master implementation contract §1.5)

New Ω modules and the existing modules they reuse. Nothing here duplicates the judge, the sandbox, the store, the
ledger, the domain adapters, provenance or checkpointing. Status as of 24 Oct 2026; see `docs/OMEGA_GAP_MATRIX.md`.

| New module (plane) | Purpose | Reuses (existing, unchanged) | Never touches |
|---|---|---|---|
| `science/design.py` (research) | Domain-independent experimental scientist: beliefs, predicted outcomes, adaptive acquisitions, costs | `autonomy/feedback.py` (its searches are judged by the contract) | the judge, the checkers |
| `science/acquire.py` (research) | Genesis's typed acquisition language: interpreter, search operators, feature sets | `autonomy/feedback.steady_state_search` | — |
| `causal/active3.py` (domain adapter) | Causal discovery as a `science.design` domain; the lab drawn once | `causal/sem.py` (the simulator, evaluator side), `fci.py`, `active2.classify`, `admg.score` (checker) | `admg` (protected scoring) |
| `causal/instruments.py` (research) | Per-pair instruments as programs, calibrated by simulation | `active3`, `active.dependent` | `admg` |
| `causal/joint.py` (research) | Joint re-analysis: FCI with a pooled-regime test | `fci.run` | — |
| `causal/global_ml.py` (research) | Established LLC estimator; multi-regime ML | `methods._acyclic_part` | `admg` |
| `compiler/` (domain adapters, in development) | The Problem Compiler: BQP intermediate form, exact or penalised back-end forms, families with their own verifiers | `candidate_kinds/mcx2.py` (engine), the pinned MaxSAT champions (`maxsat2026.py`), HiGHS via `scipy.optimize.milp` | each family's verifier is the only judge of answers |
| `vault.py` (research memory; planned, Ω5) | Content-addressed artifacts, two status ladders, append-only annotations and capability edges, a bounded reactivation queue | `store.Store` (CAS, journal, verify, snapshot, export), `lineage.py` | `kernel/` records: the vault proposes, the kernel promotes |
| `genesis discovery …` CLI (planned) | List, show, replay, explain, export, revisit | `cli.py` conventions, `vault.py` | — |
| Ω stage studies (`scripts/b20r129*`, `b20r130*`, …) | Preregistered tests of each capability | The batch protocol (HANDOVER §3), `common.code_identity`, `b20r33.pinned_core` | sealed tasks (none are used: DEV only) |

**The trust boundary.**
- The research plane (everything above marked "research", and every inventor, archive policy and allocator) may
  read from the protected kernel and submit evidence to it.
- It may not write kernel records, change a checker, see sealed data, or promote its own artifacts.
- In code: the Ω research modules import nothing from `genesis.kernel` that writes. A boundary test enforces this
  when `vault.py` lands.
- Promotion of a vault artifact to `promoted` requires an evidence record that references a recorded study and its
  record test. The vault refuses the transition without one.
