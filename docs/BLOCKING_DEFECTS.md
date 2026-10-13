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
