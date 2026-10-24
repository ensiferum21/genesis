# Genesis Ω: architecture (master implementation contract §18)

What exists today (24 Oct 2026), how the parts connect, where the trust boundary runs, and how each part fails.
The plan and its stages are in `docs/GENESIS_OMEGA_PLAN.md`; stage gates are in `docs/OMEGA_ROADMAP_STATUS.md`.

## Trust boundary

| Protected kernel (never modified by the research plane) | Mutable research plane |
|---|---|
| Domain adapters and checkers: `domains.py`, `causal/admg.py` (scoring), `compiler/families.verify`, the Gset checkers, Lean, DRAT | The experimental scientist (`science/design.py`) and its languages (`science/acquire.py`, `science/library.py`) |
| The judge: `autonomy/feedback.py` (contract v2), `judge.py`, the statistics of each preregistered script | Inventors (`autonomy/selfimprove.py`), processes (`autonomy/process.py`) |
| The evidence microkernel (`kernel/`: evidence DAG, signing, roles, receipts, leak scanner, replay contracts) | Interpretations and estimators (`causal/active3.py`, `instruments.py`, `joint.py`, `global_ml.py`; `interpret.py`) |
| The sandbox (`sandbox.py`, `launcher.py`), the store (`store.py`), versions and rollback (`versions.py`) | The Problem Compiler's forms and back-ends (`compiler/`) |
| Sealed tasks (none used on this line: DEV only) | The vault's contents and edges (`vault.py`), the CLI (`discovery_cli.py`), replayers (`replayers.py`) |

Enforcement:
- `test_omega_boundary`: the research plane imports no kernel, judge, custody or release module.
- `vault.annotate`: `verified` and `promoted` require an EvidenceRecord naming a recorded study and its record test.
- `replayers.replay`: only registered replayers run.
- Every study's record test recomputes its verdict from saved rows.
- The no-LLM gate: `test_no_llm`.

## Data flow (one research cycle)

```
problem family (domain adapter / compiler family)          ← verifier: the only judge of answers
   │
   ├─ the experimental scientist (science.design):
   │    beliefs over explanations ─ choose the next experiment ─ run (sandbox / simulator) ─ update ─ decide
   │
   ├─ inventors (selfimprove, acquire search, instrument search):
   │    propose programs ─ evaluate on training splits ─ the judge (B, C splits) releases only beyond its noise
   │
   ├─ the vault: every evaluated artifact, exact bytes, lineage, status; edges failed_due_to / enables / ...
   │    └─ a new verified capability → opportunities → reactivation → re-test (bounded by fuel)
   │
   ├─ interpretation (interpret.py): simplification under ranges, fingerprints, refutable conjectures, ablation
   │
   └─ preregistered study (scripts/b20r*.py): fresh worlds; Holm; record test; evidence README; ledger
```

## Interfaces

| Interface | Definition |
|---|---|
| `science.design.Domain` | `questions`, `hypotheses`, `prior`, `experiments`, `touches`, `outcomes`, `predict(q, e)`, `execute(e)`, `cost(e)` |
| Acquisitions | `{'kind': random / order / static_eig / eig / dec / hybrid / program, ...}`, optionally `per_cost` |
| Inventor searches | `feedback.steady_state_search(ops, evaluate, max_evals, seed, contract, calibrate)`, with ops `{random, mutate, crossover, size}` |
| Compiler | `families.compile` → BQP; `backends.run(backend, bqp, cpu, seed)` → assignment; `families.verify` → (valid, score) |
| Vault | `put`, `get`, `raw`, `annotate`, `edge`, `query`, `ancestors`, `descendants`, `opportunities`, `reactivate`, `cascade`, `verify` |
| Processes | `{'level', 'kind', 'params', 'lineage'}`; `process.step(proc, task, fuel, measure)` |

## Failure modes and what catches them

| Failure | Caught by |
|---|---|
| A search mistakes noise for progress | The feedback contract's judge (B20_R103, R107); test sets used once |
| A broken reduction or decoder | `compiler/contracts.py` (REJECTED); the family's verifier on every answer |
| A tampered artifact | The store's CAS hash check and `Vault.raw` identity check (`test_vault`) |
| A runaway cascade or meta-recursion | Fuel, the seen set and the depth limit (`test_vault`, `test_process_levels`) |
| Self-promotion | The vault's evidence gate; the boundary test |
| Overconfident beliefs | Calibration measured in studies (B20_R129: Brier, ECE; information gain against accuracy gained) |
| An LLM dependency | `test_no_llm` (static, configuration, dynamic, with a planted control) |
| A replay difference | `genesis discovery replay` → DIFFERENT; record tests recompute every result |
