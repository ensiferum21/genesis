# Genesis integrated development checkpoint

An executed bounded experimental implementation built on REV18 and Batch 42.
**This is not the complete grand vision, an accepted scientific release, or
evidence of recursive self-improvement.** Full scope is documented in
`docs/REQUIREMENTS_AND_GAPS.md`.

The new `genesis` package supplies a coherent graph research workflow. Existing
`gap_engine` induction, learning, proof-checking and Lean custody modules are
preserved. `legacy_batch42` remains a development-only compatibility branch.

## Run

Use Python 3.12 and the observed versions in `requirements.lock`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
export PYTHONPATH=src
python -m genesis doctor
python -m genesis smoke runs/my_smoke
python -m genesis init runs/my_campaign --config configs/offline.json
python -m genesis campaign run runs/my_campaign
python -m genesis trial replay runs/my_campaign --limit 10
python -m genesis freeze candidate runs/my_campaign --tasks 300
```

These commands use public generated graphs. Freeze exports an evaluation request,
not a sealed evaluation. The default 300-task request is not a power calculation.

## Implemented narrow mechanisms

- Strict data schemas; immutable CAS; transactional SQLite events and state;
  append-only export; single writer; complete terminal attempt records and recovery.
- C4-free and triangle-free host optimization, dual witness predicates, two
  structurally different exact algorithms and exact bounded isomorphism screening.
- Bounded solver programs executed as data by a fixed interpreter in subprocesses
  with wall/CPU/address-space/output limits. Candidate code cannot supply scores.
- All 16 Research IR primitive handlers in declared graph/data scopes, exact MRDL
  representations, bounded world ecology, Pareto records and reusable capabilities.
- Equal-budget research-policy comparisons; preferences learned from DEV only;
  successor freeze, subsequent public tasks, ablation/placebo, transfer and generations.
- Private evaluator registration, exposure reservations, full private execution
  records, signed receipts and separate role-pin checks. Local preflight never releases.

## Blockers

This host had no Lean or Docker and could not switch to the separate research UID
used by an isolation test. The fixed data-only executor is not an arbitrary-code
sandbox. No external custodian, external timestamp, auditor or release authority
was established. No accepted checkpoint was overwritten.

General ontology invention, foundation lifting, neural mechanism extraction,
arbitrary software research, physical instrumentation and model training are not
completed by these graph mechanisms. Historical missing evidence remains missing.

## Verify

```bash
PYTHONPATH=src python -m unittest discover -s tests -t .
PYTHONPATH=src python -m unittest discover -s tests_genesis -t .
(cd legacy_batch42 && PYTHONPATH=. python -m unittest discover -s . -p 'test_*.py')
```

Tests establish engineering behavior only. Original failures and later logs are
retained in `evidence/`. An environment-dependent UID test skips explicitly when
UID switching is unavailable; this is not an isolation pass. Read
`IMPLEMENTATION_HANDOFF.md` before continuing.
