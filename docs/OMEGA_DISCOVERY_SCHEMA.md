# Genesis Ω: discovery schema (master implementation contract §3, §18)

The vault's artifact model (`src/genesis/vault.py`, schema `genesis-vault-artifact-v1`), on the store
(`store.Store`: a single-writer SQLite journal, immutable content-addressed objects, hash-chained events,
verification, snapshots, recoverable export).

## Artifact (immutable)

| Field | Meaning |
|---|---|
| `schema` | `genesis-vault-artifact-v1` |
| `type` | ProblemSpec, WorldSpec, ObservableSpec, ProgramSpec, ProcessSpec, ExperimentSpec, EvidenceRecord, DiscoveryRecord, CapabilityRecord or ResearchOpportunity |
| `content` | The exact artifact: source or AST (for example, an acquisition program's tree), definitions, data |
| `domain` | The task family it belongs to |
| `creator` | The process that made it (name, search, order of evaluation, ...) |
| `parents` | The artifact IDs it derives from (lineage); each must already exist |
| `seeds`, `contracts`, `costs`, `environment`, `replay` | Random seeds; evaluation contracts and scores; measured costs; code identity or commit; a registered replayer, its arguments and the expected result |
| `created` | Empty unless pinned. The time of storing is in the first annotation, so identical content has one ID |

The **ID** is the SHA-256 of the canonical JSON bytes. `Vault.raw(ID)` returns exactly those bytes and checks the ID
against them. The store checks every object's hash.

## Annotations (append-only, numbered per artifact)

`{artifact, n, status, explanation, failure, novelty, evidence[], reason, actor, time}`. The latest non-empty value of
each field is the artifact's current value.

| Ladder | Values | Rule |
|---|---|---|
| Status | generated → exploratory → reproducible → verified → promoted; dormant; rejected; superseded | Only along `TRANSITIONS`. `verified` and `promoted` need EvidenceRecords naming a recorded study and its record test |
| Explanation | unknown, conjectural, empirical, established | Independent of the status: a discovery may be promoted for a verified use with an unknown explanation |
| Failure | incorrect, too_expensive, context_limited, missing_prerequisite, unexplained, promising | Why a dormant or rejected artifact stopped |
| Novelty | syntactic, behavioral, mechanistic, verified_useful, transferred, literature_checked, reviewed | The highest rung with evidence |

## Edges (append-only)

`{kind, src, dst, evidence[], confidence, scope, provenance, score, time}`. The kinds are requires, enables, improves,
explains, contradicts, equivalent_to, generalizes, transfers_to, combines_with, failed_due_to and reactivated_by.
`dst` may be a tag (`tag:interpretation`) naming a prerequisite. An inferred edge carries a confidence below 1 and is
never treated as proven.

## Migration and integrity

- The schema version is in every record.
- A new schema version is a new `schema` string, and old records stay readable as they were.
- `Vault.verify()` runs the store's verification (event chain, derived state, every object's hash) and then checks
  every artifact's identity against its bytes.
- Backup and restore are the store's (`genesis store backup|restore`).
