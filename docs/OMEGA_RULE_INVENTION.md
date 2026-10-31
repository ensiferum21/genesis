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
   to abstract, and which productions of the grammar to try first. Each admission updates the inventor's posterior
   over generalisation levels (which levels produced rules that transferred), and each verified dream repair its
   posterior over grammar productions, so later probes start from the levels that worked and later dreams from the
   productions that worked. The claim of self-improvement needs evidence across generations on
   fresh tasks at matched resources (`docs/OMEGA_SELF_REPAIR.md` §8, the Foundry directive item 6); the mechanism is
   built first, the claim is tested later.

**Never.** The inventor may not create a rule that touches a protected path, changes a check, or uses a name the guard
denies; rules are applied to repairable components only; the verifier and the policy stay the kernel's.

## 3. What is built (31 Oct 2026)

`src/genesis/repair/invent.py` (research plane; `tests_genesis/test_repair_invent.py`):
- **the dream** (`dream_edits`): the grammar of statements from the component's own vocabulary (`vocabulary`: each
  attribute by the kind of value it holds, dict values by how they are used, the private methods): counters and
  indexed counters incremented or decremented by an argument, a local or 1; container calls (`add`, `discard`,
  `append`, `remove`) on indexed values; `setdefault` insertions; deletions, also of entries left empty;
  invalidations; calls of private methods; and every augmented assignment flipped to its sibling operator. On
  B20_R181's development defects the grammar holds the repairs of N1, N4, K1 and E3, which no arm reached; not those
  of D3 or D4.
- **anti-unification** (`abstract`): the verified patch's edit (an insertion after an anchor statement, or a
  replacement) lifted at six levels: concrete; bare names; names and attributes; also the operations on values
  (`add`, `discard`: lifting them is what turns "after `adj[u].add(v)`, add `adj[v].add(u)`" into the general mirror
  rule); also the constants; and `free`, where an attribute the template names and the pattern does not becomes a
  hole filled by every attribute of the target that holds the same kind of value. Builtins are never lifted. Lifting
  the reference repairs of the 45 development defects gives 86 rules over 32 defects; two of them transfer exactly to
  another defect (the mirror rule, N1 to N2 and back).
- **application** (`apply_rule`): a rule matches every statement with the same lifted shape and instantiates its
  template there; it does not insert what the method already does.
- **the library** (`Library`, `rules.jsonl` in the research plane's own directory): rules with provenance (the
  episode, the family, the edit, the missing capability), status (candidate, admitted, rejected), successes and
  failures, a Beta posterior. A rule is admitted only by a repair the kernel's verifier accepted on an obstacle of
  another family; a candidate whose patch the verifier rejects, with no admission, is rejected.
- **the inventor** (`Inventor`, `inventor.json`): a Beta posterior per level; probes try candidate rules in the order
  of their level's posterior mean, then by how few candidates they produce (minimum description length).

`src/genesis/repair/loop.py`: version 4 ('loop') is version 3 ('loop_v3', frozen) plus the library's admitted rules;
'dream' adds the grammar and lifts its verified patches; 'dream_online' is the same search without the learning;
'probe' tries only other families' candidate rules and records what the verifier said; the inventor learns from it.

`scripts/b20r182_rule_invention.py` (B20_R182): the cycle with no human step (§4).

## 4. The test: B20_R182 (SR-2a)

Preregistered before any of it runs on its held-out defects:
- a **curriculum** of the 45 development defects (B20_R178's 21, B20_R180's 12, B20_R181's 12); Genesis runs the
  invention cycle on it with no human step: it finds the obstacles version 3 does not solve (job seed 1), dreams on
  each (a fresh job, 1,000 evaluations), lifts the verified repairs into rules, probes every development defect (seed-2
  jobs) with the candidate rules of other families, admits by verified transfer, and keeps a library;
- a **fourth catalogue** of 12 held-out defects in three new components, written before the cycle runs, each checked
  automatically for an unintended homologue (B20_R181's lesson);
- the comparison at the same budget per obstacle: version 4 (Genesis's own rules) against version 3 (the builder's
  rules only) and against version 3 with the dream grammar searched online at the same budget (does a learned rule
  beat searching the bigger space directly?); the invention cycle's cost reported separately.

## 5. Status (31 Oct 2026, after B20_R182)

| Step | Built | Shown (B20_R182, testbed only) | Not built or not shown |
|---|---|---|---|
| 1 detect | unsolved, and false repairs (the verifier's rejection), told apart | 16 of 45 development defects unsolved by the builder's rules, 3 of them false repairs | an exhausted repertoire told from a spent budget (version 3 always spends its budget); only exhausted repertoires sent to invention (every unsolved obstacle is) |
| 2 diagnose | suspected methods (posterior); the component's vocabulary | | missing-capability classes beyond code defects |
| 3 invent | the dream grammar; anti-unification lattice | 6 of the 16 repaired by the dream, verified; 17 rules lifted | new *kinds* of transformation outside the grammar (the grammar is the builder's) |
| 4 verify | admission by kernel-verified transfer to another family | **1 rule admitted**: symmetry completion (`self.A[x].m(y)` → `self.A[y].m(x)`), lifted from N2's repair, verified on N1; no false repair in any probe | failures of candidates that never pass the visible tests are not counted |
| 5 learn, reuse | library with provenance and Beta posteriors; loop v4 | | **reuse on unseen problems: not shown** (the rule matched no held-out defect; v4 = v3, 21 of 36 each) |
| 6 improve the inventor | posteriors over generalisation levels and grammar productions; derivation of new transformations (inverse, transfer, composition, generalisation) with a posterior per operator | the learned grammar order did not invent faster (B20_R183); **the derived transformations reached two random mutants the lifted ones and the builder's rules did not** (B20_R185, P2, p_Holm 0.047) | that the effect replicates; compositions (never admitted); beating the builder's grammar |

**What B20_R182 found against the plan.** The grammar searched online at test time repaired 30 of 36 held-out
obstacles, version 4 21 (p 0.022), at a quarter of the CPU, and lost 2 that version 3 reaches because the bigger
space pushed them past the budget. At this scale the space is what helps, not the rules lifted from it: a learned rule
pays when it compresses a space too big to search, and this testbed's is not. And the grammar is the builder's. The
next step toward the requirement is therefore not more rules from the same grammar but **Genesis growing the grammar
itself** (new productions composed from verified repairs, kept only when they buy verified repairs per candidate
added: the MDL trade of step 4 applied to the space), and a testbed whose repair space is too big to search online.

| Study | Status | Result |
|---|---|---|
| B20_R182 (SR-2a) | recorded (`docs/checkpoints/B20_R182_RECORD.md`) | RULES_INVENTED; LOOP_V4 = LOOP_V3; DREAM_ONLINE_BEATS_LOOP_V4 |
| B20_R183 (SR-2b) | recorded (`docs/checkpoints/B20_R183_RECORD.md`) | RULES_INVENTED replicated (the same rule); LOOP_V4 = LOOP_V3 replicated; the grammar's lead not replicated (11-5, p 0.21); step 6 NO_DIFFERENCE_SHOWN |
| B20_R185 (SR-2c) | recorded (`docs/checkpoints/B20_R185_RECORD.md`) | SPACE_INVENTED; P1 NO_DIFFERENCE_SHOWN (lifted = version 3); **P2 INVENTOR_IMPROVED** (derived > lifted, 7-0, p_Holm 0.047, two mutants); P3 NO_DIFFERENCE_SHOWN (= the builder's grammar) |

## 6. Next: Genesis growing its own repair space (SR-2c, B20_R185; planned 31 Oct 2026, 12:55)

B20_R182 showed that what helps is the space searched, and the space (the dream grammar) is the builder's. SR-2c moves
the space to Genesis: it invents the *productions* themselves, from its own verified repairs, and invents new ones from
those it has (the closure of a set of symmetries), with every production admitted only by a verified repair of another
family.

**Physics: a defect breaks a symmetry, the repair restores it.** A component's code is full of near-copies: `link`
adds `adj[u].add(v)` and must add `adj[v].add(u)`; `reserve` moves an amount from `held` to `reserved` and `release`
moves it back. A verified repair is very often the image of a statement the component already has under a small
transformation: two names exchanged, one attribute put for another of the same kind, an operator or a method put for
its partner, a constant shifted. Genesis finds, for each verified repair, the *donor* (the statement of the component
with the same syntax tree whose leaves differ least from the repaired statement) and the *transformation* that maps
the donor to the repair (the leaf substitutions, abstracted by role: "exchange two names", "another attribute holding
the same kind of value", "`add` for `discard`", "`+` for `-`", "a constant one larger"), and where the repair went
relative to the donor (after it, in its place).

**Maths: a transformation is a production; the set grows by group operations.** Applied to a new obstacle, a
transformation generates candidates: the image of every statement of the suspected methods, inserted after it or put
in its place. The inventor then derives new transformations from the admitted ones, without new repairs: the
*inverse* (`discard` for `add` from `add` for `discard`; a constant one smaller), the *transfer* to the other edit
(after ⇄ in place), the *composition* of two (at most two substitutions), the *generalisation* of a concrete map to
any partner of the same kind. These are the operations of the group the symmetries generate. A derived transformation
is admitted, like a learned one, only by a verified repair of another family; the inventor keeps a Beta posterior over
its derivation operators, so the operators that produced admitted transformations are tried first: it learns how to
invent.

**Reality: defects nobody chose.** The held-out catalogue is drawn by random mutation (`defects5.py`, sealed before
any of this code; `evidence/mutant_catalogue_b20r185/README.md`): 24 mutants of the fifteen components, the
first real obstacles of a shuffled enumeration.

**The test (to be preregistered).** Curriculum: the 57 hand-written defects (all now development data). Generation 1:
version 3 and the dream on the curriculum; every verified repair lifted into transformations; probes on other families
admit. Generation 2: the inventor's derivations of the admitted ones, and the transformations lifted from what
generation 1's library repairs; probes admit. Held out: the 24 mutants x 3 jobs at 300 evaluations, arms version 3
(the builder's rules), version 3 + generation 1's transformations, version 3 + generations 1 and 2, the builder's
grammar searched online, enum. The questions: does Genesis's own space make it more capable than the builder's rules
(generation 1 against version 3)? Does the second generation improve on the first (step 6)? Does Genesis's space match
the builder's grammar on defects neither chose?
