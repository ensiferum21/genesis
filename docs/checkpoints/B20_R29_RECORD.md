# B20_R29 record: the second-machine reference results, repaired after the B20_R28 rehearsal

- **Run by:** the builder. Nothing here is independently reviewed.
- **Commit:** the B20_R29 commit that follows `72f6d87`.

## The finding

The B20_R28 checkpoint was rehearsed with the reproduction driver:
`deployment/reproduce.sh <zip> <sha> <work> --build-toolchain`, on the build host. That is a
clean room, but not a second machine.

| Step | Result |
|---|---|
| 1–3 | Hash, manifest (5,615 files), source history (commit `72f6d87`, tree matches) |
| 4 | Toolchain built from pins. The formal workspace matches its identity (artifact `be8f86a8…`). |
| 5 | Supported host |
| 6 | Release matrix: 1,196 tests, all OK, one declared skip |
| 7 | Reference results: **differ in `campaign.restored_events`**. Verdict **NOT_REPRODUCED**. |

## The cause

The reference campaign (`deployment/reference_run.py`) now writes 345 store events. The expected
value in `EXPECTED_RESULTS.json` was 339. Every other reference value matches:
- the generations digest;
- the latest program;
- attempts;
- replay;
- backup and restore;
- the certificate, Lean and known answers.

Bisected on the R-line:

| Commit | `restored_events` |
|---|---|
| `1095e42~1` (before B20_R16) | 339 |
| `1095e42` (B20_R16: active version pointer, rollback, revocation) | 345 |
| `a2f40af` (B20_R22) | 345 |
| `77a7b78` (B20_R24) | 345 |
| `72f6d87` (B20_R28) | 345 |

B20_R16 added the version-pointer events to every campaign, and this reference campaign is one of
them. `EXPECTED_RESULTS.json`, last updated in B20_R4, was not changed with it. The release
matrix never runs the reference campaign. Checkpoints B20_R16 to B20_R24 were restore-verified,
not rehearsed with the driver, so the drift went unnoticed until B20_R28's rehearsal.

## The repair

- **`deployment/EXPECTED_RESULTS.json`.** `campaign.restored_events` changes from 339 to 345.
  Nothing else changes: the full reference run differs only there.
- **A drift test.** `tests_genesis/test_reproduce.py::Reproduce.test_reference_campaign_matches_the_expected_results`
  runs the reference campaign in the matrix and compares the whole campaign section, so the next
  change to campaign records has to update the reference with it.

B20_R28's rehearsal report (NOT_REPRODUCED) is kept and delivered with that checkpoint. The
B20_R29 checkpoint is rehearsed the same way.

## Open

None from this batch. R-04 (a second supported machine) stays open: these rehearsals run on the
build host.
