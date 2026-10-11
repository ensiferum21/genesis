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

