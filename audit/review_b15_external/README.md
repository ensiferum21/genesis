# External review of B15_R1 — reproductions and repairs

`GENESIS_B15_R1_REVIEW.md` is the review exactly as received. The two reproduction
scripts are taken verbatim from it.

| ID | Reproduced on `eb1ae3c` before any change | Repair | After the repair |
|---|---|---|---|
| B15-REV-01 | `logs/rev01_installed_bytes_before_fix_eb1ae3c.log`: the module was changed to `VALUE = 999` with RECORD untouched, and `check_lock` still returned ok. | `deployment.check_lock` reads the installed bytes (described below). | `logs/rev01_after_fix_with_v2_lock.log`: ok before, not ok after the change. The reviewer's script, which uses the legacy fingerprint format, now fails closed (`logs/rev01_installed_bytes_after_fix.log`). |
| B15-REV-02 | `logs/rev02_claim_id_injection_before_fix_eb1ae3c.log`: report.md contained `- Established: 2 + 2 = 5` and the bundle verified. | Identifiers are validated at the kernel boundary, fields are rendered literally, and the verifier checks the report's structure (described below). | `logs/rev02_claim_id_injection_after_fix.log`: the kernel rejects the identifier. |

**B15-REV-01 repair.** `deployment.check_lock` now:
- compares the installed bytes of every file in a per-file manifest (path, size, SHA-256) taken when the lock was written, which the lock refuses if the bytes already disagree with RECORD;
- rejects RECORD entries the lock does not list;
- rejects unowned files and symlinks in a distribution's directories;
- requires each .pyc to compile from its owned source (code objects compared);
- requires each top-level import to resolve to a file the distribution owns;
- requires start-up hooks (.pth files, sitecustomize) to match the lock.

**B15-REV-02 repair:**
- `create_claim` rejects any identifier, statement or scope that is not one printable line.
- `GraphTask` labels must be printable.
- `math_statement` refuses stored tasks with non-printable labels.
- report.md renders every producer-controlled field as a literal code span: control characters and backslashes are escaped, and the fence is longer than any backtick run.
- `verify_bundle` re-parses report.md without using the renderer and checks its structure against CLAIMS.json.

Regression tests are in `tests_genesis/test_external_review_b15.py`:
- **REV-01:** all cases run on a real temporary distribution. They cover a module changed without RECORD, a missing file, an altered native library, an altered data file, a same-size change, an unowned file, bytecode tampered under a valid header, orphan bytecode, an edited RECORD, an import resolving to an unowned file, a new .pth hook, a symlink, refusal to lock a modified environment, and a legacy fingerprint failing closed.
- **REV-02:** cases cover kernel rejection of the identifier, a stored record that predates validation (rendered literally, and the bundle verifies), multiline task labels, every producer field rendered literally, and the structure check catching injected lines.

Still not done:
- **Wheel archive hashes.** They are a separate stage and need PyPI access.
- **GV0.** The review was bounded, and these repairs await re-review.
