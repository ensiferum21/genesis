# Genesis: checkpoint and input archive

Kept by the builder on 13 Oct 2026 so that nothing depends on one workspace. This branch (`archive`) holds files only. The source history is on the other branches; see "Branches and tags" below.

## Checkpoints (`checkpoints/`)

| File | Commit | What it is |
|---|---|---|
| `GENESIS_COMPLETION_CHECKPOINT_B20.zip` | `97fb233` | The B20 checkpoint you supplied: the starting point of the continuation |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R11.zip` | `36954d6` | **The canonical line B20_R1–R11** (branch `continuation-b20-repairs`): repairs, CRPD, policy study, lineage, candidate custody, statement panels, replay contracts, curation pilot, E1 readiness |
| `GENESIS_COMPLETION_CHECKPOINT_B20_RX1.zip` | `3456797` | Recovery branch: CRPD-2b, W22, W23, H06 search failures, B20_R13 |
| `GENESIS_COMPLETION_CHECKPOINT_B20_RX2.zip` | `0db2e6c` | Recovery branch: B20_R14, RX3/RX3b capability pilots, RX4 E1 calibration, RX5 proposal pilot |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R16.zip` | `988c7f5` | The current line at B20_R16 (branch `continuation-b20-rx`): the canonical R11 line, the recovery work ported onto it, B20_R12 (E1 redo: UNDERPOWERED), B20_R15 (replay contracts for the causal, replication and priority levels) and B20_R16 (H08 rollback). Release matrix 1,139 tests, all OK; restore-verified (5,447 manifest entries; bundle clone gives the same commit and tree) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R21.zip` | `0bf3a96` | **The current line** (branch `continuation-b20-rx`): B20_R16 plus B20_R17/R19 (generated relational decoders: Lean-checked, NO_UTILITY_AFTER_COST), B20_R18 (DEV rows bound to executions), B20_R20 (THEOREM_CHECKED through theory packages), B20_R21 (external reproduction repeats a supporting evaluation; replication handoff), the review brief and the operations runbook. Release matrix 1,157 tests, all OK; restore-verified (5,476 manifest entries; bundle clone gives the same commit and tree) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R65.zip` | `821b743` | The other builder session's line through B20_R59–R65, supplied by Daniel as the B20_R65 handover (19 Oct 2026); restore-verified on arrival (6,093 manifest entries), release matrix re-run here: 1,459 OK (with the B20_R66 setup) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R73.zip` | `5f3dd5e` | The line (branch `continuation-b20-rx`): B20_R65 plus B20_R66–R73 (E1d at n60 replicated; registry v2 kind map fix; domain and physics-inspired baselines; E1d matched by tabu search and slower than simulated bifurcation by time-to-solution; physics move rules in the invention engine, a fair negative; a multiverse analysis). Release matrix 1,515 tests, all OK, one declared skip; restore-verified (6,151 manifest entries; the bundle gives the same commit and tree) |

Each zip contains the full source tree, a git bundle of the whole history, the release test-matrix report, and a SHA-256 manifest of every member.

`GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip` (140,663,690 bytes, SHA-256 `a1e5305d…6204`) is larger than GitHub's 100 MiB file limit, so it is stored in two parts. Rebuild it with
`cat GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip.part0 GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip.part1 > GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip` and check the whole file's hash in `SHA256SUMS`.

`GENESIS_COMPLETION_CHECKPOINT_B20_R11.zip` (SHA-256 `00aa4c70…cab7`) was re-attached by the user on 13 Oct 2026 and restore-verified: all 5,336 manifest entries match.

## Patches (`patches/`)

| File | Applies to | Content |
|---|---|---|
| `B20_R1_repairs_A-D.patch` | B20 `97fb233` | Review repairs A–D (4 commits) |
| `B20_R2_crpd_batch.patch` | after R1 | CRPD-1, 2a and 3 (3 commits) |
| `B20_R6-R8_statements_replay_contracts.patch` | canonical B20_R5 | R6–R8 (7 commits). Needs the R3–R5 history in the R11 zip |
| `B20_R9-R11_curation_screen_e1.patch` | canonical B20_R8 | R9–R11 (6 commits) |
| `B20_RX1_recovery.patch` | after R1 + CRPD | The recovery branch's first 11 commits |
| `B20_RX2_capability_e1.patch` | RX1 `3456797` | The 12 commits after RX1 |
| `B20_RX2_optimum_gap_probe.patch` | RX1 `3456797` | Superseded by `B20_RX2_capability_e1.patch` |

## Inputs (`inputs/`)

- The handoff "Genesis: B20 to the grand vision".
- The CRPD v3 proposal.
- The B20 review brief.
- The B20 clean-room rehearsal report (JSON and PDF).
- The two NEXT_ACTIONS files.

## Branches and tags

| Ref | What it is |
|---|---|
| `continuation-b20-rx` | **The current line**: the canonical R11 line plus the ported recovery work, B20_R12, R15 and R16, and later batches |
| `continuation-b20-repairs` | The canonical line, up to B20_R11 (`36954d6`) |
| `continuation-b20-r15-r16` | B20_R15 and R16 before their merge (kept for reference) |
| `recovery-b20r1-partial` | The continuation built in this workspace: B20 + R1 repairs + CRPD + the recovery-branch work |
| `continuation-b14` | B20 (`97fb233`) |
| `master`, `completion-p0-p2`, `b21-wip` | Branches from the B20 history bundle |
| tags `B20`, `B20_RX1`, `B20_RX2` | The checkpoint commits |

## Restore

```
git clone <this repo> genesis-work && cd genesis-work
git checkout continuation-b20-rx
GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # pinned toolchain, about 30 to 60 minutes
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc)
```

Check the file hashes with `sha256sum -c SHA256SUMS`.
