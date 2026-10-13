# Review brief: the continuation line after B20 (B20_R1 to B20_R20)

This brief tells an independent reviewer, statistician or custodian what to check on the `continuation-b20-rx` branch. The builder ran everything listed here on one host, with fixture keys where keys appear. **Nothing here has been independently reviewed, run on sealed material, or promoted to a scientific claim.**

## Reproduce

```
git clone https://github.com/ensiferum21/genesis genesis-work && cd genesis-work && git checkout continuation-b20-rx
GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh            # pinned sources; CRPD-2b workspace pin
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc); about 25 min on 2 cores
```

Each DEV study below is one script, committed before it ran. It is re-runnable with `python3 scripts/<script>.py OUT_DIR`. Re-runs on a loaded host can differ in CPU-bounded search.

## 1. Trusted-core changes to review (engineering)

| Area | What changed | Code | Tests |
|---|---|---|---|
| Replay contracts (B14-OPEN-4) | Every evidence level now has a kernel replay contract. Exact, formal and DEV came in B20_R8. Causal (signed ablation/placebo receipts whose arms replay as one registered intervention), internal replication and priority came in B20_R15. DEV rows bound to executions came in B20_R18. A Lean-package route for THEOREM_CHECKED came in B20_R20. | `kernel/replay_contracts.py`, `kernel/evidence.py`, `kernel/receipts.py`, `kernel/roles.py` | `test_replay_contracts.py`, `test_b14_open4_contracts.py`, `test_evidence_kernel.py` |
| Custodian | Time-matched baselines (`dsl-time-matched-v1`). A SELECT-panel comparator chosen and signed by the custodian, then enforced at registration. Ablation/placebo registration only for registered interventions. The internal replicator's selection-key rule. | `candidates.py`, `custodian.py`, `cli.py` | `test_candidate_custody.py` |
| Calibration | Separately versioned study rules (`e1-hard-v1`). Records validate only under registered rules; study adoptions name their rule. | `calibration.py`, `configs/dev_calibration.json` | `test_calibration_rules.py` |
| Versions (H08 s20.6) | Active-version pointer, rollback, inherited version revocation (kernel nodes included), resume gate. | `versions.py`, `campaign.py` | `test_versions.py` |
| Formal workspace (CRPD-2b) | Pin revision with a hash-chained history; Lean-checked C4 pair-count bound (`PAIR_COUNT_LEAN`). | `formal_research/workspace.py`, `invention/pair_count.py`, `verification/certificates.py` | `test_workspace_pin_history.py`, `tests_formal/test_pair_count.py` |
| Fault tolerance (W23), primitives (W22) | Heterogeneous routes with quarantine (no majority vote); derived primitives with reference expansions. | `verification/reliability.py`, `primitives.py` | `test_reliability.py`, `test_primitives.py` |

Questions for the reviewer:
1. Do the B20_R15 contracts close B14-OPEN-4 without a path around them? Consider a producer-written verdict, wrong-role signatures, arms that are not one intervention, a replication by the same operator, or a priority record with an injected source.
2. Does the Lean-package route bind the statement's meaning? The package digest binds the definition modules, but the reviewer must read those definitions.
3. Is accepting another custodian's selection under an operator-named key (`accepted_selection_keys`) acceptable for internal replication?

## 2. Decisions only a reviewer or statistician can make

| # | Decision | Where |
|---|---|---|
| 1 | **E1 (B20R12-OPEN-1).** The decided design (time-matched baselines, custodian comparator, centred power, `e1-hard-v1` family) is fair (CPU ratio 1.00, +0.97 per host on DEV) but UNDERPOWERED. The options are a per-stratum power model, a rule version that also bounds headroom, or retiring E1 at this design. | `handoff/e1/README.md`, `evidence/e1_redo_b20r12/` |
| 2 | Sign-off of the user's E1 decisions: the time-matched cost contract, the custodian comparator rule, the centred power model (statistician), and the `e1-hard-v1` calibration rule. | `docs/checkpoints/B20_R12_RECORD.md` |
| 3 | **GV4 study design.** What counts as an invented component, and the domain (graph construction). | `handoff/gv4/README.md` (DRAFT) |
| 4 | The CRPD-2b workspace pin revision. | `toolchain/FORMAL_WORKSPACE_HISTORY.jsonl` |

## 3. DEV results to audit (none licenses a claim)

| Study | Result | Evidence |
|---|---|---|
| B20_R13 graph-construction selection headroom | NO_HEADROOM in all 7 settings | `evidence/graph_headroom_b20r13/` |
| B20_R14 optimum gap | Capability headroom to the optimum on S2, S3 and S7 | `evidence/optimum_gap_b20r14/` |
| B20_RX3, RX3b builder LP/SAT components | +0.63 to +1.38 per host, replicated | `evidence/capability_pilot_b20rx3/`, `capability_replication_b20rx3b/` |
| B20_RX5 proposal headroom over compositions | NO_PROPOSAL_HEADROOM | `evidence/proposal_pilot_b20rx5/` |
| B20_R12 E1 calibration and redo | `e1-hard-v1` selects 4 settings; UNDERPOWERED | `evidence/dev_calibration_e1_b20r12/`, `e1_redo_b20r12/` |
| B20_R17, R19 generated relational decoders (s15.3) | Lean-checked semantics and transport; NO_UTILITY_AFTER_COST (+0.19 and +0.125 per host against the menu) | `evidence/relation_invention_b20r17/`, `relation_invention_b20r19/` |

What to check for each study:
- that the script commit precedes its evidence commit;
- that the hosts are fresh and the exclusions hold;
- that budgets are matched, counting child-process CPU where it applies;
- that the verdict follows from the rows. The formal and genesis tests re-derive several verdicts.

## Claim ceiling

Engineering and DEV diagnostics only. GV0–GV8 are open. There are no sealed panels, no independent custodian and no second machine. Better-improver is UNESTABLISHED. E1 is not ready to register.
