# B15_R1 checkpoint record — follow-up from the clean-room rehearsal

Parent: `GENESIS_COMPLETION_CHECKPOINT_B15.zip`
(sha256 `bf5c1b2b0b1e542baee9a0263ce00bdc418f527c08170fc2b8a0b47fb0f4578b`, commit `6160d53`).

## Rehearsal of B15: NOT_REPRODUCED

`deployment/reproduce.sh --build-toolchain` was run against the B15 checkpoint, on
the build host only.

**Passed:**
- the checkpoint hash and manifest;
- the git history, compared file by file;
- the toolchain, built from GitHub, with every pin matching byte for byte and all
  known answers passing;
- the host check, which reported SUPPORTED.

**Failed:** the release matrix. 709 tests ran with 0 failures, but
`test_no_pickle_caches_tracked` skipped because the extracted checkpoint is not a git
checkout. An undeclared skip blocks the matrix, so the mandatory matrix depended on
hidden state.

Run by hand from the extraction, the reference computations matched.

## Change

`tests_genesis/test_gi6_legacy_paths.py`: outside git, the test checks every shipped
file rather than skipping. Evidence is in `audit/b15_rehearsal/`.

## Status

Unchanged from `B15_RECORD.md`. R-04 still needs:
- a second-machine run with operator attestation;
- the image digest;
- wheel hashes.

A second rehearsal against this checkpoint is stored beside it, not inside it.
