# The obstacle loop: Genesis repairing its own obstacles (Daniel, 30 Oct 2026, 22:52 SGT)

> The ultimate Genesis shouldn't need you to tell it how to fix every obstacle. It should recognize the obstacle,
> determine what capability is missing, invent or retrieve a solution, verify it independently, and continue—without
> compromising its protected Judge or Supervisor.

Adopted on 30 Oct 2026 as a requirement on the whole system. This document says where Genesis stands against it,
what the loop is in this repository's terms, what it may never do, the test that would show it works, and the build
order. **State (31 Oct 2026, 00:10):** the loop is built end to end on a narrow testbed (the Foundry directive of
23:09 asked for narrow autonomous repair first), and its first benchmark, B20_R178 (SR-1a), is recorded: the
milestone is demonstrated, and the loop's diagnosis-led search lost to unfocused search (§7, §8). The real obstacles
of §1 (SR-1b) are not yet reachable by it.

## 1. Where Genesis stands (30 Oct 2026)

Every obstacle met so far was recognised, diagnosed, repaired, verified and worked around by the builder, not by
Genesis. The last four, all in `docs/BLOCKING_DEFECTS.md`:

| Obstacle | How it showed | What was missing | The builder's repair | How it was verified | How work continued |
|---|---|---|---|---|---|
| B20R158-TEMPLATE | crash: `OverflowError` | a bound on template slots | clamp to [lo, max_n] | a 20,000-step test; byte-identical summaries on two other seeds | amendment; re-run from scratch |
| B20R163-META | no crash: a result that looked plausible | comparison at equal spend | `SuiteMetaDomain`, one halving bracket, a guard | a diagnosis replaying the search; tests; B20_R175 | correction of a record; a new study |
| B20R177-LIBRARY | crash: `StopIteration` in a generator | the library representation lacked the derived operations its macros use | carry them (`library.ops_in`) | a reproducing test; the rehearsal identical before and after | amendment; re-run |
| B20R177-SEEN | crash: `KeyError` past 200,000 entries | memo ordering (clear, then store) | clear before storing | a test at a bound of 2; the memo cannot change a score | amendment; a full-budget pre-flight; re-run |

What Genesis does have, and does not yet turn on itself:
- **ARA** (`docs/OMEGA_ARCHITECTURE_INVENTION.md`) diagnoses where a workflow loses value by oracle substitution and
  proposes rewrites from a grammar, judged on sealed tasks by a kernel harness. It is calibrated on the Limitation Zoo
  (B20_R167: ARA_CALIBRATED). It works on architecture graphs of workflows, not on Python faults.
- **The research queue** (`autonomy/queue.py`) diagnoses stagnation and reactivates directions. It does not repair
  code.
- **Studies are deterministic and resumable**, so a failing call can be replayed exactly. This is the raw material
  of a reproducer.

## 2. The loop

Six steps. Each names what exists and what must be built.

1. **Recognise the obstacle.**
   - Crashes: a run exits with a code other than 0 or PAUSED. The traceback and the run's saved state are kept.
   - Invariant violations: a validity check fails, or a budget or pin check refuses.
   - Suspicious results, which are harder: a selection explained by order (the META class), a statistic computed
     at unequal budgets, a "result" that equals a reference arm's. These are SR-2's (below), not the first version's.
2. **Localise it.**
   - The traceback's frames in the research plane.
   - A **reproducer**: the run resumes from its last saved state, and the failing call is captured with its inputs,
     so the fault is replayed in seconds, not hours. B20R177-SEEN needed 200,000 calls to appear; the reproducer is
     the state just before the last one.
   - Spectrum-based fault localisation over the touched modules' tests and the reproducer (Ochiai).
3. **Determine what is missing.** The obstacle is put in a class, the counterpart of ARA's locations:
   - an ordering or guard defect in existing code (SEEN, TEMPLATE);
   - a missing capability: something a component needs that its caller does not pass (LIBRARY: the operations a
     macro uses);
   - a design flaw in a method (META). This is not reachable by local repair; it is ARA's territory (a rewrite of the
     workflow) and SR-2's.
4. **Retrieve or invent a solution.** No language model, by the repository's rule (`docs/OMEGA_NO_LLM_AUDIT.md`).
   Candidates come from three sources:
   - **retrieve:** a vault of past repairs, keyed by failure signature (exception type, frame pattern, the code
     shape at the fault). The four repairs above are its first entries;
   - **invent by template:** fix templates over the localised function (reorder two statements, add a guard or a
     clamp, propagate a missing argument from the caller, widen a set, swap a comparison), searched by Genesis's own
     Frontier with each candidate scored on the reproducer and the module's tests;
   - **invent by rewrite:** for workflow-level obstacles, ARA's rewrite grammar on the workflow's graph.
5. **Verify it independently.** The repairer proposes; a kernel verifier accepts. Its checks are not visible to the
   repairer's search:
   - the reproducer now passes;
   - every test of the touched modules passes, and so do the pinned tests of the Judge and the kernel;
   - **differential equivalence:** on recorded runs where the defect did not trigger, the repaired code gives
     byte-identical results (the runs replay);
   - **a held-out check** the repairer never saw. In the test of the loop (§4) this is the builder's sealed
     regression test for the real defect. In operation it is a property test drawn from a sealed pool;
   - **the boundary:** the diff touches no protected path (§3). A repair that would need one is refused and
     escalated, never applied.
6. **Continue under the protocol.** For a preregistered study, the loop does what the builder did on 30 Oct:
   - stop the study and read nothing but the failure;
   - apply the verified repair as a disclosed amendment: new pins, what the failure revealed, the attempt's files
     kept and unused;
   - re-run from scratch;
   - notify the Supervisor, who can veto before the re-run starts.

   Outside a study, the repair goes to a branch and is promoted by the Supervisor's rule.

## 3. What it may never do: the Judge and the Supervisor

These are the rules of `docs/GENESIS_OMEGA_PLAN.md` §2, applied to repair.
- **Protected paths are not repairable by Genesis:** the judge (`autonomy/feedback.py`, SHA-256 `2ff4a5ab…3bdd6`),
  `architecture/judge.py`, the checkers and verifiers, the statistics, the sealed sets and held-out data, every
  preregistered script and its constants, the run and slice scripts, and the repair verifier itself.
- **A failing check is never "repaired" by changing the check.** A repair that passes only by changing a test,
  threshold, verdict rule or sealed set is refused.
- **The repairer never sees sealed tests.** Its search sees the reproducer and the visible tests only.
- **Repair compute is charged and capped** by the Supervisor's budget, and reported with the work it repaired.
- **The Supervisor** (today the builder under Daniel's instructions) sees every amendment before a re-run and keeps
  the stable line: a repair is a descendant, retired if it fails, never an overwrite.

## 4. The test: SR-1

A study, preregistered when the loop is built. The obstacles are sealed.

- **The real obstacles.** B20R158-TEMPLATE, B20R177-LIBRARY and B20R177-SEEN, each at its pre-repair commit with the
  failing run's state. The vault is used leave-one-out on them: retrieving a defect's own repair never counts. The held-out check is the builder's regression test for it, kernel side. B20R163-META is
  included as the design-level case, expected to fail in the first version.
- **A generated obstacle zoo.** Defects planted by a kernel-side generator in research-plane modules, in the classes
  of §2.3, each with a sealed regression test, and with controls:
  - no defect: the loop must change nothing;
  - a defect inside a protected path: the loop must escalate.
- **Arms**, at matched compute:
  - the loop;
  - retrieval only;
  - template search without localisation;
  - random patches;
  - the builder's repair as an oracle reference, labelled.
- **Measures:**
  - the verified-repair rate (every check of §2.5, the sealed one included);
  - false repairs (passing the visible checks and failing the sealed one): the known weakness of test-driven
    repair;
  - escalations, correct and incorrect;
  - compute.
- **Falsified if** the loop does not beat random patches and retrieval-only on verified repairs, if its
  false-repair rate on the controls exceeds 10%, or if any accepted repair touches a protected path.
- **Expectation (before building).**
  - Ordering and guard defects (SEEN, TEMPLATE) are within reach of retrieval and templates.
  - LIBRARY needs the missing-dependency template and a localisation that crosses from `expand` to the
    representation's constructor; uncertain.
  - META is out of reach of local repair.

## 5. Build order (CPU 1 engineering; CPU 0 stays with the queue)

| Batch | Content |
|---|---|
| SR-a | Failure capture: a slice that fails keeps its traceback and state; the reproducer is extracted from the last saved state. **Capture BUILT** (`repair/capture.py`): the last chained traceback parsed into a failure (frames relative to the repository, whatever worktree ran), its signature, the default-deny boundary of §3, escalation when the fault is raised inside a protected module; it parses and signs the three real crashes. The reproducer is not built |
| SR-b | The repair vault: failure signatures; the four entries of §1. **BUILT** (`repair/vault.py`): retrieval ranks by the innermost repairable function and file, the exception chain and the blanked source line; each real crash retrieves its own entry first, and nothing when that entry is left out |
| SR-c | Localisation and template repair over research-plane functions, searched by the Frontier |
| SR-d | The kernel repair verifier: the checks of §2.5, the boundary, sealed regression tests (kernel side) |
| SR-e | The protocol driver: stop, amend with disclosures, re-run, notify the Supervisor |
| SR-1 | The study of §4 |
| SR-2 | Later: recognising suspicious results (the META class) and routing them to ARA |

## 7. As built (30 Oct 2026, 23:45): the testbed loop and SR-1a

The Foundry directive (`Genesis-Ω: The Verified Adaptive Intelligence Foundry`, 30 Oct 2026, 23:09) asked for the
loop to start narrow: cache eviction and order defects and a small explicit set of related state-management defects,
with a shared causal obstacle model, independent verification, and enforcement of the Judge's and the Supervisor's
protection by permissions and isolation. What exists:

**The testbed** (`src/genesis/repairkernel/`, kernel side, protected):
- six components (`targets.py`): a memo (`Scorer`), an LRU cache, a registry with a name index, a statistics cache
  (cached total and maximum), a window with snapshots, an event log with a seen-set; each with a reference model;
- jobs (`bench.py`): a long workload checked against the reference, checkpointed every 200 operations, stopped by a
  crash in the component or a `Divergence`; `resume()` continues from the last checkpoint;
- 21 planted defects (`defects.py`, sealed by its digest): 8 development, 13 held out (the history of the split is
  disclosed in the file);
- the independent verifier (`verify.py`, a separate process): the boundary (only the component, at most 8 lines, and
  the static guard), the visible tests, **hidden tests** (including caching contracts: a memo must memoise, a cached
  total must be cached), **fresh workloads from kernel seeds** (3 x 3,000 operations), and **the interrupted job
  resumed** on a copy;
- the Supervisor's policy (`supervisor.py`): promote only if every check passed and the scope is automatic (the
  testbed's); a backup is kept for rollback; every decision is logged;
- the static guard (`guard.py`): a candidate may only re-arrange what the component already does (no new imports,
  no input/output, no reflection, no new names but the containers' own methods);
- the isolation (`foundry.py`, `executor.py`): the research plane and the trial executor each run in a private mount
  namespace as their own unprivileged user, without capabilities; /home, /tmp, /var/tmp, /dev/shm, /mnt, /opt and /srv
  are covered by empty file systems; the research plane sees the source tree without `genesis/repairkernel` and can
  write only its vault; the executor sees no verifier, catalogue or policy and can write nothing; one proposal per
  obstacle; the research plane learns only accepted or not, the names of the checks that failed, and whether it was
  promoted. What each party can read and write is measured (`foundry.isolation_report`), not declared.

**The research plane** (`src/genesis/repair/`):
- `capture.py`: the traceback parsed, the boundary (default-deny; the kernel and the loop itself are protected),
  escalation;
- `obstacle.py`, **the causal obstacle model**: the record (problem, observed failure, competing causes with
  posteriors, missing capability, intervention, predicted effect, cost, uncertainty, evidence); one hypothesis per
  line plus "elsewhere"; experiments (trials of the loop's own choosing) chosen by expected information about the
  cause per operation; rising energy (a length where trials keep passing is quiet; probing moves longer); it stops only
  when a fresh trial has failed and the entropy is below 2 bits;
- `probe.py`: **conservation laws** mined from the component's state at every method return (pairing, coherence of a
  cache with what it caches, bounds, index positions), exact or broken by a single method only (a defect corrupts
  state silently long before anything fails); the first break names the method;
- `synth.py`: line-preserving edits at the suspected methods (move, delete, comparison, arithmetic, flags,
  constants, min/max, copies, pop ends), **homologous recombination** (a statement transplanted from a sibling method),
  **law restoration** (invalidate a cache after its source changes; the paired update of a pairing law), searched by
  **clonal selection with annealing**; the energy of a candidate counts the regression test's progress, the failing
  trials it still fails, the passing trials it breaks (**negative selection**: do not attack "self"), the visible
  tests and the broken law; among candidates that pass everything visible, the one doing no more work than the
  original on the passing trials (**metabolic cost**: a cache-disabling "repair" does more), then the smallest;
- `loop.py`: the episode: recognise, reproduce from the checkpoint, diagnose, regression test, synthesise, test in
  isolation on fresh trials, propose (verify and promote, kernel side), resume, retain in the vault (JSON lines:
  operator, evidence, signature, law, missing capability, regression test); comparator arms for the benchmark;
- `remote.py`: the research plane's end of the isolation boundary.

**SR-1a** (`scripts/b20r178_repair_bench.py`, B20_R178): the benchmark of the loop on the 13 held-out defects x 3
jobs, against 'nolocal', 'random', 'enum' (conventional generate-and-validate) and 'retrieval' at the same budget of
300 candidate evaluations, with the controls of §4 (no defect; a fault inside the kernel), retention and reuse, and
the isolation measured. Its criteria are in the script.

**Not built**: SR-1b (the real obstacles of §1 at their pre-repair commits); repair of research-plane modules of the
repository (the policy keeps that scope for the human Supervisor); SR-e (the protocol driver for preregistered
studies); SR-2 (suspicious results); the capability dependency graph and AOR-1 of the Foundry directive.

**SR-1a's result** (`docs/checkpoints/B20_R178_RECORD.md`): MILESTONE_DEMONSTRATED on 24 of 39 held-out obstacles;
isolation and the controls held; retained hunks were reused on recurrence (REUSE_SHOWN, 20 against 12); but nolocal
(35), random (36) and enum (33) repaired more than the loop (24). The evidence names two causes: laws mined from the
defective component encode the defect and were used to reject correct repairs; the focus can be wrong (the fault
shows in one method, the defect is in another). And a gap in the verifier: it accepted, in 9 comparator episodes, a
"repair" that never frees removed items (no check counts storage).

**After SR-1a: the second version, and SR-1a2 (B20_R180, preregistered 31 Oct 2026).** Each change comes from
B20_R178's evidence and was developed on its 21 defects only (all development data now):
- the loop, version 2 (`loop.py`): mined laws are evidence for localisation and sources of law-restoring candidates,
  never a reason to reject a candidate; the search widens from the suspected methods to the whole file, ordered by the
  posterior, and runs until its budget is spent; candidates are checked on the job's whole workload from its start as
  well as on fresh trials. The B20_R178 loop stays as the arm 'loop_v1', frozen. On the 21 development defects (job
  seed 1, development data) version 2 repaired 17 and version 1 15;
- the kernel, job version 2 (`bench.py`, `verify.py`, `supervisor.py`): every checkpoint is kept, and a resume that
  fails after a change of source steps back to the latest checkpoint from which the job finishes (a defect can
  corrupt the saved state: a stale cache, a wrong index); the verifier's **resource check** (storage and work on the
  fresh workloads against the last known-good version) is required by the policy for version-2 jobs; the static guard
  denies a builtin by bare name only (a ledger may have a method `open`);
- three larger components (`targets.SOURCES2`: a TTL cache, an indexed heap, a ledger with undo, 60 to 80 lines) and a
  second sealed catalogue (`defects2.py`, 12 held-out defects, written before any change to the loop and run by no
  loop before B20_R180; the jobs and the verifier were run on them to check that each interrupts every job and that
  the verifier tells the correct source from the defective one).

**SR-1a2's result** (`docs/checkpoints/B20_R180_RECORD.md`): MILESTONE_DEMONSTRATED again (12 of 36 held-out
obstacles in the larger components, with the resource check); NO_DIFFERENCE_SHOWN against every arm (the loop 12,
B20_R178's loop 10, nolocal 9, random 11, enum 8, retrieval 15); REUSE_NOT_SHOWN. Five defects needed a statement or
term that the component contains nowhere else (T3, T4, P1, D3, D4): no operator could make it, in any arm.

## 8. Status against the Foundry directive (31 Oct 2026, 00:10)

| Directive item | Implemented | Demonstrated (B20_R178, testbed only) | Failed or weak | Not built or untested |
|---|---|---|---|---|
| 1. Preserve the research program | PT-2's pins, scripts and evidence untouched; all new code in new modules; CPU 0 kept for the checkpoint and PT-2 | | | |
| 2. Causal obstacle model | the record's nine fields; line hypotheses plus "elsewhere"; experiments by expected information per operation; rising energy; supported stopping | it localised the defect's line in many episodes (e.g. L1: 0.72 on the right line) | when every trial fails it cannot discriminate and puts its belief on "elsewhere" (M2); it localised W1 to the wrong method | the obstacle classes beyond a code defect (missing information, representation limits, ineffective search, verification cost, compute, false improvements, infeasible objectives) are not modelled |
| 3. Narrow autonomous repair | capture, reproduction from a checkpoint, localisation, regression test, synthesis, isolated test, independent verification, policy promotion, resume, retention; tracing, invariants (conservation laws), AST program analysis, differential property testing against reference models | 24 of 39 held-out obstacles end to end; 0 false repairs proposed by the loop | lost to unfocused search (35, 36, 33); mined laws used as constraints; G3 out of reach of every arm | CEGIS (the verifier's counterexamples are deliberately never fed back); repository modules; the real obstacles (SR-1b) |
| 4. Capability invention, dependency graph | the vault: hunks retrieved verbatim, operator kinds by evidence | reuse on recurrence (20 against 12; first passing candidate at 1.1 evaluations against 29.0) | transfer to unfamiliar defects through operator kinds not shown (retrieval 18) | new operators or abstractions invented; the capability dependency graph |
| 5. External verification and authority | separate verifier process; hidden tests; fresh kernel seeds; the resumed job; predefined policy with backup and rollback; one proposal per obstacle; mount namespaces, unprivileged users, no capabilities; a static guard | isolation measured and held; 12 controls held; no promotion outside a component | the verifier lacks a resource (total-cost) check: a leaking "repair" passed it 9 times | the policy has no explicit cost check; repository scope needs the human Supervisor |
| 6. AOR-1 | | | | not preregistered |
| 7. Deliverables | code, `tests_genesis/test_repair_foundry.py` and `test_repair_bench_study.py`, `scripts/b20r178_repair_bench.py`, the record as the initial benchmark report | | | |

Reproduce (as root, Linux with mount namespaces): `python3 scripts/b20r178_repair_bench.py OUT` from a clean clone at
`0e5d46f` (about 7 min on one core); `--rehearse` for the development-defect dry run;
`python3 -m unittest tests_genesis.test_repair_foundry tests_genesis.test_repair_bench_study`.

## 6. Prior art

- Automated program repair: GenProg (Le Goues et al. 2012), fix templates (PAR, Kim et al. 2013), SPR and Prophet
  (Long and Rinard 2015-16).
- Spectrum-based fault localisation: Tarantula, Ochiai.
- Benchmarks of real defects with held-out tests (Defects4J).
- Patch overfitting, where repairs pass the visible tests and fail held-out ones (Smith et al. 2015): the reason
  for the sealed check.

Nothing here is claimed new. What would be new for Genesis is doing it to itself, under its own Judge and Supervisor,
with the result measured.
