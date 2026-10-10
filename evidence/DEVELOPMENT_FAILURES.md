# Development failures and interventions

This is a developer-maintained account, not an independently anchored timeline.
All experiments in this delivery use public development material. No sealed
outcome was used to repair or select code. Host wall-clock timestamps are not an
independent chronology; the export label follows the session date.

1. The restored REV18 suite had 282 tests, with one failure and one skip. The
   separate-UID isolation test could not run because this host rejects setpriv
   UID switching. An explicit capability probe now skips it with an unverified
   isolation explanation. This is not a security pass. Original logs are retained.
2. The first custody repair suite hit that same environment restriction. Its
   output is retained as `custody-repair.*`.
3. The first integrated runtime suite found overlapping world identifiers in
   different research policies. IDs now include generation/policy/seed scope.
4. The next integrated suite found a mismatch between in-memory tuple scores and
   JSON-loaded list scores when reopening a completed campaign. The returned
   summary now uses canonical JSON normalization. Both failed suite logs remain.
5. The first full three-generation run completed 600 attempts and wrote three
   snapshots. Its subsequent independent CLI reopen failed with SQLite's
   `database disk image is malformed`. All three snapshots passed SQLite
   integrity checks; the live database failed. The run and its diagnostics are
   retained under `runs/dev_three_generations_wal_reopen_failed` and
   `evidence/sqlite_reopen_failure`. Its source identity predates the storage
   repair and it must not be resumed or used as the final verified run.
6. A small standalone stress probe did not reproduce the corruption in either
   WAL or DELETE mode. The root cause is unresolved. The single-writer store now
   uses DELETE journaling to avoid transfer/checkpoint dependence on WAL/SHM
   sidecars, checks database structure on reopen, and verifies snapshot structure.
   New tests cover large state plus snapshot/reopen and abrupt process exit after
   a committed transaction. This is a mitigation with regression evidence, not a
   proven root-cause diagnosis.
7. An attempt to reuse the original directory name after moving the failed run
   found residual directories and was rejected by the empty-destination guard.
   Its command logs are `final-three-generation.*`; the authoritative fresh run
   uses the distinct `runs/dev_three_generations_v2` directory.
8. The final new suite has 74 tests, 72 passing and two environment skips.
   The fresh three-generation run then completed all 600 attempts, reopened
   successfully, matched ten additional replay attempts, and passed live-database,
   snapshot and exported-artifact checks. See `VALIDATION_SUMMARY.json`.

No failed attempt was converted into a success receipt. Test fixtures for private
evaluation used temporary local signing keys and cannot establish independent
custody. The original accepted checkpoint and its historical audit status were
not changed by this work.
