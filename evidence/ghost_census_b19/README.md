# B19 / W16 evidence: Ghost Census beyond the small development family

DEV diagnostic. Nothing here was reviewed independently. No sealed study was run, and no
efficacy is claimed. B13's Experiment B result (KILL on its small family) stands
unchanged in `evidence/experiment_b_dev/`.

## What was run

**Plan.** `discovery/ghost_census.PLAN` was written to `run*/plan.json` before anything
ran (SHA-256 in the file). Both runs used the same plan.

**Family.** Ten equational theories and 125 problems:
- groups, groups with (xy)² = x²y², groups of exponent 2;
- lattices and distributive lattices;
- rings and Boolean rings;
- quasigroups and Moufang loops;
- Huntington's basis for Boolean algebra.

Each problem has one goal and three candidate lemmas from the same theory, including a
true and a false lemma where the theory has them.

**Labels.** Labels come first and do not depend on the arms:
- TRUE: E (strategy schedule, 30 s) claims Theorem *and* the proof object replays in
  Lean;
- FALSE: a countermodel re-checked by the independent evaluator.

The result is 85 TRUE, 39 FALSE and 1 UNKNOWN.

**Validation.**
- Lean `decide` agrees with the independent finite evaluator on 138 random finite tables
  for every family formula, so the FOF→Lean translation is faithful on those tables.
- Every formula round-trips through the parser.

**Arms.** Six arms, at 2 s and 8 s CPU per problem, in randomized order:
- B11's portfolio with `--auto`;
- the strongest baseline: countermodel search, then E's strategy schedule;
- lemmas unfiltered;
- Ghost Census (B11 allocation);
- Ghost Census with a leaner allocation;
- an oracle that is given the true lemmas for free (diagnostic only).

**Lean replay.** Every PROVED outcome (deduplicated) is replayed step by step in Lean.
Replay is evaluator cost and is not charged to the arms.

## Run 2 (`run2/`, the result)

Settled problems out of 125:

| Arm | 2 s | 8 s |
|---|---|---|
| portfolio_auto (B11) | 50 | **124** |
| portfolio (strongest baseline) | 48 | 123 |
| lemmas_unfiltered | 2 | 85 |
| ghost_lemmas (B11 allocation) | 37 | 76 |
| ghost_lemmas_lean | 39 | 102 |
| oracle_lemmas (diagnostic) | 48 | 123 |

**Decision (preregistered rule): RETIRE_NO_HEADROOM.**
- The margin is 7 problems.
- Even free knowledge of which lemmas are true does not beat the best baseline at either
  budget: oracle − best baseline = −2 at 2 s and −1 at 8 s.
- The Ghost Census arms lose to the baseline at both budgets.

The branch is retired for this scope: equational theories of this size, E 3.5.1, and 2–8
CPU-second budgets.

**Diagnosis.**
- **Family.** E's strategy schedule proves 84–85 of the 85 true goals within 8 s from the
  axioms alone. That leaves no room for lemma selection.
- **Allocation.** At 2 s the B11 slices dominate. They give at least one second to
  countermodel search, and on true goals that search uses the slice and leaves no time to
  prove. The lemma arms cannot even reach the goal.
- **Mechanism.** It is not tested by this family. A family where E fails without help is
  needed. B20's pilots on Wolfram's single axiom for Boolean algebra are such a regime:
  E needs 5–15 s for basic lemmas there.

## Run 1 (`run1/`, kept with a harness defect)

Run 1 used `modelfind.find_model(total_seconds=…)` as first written in B19. Before each
model size, that code required a full second left. Under the 2 s budget the countermodel
slice is about one second, so the search stopped after size 1, and no arm found a
countermodel at 2 s. Run 1's 2 s results therefore mostly measure proving.

At 8 s the effect depended on the arm:

- **Baseline and oracle arms.** Unchanged: portfolio_auto 124, portfolio 123, oracle 124.
  These arms search for countermodels only to the goal, with a 2.4 s slice.
- **Ghost Census arms.** Much better in run 1: 120 and 114, against 76 and 102 in
  run 2. The defect made their one-second per-lemma countermodel checks almost free.
  Even that nearly free filter stays below the baseline.

Run 1 reached the same decision, because the rule compares the oracle with the baseline.

Once the defect was found, run 1 was stopped during Lean replay. Its plan, labels, family
and full log, with every arm outcome, are kept.

The fix allows a final call when less than a second remains. A regression test is
`tests_formal/test_ghost_census.ModelFinderBudget`.

## Lean replay of E proofs

`formal_research/fof_lean.py`:
- The trusted statement `∀ (U : Type) [Nonempty U] (symbols…), axioms → goal` is
  generated from the problem, never from the proof.
- The untrusted proof module has one lemma per E inference. Each lemma is proved from
  exactly E's parent clauses, by `grind` given ground instances. The instances are found
  by superposition overlaps and bounded instantiation, and confirmed by a small
  congruence closure.
- Skolem constants become existential witnesses.
- Lemma-assisted proofs replay each lemma's own E proof first.
- The checker binds the result to the statement and audits axioms.
- Tests check that a proof cannot be bound to another goal and that a tampered step
  fails.

**Run 2 result.** 471 of the 473 distinct PROVED proof objects replay to THEOREM_CHECKED. Two do not, and stay E's claims. All 85 TRUE labels are Lean-checked.
