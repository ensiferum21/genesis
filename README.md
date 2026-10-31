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
| `GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip` (as `.part0` + `.part1`) | `469f7f0` | The line (branch `continuation-b20-rx`): B20_R73 plus B20_R74–R118 (state-of-the-art MaxSAT and max-cut tool chains; the large-graph engine and the autonomy layer; the knowledge map; the feedback contract v1 and v2; the Gset track with Genesis's max-cut engine `mcx-v1`, 40 of 54 best known values matched, none exceeded; three invention tests, NOT_DEMONSTRATED; the hidden-confounder causal benchmark and its calibration). Release matrix 1,948 tests, all OK, one declared skip; restore-verified (6,539 manifest entries; the bundle gives the same commit and tree) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip` (as `.part0` to `.part3`) | `012f133` | The line (branch `continuation-b20-rx`): B20_R118 plus B20_R119–R148. That covers the causal track: FCI, Genesis's active procedure and the adaptive experimental scientist (B20_R129, ADAPTIVE_SCIENTIST). It covers B20_R130 (CHOICE), the self-rewritable max-cut engine `mcx2` and its inventor (B20_R125–R128), and the Problem Compiler (B20_R133). It covers the vault, the cascade and the research queue (B20_R131), and the representation language (B20_R135, INVENTED_REPRESENTATION_BETTER). It covers the bottlenecks of invention (B20_R132, NOT_SHOWN, EXPRESSIVENESS) and the portfolio of discovery processes (B20_R148, NOT_SHOWN). Release matrix 2,260 tests, all OK, one declared skip; restore-verified (6,782 manifest entries; the bundle gives the same commit and tree) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R169.zip` | `5d7b7f0` | The line (branch `continuation-b20-rx`): B20_R148 plus B20_R149–R174. This adds expressiveness (the engine language Λ1, B20_R151 NOT_SHOWN; self-extension, B20_R152 NOTHING_ADMITTED; the planar replication, B20_R165 REPLICATED_WITH_SINGLE_ENGINE). It adds the Autonomous Research Architect (ARA-1; B20_R141 INVALID, B20_R167 ARA_CALIBRATED, B20_R144 NOTHING_ADOPTED). It adds the Frontier (F1–F6 machinery; B20_R156 FRONTIER_BETTER, B20_R157 PARTIAL, B20_R158 NOT_SHOWN). It adds the protected judge's first release of an engine Genesis's own search found (B20_R173 RELEASED, with its caveat), the synthesised-sense slice (B20_R136 NOT_SHOWN), and the Foundry's G2 and G4. B20_R163, R170, R172 and R174 and PT-1 are preregistered. Release matrix 2,664 tests (integration 2,127, legacy 282 with one declared skip, sandbox 28, certificates 43, formal 184), all OK, run in two parts and merged (`make_checkpoint.py --reports`). Restore-verified: 6,999 manifest entries; the bundle gives the same commit and tree (`GENESIS_COMPLETION_CHECKPOINT_B20_R169.restore_verify.json`). Made from a single-branch clone, so its bundle holds this line's history and tags only: 40 MB, against 289 MB for B20_R148's, which bundled other branches too |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R176.zip` | `2e7fd2f` | The line (branch `continuation-b20-rx`): B20_R169 plus the records of B20_R163 (F6), B20_R170 (G2), B20_R172 (G4), B20_R174, B20_R175 (F6b) and PT-1 (B20_R159), PT-2 (B20_R177) preregistered with its two amendments, and the obstacle loop's design. Release matrix 2,723 tests (integration 2,186, legacy 282 with one declared skip, sandbox 28, certificates 43, formal 184), all OK, run on CPU 0 in two parts and merged. Restore-verified: 7,079 manifest entries; the bundle gives the same commit and tree; the 7,077 tracked files match the archive (`GENESIS_COMPLETION_CHECKPOINT_B20_R176.restore_verify.json`) |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R184.zip` | `804f479` | **The current line** (branch `continuation-b20-rx`): B20_R176 plus PT-2's record (B20_R177, NOT_PROVED_OUT), the obstacle loop and its benchmarks (B20_R178, R180, R181: MILESTONE_DEMONSTRATED), Genesis inventing its own repair rules (B20_R182, R183: RULES_INVENTED), the fifth catalogue of random mutants and SR-2c preregistered (B20_R185), the repairs of B20R183-CATALOGUES and B20R184-PICKLE, and the matrix's sharding. Release matrix 2,840 tests (integration 2,303 in six shards, legacy 282 with one declared skip, sandbox 28, certificates 43, formal 184), all OK, run on CPU 0 and merged (`make_checkpoint.py --reports`); a first build at `652f36d` failed GI6-02 (B20R184-PICKLE) and wrote nothing. Restore-verified: 7,281 manifest entries; the bundle gives the same commit and tree; the 7,279 tracked files match the archive (`GENESIS_COMPLETION_CHECKPOINT_B20_R184.restore_verify.json`) |

Each zip contains the full source tree, a git bundle of the whole history, the release test-matrix report, and a SHA-256 manifest of every member.

`GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip` (140,663,690 bytes, SHA-256 `a1e5305d…6204`) is larger than GitHub's 100 MiB file limit, so it is stored in two parts. Rebuild it with
`cat GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip.part0 GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip.part1 > GENESIS_COMPLETION_CHECKPOINT_B20_R118.zip` and check the whole file's hash in `SHA256SUMS`.

`GENESIS_COMPLETION_CHECKPOINT_B20_R169.zip` (81,343,766 bytes, SHA-256 `dcd5a0fd…7112`) is under GitHub's 100 MiB limit and is stored whole.
`GENESIS_COMPLETION_CHECKPOINT_B20_R176.zip` (82,429,873 bytes, SHA-256 `43d8621b…bd81`) is stored whole too.

`GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip` (328,329,645 bytes, SHA-256 `bb89b23b…33e4`) is stored in four parts of at most 95 MiB. Rebuild it with
`cat GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip.part0 GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip.part1 GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip.part2 GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip.part3 > GENESIS_COMPLETION_CHECKPOINT_B20_R148.zip` and check the whole file's hash in `SHA256SUMS`.

**Reproduction of B20_R148 on the build host** (not a second machine; R-04 still needs an independent operator):
- `GENESIS_COMPLETION_CHECKPOINT_B20_R148.reproduction.json`: **REPRODUCED**. Every step passed, the release matrix ran 2,260 tests with one declared skip, and the reference results match. It used the harness of `continuation-b20-rx` `c6dd05e`, with the pinned OR-Tools wheel (SHA-256 `ebd5aea0…3c9a`).
- `..._attempt1.json`, the first attempt with the older harness: NOT_REPRODUCED, on two undeclared skips.
  - A record test needs the git history, which the extracted tree lacks.
  - The wheel was not passed.
  - Both were inputs of the clean room, not defects of the checkpoint. The harness now runs the matrix in the verified checkout of the recorded commit and passes the wheel.

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
