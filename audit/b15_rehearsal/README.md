# B15 clean-room rehearsals (build host — NOT a second machine)

`deployment/reproduce.sh` was run as root on the build host against the B15
checkpoint, using a copy of the script taken from inside the checkpoint:

    reproduce.sh GENESIS_COMPLETION_CHECKPOINT_B15.zip bf5c1b2b…4578b /tmp/genesis-b15-repro --build-toolchain

## Rehearsal 1 (checkpoint B15): NOT_REPRODUCED

Steps 1–5 passed:

- the checkpoint hash and manifest matched;
- the git history matched the extracted tree, file by file;
- **the toolchain was rebuilt from fresh GitHub clones and the Lean release
  tarball, and every pinned hash matched, byte for byte.**
  `toolchain/install_tools.sh` ran in a new directory, and the known answers passed.
- The host check reported SUPPORTED.

Step 6 (the release matrix) failed, with 709 tests run and 0 failures. One
integration test, `test_no_pickle_caches_tracked`, skipped with "not a git
checkout". An undeclared skip fails the matrix. So the mandatory matrix had
depended on hidden state: being run inside a git checkout.

Step 7 was not reached. Run by hand from the extracted tree with the freshly built
toolchain, the reference computations matched `EXPECTED_RESULTS.json`.

**Repair (B15_R1).** Outside a git checkout, the test now checks every shipped
file instead of skipping.

Files:
- `rehearsal1_B15_report.json`
- `rehearsal1_B15_matrix.json`
- `rehearsal1_check_pins.log`

## Rehearsal 2 (checkpoint B15_R1)

This rehearsal is run after the B15_R1 checkpoint is made. Its report is stored
beside the checkpoint, as `GENESIS_COMPLETION_CHECKPOINT_B15_R1.rehearsal.json`,
because a checkpoint cannot contain its own reproduction.

Neither rehearsal is the R-04 second-machine acceptance. Both used the same host,
operator and kernel.
