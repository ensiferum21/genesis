# Next actions (continuation after B20)

## Where things stand

- **Branch:** `continuation-b20-rx` (GitHub `ensiferum21/genesis`). It is the canonical B20_R11 line (`continuation-b20-repairs`, `36954d6`), with the recovery-branch work ported onto it, plus B20_R12 and B20_R15–R23.
- **Checkpoints:**

| Checkpoint | Commit | Archive SHA-256 |
|---|---|---|
| B20 | `97fb233` | `44bbbbeb…2091` |
| B20_R1 | `972dbb6` | `b8e99c16…bbf4` |
| B20_R2 | `3c1089e` | `d5056b57…b304` |
| B20_R5 | `0989a4f` | `60d5c307…4ddb` |
| B20_R8 | `ae50d74` | `9f34fec8…334f` |
| B20_R11 | `36954d6` | see `archive` branch `SHA256SUMS` |
| B20_R16 | `988c7f5` | `c0a201b0…c37a` |
| B20_R21 | `0bf3a96` | `72e78fab…0796` (release matrix 1,157 tests, all OK; restore-verified) |
| B20_R23 | `e7fad0e` | `da3eb0fd…a354` (release matrix 1,164 tests, all OK; restore-verified; sent to Daniel directly while GitHub was disconnected) |

  The recovery-branch checkpoints B20_RX1 and B20_RX2 are on `recovery-b20r1-partial`; their work was ported here.
- **Records:** `docs/checkpoints/B20_R1_RECORD.md` … `B20_R11_RECORD.md`, `B20_RX1_RECORD.md`, `B20_RX2_RECORD.md`, `B20_R12_RECORD.md` and `B20_R15_RECORD.md` … `B20_R23_RECORD.md`.

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
| B20_R20 | B14-OPEN-4 remainder: THEOREM_CHECKED through a theory package (route lean-package-v1), replayed in Lean under a revocable route identity |
| B20_R21 | W24: external reproduction must repeat a supporting evaluation (stricter); replication handoff package (blocked: nothing to replicate yet, no independent operator) |
| B20_R19 | s15.3, second attempt: versioned k ≤ 4 relational decoders (twins merged). One new decoder is Lean-checked; NO_UTILITY_AFTER_COST (+0.125 per host against the menu). The ledger is reconciled |
| B20_R22 | H08 s20.6 complete in engineering terms: retention and negative transfer under a frozen protocol (protected material, measured once, within budget); a DEV demonstration finds NEGATIVE_TRANSFER of a campaign's first retained change |
| B20_R23 | Candidate kind `construct-pipeline-v1` (GV4 draft item 1) with a registered ablation and placebo of its LP guidance. **E1b** (the LP-guided candidate, under E1's decided design) is READY_FOR_REVIEW on DEV: triangle-free +1.79 per host (power: 12 per stratum), with causal follow-ups ready (ablation +1.42, placebo +2.53); C4 +1.00, but its causal pilot is UNSETTLED_REFERENCE. DRAFT package `handoff/e1b`; its SELECT step waits on a family decision |

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
2. **E1b host family (B20R23-OPEN-1)**, `handoff/e1b/README.md`. E1b is ready for review on DEV, but the custodian's SELECT step needs a study calibration, and `e1-hard-v1` applies to E1 only. The options are:
   - extend `e1-hard-v1` to E1b;
   - a new versioned rule that does not read the candidate;
   - approved builder-chosen settings (C1/C2, and C3 only with a certification budget fixed in advance);
   - no E1b.
3. **GV4 study design** (`handoff/gv4/README.md`, DRAFT). The question is what counts as an invented component. The decision is needed before the s15.3 work below can become a study.
4. **CRPD-2b pin revision:** review.

## Next engineering, in order

1. **H06 s15.3 / W10: richer representation invention.** This is GV4-critical.
   - B20_R17 and R19 generated two representations outside the menu: an oriented 3-cycle decoder, and a k = 4 decoder from the versioned v2 generator. Their semantics and transport are Lean-checked, but both are NO_UTILITY_AFTER_COST on DEV (+0.19 and +0.125 per host against the menu). The relational family is retired as a utility source there.
   - Next, each family as its own preregistered step, with all attempts counted:
     - partitions/quotients with proved transport conditions;
     - decompositions with verified witness composition.
2. **E1b, once the family is decided:** calibrate under the decided rule, adopt study `e1b`, re-pilot if the settings change, and regenerate `handoff/e1b`. Then run a same-operator rehearsal of SELECT, register, evaluate and judge with fixture keys, as for E1 in B20_R12.
3. **Registered interventions for the remaining candidate kinds** (`represent-and-repair-v1`, the formal successor kind), and a supervised child process in the runner, so that the SAT finisher can become a pipeline component. (B20_R23 registered the LP guidance of `construct-pipeline-v1`; the Lean-package route for THEOREM_CHECKED was added in B20_R20.)
4. **H08, the rest:** paired research lineages for `sealed_improver_evaluation` (needs a GV4 domain with headroom); custodian-held retention material. (Retention and negative transfer were added in B20_R22.)
5. **H11:** an independent reviewer works through `docs/checkpoints/B20_R20_REVIEW_BRIEF.md`; the operations runbook is `docs/OPERATIONS.md`.

## Needs external resources

These are BLOCKED_ENVIRONMENT here:
- PyPI and the Docker registry are unreachable from this workspace, so the R-04 wheel hashes and the image digest cannot be produced.
- A second machine and operator.
- An external time anchor.
- An independent reviewer, statistician and custodian (GV0, GV1, and every scientific gate).

## Claim ceiling

Engineering and DEV diagnostics only. No sealed task has been run on real panels. Better-improver remains UNESTABLISHED.
