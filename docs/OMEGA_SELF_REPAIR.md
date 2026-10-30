# The obstacle loop: Genesis repairing its own obstacles (Daniel, 30 Oct 2026, 22:52 SGT)

> The ultimate Genesis shouldn't need you to tell it how to fix every obstacle. It should recognize the obstacle,
> determine what capability is missing, invent or retrieve a solution, verify it independently, and continue—without
> compromising its protected Judge or Supervisor.

Adopted on 30 Oct 2026 as a requirement on the whole system. This document says where Genesis stands against it,
what the loop is in this repository's terms, what it may never do, the test that would show it works, and the build
order. **State (30 Oct 2026, 23:20):** SR-a's capture and SR-b are built (`src/genesis/repair/`,
`tests_genesis/test_repair_capture.py`); everything else is not.

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

## 6. Prior art

- Automated program repair: GenProg (Le Goues et al. 2012), fix templates (PAR, Kim et al. 2013), SPR and Prophet
  (Long and Rinard 2015-16).
- Spectrum-based fault localisation: Tarantula, Ochiai.
- Benchmarks of real defects with held-out tests (Defects4J).
- Patch overfitting, where repairs pass the visible tests and fail held-out ones (Smith et al. 2015): the reason
  for the sealed check.

Nothing here is claimed new. What would be new for Genesis is doing it to itself, under its own Judge and Supervisor,
with the result measured.
