# B20_R98 record (engineering), and the setup of B20_R98–R100

- **Run by:** the builder continuing the line on 22 Oct 2026 (the second session's work, B20_R66–R97, is the base).
- No claim, rule, comparator or package changes.

## The state-of-the-art toolchain, rebuilt in a new container

Built tools do not survive a container. On 22 Oct 2026 every external tool was rebuilt from its pinned source by its
own build script:
- MQLib;
- DeepDist;
- `tfx`, `tfxw` and `tfxw2`;
- the four other 2024 champions;
- the six 2026 entrants.

The GMP packages and the OR-Tools wheel came from Daniel, with the same SHA-256 as B20_R87 and B20_R76 record. Then:
- **Matched their pins byte for byte:** 13 binaries, the SGAT weight file, and the OR-Tools library files.
- **Did not match:** two binaries and one tree. Both kinds of mismatch are pin defects.

## Defect B20R98-PIN: two pins depended on the build environment, not on the tool

- **CP-SAT (`cpsat-v1`, B20_R76).** The pin was a digest over every file of the installed tree.
  - pip writes `*.dist-info/direct_url.json`, which holds the absolute path the wheel was installed from, and
    `RECORD` lists that file.
  - Installed from another folder, the pinned wheel gave 336 library files byte-identical to the wheel's members, and
    a tree digest `4e6f0f66…` against the pin `fb5ef9ac…`.
  - B20_R76's "a reinstall gives the same digest" held only for a reinstall from the same folder. A search of 874
    plausible folders did not recover the original one.
- **Aperture (2024) and Aperture 2026.** Their bundled SAT solvers' configure scripts write `date; uname` output into
  the binary ("Thu Oct 22 22:07:48 +08 2026 Linux vm …"). The GNU build-id note, a hash over the binary, then differs
  too.
  - Rebuilt twice, 40–50 minutes apart, each Aperture differed from its own first rebuild in exactly those bytes: 23
    and 25 (clock digits and the 20-byte build-id).
  - A search of every second of the original build window (20 Oct 2026, 03:00–08:00 UTC) found no stamp that
    reproduces the old pin, so the host or kernel string must differ too.

**Repair** (`scripts/b20r98_repin.py` documents it and checks every pin):
- `cpsat.tree_digest` leaves out pip's install-time metadata (`direct_url.json`, `INSTALLER`, `REQUESTED`, `RECORD` in
  `*.dist-info`). `cpsat.wheel_digest(WHEEL)` computes the same digest from the wheel's own members, so the pin is now
  a function of the pinned wheel alone. New pin `2010e03a…e47a`: tree and wheel agree.
- `maxsat.binary_digest`, used by every MaxSAT kind, zeroes a build stamp and, when there is one, the build-id before
  hashing.
  - Binaries without a stamp hash as before, so the other nine MaxSAT pins are unchanged.
  - The new Aperture pins are `862515f4…3fe9` and `8db73f91…f7b5`. Both rebuilds of each give them.
- **Disclosed:** that the new Aperture binaries equal B20_R87's outside those bytes rests on B20_R87's recorded
  rebuild check (22 bytes). The original binaries are not here to compare.

**Identity.** `cpsat.py`, `maxsat.py` and `maxsat2026.py` changed, so every descriptor of `cpsat-v1`,
`maxsat-anytime-v1`, `maxsat-anytime-2026-v1` and `maxsat-anytime-large-v1` has a new id. Evidence is never
rewritten. As B20_R67 did for its core edit, the record tests of earlier evidence compare what they recorded with
`b20r98_repin.pre_r98_id` and the PRE_R98 constants. These accept exactly the descriptor this code builds with the
three files as they were before, and nothing else:
- B20_R76 and B20_R77: the tree digest and the descriptors;
- B20_R92: every frozen descriptor.

A check: `pre_r98_id` of the four `maxsat-anytime-large-v1` descriptors B20_R98 builds equals B20_R97's recorded ids.

**Tests:**
- the CP-SAT pin does not depend on the wheel's folder, but still sees a library change;
- the pin equals the wheel's digest (when `GENESIS_ORTOOLS_WHEEL` names the wheel);
- the MaxSAT pin ignores a build stamp only;
- the record tests above, moved to the pre-R98 identities.

`tests_genesis` in full after the repair: see the commit.

## Setup (preregistered before any of them runs)

Each study runs alone on CPU 0, in the order B20_R100 prediction → B20_R98 → B20_R86 → B20_R99. B20_R100's scoring
runs after B20_R86 is recorded.

| Study | Script (SHA-256) | Question | Labels |
|---|---|---|---|
| **B20_R98** | `scripts/b20r98_harness_check.py` (`52369b92…57bb`) | Why do DeepDist-c and NuWLS-c-2026 end near half the best value on large hosts (B20_R97)? Five conditions on one host per B20_R97 cell: the kind in runc; direct with pipe; a file; the solver stopping itself; 60 s. Each solver's own reported cost is kept beside the model read | PARSE_MISMATCH, SANDBOX/INPUT/STOP/BUDGET_EFFECT per solver; headline HARNESS_DEFECT or NOT_THE_HARNESS (controls: DeepDist 2024, NuWLS-c-2026-UB) |
| **B20_R99** | `scripts/b20r99_headroom.py` (`405412a7…d33c`) | Daniel's discovery note (`docs/DISCOVERY_PLAN.md`): is there structure left where the searches stop, and is it describable? 16 fresh large hosts; exhaustive (r, r+1)-exchanges for r ≤ 2 at the states of tfxw, hybrid-swap-v1 and the four language programs; proved CP-SAT re-optimization of small neighbourhoods at tfxw's states; recognizers in a primitive grammar against random ones, fitted on 8 hosts and judged on 8 | NO_HEADROOM, HEADROOM_UNSTRUCTURED, HEADROOM_STRUCTURED |
| **B20_R100** | `scripts/b20r100_knowledge_map.py` (`5fff7aaa…0e33`), `src/genesis/autonomy/kmap.py` (`5eca6000…8a81`) | The first mechanism of `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`: does the knowledge map, Genesis's model of how well which method does where, with uncertainty, predict B20_R86 better than a naive baseline? Predictions written and committed before B20_R86 runs | MAP_BETTER, MAP_WORSE, NO_DIFFERENCE; coverage of its 90% intervals; whether unseen methods get wider intervals *and* keep coverage |

**Development looks, disclosed in each script.**
- B20_R99 moved from n63 to the large domain after looks on exposed hosts. On n63 every arm reached the same value.
  The verdict thresholds were written before those looks (`ba2b052`).
- B20_R100's replay over the recorded studies shaped the map. Its sd self-calibration was added after the first
  replay. The prospective part, B20_R86, is unseen.
- B20_R98 has no look at its outcome.

**Tests:**
- `test_harness_check.py` (6): hosts, conditions, the solver-claims parser, the label rule;
- `test_headroom.py` (11): exchanges against brute force, gap pieces, region re-optimization exact on a small case,
  a planted recognizer found and noise not, the verdict rule;
- `test_knowledge_map.py` (8): cells, wider intervals for unseen methods, self-calibration, the grid, the rule, refusal
  once B20_R86 is in the corpus.

## B20_R98 result: NOT_THE_HARNESS

Alone on CPU 0, 1,729 s (`evidence/harness_check_b20r98/`).

No condition under our control changes either collapsing solver's result:
- In every direct run, the model we read is the solver's own reported best.
- Pipe and file give identical values.
- The sandbox matches the direct run.
- DeepDist-c's own timeout alarm gives the same value as SIGTERM.
- 60 s adds at most 3%.

DeepDist-c reaches 40–62% of the best known value on all four hosts. NuWLS-c-2026 reaches 97–99% at n128 and 40–52%
at n256. NuWLS-c-2026-UB, the same code with its upper-bounding phase, does not collapse. The collapse is these solvers'
own behaviour on these instances and budgets, so B20_R97's margins over them stand as such. They do not speak to these
solvers on the Evaluation's families, hardware or budgets. The adaptation cell's work order for `deepdistc` (`fix
harness`) is answered: there is nothing in the harness to fix.

**Disclosed:** on the G(256, 0.5) host both controls ended 3% below their B20_R97 values at 10 s, and reached them with
5 s more. On the densest instance, a 10 s wall-clock budget sits where machine speed decides a few hundred edges; 10 s
comparisons there should allow a 3% band. This held on one host, below the preregistered rule.

Record tests (3).

