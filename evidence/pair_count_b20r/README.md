# CRPD-2b: the Lean-checked C4 pair-count bound (DEV)

- **Script:** `scripts/b20r_pair_count.py`, committed in 61cd54a before it ran.
- **Workspace:** the revised pin. Source identity `7f5bcfa1…`, artifact identity `be8f86a8…`, 910 modules (see `toolchain/FORMAL_WORKSPACE_HISTORY.jsonl`).
- **Decision:** the user, 13 Oct 2026: Go on CRPD-2b, time-boxed.

## Statements

Both are stated over the repository's own definitions: `GT.Edges`, `G4.adj`, `G4.C4Free`. S is an edge set of pairs u < v < n, which is exactly the `GraphTask` contract.

| Statement | Lean | Status |
|---|---|---|
| pair_count_c4 | sum over v < n of C(deg v, 2) ≤ C(n, 2) | CHECKED (screened on 2,724 instances first) |
| c4_quadratic_bound | 4 \|S\|² ≤ n²(n − 1) + 2n\|S\| | CHECKED (screened on 2,731 instances) |

**Axioms used:** `propext`, `Classical.choice`, `Quot.sound` (the allowed set).

The package replays from its sources (`replay.json`). These are known results, and the statements and proof recipes are builder-written: this is a checked bound for later use, not a discovery.

## As a checked upper certificate

Bundle v2 gains the method `PAIR_COUNT_LEAN`. To check one, replay:
- re-checks the host contract;
- recomputes the bound from n alone;
- requires the stored package to be exactly the checked statement over the repository definitions;
- replays the package in the pinned workspace.

| Host | n, m | Exact optimum | Bound | Replay | SAT/DRAT cross-check |
|---|---|---|---|---|---|
| K3, K4, K5 | complete | 3, 4, 6 | 3, 4, 6 | OPTIMALITY_CHECKED | not needed |
| K6, K7 | complete | 7, 9 | 8, 10 | BOUNDS_CHECKED | optimum 7, 9 |
| 4 dense hosts | n = 7–8, p = 0.85 | 11, 11, 9, 11 | 12, 12, 10, 12 | BOUNDS_CHECKED | agrees with the witness |

On K3–K5 the optimum is now certified with no SAT proof, by a witness and a Lean-checked bound. Elsewhere the bound is one edge above the optimum, as expected for this classical bound on small hosts.

## Earlier evidence

All earlier formal packages replay under the revised pin: 151 of 152 tests in the formal suite pass. The one failure needs `evidence/obstruction_custody_b20r`, which is missing on this recovery branch (see `docs/checkpoints/B20_RX1_RECORD.md`). Earlier evidence keeps the workspace identity it recorded.
