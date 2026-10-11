# B21 evidence: repeated improvement (W21–W23; E4 as DEV transitions), DEV only

Builder-generated and not reviewed independently. There are no sealed panels and no
custodian. Compounding generations (E4, GV5) stay **NOT ESTABLISHED**, and nothing here
is evidence about real experts.

The domain is B20's equational research on Wolfram's single axiom for Boolean algebra.
It is the one system where research raises successors (from 0 to 8–12 of 15 targets in
B20). The rules are fixed in `scripts/b21_improvement.py` (`rules.json` records them with
the code identity).

## Main run (`b21_improvement.py`; `run.log`, 1,816 s)

### E4 / W21: generations (`e4/transitions.json`)

A generation is a frozen library plus policy weights plus lineage, content-addressed by
`generations.freeze`. Each transition works as follows:
- it starts from the frozen parent;
- it runs two research runs under the parent's policy, with the parent's library as
  memory;
- it retrains the policy;
- it is scored on a fresh 15-target panel and on every earlier panel.

The rule (`generations.RULE`, declared before the run) accepts a child only if it gains
at least 1 target on the fresh panel and loses at most 1 on every earlier panel. There are
no human interventions and at most one child per transition.

| Transition | Parent → child (panels) | Decision | Research CPU |
|---|---|---|---|
| 1 | P1: 0 → 11 | ACCEPTED | 52.0 s |
| 2 | P1 11 → 11, P2 9 → 9 | ROLLED_BACK (no gain on P2) | 0.07 s |
| 3 | P1 11 → 11, P2 9 → 9, P3 12 → 12 | ROLLED_BACK (no gain on P3) | 0.09 s |

- **Saturation.** The only accepted transition is the first, which starts from an empty
  library. After it, the conjecture space the pools draw from is saturated: the library
  holds 94–96 lemmas, the later runs' pools were almost entirely proved already, and
  research had nothing new to try.
- **Retention.** It held on every earlier panel.
- **Cost.** The process cost is 52.1 CPU-s for one accepted improvement.
- **GV5 (three compounding generations): NOT ESTABLISHED.** One supported transition
  from scratch, then two rollbacks. A domain with a larger frontier is needed before
  compounding can even be tested.

### W22: a primitive from an operator-completeness adversary (`w22/summary.json`)

**The proposal.** The adversary (`primitives.propose`) counts subterm patterns in the
development targets that E failed on, at seed 600. It skips patterns that are merely an
operation applied to distinct variables, because those would only rename an existing
operation. It proposed `p1(P0,P1) := s(s(P0,P1),P0)`.

**The contract.**
- **Round trip.** Fold then unfold returns the original on all 119 pool equations.
- **Migration.** Migrating the base library and rolling it back gives the identity.
- **Lean.** The definition becomes the last axiom of `ba_wolfram+p1`. The Lean bridge
  binds every replay to the *base* statement (without `p1`) and instantiates `p1` by its
  λ-term, so the definition is discharged by `rfl`. An extension can therefore never prove
  anything new about the base language.

**The comparison**, at equal 60 s research budgets, scored on 15 targets in the base
language:

| Seed | Base | Primitive | Renaming control | Empty |
|---|---|---|---|---|
| 610 | 11 | 11 | 11 | 0 |
| 611 | 12 | 12 | 12 | 0 |

- **Result.** No gain from the primitive, and no difference from the renaming control:
  the same conjectures, unfolded into the base language.
- **SPEC-41.1.** The renaming control is the test of whether a primitive is genuinely
  new. This primitive is not.

**Lean bridge.** In the main run, 0 of the 11 primitive-arm successor proofs replayed;
all failed with ELABORATION_ERROR. The cause was in `fof_lean.ground_hints`, not in the
bridge. See the follow-up below.

### W23: heterogeneous routes and fault injection (`w23/routes.json`, `w23/expert.json`)

**Routes.** Each claim goes through four routes that share no code:
- the decider (exact evaluation);
- the prover (E);
- the kernel (Lean replay bound to a statement generated from the claim);
- countermodels (the finite model finder, re-checked by the independent evaluator).

**Diagnosis.** `faults.diagnose` accepts only with a kernel check. It reports
disagreement, naming the suspect route, and never resolves it by majority.

**Fault injection.** Faults are a corrupted proof (one literal flipped in a derived
clause), another item's proof, a valid proof offered for a false claim, and a flipped
decider.
- Only 2 items qualified: lemmas whose library proof used no earlier lemma.
- 0 false acceptances.
- Clean true claims were ACCEPTED and clean false ones REJECTED_FALSE.
- Corrupted and swapped proofs gave UNVERIFIED.
- False claims with proofs gave REJECTED_FALSE.
- Flipped deciders gave DISAGREEMENT, with the decider as suspect.

**Expert questions.** There were 12 claims on Wolfram's axiom with the decider withheld,
a 1 s prover and countermodels up to size 2. Without help, 8 stay undecided. With 6
questions answered by a **SIMULATED** expert (the decider flipped at error rate 0.1), the
correct decisions rose from 4/12 to 10/12, at an intervention cost of 6.

## Follow-ups (written after the main run; the main run's records are unchanged)

### `w22_lean_followup.json` (`b21_w22_lean_followup.py`; log `w22_lean_followup.log`)

**The defect.** E steps of the form `rw(…rw(spm(A, B), C)…)` on Wolfram's axiom got no
ground instances. These steps often include ordered rewriting by a derived commutativity
law. Without instances, `grind` alone could not close them.

**The repair** (`fof_lean`):
- the overlap result is rewritten towards a normal form by the other parents, using
  size-decreasing rules and matching modulo a commutativity parent;
- it is then matched to the conclusion;
- the rule and commutativity instances it used become hints;
- matched overlaps are tried before blind enumeration.

`tests_formal/test_improvement.py::Hints` covers it, using the step that used to fail.

**The rerun.** The main run kept no proof objects, so the follow-up regenerates the seed-610
arms under the same rules. A CPU budget means the libraries can differ from the main
run's. The panel is the same: every main-run bridge target is in it.

| Arm | Library | Successor | Lean replays |
|---|---|---|---|
| primitive (bound to the base statement, `p1` as λ-term) | 71 | 11/15 | **11/11 THEOREM_CHECKED** |
| base (plain Wolfram chains) | 87 | 11/15 | **11/11 THEOREM_CHECKED** |

Chains are 5–21 lemmas long in the primitive arm and 29–43 in the base arm.

### `w23_followup.json` (`b21_w23_followup.py`; log `w23_followup.log`)

There were 8 items: true Sheffer equations that E proves from the axioms alone. Each was
checked clean and with every fault kind, 48 checks in all.

| Kind | n | Verdicts |
|---|---|---|
| clean true | 8 | ACCEPTED 8 |
| clean false | 8 | REJECTED_FALSE 8 |
| corrupted proof | 8 | UNVERIFIED 8 |
| swapped proof | 8 | UNVERIFIED 7, **ACCEPTED 1** |
| false claim with proof | 8 | REJECTED_FALSE 8 |
| flipped decider | 8 | DISAGREEMENT 8 |

**The one acceptance.** The predeclared definition (as in the main run) counts any
acceptance under a proof fault as a false acceptance, so the count is **1**.

On inspection the acceptance is sound:
- The claim `s(s(X,s(X,X)),X) = s(X,X)` is true. The decider says so, and the kernel
  checked it.
- It is the `Y := X` instance of another item, `s(s(X,s(Y,X)),X) = s(Y,X)`. That is the
  only other item it instantiates.
- Replay rebuilds the inputs from the trusted statement of *this* claim. A refutation of
  the general equation's negation, replayed against the instance, is therefore a genuine
  proof of the instance.

No false claim was accepted, in either run.

**Expert sweep.** There were 24 claims (16 true, 8 false), 16 of them undecided without
help. Correct decisions out of 24:

| Budget (questions) | 0 | 4 | 8 | 16 |
|---|---|---|---|---|
| SIMULATED expert, error 0.1 | 8 | 12 | 15 | 21 |
| SIMULATED expert, error 0.3 | 8 | 11 | 15 | 21 |

Each answered question is charged to the intervention budget. Wrong expert answers (up
to 3 at budget 16) are recorded. The simulated expert only exercises the interface and
the budget accounting. Whether real experts help remains unmeasured.

## Not established

- **GV5, compounding.** One transition from scratch, then saturation.
- **W22, a primitive that helps.** No gain over base research or the renaming control.
- **W23 with real experts and real disagreements.** Every disagreement observed was
  injected.
