# Genesis inventing its own repair rules (Daniel, 31 Oct 2026, 11:26 SGT)

> Genesis needs to learn how to invent its own repair rules, instead of relying on you.
> 1. Detect why existing repairs fail. 2. Diagnose what capability or repair rule is missing. 3. Invent a new repair
> rule autonomously. 4. Verify it against independent tests. 5. Learn from successful repairs and reuse them.
> 6. Improve itself by developing better ways to invent future rules.
> The ultimate goal: Genesis encounters a problem it cannot solve, figures out what's missing, invents the solution,
> and becomes more capable—without human intervention.
> Pls adapt and attempt this using physics, maths and reality.

Adopted on 31 Oct 2026. This document is the adapted vision, in this repository's terms, with what is built, what is
tested and what is not. It extends `docs/OMEGA_SELF_REPAIR.md` (the obstacle loop, B20_R178-R181).

## 1. Where Genesis stands (31 Oct 2026, 11:30)

Every repair rule the loop has was written by the builder: the line-preserving edits, the homologous transplant, law
restoration (B20_R178), and the three operators of B20_R181 (symmetry completion, vestigial calls, dimensional
offsets), which the builder wrote after reading where B20_R180's arms failed. B20_R181 showed that such a rule can
reach a held-out defect nothing else reaches (the vestigial call, E2, in every job), and that a rule written for one
defect can miss its own class when the defect erases the evidence the rule looks for (symmetry completion, N1 and N2).
Seven of B20_R181's twelve defects were beyond every rule.

The requirement: the builder stops writing rules; Genesis writes them.

## 2. The adapted loop: from an unsolved obstacle to a new rule

**A rule** is a program transformation with holes: a *pattern* (a statement shape, its identifiers and constants
replaced by metavariables where they are abstracted) and a *template* (the statement to insert after a match, or to
put in its place), sharing the metavariables. A rule applied to a source gives candidate patches; the loop's search
evaluates them like any other candidate. A rule is data, kept in a library, not code the builder writes.

The six steps, each with the principle it rests on:

1. **Detect why existing repairs fail** (reality: measured, not declared). An obstacle is *unsolved* when the loop, at
   its normal budget, proposes nothing that passes what it can see, or proposes a patch the independent verifier
   rejects. The loop's own record says which: the repertoire was exhausted (no rule produced a passing candidate:
   *a missing rule*), the budget ran out first (*a search problem*, not a missing rule), or a candidate passed the visible
   checks and failed the verifier (*a false repair*: the rules are fine, the evidence is too weak). Only the first is
   sent to invention.

2. **Diagnose what is missing** (physics: the residual; maths: the posterior). The obstacle model already holds a
   posterior over where the fault is. What is missing is a *transformation* that the current rules do not generate
   there. The diagnosis is the set of suspected methods and the *vocabulary* the component already uses: its
   attributes, the arguments of the suspected methods, the container methods and the private methods it has. The
   missing rule must be expressible in that vocabulary (the guard forbids anything else: a repair may only re-arrange
   what the component already does).

3. **Invent** (physics: dreaming as annealing at high temperature; maths: least general generalisation). Two stages:
   - **search for a solution the rules could not make**: a deeper, more expensive search over a *grammar of statements*
     built from the vocabulary (calls of container methods on indexed attributes, assignments, deletions, calls of
     private methods, increments, and the flip of every operator to its siblings, augmented assignments included),
     inserted or substituted at the suspected methods, at a budget several times the normal one. This is the
     "dream": the expensive exploration happens offline, not when a job is waiting;
   - **abstraction**: a solution found by the deep search is generalised into rules by **anti-unification** (Plotkin,
     1970): the concrete before and after are lifted into pattern and template, and each identifier class (names,
     attributes, methods, constants) is either kept or abstracted. The candidates form a lattice from the concrete
     patch (it matches only where it was found) to the most general rule (it matches everywhere and proposes too
     much). Which point of the lattice is right is not known in advance; it is measured (step 4).

4. **Verify against independent tests** (reality: held out, independently judged). A candidate rule is admitted to the
   library only if, on obstacles it was **not** learned from (other defects of the training curriculum, other
   components, other jobs), the loop using it obtains repairs that the **kernel's verifier** accepts (hidden tests,
   fresh workloads, the resumed job, the resource check), and it causes no false repair the verifier has to catch. The
   score is a **minimum description length** trade (maths: Rissanen; Occam): a rule earns its place by the verified
   repairs it buys per candidate it adds to every future search. The rule never sees the verifier's checks; it sees
   only accepted or not, once per obstacle.

5. **Learn and reuse** (maths: Bayesian updating). Each admitted rule keeps its record: where it came from, what it
   matched, its successes and failures, a Beta posterior on its success rate. The loop applies library rules early,
   ranked by that posterior and by how cheap they are; rules that keep failing sink, and are retired below a
   threshold. Provenance is kept for every rule (the obstacle it came from, the solution, the generalisation chosen,
   the verified repairs that admitted it).

6. **Improve the inventor** (physics: renormalisation, the flow toward the right scale of description; maths: a
   bandit over the inventor's own choices). The inventor's choices are themselves parameters: which identifier classes
   to abstract, how deep the grammar goes, how many candidate rules to test. Each admission outcome updates the
   inventor's posterior over its choices (which generalisation levels produced rules that transferred), so later
   inventions start from the levels that worked. The claim of self-improvement needs evidence across generations on
   fresh tasks at matched resources (`docs/OMEGA_SELF_REPAIR.md` §8, the Foundry directive item 6); the mechanism is
   built first, the claim is tested later.

**Never.** The inventor may not create a rule that touches a protected path, changes a check, or uses a name the guard
denies; rules are applied to repairable components only; the verifier and the policy stay the kernel's.

## 3. What is built (31 Oct 2026) — see §5 for the status table

`src/genesis/repair/invent.py`: the grammar of statements (the dream), anti-unification into a lattice of candidate
rules, rule application, the rule library with provenance and Beta posteriors, the inventor with its posterior over
generalisation levels, and the invention cycle (detect, dream, abstract, admit by kernel-verified transfer, retain).
The loop version 4 (`loop.py`, arm 'loop') is version 3 plus the library's rules; version 3 is frozen as 'loop_v3'.

## 4. The test: B20_R182 (SR-2a)

Preregistered before any of it runs on its held-out defects:
- a **curriculum** of the 45 development defects (B20_R178's 21, B20_R180's 12, B20_R181's 12); Genesis runs the
  invention cycle on it with no human step: it finds the obstacles version 3 does not solve, dreams, abstracts, admits
  by verified transfer within the curriculum, and keeps a library;
- a **fourth catalogue** of 12 held-out defects in three new components, written before the cycle runs, each checked
  automatically for an unintended homologue (B20_R181's lesson);
- the comparison at the same budget per obstacle: version 4 (Genesis's own rules) against version 3 (the builder's
  rules only) and against version 3 with the dream grammar searched online at the same budget (does a learned rule
  beat searching the bigger space directly?); the invention cycle's cost reported separately.

## 5. Status

| Step | Built | Shown | Not built or not shown |
|---|---|---|---|
| 1 detect | the loop's record distinguishes exhausted repertoire, spent budget, false repair | | |
| 2 diagnose | suspected methods (posterior); the component's vocabulary | | missing-capability classes beyond code defects |
| 3 invent | the dream grammar; anti-unification lattice | (B20_R182) | inventing new *kinds* of transformation outside the grammar |
| 4 verify | admission by kernel-verified transfer, MDL score | (B20_R182) | |
| 5 learn, reuse | library with provenance and Beta posteriors; loop v4 | (B20_R182) | |
| 6 improve the inventor | posterior over generalisation levels | | evidence across generations on fresh tasks |
