# B20_R1 checkpoint record — repairs of the external B20 review (handoff H01–H03)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B20.zip`
(sha256 `44bbbbeb1b8781203af8b3489b7c1a396d7694806232193dce9e7fee46f12091`, commit `97fb233`).
Branch: `continuation-b20-repairs`. Builder-run; nothing here is independently reviewed.

Each change below is stated as: problem, implementation, evidence actually executed,
remaining limitation, acceptance consequence.

## B20-REVIEW-01: evaluation material was not globally disjoint

- **Problem.** Evaluation targets were sampled excluding only the same seed's pool and
  development targets. Three statements (four slots) were also training development targets.
- **Implementation.** `learning/partitions.py`: a study-wide exposure set frozen first;
  evaluation drawn against it with EXACT / ALPHA / INSTANCE / GENERALIZES relations,
  cross-unit distinctness, quarantine and an explicit `INSUFFICIENT_DISTINCT_MATERIAL`;
  `InsertionScreen` for lemma, macro, memory, curriculum and import routes (ALLOW/BLOCK
  only, salted commitment, query budget); pure `partition_problems` validator.
- **Evidence executed.** `tests_formal/test_learning_partitions.py` (15 tests), including
  detection of the original four slots without a prover. A probe over the full B20
  material (2,062 visible items, 886 distinct) rebuilt eight evaluation units of 25 with
  zero validator problems.
- **Limitation.** Relations are syntactic: equivalence modulo theory laws is not detected.
  Pretraining exposure is outside its reach.
- **Consequence.** The B20 comparison stays contaminated. A fresh frozen DEV study is
  needed before any E3 statement on the repaired harness.

## B20-REVIEW-02: research budgets were not enforced

- **Problem.** Preparation was free, the cap was checked before the action, fractional
  remainders became whole prover seconds, and late proofs were credited (33 of 40 W19 runs
  over cap; learned 1.93 s vs fixed 1.01 s under 1 s on Huntington 204).
- **Implementation.** `learning/budget.py`: `StudyBudget` and `Account` opened before
  preparation; every in-process category charged; reservations before launch with the kill
  tolerance held back; `run_bounded` meters every descendant through a per-attempt cgroup
  and kills at the reservation; late or killed results are never credited; a journal charges
  interrupted reservations on restart; `grant_bridge` ties a campaign to the kernel
  `GrantLedger`. `research.run`, `evaluate_successor` and `macros.expand` use it.
- **Evidence executed.** `tests_genesis/test_research_resource_accounting.py` (16 tests, real
  CPU burners and a setsid grandchild); the legacy loop reproduces the overrun, the repaired
  loop stays within cap plus the declared tolerance.
- **Limitation.** The procfs fallback meter is a lower bound (labelled, never credited).
  Kill latency is bounded but finite; small effects need caps far above the 50 ms tolerance.
  Under PROVER_QUANTUM a 1 s campaign cannot afford one 1 s E attempt (1.25 s with overhead):
  the B20 Huntington budget rule is not reusable as it was.
- **Consequence.** No equal-cost statement until a fresh comparison runs on this mechanism.

## B20-REVIEW-03: Lean replay covered 67 of 778 reported successes

- **Implementation.** `learning/custody.py`: successor manifests with run-bound lemma uids,
  per-target custody records, pure validators, replay rebuilt from custody only, and three
  metrics kept apart (prover-reported, checked, eligible).
- **Evidence executed.** `tests_formal/test_successor_proof_custody.py` (11 tests; two real
  Lean replays with proof search disabled, one of them an axioms-only proof).
- **Limitation.** Forward only: B20's uncovered scores have no stored proof objects.
- **Consequence.** A checked-successor endpoint is now definable; it must name its metric.

## B20-REVIEW-04: B19 joint bounds lacked witness and certificate custody

- **Implementation.** `verification/lp_dual.py` (the exact checker, moved verbatim, with a
  content identity); certificate bundle v2 (witness object, exact LP certificate, CNF/DRAT
  bytes, attempts, checker identities); `obstruction.certify` returns bundle and objects;
  `record_evidence` uses the shared kernel; certificate replays are cached per revocation state.
- **Evidence executed.** `tests_certificates/test_obstruction_custody.py` (16 tests); a new
  DEV re-run (`evidence/obstruction_custody_b20r/`): 12/12 OPTIMALITY_CHECKED, 12/12 replay in
  a separate process with scipy blocked and the SAT solver refused.
- **Limitation.** One task differs from the B19 record (closed this time); two executions,
  no reconciliation. The B19 file is unchanged history.

## B20R-NEW-01 (found during repair)

E's `%% SZS status ResourceOut` was parsed as `ERROR`. Repaired; labels only (B20 counted
PROVED from THEOREM).

## Also in this checkpoint

- `audit/review_b20/`: read-only reproduction of the four findings.
- Ledger: 348 rows (five review-finding rows added); defect register and `batch_state.json`
  (`continuation_b20_r1`) updated without changing B20's own entries.
- Toolchain rebuilt from the pinned sources in a fresh container: all pins match, the
  known-answer suite passes, and the formal workspace artifact identity equals B20's
  (`95a6ec9f…`). This is the same build host type, not a second machine.

## Claim ceiling

Engineering repairs on DEV material. No sealed task, no promoted scientific claim.
Better-improver: still explicitly UNESTABLISHED.
