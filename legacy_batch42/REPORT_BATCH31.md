# Genesis Batch 31 — Frozen trial binding (DEV)
Date: 2026-10-09

## Implemented
- `frozen_trial.py`: recomputes the complete prospective registration from supplied frozen inputs rather than trusting a registration identifier.
- Derives task IDs from the registered DEV/SELECT/CONFIRM split; prohibits SEALED plaintext tasks in this accounting interface.
- Reuses exhaustive attempt accounting from Batch 30; records split and derived task-roster digest.
- Rejects altered task statements, altered solver configurations, changed sealed commitments, forged registrations and events on the wrong split.
- `test_frozen_trial.py`: 12 new regression/adversarial tests.

## Tests
`python -m unittest discover -q`: 148 tests passed.

## Limitations
- These are development fixtures and synthetic event records, not real Lean proof replay.
- The registered sealed commitment is caller-provided; independent custody and semantic leakage screening are not established.
- This interface does not bind evidence hashes to externally checked raw proof receipts.
- No statistical scientific claim is justified, no independent replication, and promotion is BLOCKED.

## Next actual dependency
Run the pinned Lean operator workflow on a trusted external machine; preserve raw evidence and have a separate custodian replay it. Then feed independently verified receipts into a frozen prospective comparison.
