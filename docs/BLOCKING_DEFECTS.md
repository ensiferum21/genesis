# Blocking defects (registered at the start of B14)

Source: reviewer roadmap "Genesis: what remains to reach the grand vision"
(baseline `GENESIS_COMPLETION_CHECKPOINT_B13.zip`, commit `82aa557`, tag `b13-baseline`).
Scientific promotion is blocked until each is closed by an adversarial regression
test and independent review (gate GV0).

| ID | Defect | Reproduced on B13 here | Status |
|---|---|---|---|
| R-01 | Evidence kernel accepts a valid envelope without schema, role-to-kind authorization or claim binding; one envelope in three wrapper nodes counts as three generations | yes — `audit/reproductions/logs/b13_baseline_82aa557.log` (R-01a, R-01b ATTACK_SUCCEEDED) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-02 | Release bundle exports stored claim levels and ignores revocation; `verify_bundle` returns ok | yes — same log (R-02 ATTACK_SUCCEEDED, `verify_ok: true`) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-03 | World loop / IR drop the DRAT proof and full upper certificate; no checker-only replay | source inspection (not an exploit) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-04 | Deployment not reproducible: placeholder image digest, Python 3.12 lock vs 3.13 run, containment needs a supporting host | environment finding | WORKED IN B15; SECOND-MACHINE ACCEPTANCE AND IMAGE DIGEST OUTSTANDING |

Reproduction command (run from the repo root against any tree):

    PYTHONPATH=src python3 audit/reproductions/r01_r02_b13.py

The script uses the B13 fixture hook (`kernel._load_roles = ...`) on purpose so the
original log stays meaningful. Post-repair regression tests live in
`tests_genesis/test_acceptance_regressions.py`.

## B14 outcome

- After the repair the original script reports every attack blocked
  (`audit/reproductions/logs/after_r01_r02_repair.log`).
- An internal red-team pass on the first repair found eleven further ways
  through (four critical); a second pass on the repaired tree found twelve more
  (two critical); a third pass found nine more (one critical). All are
  repaired with regression tests; see `audit/redteam_b14/README.md`,
  `audit/redteam_b14_round2/README.md` and `audit/redteam_b14_round3/README.md`. The
  reviewers were fresh agents under the same operator, so this is not the
  independent source review GV0 requires — and three rounds that each found
  critical issues are a reason to expect more.
- R-04 remains OPEN (main work in B15). B14 only fixed packaging consistency
  (networkx declared in `pyproject.toml`) and made undeclared test skips fail.

| ID | Item still open | Needs |
|---|---|---|
| R-04 | Supported deployment: what B15 could not do here — the pinned image digest (no registry), wheel download hashes (PyPI denied), and the second-machine run of `deployment/reproduce.sh` with its operator's attestation | registry and PyPI access, a second machine |
| B14-OPEN-1 | ~~Custodian did not verify request facts against the campaign export~~ — CLOSED in B14 (round-2 C1): the custodian rebuilds the export and checks campaign, source and domain | — |
| B14-OPEN-2 | ~~Selective reporting across candidates or campaigns~~ — REPAIRED IN B16, PENDING REVIEW: the custodian assigns the hypothesis family (evidence kind × domain at that custodian), enforces its declared size, publishes a signed hash-chained registration log, and Holm uses exactly the family results published before each evaluation (checked at preflight). Scope: one custodian; a researcher using several custodians is outside it | W06/W07 |
| B14-OPEN-3 | `sealed_improver_evaluation` and `sealed_generation_evaluation` are refused by the custodian until a research-lineage protocol can be checked from the export | W21 |
| B14-OPEN-4 | FINITE_CERTIFIED, THEOREM_CHECKED, causal, internal-replication, DEV_ONLY and priority levels have no replay contract and are unreachable (fail closed) | W03/W05/W08 |
| B14-OPEN-5 | ~~Report prose linted against the bundle-wide ceiling~~ — CLOSED after the external review (F-01): report.md is derived from per-claim current wording; caller prose is checked at the floor. Still open: ladder/world-loop internal reports lint against fixed levels (they are not exported as claims) | W02 |
| F-01 (external review) | ~~A requested optimum exported as the claim's statement at WITNESS_VALID~~ — REPAIRED: requested vs established wording separated; see `audit/review_b14_external/` | pending re-review |
| GV0 | Independent source review of R-01..R-03 and the F1–F11 repairs | an auditor outside the research operator |

## B15 outcome (R-04, W04)

Done on the build host, with regression tests:

- **Platform.** One Python version, 3.13, across `pyproject.toml`,
  `requirements.lock`, the Containerfile and the runtime. The lock is the full
  transitive closure with wheel-content fingerprints. The supported platform is
  data, and `genesis platform check` checks a host against it.
- **Toolchain.** Rebuilding the pinned commits elsewhere used to give different
  zstd, CaDiCaL and E binaries (embedded paths and dates). They are now
  byte-reproducible with `toolchain/build_reproducible.sh`. The pins changed
  only through the new hash-chained, known-answer-gated revision protocol.
- **Roles.** A root sandbox launcher serves one unprivileged worker UID. It
  checks the peer with SO_PEERCRED and enforces ceilings, allowlists and a
  budget, and its log is anchored by the worker's receipts. The research
  worker no longer needs root; this was demonstrated end to end, including a
  Lean check from UID 65534.
- **Crash consistency.** Faults are injected by real process death at 14
  points. Repairs found while doing this:
  - a torn CAS object would have blocked that object forever;
  - an interrupted export zip or snapshot left a torn file under its final
    name;
  - an interrupted sealed evaluation left no receipt at all (now `recover`
    publishes one, INVALID unless complete);
  - an interrupted DEV campaign could only be aborted (now resumable);
  - a second export at the same event head failed.
- **Backup and restore.** Both are verified; a restore can be pinned to a head
  recorded elsewhere.
- **Second machine.** `deployment/reproduce.sh` verifies a checkpoint, then
  runs the host check, the release matrix and deterministic reference
  computations, and writes a report for the second machine's operator to
  attest.
- **Internal red-team pass.** It found five issues, all repaired:
  - `recover` adopted any receipt file;
  - backups dropped quarantined databases;
  - restore followed a symlinked destination;
  - the pin history could be re-initialised;
  - divergence on resume needed to fail closed.

  See `tests_genesis/test_redteam_b15.py`.

Still open for R-04:

- the container digest;
- wheel download hashes;
- an independent second-machine run.

New residual:

- **B15-OPEN-1.** A custodian who never calls `recover` leaves a registered
  anchor without a receipt. That is visible only to someone who holds the
  anchor (W06: a published registration log).

## External review of B15_R1 (B15_R2)

The review is in `audit/review_b15_external/`. It confirmed that the B14 F-01 repair
holds, and it reproduced two new defects on `eb1ae3c`.

| ID | Defect | Status |
|---|---|---|
| B15-REV-01 | The dependency check hashed RECORD's strings, never the installed files, so a modified importable package passed. | REPAIRED IN B15_R2, PENDING RE-REVIEW. Installed bytes are verified file by file, along with ownership, bytecode, import resolution and start-up hooks. |
| B15-REV-02 | A claim identifier containing newlines and Markdown injected an `Established` line into report.md, and the bundle still verified. | REPAIRED IN B15_R2, PENDING RE-REVIEW. Identifiers and texts are validated at the kernel, every field is rendered as a literal code span, and the verifier checks report structure. |

The review keeps GV0 and R-04 open. Wheel archive hashes still need PyPI access.

## B16 outcome (W05–W07)

- **B14-OPEN-2 (multiplicity).** Repaired, pending review. The custodian assigns
  the hypothesis family itself, so a requester cannot pick a fresh family per
  candidate. A family cannot exceed its declared size. Analysis plan v2 applies
  Holm with exactly the published results of the family. Release preflight checks
  all of this against the custodian-signed registration log.
- **B15-OPEN-1 (unrecovered registrations).** Repaired. The registration log is
  public, and every registered evaluation without a result is listed as OUTSTANDING
  for anyone to see. In the analysis an outstanding member counts as p = 1, which is
  conservative.
- **New residual: B16-OPEN-1.** There is no external time anchoring. The anchor
  time, the decision record's FROZEN status and the log order are all attested by
  the operator. An RFC 3161 or transparency-log anchor needs a network service that
  this host cannot reach.
- **New residual: B16-OPEN-2.** The power analysis rests on a modelling assumption,
  the headroom-limited integer-improvement model with a design effect of 0.5 edges
  per task. It needs independent review (see `evidence/study_design_b16/STUDY_DESIGN.md`).

## B17 outcome (W08, first theory-package path)

The exit "real generated reusable Lean artifacts replay" is met by the builder only:
`evidence/formal_research_b17/replay.json` reports REPLAYED. An independent replay is
outstanding (see `docs/checkpoints/B17_REVIEW_BRIEF.md`).

| ID | Residual | Needs |
|---|---|---|
| B17-OPEN-1 | Proof strategies are builder-written recipes. Search chooses among them and fills in binders and library lemmas, but it does not invent strategies. Two true statements stay UNRESOLVED. | learned or open-ended proof search (W18, W20) |
| B17-OPEN-2 | Workspace artifacts are byte-identical across two builds on one host only. | the R-04 second machine |
| B17-OPEN-3 | The package is elementary rediscovery. The method is sound but not tight on DEV (gap 1–9 edges) and certified no optimum. W11's done-when (a structural result used by a solver on fresh tasks) is not met. | W11, W13 |

## B18 outcome (W09–W12)

The exit, "typed concepts, explicit worlds and checked semantics", is met by the builder
only, on DEV. `evidence/invention_b18/replay.json` reports all eight packages REPLAYED.
Independent review is outstanding; see `docs/checkpoints/B18_REVIEW_BRIEF.md`.

| ID | Residual | Needs |
|---|---|---|
| B18-OPEN-1 | W09 ran on a Genesis-generated history library, not a historical Mathlib cutoff. The recovered concept is a known abstraction (`Antitone`). | an ingestion study over a dated library snapshot |
| B18-OPEN-2 | The W10 grammar has vertex-class decoders only. The usefulness evidence is DEV-only, against per-task strongest baselines. | B19 sealed evaluation (E1) |
| B18-OPEN-3 | W12 worlds take assumptions over hosts only. `WD.Bipartite` fixes a vertex range to be decidable in Lean. "max degree 1 → triangle-free" stays unresolved. | richer world semantics, learned proof search |

## B19 outcome (W13–W17; E1/E2 readiness)

The exit, "prospective usefulness accepted or branch rejected", is met by the builder
only, on DEV:
- usefulness evidence for W13–W15;
- the Ghost Census branch retired for its scope (W16);
- literature and priority records (W17);
- E1 and E2 drafts.

Acceptance needs independent review and a custodian; see
`docs/checkpoints/B19_REVIEW_BRIEF.md`.

| ID | Residual | Needs |
|---|---|---|
| B19-OPEN-1 | W13 builds only the relaxation route (LP dual certificates + SAT/DRAT). The joint method's advantage over the B13 reference loop is DEV-only. | symmetry reduction, kernelization, continuation; a sealed comparison |
| B19-OPEN-2 | W14: KG* was chosen after EIG failed, and it beats fixed and random selection on fresh DEV pools only. The hypotheses are a finite method set. | a sealed comparison with KG* frozen first; richer hypothesis spaces |
| B19-OPEN-3 | The E1 candidate (represent-and-repair) is not a DSL program, and the custodian's evaluator cannot run it. | an evaluator adapter, with trusted-path review |
| B19-OPEN-4 | The E1 power analysis uses a centred-headroom option added in B19, because the B16 model reported INFEASIBLE for a near-ceiling candidate. | a reviewer to accept or reject the correction (with B16-OPEN-2) |
| B19-OPEN-5 | The W16 decision covers equational theories that E solves from the axioms alone. Lean replay of E proofs does not cover Skolem functions with arguments, or steps that the tactic cascade cannot close. | a family where E needs help; a fuller replay |
| B19-OPEN-6 | The W17 quotes come from a summarising fetch tool and are unconfirmed (ADJ-1 to ADJ-4 pending). The search record is small. The E2 design is a draft without a sealed statement generator. | a person to adjudicate; a priority reviewer; a custodian-side generator |

## B20 outcome (W18–W20; E3)

The exit, "better-improver claim supported or explicitly unestablished", is met in its
second form: **UNESTABLISHED**. B20 built and tested the research-learning machinery on
DEV. See `docs/checkpoints/B20_REVIEW_BRIEF.md`.

| ID | Residual | Needs |
|---|---|---|
| B20-OPEN-1 | The learned research policy does not beat fixed rules on DEV (1W/7T/0L vs fixed) and its predictions are nearly uninformative. Most systems leave research no headroom. | harder domains, better features, a sealed E3 study |
| B20-OPEN-2 | Macros replay faithfully and compress, but they do not beat plain research on unseen seeds, and strict transfer across axiomatizations fails at the first hard step. | macro semantics robust to transfer; generative compression that helps |
| B20-OPEN-3 | Research outcomes on Wolfram's axiom depend on load-sensitive E time limits and on the first attempts. The main budget rule starved 10-second attempts. Single runs are noisy. | repeated runs on a quiet host; budget rules per attempt cost |
| B20-OPEN-4 | Memory and curriculum show no effect without headroom, and only parity with plain research where there is headroom. | a regime where reuse across runs matters |


## External review of B20 (B20_R1)

The external B20 review (handoff "Genesis: B20 to the grand vision", 12 October 2026)
reported four findings. Each was reproduced from the stored evidence, without a prover,
before any repair: `python3 audit/review_b20/reproduce_b20_review.py` writes
`audit/review_b20/findings.json`. Repairs keep the original observations as history; none
of them makes the B20 comparison valid after the fact.

| ID | Finding | Reproduced | Status |
|---|---|---|---|
| B20-REVIEW-01 | Three evaluation statements (four slots: Huntington 201, 203, 204 ×2) also occur in training development targets (seed 103). The global holdout property is false for those records. | yes (exact text match) | REPAIRED IN B20_R1, PENDING INDEPENDENT REVIEW. `learning/partitions.py`: one study-wide exposure set, EXACT/ALPHA/INSTANCE/GENERALIZES screening, quarantine, `INSUFFICIENT_DISTINCT_MATERIAL`, insertion screen on every route. The B20 comparison stays contaminated. |
| B20-REVIEW-02 | Research CPU above the nominal cap: learned 1.93 s vs fixed 1.01 s under 1 s (Huntington 204); 33 of 40 W19 runs exceed their cap, every Sheffer run by up to 63%. | yes | REPAIRED IN B20_R1, PENDING INDEPENDENT REVIEW. `learning/budget.py`: account opened before preparation, reservations before launch, cgroup-metered outer kill, no rounding up, late results never credited, interrupted reservations charged. |
| B20-REVIEW-03 | The 67/68 Lean replays cover fixed/learned on the first evaluation seed only: 67 of 778 reported target successes (8.6%). Other proof objects were not stored. | yes | REPAIRED IN B20_R1 (forward only), PENDING INDEPENDENT REVIEW. `learning/custody.py`: custody before counting, replay from custody, prover-reported / checked / eligible reported separately. Old uncovered scores cannot be checked retroactively. |
| B20-REVIEW-04 | All 12 B19 joint upper bounds (LP_DUAL_EXACT, 11 closing the gap) were exported without the witness or the exact LP certificate; the SAT fallback discarded CNF/DRAT bytes. | yes | REPAIRED IN B20_R1, PENDING INDEPENDENT REVIEW. Certificate bundle v2, a separate LP checker, kernel promotion and revocation; a custody-complete DEV re-run is a new execution (`evidence/obstruction_custody_b20r/`). The B19 record is unchanged. |
| B20R-NEW-01 | Found while repairing B20-REVIEW-02: E writes `%% SZS status ResourceOut`, which the wrapper parsed as `ERROR`. | yes | REPAIRED IN B20_R1. Labels only: B20 counted PROVED from THEOREM, so recorded scores are unaffected. |

B20-OPEN-1 to B20-OPEN-4 stay open. The repaired harness has not yet been used for a
fresh E3 comparison, so nothing about the better-improver question has changed.

## B20_R2 outcome (adopted CRPD subset, H02 exit run, H05/H08 first parts)

Builder-run, DEV only, nothing independently reviewed. See `docs/checkpoints/B20_R2_RECORD.md`.

| ID | Residual or finding | Needs |
|---|---|---|
| B20R-OPEN-1 | Fresh E3 on the repaired harness (`evidence/e3_fresh_b20r/`): learned vs fixed 0W/2T/6L. With preparation charged, the learned policy's feature computation (pool × development-target overlap) uses ~0.6 s of the 0.65 s Huntington cap, so it attempts no proof; on Sheffer it builds the largest libraries without gain. Training costs 75 s CPU against caps of 1.85 s / 0.65 s. | a redesigned policy (cheaper features, per-attempt cost model) under a NEW study; never a patch to this one |
| B20R-OPEN-2 | The stored DEV campaign export cannot support counting generations (`audit/lineage_b20r/report.json`): SELECT totals not exported, candidates not bound to journal attempts, no per-run account, declared component differs from the actual version diff (generation 1 changed only its library). | campaign export carrying lineage records; then wire `lineage.lineage_problems` into request checking (B14-OPEN-3) |
| B20R-OPEN-3 | The C4 pair-count bound (`graphs.universal_upper`) is still an unchecked THEOREM bound: proving it needs Finset big operators outside the pinned workspace import closure. | Daniel's decision on a reviewed workspace pin revision |
| B20R-OPEN-4 | The trusted candidate runner (`candidates.py`) is not wired into the custodian; request/receipt schemas carry no candidate descriptor. | a reviewed schema extension (B19-OPEN-3) |
| R-04 (re-checked) | From this workspace on 12 October 2026, PyPI does not resolve and the Docker registry is refused by the egress proxy: wheel hashes and the image digest remain BLOCKED_ENVIRONMENT. | registry and PyPI access, a second machine |

Closed or answered in B20_R2 (DEV scope): CRPD-3 orbit-sensitivity probe NOT_DETECTED on Sheffer,
Wolfram and Huntington (outcomes deterministic at fixed limits on a quiet host, relevant to B20-OPEN-3);
H02's exit run executed with all runs within cap and zero custody problems.

## B20_R3 to B20_R5 outcome (redesigned policy study, H08 lineage in campaigns, H05 custodian wiring)

All three batches were run by the builder on DEV material and have not been independently reviewed. Details are in `docs/checkpoints/B20_R3_RECORD.md`, `B20_R4_RECORD.md` and `B20_R5_RECORD.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B20R-OPEN-1 | ANSWERED ON DEV, NEGATIVE. The redesigned cost-aware policy was run under a new frozen study (`evidence/e3_costaware_b20r3/`). It fixed the preparation cost (15 ms against 481 ms) but came out INFERIOR_DEV against the fixed policy: 2W/3T/3L, mean −5.5. The test material is NOT_DISCRIMINATING: ORACLE − fixed averages 0.125. | superseded by B20R3-OPEN-1 and B20R3-OPEN-2 |
| B20R3-OPEN-1 | The E3 family leaves no room for a better selection policy (`evidence/headroom_pilot_b20r3/`): ORACLE − FIXED@CAP is at most 1 of 12 targets on six systems and three target ranges. On Huntington, smallest-first already picks lemmas in the oracle's order. | a task family, chosen on DEV, where the lemmas that matter are not the smallest ones and libraries change outcomes. Only then a new frozen study. |
| B20R3-OPEN-2 | Lemma libraries are not monotone for E. Adding one true lemma took Huntington@614 from 7/8 targets to 0/8; adding idempotence restored 8/8 (`harmful_library_diagnostic.json`). Per-lemma usefulness scores, which both learned designs use, cannot see this interaction. | a library-level selection objective (interaction-aware, for example greedy marginal gain on development targets) in the next design |
| B20R3-OPEN-3 | Diagnostic gap: the formal checker keeps only the last 6000 characters of a module log. When linter warnings flood the log, the error lines drop out of the replay record. The B20_R3 trace was recovered by re-running with full logs. Verdicts are unaffected. | keep error lines separately, or silence linters in generated proof modules; this needs a reviewed change, because the checker's identity will change |
| B20R-OPEN-2 / B14-OPEN-3 | REPAIRED IN B20_R4, PENDING INDEPENDENT REVIEW. Campaigns now write native lineage records, and the custodian accepts a `sealed_generation_evaluation` request only for a transition in the qualifying chain. `sealed_improver_evaluation` is still refused. The stored B20 export is unchanged and still yields no qualifying chain. | independent review; fresh panels for each transition |
| B20R-OPEN-4 / B19-OPEN-3 | REPAIRED IN B20_R5, PENDING INDEPENDENT REVIEW. Request v4, receipt v4 and claim binding v2 were added. The custodian rebuilds descriptors from the frozen export and runs every arm in the OCI sandbox. The s13.3 acceptance list passes end to end (`tests_genesis/test_candidate_custody.py`). | independent review |
| B20R5-OPEN-1 | Handoff s13.3 is not built: there is no sealed theorem generator and no frozen formal-research-successor candidate kind. Without them, an E2/E3 study cannot be evaluated by a custodian on private statements. | custodian-side statement generation committed before candidate access, with preregistered inclusion rules; a third candidate kind |
| B20R5-OPEN-2 | v4 requests cover `sealed_evaluation` only. Transfer, generation and improver evaluations of non-DSL candidates are refused. | a further reviewed schema step once a non-DSL lineage exists |

## B20_R6 and B20_R7 outcome (family search, sealed statement panels)

Both batches were run by the builder on DEV material, with fixture keys. See `docs/checkpoints/B20_R6_RECORD.md` and `B20_R7_RECORD.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B20R3-OPEN-1 | STILL OPEN. The B20_R6 pilot (`evidence/family_search_b20r6/`) found NO_HEADROOM on Robbins' basis (floor: libraries change nothing) and on Boolean rings (near ceiling). Eight systems have now been tried. | a family where library curation or premise selection has measurable headroom, measured against a reference that searches library subsets |
| B20R3-OPEN-2 | REPLICATED. On Boolean rings with 8–10 nodes, FIXED@CAP (34 lemmas) proves 11/12, while EXHAUST (132 lemmas) proves 8/12, the same as EMPTY. The ORACLE built from exhaust proofs inherits the interference, so it is not an upper bound. | curation and premise selection as the next action space (handoff s19.2) |
| B20R5-OPEN-1 | REPAIRED IN B20_R7, PENDING INDEPENDENT REVIEW. The custodian now generates sealed equational panels and runs the candidate kind `formal-research-successor-v1` in the sandbox. Every claimed proof is replayed in Lean, by the custodian and again by the judge. | independent review |
| B20R7-OPEN-1 | Verification (Lean replay) CPU is not metered; only wall time is recorded. | cgroup metering of the checker sandbox in replay receipts |
| B20R7-OPEN-2 | The equational research loop does not call the custodian's sealed-statement screen; it only screens against its own study's reserved items. | wire `screen_for_research` (or a statement InsertionScreen fed by it) into research runs that will be evaluated by a custodian |

## B20_R8 outcome (replay contracts)

Builder-run; nothing here has been independently reviewed. See `docs/checkpoints/B20_R8_RECORD.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B14-OPEN-4 | PARTLY REPAIRED IN B20_R8, PENDING INDEPENDENT REVIEW. The kernel now replays three evidence kinds itself: `exact_check` (FINITE_CERTIFIED, needing two different exhaustive methods), `formal_check` (THEOREM_CHECKED, through a theorem claim plus a Lean replay from equational custody) and `dev_comparison` (DEV_ONLY and CORRELATED, by recomputing the analysis). Ablation, placebo, internal replication and priority checks still fail closed. | contracts for the causal, replication and priority kinds; a Lean-package route for THEOREM_CHECKED |
| B20R8-OPEN-1 | DEV comparison rows are producer data. The contract replays the analysis, not the executions behind the rows. | rows bound to attempt evidence in the store |

## B20_R9 and B20_R10 outcome (curation pilot, small open items)

Builder-run, DEV only. See `docs/checkpoints/B20_R9_R10_RECORD.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B20R3-OPEN-1 | ANSWERED ON DEV: NO_HEADROOM on the equational domain. Across three pilots (B20_R3, R6, R9), no research-policy dimension tried reached the preregistered threshold of 2 out of 12 targets: which lemmas to prove (8 systems), prover strategy, or which lemmas to keep (4 variants, at most +1 out of 12). | superseded by B20R9-OPEN-1 |
| B20R9-OPEN-1 | GV4 (better improver) cannot be answered positively on the equational domain at these settings. A different domain or setting where research outputs matter is needed, for example a formal Lean domain, graph construction (where B19's candidate gains on DEV), or longer horizons. | a reviewed design decision on the GV4 domain; then headroom first, then a frozen study |
| B20R3-OPEN-3 | REPAIRED IN B20_R10. Error lines are now kept ahead of the tail in stored checker logs. | — |
| B20R7-OPEN-1 | REPAIRED IN B20_R10. Lean replay reports checker CPU measured by cgroup; statement replay attempts carry it. | — |
| B20R7-OPEN-2 | REPAIRED IN B20_R10. The custodian offers a signed statement screen, and research runs can require it (`CustodianStatementScreen`, `both`). | wire it into the next custodian-evaluated research study |

## B20_R11 outcome (E1 readiness, GV3 path)

Builder-run; DEV material; the rehearsal used fixture keys. See `docs/checkpoints/B20_R11_RECORD.md` and `handoff/e1/README.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B19-OPEN-3 | Exercised for E1. The custodian runs the B19 candidate in the sandbox. A same-operator rehearsal went end to end (receipt v4, the judge agrees, 50 witnesses re-checked). | — |
| B20R11-OPEN-1 | The cost rule makes the E1 DRAFT design unwinnable. Under equal sandbox metering the candidate uses 3.38× the strongest baseline's CPU, and the plan caps the ratio at 3.0, so every outcome is NOT_SUPPORTED whatever the effect (+1.33 per task on 30 DEV hosts). | a reviewed design decision made before any panel exists (for example time-matched baselines), never a threshold raised after this result |
| B20R11-OPEN-2 | The comparator rules disagree. The DRAFT names the strongest baseline on a custodian SELECT panel, while the custodian's v4 check uses the campaign's own strongest baseline (`multistart` for this export; the pilot's strongest is `low_cycle`). | the reviewer fixes the rule; the request and the custodian check then follow it |

## After B20_R11: CRPD-2b, W22/W23, GV4 pilots, B20_R12, B20_R15 to B20_R24

Builder-run; DEV material and fixture keys. Nothing here is independently reviewed. See `docs/checkpoints/B20_RX1_RECORD.md`, `B20_RX2_RECORD.md`, `B20_R12_RECORD.md` and `B20_R15_RECORD.md` to `B20_R24_RECORD.md`.

| ID | Status or new finding | Needs |
|---|---|---|
| B20R-OPEN-3 | REPAIRED (CRPD-2b), PENDING REVIEW. The workspace pin revision is recorded in a hash-chained history, and the C4 pair-count bound is Lean-checked (`PAIR_COUNT_LEAN` certifies K3–K5). | review of the pin revision |
| B20R9-OPEN-1 | ANSWERED FURTHER ON DEV. Graph construction: no selection headroom (B20_R13). There is capability headroom to the optimum (B20_R14), and builder-written LP/SAT components deploy it (+0.63 to +1.38 per host, replicated, B20_RX3/3b). There is no proposal headroom once components exist (B20_RX5). GV4 therefore reduces to component invention (s15.3, W22). B20_R17/R19: two generated relational decoders outside the menu (an oriented 3-cycle; a k = 4 decoder from the versioned v2 generator) have Lean-checked semantics and transport, but NO_UTILITY_AFTER_COST on DEV (+0.19 and +0.125 per host against the menu); the family is retired as a utility source there. | a research process that invents components; a reviewed GV4 study design (`handoff/gv4/README.md` DRAFT) |
| B20R11-OPEN-1 | ADDRESSED BY THE USER'S DECISION (time-matched baselines); the CPU ratio is now 1.00. | reviewer sign-off |
| B20R11-OPEN-2 | ADDRESSED BY THE USER'S DECISION. The custodian selects the comparator on its own SELECT panel and registration enforces it. | reviewer sign-off |
| B19-OPEN-4 | STILL OPEN. The centred model is implemented. On the E1 family it reports INFEASIBLE. | an independent statistician |
| B20R12-OPEN-1 | ADDRESSED BY THE USER'S DECISION (14 Oct 2026), PENDING REVIEW. On `e1-hard-v1` the decided E1 design was UNDERPOWERED: two of four strata could not carry a 1.0 design effect. The versioned rule `e1-hard-v2` (B20_R24) adds a candidate-independent headroom bound and a certification limit. On its family (study `e1-v2`) the E1 re-pilot is READY_FOR_REVIEW (+2.57 per host, power 0.88 at 30 hosts), and a same-operator rehearsal is SUPPORTED, with the judge agreeing. | reviewer sign-off of `e1-hard-v2` and the DRAFT v3; statistician (B19-OPEN-4); an independent custodian |
| B14-OPEN-4 | REPAIRED IN B20_R15, PENDING INDEPENDENT REVIEW. Every level now has a replay contract. Causal levels need signed ablation/placebo receipts whose arms replay as one registered intervention. INTERNAL_INDEPENDENT needs a signed internal-replicator evaluation that repeats a supporting sealed evaluation. The priority levels need a replayed literature record, with library searches re-run for CANDIDATE_NOVEL. | independent review; registered interventions for more candidate kinds (B20_R23 added the LP guidance of `construct-pipeline-v1`; the Lean-package route for THEOREM_CHECKED was added in B20_R20) |
| B20R8-OPEN-1 | REPAIRED IN B20_R18, PENDING INDEPENDENT REVIEW. DEV comparison v2 binds every row to one journalled execution per arm, whose witness the kernel re-checks; v1 is retired. The journal is still the producer's store, so the solver is not re-executed. | independent review |
| H08 (s20.6) | DONE IN ENGINEERING TERMS (B20_R16 pointer/rollback/revocation; B20_R22 retention and negative transfer under a frozen protocol). Formerly: PARTLY DONE IN B20_R16. Done: the active-version pointer, rollback that keeps the failed child, inherited version revocation that also revokes the dependent kernel nodes, and a campaign resume gate. Not done: legacy retention and negative-transfer measurement under a frozen protocol, and paired lineages for `sealed_improver_evaluation`. | a GV4 domain with headroom and its evaluation design |
| B20R23-OPEN-1 | ADDRESSED BY THE USER'S DECISION (14 Oct 2026), PENDING REVIEW. E1b's family is study `e1b` under `e1-hard-v2`, on triangle-free hosts only, because no C4 setting is eligible. The re-pilot is READY_FOR_REVIEW (+2.63 per host, power 0.97), and a same-operator rehearsal is SUPPORTED, with the judge agreeing. The causal follow-ups were piloted on the B20_R23 settings and must be re-piloted on the `e1b` family before use. | reviewer sign-off; an independent custodian; the causal re-pilot |
| B20R24-OPEN-1 | NEW AND REPAIRED (B20_R24), PENDING REVIEW. The custodian's evaluator reference for graph hosts above the exact-search range (the adapter's SAT-only path) gave up at the first SAT call that returned UNKNOWN within 60 s, while reporting 'not certified within 600s'. Both first rehearsals were INVALID (4/30 and 2/30 unsupported, against the plan's 5%); the results are kept. A v4 evaluation now uses the joint LP/SAT reference (exact LP dual, then SAT/DRAT with the whole budget; certificate bundle v2 kept in the evidence). It closed 5 of the 6 hosts in diagnosis, and the re-run rehearsals had 0/30 and 1/30 unsupported. | independent review of the reference change |
| B20R24-OPEN-2 | NEW (design point). `e1-hard-v2` admits a setting when at least 90% of its hosts are certified within 60 s. The plan tolerates at most 5% unsupported CONFIRM tasks at the evaluator's 600 s. The two limits agree only if the longer budget certifies the rest. In B20_R24 it did (0/30 and 1/30), but nothing guarantees it. Neither limit was changed. | a reviewer's decision, before a real run: keep both, align them (for example, the calibration measuring at the evaluator's budget), or fix a CONFIRM-side certification budget in the plan |
| B20R25-OPEN-1 | NEW (B20_R25), PENDING REVIEW. The `fof_lean` ground-hint generator v2 (default; v1 kept verbatim) replays Wolfram-axiom lemma chains that v1 could not (0/19 → 19/19 on identical proof objects; Sheffer 11/11 under both). Hints are only instances given to Lean, so soundness is unchanged, but v2 is heuristic with no completeness guarantee, measured on two equational systems and one research policy. | review of the generator change; coverage on other theories and proof shapes |
| B20R26-OPEN-1 | NEW (B20_R26). s15.3 quotient family, attempt 1: per-host partition and exact block pattern, one parametric Lean transport theorem (CHECKED); DEV NO_UTILITY_AFTER_COST (vs menu −0.22 [−0.38, −0.06]). | a second, separately preregistered attempt (e.g. families whose best triangle-free subgraph is far from bipartite), or retirement |
| B20R27-OPEN-1 | NEW (B20_R27). s15.3 decomposition family, attempt 1: balanced vertex partition, exact parts, Lean composition theorem (CHECKED); DEV NO_UTILITY_AFTER_COST (vs the same components on the whole host −2.53, vs menu −1.25). The cut, not the parts, limits it. | a decomposition that keeps the cut small or solves it jointly; or retirement |
| B20R9-OPEN-1 (update after B20_R28) | STILL OPEN. Four representation attempts in three families (relational ×2, quotient, decomposition) have Lean-checked semantics and transport, and none has DEV utility after cost. The E1b causal re-pilot (B20_R28) confirms that the LP signal, a builder-written component, carries E1b's gain. | a component family with utility, then the GV4 study design (`handoff/gv4/README.md`) |
| B20R29-OPEN-1 | FOUND AND REPAIRED (B20_R29), PENDING REVIEW. The second-machine reference (`deployment/EXPECTED_RESULTS.json`) expected 339 store events in the reference campaign; B20_R16's version-pointer events made it 345 and the reference was not updated, so every driver rehearsal from B20_R16 on would fail at step 7 (B20_R28's did: NOT_REPRODUCED). Bisected; only that value changed; a matrix test now compares the reference campaign section. | review; a second supported machine (R-04) |
| B20R24-OPEN-2 (update after B20_R30) | STILL OPEN (reviewer decision), now with data. On 90 fresh hosts of the decided `e1b` family: the calibration certifies 86/90 within 60 s (95.6%; 85/90 if its soft 60 s limit is counted strictly), and the evaluator certifies 90/90 at 600 s (unsupported 0, one-sided 95% upper bound 3.27%): LIMITS_CONSISTENT on this family. No value disagreements. Nothing guarantees agreement on other families. | the reviewer chooses: keep both limits, align the calibration with the evaluator's budget, or fix a CONFIRM-side certification budget in the plan |
| B20R31-OPEN-1 | NEW (B20_R31). s15.3 relaxation family, attempt 1: generated pattern inequalities (K5 ≤ 6, W5 ≤ 7, kept by an irredundancy test over every graph on at most six vertices), validity Lean-CHECKED over 0/1 adjacency. DEV NO_UTILITY_AFTER_COST as a construction component (vs the plain LP greedy +0.19 [+0.06, +0.31], below 0.5). Certification diagnostic (float): the LP floor meets the optimum on 82/90 B20_R30 hosts with the rows vs 72/90 without; 10 of the 18 SAT-certified hosts. | an exact certification route over the generated rows, preregistered on fresh hosts (B20_R32); whether certification components count toward GV4 is for the GV4 design reviewer |
| B20R9-OPEN-1 (update after B20_R31) | STILL OPEN. Five attempts in four families (relational ×2, quotient, decomposition, relaxation) have Lean-checked semantics, and none has DEV construction utility after cost. The relaxation family is the first with a positive, interval-above-zero effect over the component it strengthens (+0.19) and a certification signal. | a component with construction utility, or a reviewer decision that certification components count |
| B20R32-OPEN-1 | NEW (B20_R32). Exact certification over B20_R31's generated rows (checker `verification/lp_dual_rows.py`, registry bound to CHECKED statements; not wired into the evaluator): sound, closes 2 of 3 SAT-needing hosts on a fresh sample (12 of 21 across B20_R30/R32), but NO_CERTIFICATION_UTILITY prospectively (McNemar p 0.25; wall saving +1.17 s [−0.10, +3.22]) because the fresh sample had 3 SAT-needing hosts against B20_R30's 18 (planted 0/30 vs 10/30, Fisher p ≈ 0.0004; MILP cross-check: no evaluator defect). | a study enriched for SAT-needing hosts with the screen fixed in advance, or retirement of the certification use |
| B20R32-OPEN-2 | NEW (B20_R32), GV3 design point. HiGHS's exact MILP (scipy, pinned) finds and proves the optimum of the e1b SAT-needing hosts in under 0.72 s wall; E1 and E1b compare their candidates only with time-matched fixed DSL programs. "Beyond strong baselines" is unmeasured against an off-the-shelf exact solver. | a measured MIP arm at the candidate's budget (B20_R33); the reviewer decides whether E1/E1b need such a comparator or harder families |
| B20R33-OPEN-1 | NEW (B20_R33), GV3 design point; answers B20R32-OPEN-2. On 60 fresh e1b hosts an exact MIP arm (HiGHS, scipy pinned, one core) proves the optimum on every host within 0.36 CPU s. Against it the frozen E1 candidate is dominated (MIP − candidate +0.75 [+0.58, +0.92] at 0.5 s; MIP_DOMINATES) and the E1b candidate is within 0.2 (+0.20 [+0.12, +0.30] at 2.0 s; NO_MATERIAL_DIFFERENCE, never above). Both still beat their DSL comparators by about 2 edges per host. On this family neither can be "beyond strong baselines"; a SUPPORTED result would be scoped to time-matched DSL baselines. | Daniel and the reviewer: accept the DSL-baseline scope, add a MIP comparator, or look for settings an exact solver does not finish within the budget but the evaluator still certifies (bounded by CERTIFICATE_MAX_EDGES 200) |
| B20R33-OPEN-1 (update after B20_R34) | STILL OPEN (decision). B20_R34 probed 7 triangle-free settings near the 200-edge certification bound (n ≤ 40): NO_MIP_HARD_CERTIFIABLE_SETTING. Wherever the evaluator certifies, the exact MIP is optimal (erdos n40 p0.23: certified 8/8, MIP proofs ≤ 0.16 CPU s); in five settings the MIP proves 38/40 optima within 2 s while the evaluator's 60 s certification fails on 3–6 of 8; in planted n40 (0.8, 0.06) neither finishes, and (exploratory) the E1b candidate beats the MIP's 2 s incumbent on 7/8 hosts (mean +6.4, uncertified). | the reviewer: DSL-baseline scope; a stronger certification route (branch-and-bound with exact LP-dual leaves) plus a versioned calibration of a dense regime; a plan without certified optima; or another domain |
| B20R34-OPEN-1 | FOUND AND REPAIRED IN THE RECORD (B20_R34), PENDING REVIEW. The resumable study scripts of B20_R30, R32, R33 and R34 regenerate their hosts on resume with the exposure exclusions, which by then include their own hosts.json; a resume draws new graphs under the old task ids. R34 was resumed after a container restart (48/56 done): its last 8 rows ran on new-draw graphs and hosts.json was overwritten. `scripts/b20r34_record_repair.py` reconstructed the first-run hosts from the logged 1,988 exclusions, matched all 56 rows to their graphs (id, n, edges) and rewrote hosts.json; rows and verdict unchanged. R30/R32/R33 were not resumed. | future resumable scripts load their own hosts.json on resume; review of the repair |
| B20R35-OPEN-1 | NEW (B20_R35), PENDING REVIEW. Enriched by setting (the two B20_R34 settings the evaluator mostly fails to certify), the generated-row certification route certifies 27/40 fresh hosts within 60 s against the evaluator's 7/40 (20 vs 0 discordant, McNemar p ≈ 1e-6; wall saving +18.5 s [+13.9, +23.3]); sound: CERTIFICATION_UTILITY. The first preregistered positive DEV utility of a machine-generated, Lean-checked component, in certification (not construction); the rows are classical bounds (no novelty claim). | reviewer: whether certification components count toward GV4; whether to wire the checker into the evaluator (trust-path change, Lean package in custody); comparison with stronger certifying baselines (a certifying MIP, SAT with symmetry breaking); coverage 27/40 is below the 90% limit |
| B20R32-OPEN-1 (update after B20_R35) | ANSWERED by the enriched study B20R35-OPEN-1. | — |
| B20R36-OPEN-1 | NEW (B20_R36). s15.3 relaxation family, attempt 2 (construction) in the dense regime where the triangle LP is loose: the Lean-checked K5 rows give +3.94 [+2.41, +5.41] over the same LP greedy, +3.31 after construction cost, +11.0 over the conventional DSL and +4.31 over an exact MIP at 2 s, but −2.97 against the menu decoder `cross_2`: NO_UTILITY_AFTER_COST. | a further, separately preregistered attempt (for example rows plus a decoder), or retirement |
| B20R9-OPEN-1 (update after B20_R36) | STILL OPEN. Six attempts in four families (relational ×2, quotient, decomposition, relaxation ×2) have Lean-checked components; none has construction utility under the B20_R17 rule. Relaxation attempt 2 beats every comparator except a builder-written menu decoder. Certification utility exists (B20R35-OPEN-1). | a component with construction utility, or a reviewer decision on certification components |
| B20R33-OPEN-1 (update after B20_R36) | STILL OPEN (decision). Exploratory: in the dense planted regime the `cross_2` decoder (the representation of E1's frozen candidate) is at the certified optimum on 10/10 certified hosts while HiGHS at 2 s is 13.9 below, so a "beyond strong baselines" regime exists; it is not yet certifiable enough to calibrate (23/32, 27/40 at 60 s with generated rows). | raise certification coverage (B20_R37), then a versioned calibration of the dense regime under a reviewer decision |
| B20R37-OPEN-1 | NEW (B20_R37). Generator v2 (every graph on ≤ 7 vertices; 9 patterns incl. K7 ≤ 12 and K7−e ≤ 12; all 12 obligations Lean-CHECKED via integer rounding certificates, two needing a hoisted maxHeartbeats option) adds little at 60 s: certified 33/40 vs v1's 30/40 (4 vs 1 discordant, McNemar p 0.19; v2 3.7 s slower): NO_COVERAGE_GAIN. Dense planted reaches 19/20 with v2 (17/20 with v1). | larger budgets or cutting-plane separation (only violated copies), or retire v2 for certification |
| B20R33-OPEN-1 (update after B20_R38) | STILL OPEN (decision), now with a positive DEV result. In the dense regime (planted n40 0.8/0.06, erdos n30 0.42; 40 fresh hosts, all certified by the generated-rows route), E1's frozen candidate at 0.5 s reaches the certified optimum on 19/20 hosts per setting and is +14.6 per host above HiGHS at 2.0 s on planted (20/0/0; tie on erdos, +0.45). Preregistered verdicts: E1 CANDIDATE_BEYOND_MIP on both settings (inflated: HiGHS barely starts in 0.5 s); E1b BEYOND_MIP on planted (+4.75), MIP_DOMINATES on erdos (−6.75). | reviewer: adopt a generated-rows reference (B20R35-OPEN-1, engineering B20_R39), version a dense family rule and calibrate it, choose the MIP comparator budget, issue a new E1 package version |
| B20R35-OPEN-1 (update after B20_R39) | STILL OPEN (reviewer decision); the engineering it would need now exists, built and not wired. `verification/certificates_rows.py` gives generated-row certificates custody under their own schema (objects: witness, certificate, Lean theory package, derived registry; checker-only replay that re-derives the registry, re-checks the certificate exactly, refuses revoked checker/package identities, optionally replays the package in Lean). `generated_certify.reference` is the joint reference with generated rows and produces that custody. The evaluator, the custodian and `certificates.CHECKED_METHODS_V2` are unchanged. Adoption steps: `docs/GENERATED_ROWS_REFERENCE.md`. | the reviewer adopts (package in custody, checker identities, versioned reference method, custodian acceptance, versioned family rule and calibration) or declines |
| B20R40-OPEN-1 | NEW (B20_R40), PENDING REVIEW. Candidate registry v2 (`candidates_v2.py`, per-kind modules under `candidate_kinds/`): v2 descriptors' identity is the v2 core, the kind's files, graphs.py and models.py, not registry v1, so new kinds no longer change the frozen E1/E1b descriptor ids. First kind `milp-highs-v1` (exact HiGHS MILP, one core, time-matched). Built and tested, not wired into requests, receipts or the custodian. | a reviewed wiring (requests v4 and receipts accept v2 descriptors; the custodian rebuilds them; the plan names v2 comparators); then v2 kinds with registered interventions and a supervised SAT child |
| B20R33-OPEN-1 (update after B20_R41) | STILL OPEN (decision), with a READY_FOR_REVIEW DEV readiness result. Under the DRAFT rule `e1-hard-v3-draft` (strongest baseline = best of E1's DSL baselines and HiGHS at 0.5 s and 2.0 s; candidate-blind generated-rows reference) a calibration selected three planted settings (erdos fails: HiGHS at 2 s optimal on 20/21 certified hosts). On a 30-host re-pilot the comparator is HiGHS at four times the budget; E1's frozen candidate is optimal on 30/30, +10.6 per host [9.1, 12.1], W/T/L 24/6/0, cost ratio 0.34, dry run SUPPORTED, 80 hosts per stratum for power 0.81 (`evidence/e1d_readiness_b20r41/`). | reviewer: adopt or decline E1d (B20R41-OPEN-1) |
| B20R41-OPEN-1 | NEW (B20_R41), PENDING REVIEW. A possible E1d package: E1's frozen candidate on the three planted settings calibrated under `e1-hard-v3-draft`, against the strongest of five registered baselines including HiGHS at four times the budget, scored by the generated-rows reference (LP over Lean-checked rows, rounding of its own LP, SAT/DRAT fallback; candidate-blind; median 20 s per host). The reference itself solves these hosts in about 20 s, which a claim should state. Also new: `generated_certify.certify_with_rows(lp_rounding_seconds=…)`, off by default. | reviewer: adopt the rule, the generated-rows reference (B20R35-OPEN-1) and registry v2 wiring (B20R40-OPEN-1); issue E1d; statistician and independent custodian for a real run |
| B20R40-OPEN-1 (update after B20_R42) | STILL PENDING REVIEW; the wiring now exists, opt-in. `candidate_registry.py` dispatches by schema (v1 descriptors take the unchanged v1 path); evaluation request v5 (v4 plus a closed `reference` route) takes registry-v2 arms; `select_comparator` accepts an exact v2 baseline (`milp-highs-v1`) only under a calibration rule that names it (today only the DRAFT `e1-hard-v3-draft`, which no study adopts). v3/v4 requests, receipts, adopted rules and frozen descriptor ids are unchanged. | reviewer: adopt or decline the v5 path together with B20R41-OPEN-1 |
| B20R35-OPEN-1 (update after B20_R42) | STILL OPEN (reviewer decision); wired opt-in. A v5 request names `generated-rows-v1` with a known, integrity-checked theory package by digest and every route limit; the triangle-free adapter computes it (`_rows_reference`) and the custody bundle goes into the evaluation's evidence store; the C4 adapter refuses; the receipt binds the route through the request hash. | reviewer: accept the package and checker identities, the route, and a study adoption |
| B20R41-OPEN-1 (update after B20_R43) | STILL PENDING REVIEW, now with a package and a SUPPORTED same-operator rehearsal. `handoff/e1d` (DRAFT; evidence card in five dimensions). Rehearsal through the opt-in v5 path, with the draft rule adopted only in a throwaway copy: the custodian's SELECT chose HiGHS at 4x budget; 240-host CONFIRM, 237 certified by the generated-rows LP (3 unsupported, 1.25%); W/L/T 198/0/39, +9.80 per host [9.30, 10.35], cost ratio 0.338: SUPPORTED, judge agrees (`evidence/e1d_package_b20r43/`). Causal attribution to the discovered representation is pending (B20_R44). | reviewer: adopt or decline E1d (rule, study, reference, v5 wiring); statistician; independent custodian |
| B20R44-OPEN-1 | NEW (B20_R44), PENDING REVIEW. A builder-registered intervention in `kernel/replay_contracts.INTERVENTIONS`: represent-and-repair-v1 `representation` ablation cross_2 -> ordered_2 (B18 Lean checks: ordered_2 within cross_2 CHECKED, converse DISPROVED, ordered_2 sound on TF CHECKED); no placebo (the only other sound k = 2 decoder, adjacent_2, is Lean-equal to cross_2). B20_R15's test asserting no intervention for this kind is updated accordingly. | reviewer: accept or decline the transform; it is the only route to a causal level for E1/E1d's discovered component |
| B20R41-OPEN-1 (update after B20_R44) | STILL PENDING REVIEW, now with a causal control. On 30 fresh hosts in the E1d settings, the registered ablation of the discovered representation costs +7.07 per host [6.47, 7.70], 30/0/0, cost ratio 1.00 (READY_FOR_REVIEW; 45 hosts for power 0.86), and a Lean-certified null arm (adjacent_2 = cross_2) shows +0.03 [−0.02, +0.09] (NULL_CONTROL_CLEAN) (`evidence/e1d_ablation_b20r44/`). | reviewer: as above, plus B20R44-OPEN-1; a custodian-signed ablation evaluation for ABLATION_SUPPORTED |
| B20R41-OPEN-1 (update after B20_R45) | STILL PENDING REVIEW; every builder-side step is done. The E1d ablation evaluation was rehearsed through the v5 custody path (v5 ablation request, intervention re-checked at registration, 45-host CONFIRM): 44/0/0, +6.64 per host [6.03, 7.29], SUPPORTED, judge agrees (`evidence/e1d_ablation_rehearsal_b20r45/`). Remaining: reviewer adoption (rule, study, reference, v5 wiring, the registered transform), statistician, independent custodian. | reviewer, statistician, independent custodian |
| B20R46-OPEN-1 | NEW (B20_R46), PENDING REVIEW. The triangle-free row-invention procedure was transferred to C4-free subgraphs with a registered adaptation (`invention/cuts_c4.py`: 4-cycle rows, a bridge lemma with distinct opposite vertices, statements over pairwise-distinct vertices; search and kept rule unchanged): 34 patterns, 37/37 obligations Lean-CHECKED (`evidence/c4_generator_b20r46/`). A reviewer decides whether procedural transfer of this kind counts toward GV6 and what adaptation budget is acceptable. It is not evidence of utility in the new domain; B20_R47 tests that prospectively. | reviewer |
| B20R47-OPEN-1 | NEW (B20_R47), PENDING REVIEW. The exact checker for generated C4 rows (`verification/lp_dual_rows_c4.py`) and its route are built and tested, not wired. On fresh C4 hosts they add no certification coverage (22 vs 22) but are faster (+2.24 s per host) and close 80% of the LP gap. Adopting them in the evaluator's C4 path would be a trust-path change for a speed benefit only, unless B20_R48's branching certificates change the picture. | reviewer |
| B20R46-OPEN-1 (update after B20_R47) | STILL PENDING REVIEW. The transferred rows are sound and much stronger than the 4-cycle rows but gave no coverage gain (B20_R47). Under the roadmap (E5), C4-free and triangle-free are near domains; this is near-domain evidence, and GV6 still needs a structurally different formal domain. | reviewer |
| B20R48-OPEN-1 | NEW (B20_R48), PENDING REVIEW. A certified branch-and-bound route over the transferred C4 rows (`verification/lp_dual_tree_c4.py`, exact tree checker; `discovery/generated_bnb_c4.py`, producer) has prospective certification utility on fresh C4 hosts: 38 vs 26 of 40, p 0.00024, +27.8 s per host, every certificate VALID (`evidence/c4_tree_certification_b20r48/`). Adopting it as a certification route for c4_host_v2, in the evaluator's reference or in a DRAFT C4 rule, is a trust-path change for a reviewer; it would make C4 settings calibratable (both tested settings meet the 90% limit) and settle E1b's C4 arm (UNSETTLED_REFERENCE in B20_R23). Attribution to the invented rows: B20_R49. | reviewer |
| B20R46-OPEN-1 and B20R48-OPEN-1 (update after B20_R49) | STILL PENDING REVIEW. A registered ablation (`evidence/c4_rows_ablation_b20r49/`) attributes the tree route's certification utility to the transferred, Lean-checked rows: 36 vs 24 of 40 fresh C4 hosts certified with vs without them, p 0.00024, 14x fewer search nodes. The preregistered DEV chain B20_R46 → R49 is near-domain transfer evidence (roadmap E5); GV6 still needs a structurally different formal domain. | reviewer |
| B20R50-OPEN-1 | NEW (B20_R50), PENDING REVIEW. A DRAFT rule `e1-hard-v2-c4tree-draft` (e1-hard-v2 with the tree route over the transferred rows as reference) makes E1b's C4 arm scorable: two calibrated C4 settings, and on a 30-host DEV re-pilot E1b is READY_FOR_REVIEW against the DSL baselines (+1.17) and in both causal contrasts (+1.43, +2.73) (`evidence/e1b_c4_readiness_b20r50/`). Adoption depends on B20R48-OPEN-1 (the route as reference) and on B20R33-OPEN-1 (an exact C4 MIP at 2 s is optimal on all 30 pilot hosts and dominates E1b by 0.93). B20_R23's UNSETTLED_REFERENCE C4 causal pilot is settled on DEV. | reviewer |
| B20R48-OPEN-1 and B20R50-OPEN-1 (update after B20_R51) | STILL PENDING REVIEW. Custody (`verification/certificates_tree_c4.py`) and opt-in v5 wiring (route `generated-rows-tree-c4-v1`, C4 adapter only) now exist for the C4 tree route, and the DRAFT C4 rule is listed for record checks without any study adopting it (`docs/GENERATED_ROWS_REFERENCE.md`, section "The C4 counterpart"). Adoption remains a trust-path decision. Known limit: slow on small dense hosts (K8 not certified in 30 s). | reviewer |
| B20R50-OPEN-1 (update after B20_R52) | STILL PENDING REVIEW; every builder-side step for E1b's C4 arm is done. Package `handoff/e1b_c4` (DRAFT); same-operator rehearsal through the v5 C4 tree route: SUPPORTED, +1.15 per host [0.70, 1.65], judge agrees (`evidence/e1b_c4_package_b20r52/`). A real run needs the reviewer's adoption of the draft rule and the tree reference, the B20R33-OPEN-1 scope decision (an exact C4 MIP dominates), a statistician and an independent custodian. | reviewer |
| B20R9-OPEN-1 (update after B20_R53) | STILL OPEN. Wolfram's single axiom at B20's hard settings (10 s attempts, 3 s per target), the one equational system where research clearly matters, also has **NO_HEADROOM** for selection: ORACLE − FIXED 1, 0, 1, 0 of 15 on four fresh seeds, noise 0 (`evidence/wolfram_headroom_b20r53/`). The pool exhausts in under 10 s; what limits the successor is the ceiling (3–8 of 15 targets no pool library proves). The GV6 draft's transferred keep rule reaches the oracle with 1–3 lemmas (descriptive). | a GV4 domain decision; B20_R54 asks whether research beyond the pool reaches the ceiling |
| B20R9-OPEN-1 and B20R46-OPEN-1 (update after B20_R54) | B20R9-OPEN-1 STILL OPEN; the equational domain is closed for GV4 at these scales. Research beyond the pool does not reach Wolfram's ceiling: with 6-node conjectures the best library proves exactly what the best 5-node library does on four fresh seeds (NO_CEILING_HEADROOM, `evidence/wolfram_ceiling_b20r54/`). With B20_R53, no library-building research (selection, keeping, larger conjecture spaces, the transferred keep rule) moves Wolfram's successor by more than 1 of 15. For B20R46-OPEN-1 the equational target (GV6 draft, target 2) therefore has nothing to transfer into at these scales. | a GV4 domain decision; the GV6 target decision |
| B20R46-OPEN-1 (update after B20_R55) | STILL PENDING REVIEW. A second transfer target in a different theorem family: the row-invention procedure, unchanged in search, kept rule and proof method, generated 17 sum-free patterns with all 20 obligations Lean-CHECKED (`evidence/sf_generator_b20r55/`). New trusted definitions `SFDefs` (`SF.SumFree`, `SF.ind`) need review as the sum-free domain contract. Abstractly the target is again a hypergraph-free packing; whether it counts as structurally different is the reviewer's decision. Utility on hosts is B20_R56. | reviewer |
| B20R46-OPEN-1 (update after B20_R56) | STILL PENDING REVIEW. In the second target the transferred rows give NO_CERTIFICATION_UTILITY on 40 fresh sum-free hosts (28 vs 26 certified, p 0.25; wall saving −1.61 s, interval includes 0; `evidence/sf_tree_certification_b20r56/`). They strengthen the relaxation (root bound 5–10 lower) but slow easy hosts. The GV6 evidence is now one positive near-domain chain (C4) and one negative result in a different theorem family; a hardness-enriched follow-up is B20_R57. | reviewer |
| B20R46-OPEN-1 and B20R35-OPEN-1 (update after B20_R57) | STILL PENDING REVIEW. In the second target, on hosts the conventional route cannot certify within 20 s (candidate-blind screen), the transferred rows give CERTIFICATION_UTILITY: 22 vs 14 of 40 certified (8/0, p 0.0039), wall saving +6.02 s [2.50, 9.88], certified bound 6.875 lower [5.375, 8.475] (`evidence/sf_hard_certification_b20r57/`). With B20_R56 (unenriched: none) this is the C4 and triangle-free profile in a different theorem family. Decisions: whether sum-free counts as structurally different (same abstract structure), and whether certification utility counts as "helps". | reviewer |
