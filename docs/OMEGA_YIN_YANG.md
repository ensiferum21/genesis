# Yin and yang: the LLM improves Genesis, Genesis improves the LLM, and both improve how they improve (Daniel, 31 Oct 2026, 21:56 SGT)

> The idea is: the LLM improves Genesis. Genesis improves the LLM. Together, they improve the process by which both
> systems improve. So it's like yin and yang: one pushes the other, so mutually they improve. Can we have a solid
> approach to it?

Adopted on 31 Oct 2026 as a design. **Nothing in it is built or tested yet** (§8 says what is). It extends
`docs/OMEGA_RULE_INVENTION.md`, whose results (B20_R182-R186) are its starting point.

## 1. The two halves, and what each lacks

| | The LLM (yang) | Genesis (yin) |
|---|---|---|
| Strength | breadth: proposes anything expressible, fast, from a vast prior over code and mathematics | exactness: searches a defined space completely, verifies every claim against independent checks, keeps only what transfers |
| Weakness | unverified: plausible and wrong look alike; it cannot tell which of its ideas work on *these* problems; it repeats its own blind spots | narrow: it can only invent inside the language it was given; B20_R182-R186 showed its building blocks (the grammar, the substitution kinds, the derivation operators) are still the builder's |
| Temperature (physics) | hot: large jumps across the landscape | cold: careful descent, exact acceptance |

Each one's weakness is the other's strength. That is the yin and yang: not two copies of one thing, but two halves
that need each other to be whole.

**The circle around them belongs to neither.** In the symbol, the two halves turn inside a fixed circle. Here the
circle is the kernel's independent verifier (hidden tests, fresh workloads, the resumed job, the resource check),
the protected judge (`autonomy/feedback.py`, never modified), the preregistration of every comparison, and held-out
problems drawn by fixed random rules after both sides have committed their contributions. Neither side can change
the circle, and neither sees the held-out draw before a run. Without the circle, two systems that grade each other
drift into agreeing with each other (mutual reward hacking); with it, they can only improve by doing better on
problems neither chose.

## 2. The contract stays: Genesis's runtime is LLM-free

The no-LLM contract (`docs/OMEGA_NO_LLM_AUDIT.md`, `tests_genesis/test_no_llm.py`) holds. Genesis never calls a
language model. The LLM is outside the runtime, as the builder is today. The two meet only through **files**:

- the LLM writes **offers** (data in Genesis's own languages: transformations, grammar productions, derivation rules,
  mutation operators, components with their tests), which Genesis treats as unverified candidates, exactly like its
  own;
- Genesis writes **briefs** (computed, verifiable reports), which the LLM reads.

What changes is the labelling of results. Experiments in which LLM offers enter Genesis are a new, separate class:
**co-improvement experiments (LLM-assisted)**. Their results are never reported as Genesis's autonomous results, and
every admitted item carries its provenance (`genesis`, `builder`, or `llm:<session>`). Autonomy claims stay with the
LLM-free experiments.

## 3. The three loops

### Loop 1: the LLM improves Genesis (yang into yin)

Today the builder writes Genesis's building blocks by hand. Instead, the LLM sends offers, each as data and each tagged
with its provenance:
- **transformations**: an edit and its substitutions, for example `('map', 'meth', 'append', 'pop')`;
- **grammar productions**: statement templates over a component's vocabulary;
- **derivation rules**: rewrite rules over substitution tuples, new ways to make transformations from transformations;
- **mutation operators**: kinds of defect the random catalogue does not yet draw;
- **new components with their tests**: larger and more realistic testbeds.

None is trusted. An offer enters Genesis's library only through the gate its own inventions pass: a verified repair
on a family it did not come from. Genesis's posteriors then rank the offers by what they buy: verified repairs per
candidate added, the MDL score of `docs/OMEGA_RULE_INVENTION.md` §2.

Code-level contributions, such as a new kind of substitution, still go through the builder's protocol: tests,
preregistration, a record.

### Loop 2: Genesis improves the LLM (yin into yang)

An LLM's weights are not ours to change, and the contract forbids training a language model inside Genesis. Genesis
improves the LLM in the way that is open to it: through what the LLM knows when it works, its context, and the
procedures it follows. Every brief is computed from evidence, versioned, and stored under `docs/yinyang/briefs/`.

- **The failure atlas: what is missing, precisely.** For every obstacle no arm repaired, it records:
  - the suspected methods;
  - the admitted transformations that came closest, and why each failed (no donor with that skeleton, or a
    substitution kind the language lacks);
  - after the study is recorded and the defect becomes development data, the minimal missing substitution, computed
    by diffing the repair against the nearest donor.

  This turns "invent something better" into a sharp specification.
- **The verified library as worked examples.** These are the admitted transformations with their donors, repairs and
  admitting families. They are the LLM's few-shot context of what has actually worked here.
- **Refutations.** Every LLM offer that was rejected, or that caused a false repair, comes back with the
  counterexample: the failing check and the trace. This is Lakatos's proofs and refutations, mechanised.
- **The credit report.** For each earlier offer it gives whether it was admitted, how many held-out repairs it made,
  and how many candidates it cost. The LLM's next offers are conditioned on what paid.
- **Mutation reports on the LLM's own code.** Genesis's mutant generator (`genesis.repairkernel.mutants`) is a
  test-quality instrument. Run on code the LLM wrote, the surviving mutants show where the LLM's tests are blind. Run
  through Genesis's repair loop, they show what the LLM's code gets wrong.

The LLM is improved if its offers are admitted more often, its admitted offers repair more held-out problems, and its
tests kill more mutants. All three are measured against an LLM given the same budget without Genesis's briefs.

### Loop 3: both improve the process (the turning of the circle)

The process is the set of choices that govern the loops: what a brief contains, how many offers are allowed per
cycle, the admission threshold, which derivation operators run, how catalogues are drawn, how the budget is split
between Genesis's own search and the LLM's offers.

A meta-ledger (`docs/yinyang/LEDGER.md`) records every cycle's choices and outcomes. Either side may propose a change
to a choice:
- Genesis by its posteriors, for example its deriver's beliefs over operators;
- the LLM by an offer.

A change is adopted only when a preregistered comparison on a fresh draw shows that it raises verified capability per
unit of cost. The circle (verifier, judge, sealed tests, random draws, preregistration) is not a choice and is never
on the table.

## 4. Mathematics and physics of it

- **Expert iteration** (Anthony, Tian and Barber 2017; AlphaZero). A fast policy proposes, a slow exact search improves
  on the proposals, and the policy is trained on what the search found. Here the policy is the LLM, the search is
  Genesis with its verifier, and "training" is the brief: in context, since no weights are touched. With an auditable
  open model this could become fine-tuning on verified outputs (as in STaR or ReST); that would be a separate decision
  under the contract.
- **Replica exchange** (parallel tempering, Swendsen and Wang 1986). Replicas at different temperatures explore the
  same landscape and exchange states, so the hot one escapes local minima and the cold one refines. Here:
  - the LLM is the hot replica;
  - Genesis is the cold replica;
  - offers and briefs are the exchange moves;
  - the verifier is the acceptance rule.
  The theory's lesson applies: exchange helps when the replicas' distributions overlap. Offers must be in Genesis's
  language; briefs must be specific enough to move the LLM's proposals.
- **Mutual improvement, defined so it can be measured.** Let:
  - C_G(t) be Genesis's verified capability after cycle t (repairs on a fresh random draw per unit of compute);
  - C_L(t) be the LLM's (admitted offers per offer, held-out repairs per offer, mutation score of its tests).

  "The LLM improves Genesis" means C_G rises with offers on against off. "Genesis improves the LLM" means C_L rises
  with briefs on against off. "Together they improve the process" means the per-cycle gain ΔC_G(t) grows with t
  under the full loop faster than under either half-loop. In other words, a positive interaction in a 2 x 2 design
  (offers x briefs), compounding over cycles.
- **Collusion bound.** Both sides are measured only by the circle, on draws made after their contributions are sealed.
  So the only route to a better score is better repairs on problems neither chose. This is the guard against Goodhart.

## 5. The experiments, in order (none preregistered yet)

- **YY-0 (build, engineering):**
  - `genesis.repair.offers`: validate and import offers as data, with provenance, as candidates;
  - `genesis.repair.atlas`: the failure atlas and the brief, computed from a recorded study's rows and the then-public
    catalogue;
  - the provenance-split credit report.

  Tests: an offer cannot bypass admission; a brief is a pure function of recorded evidence; no runtime import of any
  LLM library (`test_no_llm` unchanged).
- **YY-1, Genesis improves the LLM:**
  - Setup: two fresh, independent LLM sessions with the same budget and the same development material. One also
    receives Genesis's brief (atlas, library, refutations, credit). Each submits at most K offers as data, sealed
    before the held-out draw.
  - Genesis admits on the development defects and is tested on a fresh random draw.
  - Primary: held-out repairs made by each session's admitted offers. Secondary: admission rate and false repairs.
- **YY-2, the LLM improves Genesis:**
  - Generation 2 alone, against generation 2 plus the briefed session's admitted offers, against generation 2 plus
    the unbriefed session's, on the same fresh draw (the 2 x 2 of §4).
  - The question: does the LLM add capability Genesis's own derivations do not, and does Genesis's brief make that
    contribution larger?
- **YY-3, the code loop:**
  - The LLM writes new, larger components with their tests.
  - Genesis mutation-tests them and returns the surviving mutants; the LLM strengthens the tests. Rounds continue
    until the mutation score stops rising.
  - Measured: the mutation score's rise with Genesis's reports, against generic feedback.
  - The components then become Genesis's next held-out testbed, so the realism gap closes as a side effect.
- **YY-4, the process:**
  - Three or more full cycles. Each draws a fresh catalogue, takes both sides' process proposals, and runs a
    preregistered adoption test.
  - Primary: whether the per-cycle gain grows under the full loop, against the half-loops.

**Running an LLM session is a cost, and the builder spawns one only with Daniel's go-ahead.** YY-1 and YY-2 need
two independent sessions per cycle; YY-0 needs none.

## 6. What could go wrong, and the guard for each

| Risk | Guard |
|---|---|
| The LLM sees the held-out problems | Offers are sealed (hashed and committed) before the draw. Draws use fixed random rules. Sessions get development material only |
| The builder, being an LLM, contaminates the comparison | The proposing sessions are fresh and independent of the builder's session. The builder never edits offers. Conditions are assigned before sessions start |
| Mutual reward hacking | Only the circle scores. The verifier and judge are fixed. The held-out set is drawn after sealing |
| Offers that are plausible but wrong | The admission gate. False repairs are counted and reported. A candidate the verifier rejects is rejected |
| Credit confusion | Provenance on every item. The credit report splits held-out repairs by source |
| Cost runs away | A fixed offer budget per cycle. Every report states the CPU and tokens per verified gain |
| "Genesis improves the LLM" overstated | Only context and procedure are claimed, measured against an unbriefed control. No claim is made about weights |

## 7. Why this is the right next step after B20_R182-R186

Those studies showed three things. First, Genesis can invent, admit and derive its own repair transformations, and
its derived generation reaches problems its lifted one does not (twice, B20_R185 and B20_R186). Second, its building
blocks are still the builder's, and its space has not beaten the builder's grammar. Third, about a third of every
random draw is beyond every arm. The first is the yin working. The second and third are exactly what a hot proposer
can supply, if a cold verifier filters it and the cold side's failure atlas tells the proposer where to look.

## 8. Status (31 Oct 2026)

| Part | Status |
|---|---|
| The circle (verifier, judge, preregistration, random draws, provenance) | **built** (B20_R178-R186) |
| Genesis's own invention, admission and derivation | **built and shown** (B20_R182-R186) |
| Offers importer, failure atlas, briefs, credit report | **not built** (YY-0) |
| Fresh LLM sessions as proposers | **not run**; needs Daniel's go-ahead |
| Mutation reports on LLM-written code | the mutant generator is built (`genesis.repairkernel.mutants`); the loop is **not built** |
| Meta-ledger and process adoption tests | **not built** |
| Any measured co-improvement | **none yet** |
