# Genesis Batch 32 — prospective statistical sensitivity (DEV)

Date: 2026-10-09. Scientific promotion: **BLOCKED**.

## Implemented

- `prospective_statistics.py`: one-sided exact paired sign test on discordant outcomes; explicit tie/invalid handling; cluster-level aggregated sign-test sensitivity.
- `analyze_frozen_trial` revalidates the complete Batch 31 frozen registration and event accounting before descriptive inference.
- Reports statistical thresholds as **descriptive only**, never as a scientific promotion decision.
- Does not invent cluster independence: the integration's one-task-per-cluster default is explicitly marked exploratory and unverified.
- `test_prospective_statistics.py`: 13 new tests including a ten-task/one-cluster case that prevents a false cluster-level conclusion.

## Verification

`python -m unittest discover -q`: **161 tests passed**.

## Limitations and blockers

- Event evidence hashes are not independently replayed; fabricated input records can pass schema validation.
- Cluster labels are caller-supplied for `analyze_pairs` and are not yet bound into the v1 frozen registration. Therefore the cluster sensitivity calculation is exploratory, not a pre-registered confirmatory test.
- The frozen-trial convenience function uses task-as-cluster only as an explicitly unverified proxy.
- No trusted Lean executable available; no genuine Lean proof replay, no independent sealed data custody, no evidence of solver or improver gains.
- All outputs retain `promotion_allowed: false` and `scientific_claim: NONE`.

## Next milestone

Freeze task-family clusters in the original prospective registration **before** seeing outcomes, then obtain actual externally verified Lean proof receipts and independent benchmark custody. Do not turn more simulated tests into scientific claims.
