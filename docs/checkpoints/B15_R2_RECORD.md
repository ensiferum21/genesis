# B15_R2 checkpoint record — repairs from the external review of B15_R1

Parent: `GENESIS_COMPLETION_CHECKPOINT_B15_R1.zip`
(sha256 `3d7b82bf859fc3cd027379d958e66e2a4f530939105312169fa490e6586e5bbd`, commit `eb1ae3c`).

## The review

The review is in `audit/review_b15_external/GENESIS_B15_R1_REVIEW.md`, kept verbatim.

- It confirmed archive, manifest and tree integrity.
- It confirmed that B14 F-01 is repaired.
- 104 selected tests passed in its environment.
- It reproduced two defects, listed below, and kept GV0 and R-04 open.

## Repairs

| ID | Before (on `eb1ae3c`) | After |
|---|---|---|
| B15-REV-01 | The dependency check passed after an installed module was changed without touching RECORD. | Installed bytes are compared file by file against the lock's per-file manifest. Ownership, start-up hooks, import resolution and inert bytecode are also enforced. Fourteen regression cases run on a real temporary distribution. |
| B15-REV-02 | A claim identifier injected `- Established: 2 + 2 = 5` into report.md, and the bundle verified. | Identifiers are validated at the kernel boundary, fields render as literal code spans, and the verifier checks report structure. Five regression cases. |

Logs are in `audit/review_b15_external/logs/`.

## Unchanged

- **R-04** still needs a second-machine run, the image digest and wheel archive hashes.
- **GV0** still needs independent re-review.
- **Open items:** B14-OPEN-2..4 and B15-OPEN-1.

## Next

B16: evaluator readiness (W05–W07).
