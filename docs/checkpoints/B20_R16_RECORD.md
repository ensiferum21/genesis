# B20_R16 record: active version, rollback and version revocation (H08, s20.6)

Builder-run engineering batch, commit `1095e42`, merged in `aced775`. Fixture versions and real DEV campaigns; nothing here is independently reviewed.

## What changed

`src/genesis/versions.py` adds the pointer that says which frozen SystemVersion is in use, and the records that change it. Everything is append-only in the campaign store:

- `active_pointer` entities record each change: sequence, version, previous version, kind, reason and actor. The `active_version` state mirrors the last record and is written in the same transaction.
- `version_revocation` entities record revoked versions.

Rules (stable error codes):

| Rule | Code |
|---|---|
| Only a stored version whose id is its content digest, with a complete parent chain, can be active | VERSION_MISSING, VERSION_ID_MISMATCH, BROKEN_CHAIN |
| Neither the version nor an ancestor may be revoked | REVOKED |
| A move goes forward (ACTIVATE, to a descendant) or back (ROLLBACK, to an ancestor). A sideways switch is refused: roll back to the common ancestor first, so each change is its own recorded decision | NOT_ON_PATH |
| Every change records a reason and an actor | UNEXPLAINED |

- **Rollback never erases.** The version rolled away from stays stored and is reported ROLLED_BACK.
- **Revocation is inherited.** Revoking a version makes every descendant REVOKED_ANCESTOR. With the evidence kernel passed in, every kernel node that names an affected version is revoked too, so the kernel recomputes the effective claims.
- **Status is recomputed** from the records on every call: ACTIVE, RETAINED, ROLLED_BACK, REVOKED, REVOKED_ANCESTOR or INACTIVE.

Campaign integration:

- The initial version is activated once.
- Each DEV-retained generation moves the pointer inside the generation's own atomic commit.
- `run(resume=True)` refuses in two cases: when the active version is no longer the one the campaign was continuing from (ACTIVE_VERSION_CHANGED), and when it, or an ancestor, is revoked.

## Not done here

- Measuring legacy retention and negative transfer under a frozen protocol, with protected retention confirmation material. This needs a GV4 domain with headroom and an evaluation design.
- Paired research lineages for `sealed_improver_evaluation`, which stays refused.

## Tests

`tests_genesis/test_versions.py` covers:

- the rules with fixture versions;
- revocation reaching kernel claims;
- a real 2-generation campaign whose pointer follows the retained generations;
- a real crash after a generation commit, followed by a revocation: the resume is refused.
