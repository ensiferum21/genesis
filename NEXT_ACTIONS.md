# Next actions (continuation after B20)

## Where things stand

- **Branch:** `continuation-b20-rx` (GitHub `ensiferum21/genesis`). It is the canonical B20_R11 line (`continuation-b20-repairs`, `36954d6`), with the recovery-branch work ported onto it, plus B20_R12, B20_R15 and B20_R16.
- **Checkpoints:**

| Checkpoint | Commit | Archive SHA-256 |
|---|---|---|
| B20 | `97fb233` | `44bbbbeb…2091` |
| B20_R1 | `972dbb6` | `b8e99c16…bbf4` |
| B20_R2 | `3c1089e` | `d5056b57…b304` |
| B20_R5 | `0989a4f` | `60d5c307…4ddb` |
| B20_R8 | `ae50d74` | `9f34fec8…334f` |
| B20_R11 | `36954d6` | see `archive` branch `SHA256SUMS` |
| B20_R16 | this record's commit | see `archive` branch `SHA256SUMS` |

  The recovery-branch checkpoints B20_RX1 and B20_RX2 are on `recovery-b20r1-partial`; their work was ported here.
- **Records:** `docs/checkpoints/B20_R1_RECORD.md` … `B20_R11_RECORD.md`, `B20_RX1_RECORD.md`, `B20_RX2_RECORD.md`, `B20_R12_RECORD.md`, `B20_R15_RECORD.md` and `B20_R16_RECORD.md`.

## Completed since B20_R11

| Batch | Work |
|---|---|
| CRPD-2b | Workspace pin revision with a hash-chained history; Lean-checked C4 pair-count bound (`PAIR_COUNT_LEAN`) |
| W22, W23, H06 (s15.1) | Derived primitives with reference expansions; fault-tolerant reasoning with quarantine (no majority vote); proof search keeps its failures |
| B20_R13, R14, RX3, RX3b, RX5 | GV4 on graph construction. No selection headroom. Capability headroom to the optimum, which builder LP/SAT components deploy (+0.63 to +1.38, replicated). No proposal headroom over compositions. GV4 reduces to component invention |
| B20_R12 | E1 under the user's decisions: time-matched baselines, custodian SELECT comparator, centred power, and the separately versioned family rule `e1-hard-v1`. Fair (CPU ratio 1.00), +0.97 per host on DEV, but **UNDERPOWERED**. `handoff/e1` v2 |
| B20_R15 | Replay contracts for the causal, internal-replication and priority levels. B14-OPEN-4 is closed pending review |
| B20_R16 | H08 s20.6: active-version pointer, rollback, inherited version revocation, resume gate |
| B20_R17 | s15.3: machine-generated relational decoders. One new decoder (the oriented 3-cycle) is Lean-checked; its DEV utility after cost is NO_UTILITY_AFTER_COST |
| B20_R18 | B20R8-OPEN-1: DEV comparison rows are bound to journalled executions (v2); v1 is retired |

## Resume

    git clone https://github.com/ensiferum21/genesis genesis-work && cd genesis-work
    git checkout continuation-b20-rx
    GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # pinned sources; the formal workspace uses the CRPD-2b pin
    export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
    python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc)

## Decisions needed from Daniel or a reviewer

1. **E1 (B20R12-OPEN-1).** The decided design cannot be powered on the `e1-hard-v1` family. The options are in `handoff/e1/README.md`:
   - a per-stratum power model (the statistician decides);
   - a rule version that also bounds a candidate-independent headroom;
   - retiring E1 at this design.

   Whichever is chosen, the reviewer still has to sign off the rule and both earlier decisions.
2. **GV4 study design** (`handoff/gv4/README.md`, DRAFT). The question is what counts as an invented component. The decision is needed before the s15.3 work below can become a study.
3. **CRPD-2b pin revision:** review.

## Next engineering, in order

1. **H06 s15.3 / W10: richer representation invention.** This is GV4-critical.
   - B20_R17 generated the first representation outside the menu, an oriented 3-cycle decoder. Its semantics and transport are Lean-checked, but its DEV utility after construction cost is NO_UTILITY_AFTER_COST.
   - Next, each family as its own preregistered step, with all attempts counted:
     - a versioned k ≤ 4 relational expansion;
     - partitions/quotients with proved transport conditions;
     - decompositions with verified witness composition.
2. **A Lean-package route for THEOREM_CHECKED.** (B20R8-OPEN-1 was repaired in B20_R18.)
3. **H08, the rest:** retention and negative-transfer measurement under a frozen protocol; paired research lineages for `sealed_improver_evaluation`.
4. **H11:** operations documentation and release review packaging.

## Needs external resources

These are BLOCKED_ENVIRONMENT here:
- PyPI and the Docker registry are unreachable from this workspace, so the R-04 wheel hashes and the image digest cannot be produced.
- A second machine and operator.
- An external time anchor.
- An independent reviewer, statistician and custodian (GV0, GV1, and every scientific gate).

## Claim ceiling

Engineering and DEV diagnostics only. No sealed task has been run on real panels. Better-improver remains UNESTABLISHED.
