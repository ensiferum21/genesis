# Next actions (continuation after B20)

## Where things stand

- **Branch:** `continuation-b20-rx` (GitHub `ensiferum21/genesis`). It is the canonical B20_R11 line (`continuation-b20-repairs`, `36954d6`), with the recovery-branch work ported onto it, plus B20_R12 and B20_R15–R35. B20_R25–R28 were built from the B20_R24 checkpoint's history bundle while GitHub was not linked; GitHub's branch is an ancestor.
- **Side branch:** `side-b21-equational` (`710d26d`) keeps work done on plain B20 in parallel with this line (equational generations W21/E4, definitional primitives, fault routes). It is not canonical. Only its Lean-replay hint repair was ported (B20_R25).
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
| B20_R24 | `77a7b78` | `8dcf9937…3633` (as received from Daniel on 15 Oct 2026; its history bundle is the base of B20_R25–R28) |
| B20_R28 | `72f6d87` | `06615761…3897` (release matrix 1,196 tests, all OK; restore-verified; driver rehearsal NOT_REPRODUCED at step 7, the stale reference repaired in B20_R29) |
| B20_R29 | `ba5318a` | `67fd8796…0ba8` (release matrix 1,197 tests, all OK; restore-verified; driver rehearsal on the build host **REPRODUCED**, not a second machine) |
| B20_R33 | `f09988e` | `1a2f6624…f496` (B20_R30–R33; release matrix 1,229 tests, all OK, one declared skip; restore-verified, 5,670 manifest entries; driver rehearsal on the build host **REPRODUCED**, not a second machine) |

  The recovery-branch checkpoints B20_RX1 and B20_RX2 are on `recovery-b20r1-partial`; their work was ported here.
- **Records:** `docs/checkpoints/B20_R1_RECORD.md` … `B20_R11_RECORD.md`, `B20_RX1_RECORD.md`, `B20_RX2_RECORD.md`, `B20_R12_RECORD.md` and `B20_R15_RECORD.md` … `B20_R35_RECORD.md`.

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
| B20_R24 | The user's family decision: versioned rule `e1-hard-v2` (time-matched baselines in the sandbox, a certification limit, a headroom bound of one design effect; no candidate input). It selects 3 triangle-free settings and no C4 setting. **E1 and E1b are both READY_FOR_REVIEW** (+2.57 and +2.63 per host, power 0.88 and 0.97 at 30 hosts). The first same-operator rehearsals were INVALID, from an evaluator defect (B20R24-OPEN-1, repaired: joint LP/SAT reference). The re-run rehearsals are **SUPPORTED** for both, and the judge agrees. Packages `handoff/e1` v3, `handoff/e1b` v2 |
| B20_R25 | Lean replay of E proofs: ground-hint generator v2 (ported from the side branch; v1 kept verbatim). On identical proof objects, Wolfram-axiom lemma chains go from 0/19 to **19/19**; Sheffer 11/11 under both |
| B20_R26 | s15.3 quotient family, attempt 1: per-host partition + exact block pattern, one parametric Lean transport theorem (CHECKED). DEV **NO_UTILITY_AFTER_COST** (−0.22 vs the menu) |
| B20_R27 | s15.3 decomposition family, attempt 1: exact parts + Lean composition theorem (CHECKED). DEV **NO_UTILITY_AFTER_COST** (−2.53 vs the same components on the whole host) |
| B20_R28 | E1b causal re-pilot on the `e1b` family: ablation +1.25, placebo +2.61, both **READY_FOR_REVIEW** (power 10 per stratum). Exposure addenda (126 hosts) next to the frozen E1/E1b packages |
| B20_R29 | The B20_R28 clean-room rehearsal found a stale second-machine reference: the reference campaign has 345 store events since B20_R16, `EXPECTED_RESULTS.json` still said 339 (NOT_REPRODUCED at step 7). Value updated, drift test added; the B20_R29 checkpoint is rehearsed with the driver |
| B20_R30 | B20R24-OPEN-2 measured: on 90 fresh `e1b` hosts the calibration certifies 86/90 within 60 s and the evaluator 90/90 at 600 s (unsupported upper bound 3.27%). **LIMITS_CONSISTENT** on the decided family; the decision stays with the reviewer |
| B20_R31 | s15.3 relaxation family, attempt 1: generated pattern inequalities (K5, W5) with Lean-checked validity. As a construction component **NO_UTILITY_AFTER_COST** (+0.19 per host over the plain LP greedy, below 0.5). Certification diagnostic: the LP floor meets the optimum on 82/90 hosts with the rows vs 72/90 without (10 of the 18 SAT-certified hosts) |
| B20_R32 | Exact certification over the generated rows (new checker with a Lean-bound registry; evaluator unchanged): sound, closes 2 of the 3 SAT-needing hosts of a fresh sample, but **NO_CERTIFICATION_UTILITY** prospectively (the sample had 3 such hosts against B20_R30's 18). Post hoc: an exact MILP (HiGHS) confirms all 21 SAT-certified optima in under 0.72 s each, which raises a strong-baseline question for E1/E1b |
| B20_R33 | Strong-baseline audit (B20R32-OPEN-2): on 60 fresh e1b hosts an exact MIP (HiGHS) proves every optimum within 0.36 CPU s. Against it E1 is **MIP_DOMINATES** (+0.75 per host) and E1b **NO_MATERIAL_DIFFERENCE** (+0.20, never above); both still beat their DSL baselines by ~2. Neither can be "beyond strong baselines" on this family (B20R33-OPEN-1) |
| B20_R34 | Probe for MIP-hard certifiable triangle-free settings (B20R33-OPEN-1): **NO_MIP_HARD_CERTIFIABLE_SETTING** in 7 settings near the 200-edge bound. Where the evaluator certifies, the exact MIP is optimal; where the MIP fails (dense planted), the evaluator certifies nothing, and (exploratory) the E1b candidate beats the MIP's 2 s incumbent there. A resume defect in the study scripts was found and R34's record repaired (B20R34-OPEN-1) |
| B20_R35 | Generated-row certification, enriched by setting (B20R32-OPEN-1): on 40 fresh hosts of the two settings the evaluator mostly fails, the route certifies **27/40 vs 7/40** within 60 s (McNemar p ≈ 1e-6; +18.5 s per host saved): **CERTIFICATION_UTILITY**. The first preregistered positive DEV utility of a machine-generated, Lean-checked component (in certification; classical bounds, no novelty claim) |

## Resume

    git clone https://github.com/ensiferum21/genesis genesis-work && cd genesis-work
    git checkout continuation-b20-rx
    GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # pinned sources; the formal workspace uses the CRPD-2b pin
    export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
    python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc)

## Decisions needed from Daniel or a reviewer

1. **GV3 sign-off: E1 and E1b** (`handoff/e1/README.md` v3, `handoff/e1b/README.md` v2). Both are READY_FOR_REVIEW on the `e1-hard-v2` family, and both same-operator rehearsals are SUPPORTED. **First decide B20R33-OPEN-1:** on this family an exact MIP solver is always optimal within 0.36 CPU s, so E1 (dominated) and E1b (within 0.2) cannot be "beyond strong baselines"; a SUPPORTED result would be scoped to time-matched DSL baselines. Options: accept that scope; add a MIP comparator; or move to a regime an exact solver cannot finish within budget. B20_R34 mapped the certifiable range: no such setting exists there (where the evaluator certifies, the MIP is optimal); a dense planted regime where the candidate beats the MIP's 2 s incumbent is uncertifiable by the current evaluator, so it would need a stronger certification route (branch-and-bound with exact LP-dual leaves, buildable here) or a plan without certified optima. To move to a real run:
   - a reviewer signs off the rule `e1-hard-v2`, the cost and comparator decisions, and freezes the DRAFTs;
   - a statistician signs off the centred power model (B19-OPEN-4);
   - an independent custodian runs SELECT, register and evaluate on its own machine.
2. **B20R24-OPEN-2:** align the calibration's certification limit (at least 90% certified within 60 s) with the plan's unsupported limit (at most 5% at 600 s) before a real run. B20_R30 measured both on 90 fresh `e1b` hosts: 86/90 at 60 s, 90/90 at 600 s (unsupported upper bound 3.27%), **LIMITS_CONSISTENT** on this family (`evidence/certification_budget_b20r30/`). The choice stays the reviewer's.
3. **GV4 study design** (`handoff/gv4/README.md`, DRAFT). The question is what counts as an invented component, and now also whether a component that helps *certification* counts toward a better improver: B20_R35 gives the first preregistered positive DEV utility of a generated, Lean-checked component, in certification (B20R35-OPEN-1); also whether to wire its checker into the evaluator (a trust-path change). The decision is needed before the s15.3 work below can become a study. After B20_R31, no invented component has DEV construction utility yet.
4. **CRPD-2b pin revision:** review.
5. **B20R33-OPEN-1** (see item 1).

## Next engineering, in order

1. **GV4: a component family with utility.** Five attempts in four families now have Lean-checked semantics, and none has DEV construction utility after cost:
   - relational ×2 (B20_R17, R19), retired;
   - quotient ×1 (B20_R26);
   - decomposition ×1 (B20_R27);
   - relaxation ×1 (B20_R31): +0.19 over the LP it strengthens, interval above 0, below 0.5; a certification signal (10 of 18 SAT-certified hosts become LP-floor certifiable, float diagnostic).

   B20_R32 built the exact certification route over the generated rows: sound, but NO_CERTIFICATION_UTILITY on an unenriched fresh sample (B20R32-OPEN-1). B20_R35, enriched by setting, found **CERTIFICATION_UTILITY** (27/40 vs 7/40 certified at 60 s; B20R35-OPEN-1). Candidates now: generated rows on 7 vertices (to lift coverage toward the 90% limit), and a construction use of the K5 rows in the dense regime.

   Each further attempt is its own preregistered step, and every attempt counts. Candidates:
   - a quotient attempt 2 on families whose best triangle-free subgraph is far from bipartite;
   - a decomposition that keeps the cut small or solves it jointly;
   - a different kind of component altogether (for example, symmetry or dominance rules; B20_RX1 H06 probe).

   The GV4 study design (`handoff/gv4/README.md`) waits on such a family.
2. **Registered interventions for the remaining candidate kinds** (`represent-and-repair-v1`, the formal successor kind), and a supervised child process in the runner, so the SAT finisher can become a pipeline component. Changing `invention/representations.py` or `candidates.py` changes the implementation identity, and so the descriptor ids, of the frozen E1/E1b candidates. This needs a versioned kind (for example `represent-and-repair-v2`), not an edit of v1.
3. **H08, the rest:** paired research lineages for `sealed_improver_evaluation` (needs a GV4 domain with headroom); custodian-held retention material.
4. **H11:** an independent reviewer works through `docs/checkpoints/B20_R20_REVIEW_BRIEF.md`; the operations runbook is `docs/OPERATIONS.md`.

Done since B20_R24: the E1b causal re-pilot on the `e1b` family (B20_R28); the certification-limit measurement for B20R24-OPEN-2 (B20_R30).

## Needs external resources

These are BLOCKED_ENVIRONMENT here:
- PyPI and the Docker registry are unreachable from this workspace, so the R-04 wheel hashes and the image digest cannot be produced.
- A second machine and operator.
- An external time anchor.
- An independent reviewer, statistician and custodian (GV0, GV1, and every scientific gate).

## Claim ceiling

Engineering and DEV diagnostics only. No sealed task has been run on real panels. Better-improver remains UNESTABLISHED.
