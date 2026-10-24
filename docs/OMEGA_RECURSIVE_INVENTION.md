# Genesis Ω: recursive perception, cognition and invention

**Status of this document.** This is the adopted design for Genesis's next architecture. It merges two attachments
from Daniel (24 Oct 2026, 20:31, "the unified research architecture" and "the master implementation directive") and
his instruction:

> "There might be things beyond senses too. I need it to be able to achieve that and be extremely powerful. Adapt to
> our solution and push this idea after adapting and refining into the branch so no agent can miss its full details."

It is adapted to the repository as it stands. **Nothing in it is claimed as achieved.** §2 says what exists, with
its tests and evidence. Everything else is a plan, and a plan is never reported as an implementation. Read it after
`docs/GENESIS_OMEGA_PLAN.md` §0a (the 15:35 directive, which still applies in full).

## 0. The goal in one paragraph

An LLM-free, autonomously developing research system. It decides for itself:
- **what capability it lacks**: an observation, an instrument, a concept, a representation, a bound, a method, a
  proof, a workflow, or a way of improving any of these;
- **how to build that capability**;
- **how to combine** capabilities, including ones that are useless alone;
- **how to attack** a problem;
- **how to improve** the procedures that do all of this, and the procedures that improve those, with no fixed
  ceiling on the levels.

Every claimed gain survives an independent judge the system cannot touch. Gains must **accumulate**: later
generations must make verified discoveries on unfamiliar tasks more effectively than earlier ones, at matched total
compute, including the cost of producing them. If that last condition fails, Genesis is only a complicated search
framework, and the measurements must be able to show it.

## 1. Beyond senses: what a "capability" is

Daniel's point is that senses are one kind of missing capability among many. Genesis must be able to discover that
the thing it lacks is not on any list we give it. Therefore:

1. **Capabilities are typed executable research objects (ROs, §3).** Their kinds form an open set. The kinds below
   are the seed set, not a limit. A new kind is defined by composing existing types and declaring a contract (§3.3),
   so Genesis can create kinds of capability nobody listed.
2. **The seed kinds**, grouped by what they contribute:

| Group | Kinds | What it contributes | First home in the repository |
|---|---|---|---|
| Perception (accessibility) | `Sense`: a deterministic computation over what is already known (a statistic, a structure, an invariant, a compression) | Makes existing information *usable*; adds no new information | `adaptation/receptors.py` (hand-made weakness sensors), `interpret.fingerprint`, graph probes of the Cartographer looks |
| Perception (new information) | `Instrument`: an experiment, probe or external measurement whose result was not computable from the inputs; `ExperimentDesign` | **New information**, at a cost | `causal/instruments.py` (45 test sets), `science/design.py` (experiments chosen by value), the lab of `causal/active3.py` |
| Fusion | `Composition`: an operator that combines observations or capabilities; `Workspace` relations | Perspectives no single part gives | — (§5, §6) |
| Representation | `Representation`, `Encoding`, `Relation`, `Gadget`, `Transformation`/`Reduction`, `Decoder` | Problems become easier, transferable or certifiable | `representation/` (relations, gadgets, encodings, factorisation), `compiler/`, `mrdl.py` + `primitives.py` (derived primitives with contracts), `invention/representations.py`, `quotients.py`, `decompositions.py`, `invention/worlds.py` |
| Mathematics | `Concept` (a definition), `Invariant`, `Bound`/`Certificate`, `Conjecture`, `Theorem`, `ProofProcedure`, `TheoryPackage` | Knowledge that is true, not only useful | `formal_research/` (pinned Lean/Mathlib, sandboxed checking, proof search, theory packages), `bounds_large.py` (certified bounds), `discovery/obstruction.py` |
| Method | `Operator`, `Algorithm`, `SearchProcedure`, `Solver` | Solutions | `candidate_kinds/mcx2.py` (programs over physics operators), `invention/solver_programs*.py`, `science/acquire.py` |
| Strategy | `AttackStrategy`, `Workflow`/`ResearchParadigm`, `Allocator` | How to spend effort | `autonomy/loop.py`, `autonomy/queue.py`, `adaptation/metabolism.py`, `autonomy/kmap.py` |
| Self-knowledge | `Diagnoser` (capability-gap scientist), `Predictor` (what will work where) | Why progress stops | B20_R132 (its first real instance), `autonomy/kmap.py`, `autonomy/adversary.py` |
| Self-improvement | `Improver`, and an improver of improvers (no fixed level) | Better inventors | `autonomy/process.py` (levels under one fuel budget), `representation/processes.py` (a gated synthesiser improver), `autonomy/selfimprove.py` (process genomes) |
| Language | `Primitive`, `TypeConstructor`, `Library` version | A larger invention vocabulary | `science/library.py` (synthesise, register, roll back), `primitives.py`, `representation/library.py` |

3. **Information and accessibility are kept apart, always.** A deterministic `Sense` cannot add information that its
   inputs did not contain; it can only make that information cheaper to use. An `Instrument` adds information and
   costs resources. Every RO declares which it is (§3). Gains are attributed to one or the other, and a claim that a
   sense "discovered" something is checked against the inputs it had.
4. **The protected kernel is not a capability.** No RO of any kind can modify it (§14). Evaluation sensitivity may be
   improved only *outside* the judge, by better instruments and more data. The judge's own thresholds and protocols
   change only by a human-gated amendment.

## 2. What exists today (audited 24 Oct 2026, 20:40; tests named, evidence named)

| Capability | Exists | Tested | Evidence on real tasks |
|---|---|---|---|
| Typed invention languages: mcx2 programs, acquisition programs, instrument programs, representation relations, gadgets and encodings, MRDL derived primitives | Yes (`docs/OMEGA_PROCESS_IR.md`) | Yes | mcx2: B20_R127 NOT_SHOWN. Acquisition: B20_R129 (a random program of the language beats the established rules; not released by the judge). Instruments: B20_R130 NO_DIFFERENCE |
| One registry across languages (the RO layer) | **Built 24 Oct, 20:50, on fixtures** (`src/genesis/objects/`): types and kinds as data with lineage, validation, run with contracts under fuel and depth, adapters for the gadget synthesiser, gadget evaluation, acquisition programs and the mcx2 engine, compositions, a gated improver and an improver of improvers, vault records of every run | Yes (`test_research_objects`, 9) | None yet |
| Exact, content-addressed memory with lineage, statuses, explanation and failure ladders, edges, bounded cascade | Yes (`vault.py`) | Yes (`test_vault`) | B20_R131 running (its trigger was not verified by B20_R130) |
| Experiment choice by expected value, domain-independent | Yes (`science/design.py`) | Yes | **Verified twice**: B20_R129 ADAPTIVE_SCIENTIST; B20_R130 CHOICE (+0.165 F1, p 7.5e-26) |
| Instrument invention (search over a language of tests) | Yes, exhaustive over 45 | Yes | B20_R130: the invented instrument ties |
| Representation invention (gadgets, encodings, factorisation, families from predicates) | Yes (`representation/`) | Yes (fixtures) | B20_R135 preregistered, not run |
| Capability-gap diagnosis | Hand-designed instruments in a preregistered study | Design tests | B20_R132 preregistered, not run |
| Senses synthesised by Genesis | **No** (receptors and probes are hand-made) | — | — |
| Perceptual workspace, synergy discovery, composition operators | **No** | — | — |
| Problem-attack strategies as data | **No** (studies choose attacks by hand) | — | — |
| Improvers as processes at any level, gated on unfamiliar tasks | Yes (`autonomy/process.py`; `representation/processes.py`) | Yes (fixtures) | B20_R128 (level 2 for engines) preregistered, not run |
| Research workflows as data, compared | Partly (`autonomy/loop.py`, `studygen.py` generate studies of one template) | Yes | B20_R93–R97: research automation, not yet a better improver |
| Allocation with stagnation and reactivation | Yes (`autonomy/queue.py`, `research_queue.json`) | Yes | The engine-invention line is stagnant, with B20_R132 as its diagnosis |
| Formal mathematics (Lean, proof search, theory packages) | Yes (`formal_research/`) | Yes | Earlier batches: certified statements; no invented concept transferred |
| The protected judge, kernel and custody | Yes (`judge.py`, `kernel/`, `feedback.py` contract v2) | Yes (`test_omega_boundary`, red-team suites) | Every recorded study |
| LLM-free operation | Yes | Yes (`test_no_llm`) | — |

**The honest summary.**
- Genesis has three verified capabilities so far:
  - a strong, verified max-cut engine;
  - an experimental scientist that chooses experiments better than chance (verified twice);
  - exact, reproducible memory.
- It has languages in which it can invent, but no invention of its own has yet been released by its judge.
- It has no synthesised senses, no synergy discovery, no attack strategies as data, and no measured recursive
  improvement.

## 3. The research object (RO): one typed, executable, bounded unit

### 3.1 The record

An RO is a vault artifact: immutable, content-addressed, with lineage and statuses (`docs/OMEGA_DISCOVERY_SCHEMA.md`).
Its `content` follows one schema, `genesis-research-object-v1`:

| Field | Meaning |
|---|---|
| `kind` | One of the registered kinds (§1), or a kind Genesis registered itself (§3.3) |
| `definition` | Executable data in one of the registered languages, never source code to `eval`. Examples: an mcx2 program, an acquisition tree, a gadget, a workflow graph, a parameter set of a registered executor |
| `executor` | The registered interpreter that runs the definition (`objects.EXECUTORS`) |
| `inputs`, `outputs` | Types from the type registry (§3.3) |
| `pre`, `post` | Contracts. Preconditions on inputs; postconditions an independent checker verifies on outputs (exactness, validity, a bound's soundness) |
| `effect` | `accessibility` (a deterministic function of its inputs) or `information` (draws new data: names its source and cost) |
| `determinism` | `deterministic`, or `seeded`, with the seed part of the call |
| `cost` | A declared budget model (CPU, calls, fuel) and the measured cost of every run |
| `dependencies` | ROs and library versions it needs |
| `limitations` | Known failure regions, filled from evidence |

The vault already supplies identity, lineage, statuses, explanation, failure and novelty ladders, evidence links and
edges. The RO layer adds the executable contract and one way to run anything.

### 3.2 Execution

`objects.run(ro, inputs, fuel)` does five things in order:
1. type-checks the inputs;
2. checks the preconditions;
3. dispatches to the executor under the shared `Fuel` (`autonomy/process.py`) and a CPU limit;
4. checks the postconditions with the registered checker;
5. records the run (inputs' digests, outputs, cost) as an ExperimentSpec in the vault.

A failed postcondition is recorded as a failure of the RO, never repaired silently. Nothing runs outside the
interpreters, and nothing an RO computes can call the judge's write paths (`test_omega_boundary`).

### 3.3 Types and new kinds

The type registry starts with the types the languages already use:
- base types: Graph, BQP, CSP, Relation, Gadget, Encoding, Assignment, Distribution, Table, Expression, Program,
  Workflow, Proof, Statement;
- constructors: List, Map, Pair, Option.

Genesis may register:
- **a new type**: a constructor applied to existing types, with a validity checker composed from theirs;
- **a new kind**: a name, its input and output types, and its contract, all as data.

Registration is admission to a versioned library, like `science/library.py` and `representation/library.py`: an
immutable new version with lineage, refused if the checker cannot be built. This is how capabilities "beyond senses"
enter: the system needs no human to name them, only to keep the kernel closed.

### 3.4 Promotion

The statuses run generated → exploratory → reproducible → verified → promoted (`vault.py`):
- `reproducible` means the RO's contract re-checks on a re-run.
- `verified` needs an EvidenceRecord naming a recorded, preregistered study and its record test.
- `promoted` needs verified usefulness on fresh tasks against strong baselines at matched compute, decided by the
  judge's rules, which no RO can change.

Unexplained ROs are archived and reused like any other: explanation `unknown` blocks nothing except claims about the
explanation.

## 4. Perception

### 4.1 Senses (synthesised)

A sense is an RO of kind `Sense`: `effect = accessibility`, and its output is typed, not necessarily a number. It
could be:
- a graph;
- a set of relations;
- a distribution;
- a candidate invariant;
- a decomposition.

**The sense language** has three parts:
- typed primitives over the problem's objects. For graphs: degree, weight and neighbourhood aggregation, induced
  subgraphs, local search probes, coarsening, cut structure, spectral sketches;
- combinators: map, filter, aggregate, compose, condition, recurse with a bound;
- primitives synthesised from recurring structure, admitted to the library with contracts (as `science/library.py`
  already does for acquisition expressions).

Variation (mutation, crossover), specialisation (which problem families a sense helps), competition (controlled
budgets) and preservation (the vault) reuse the machinery that exists for mcx2 and acquisition programs.

### 4.2 Instruments (new information)

Instruments are already a working kind: the causal lab and `causal/instruments.py`. Their invention extends to:
- probes of a solver's behaviour on an instance (perturb and re-solve, restart statistics, landscape walks);
- external evidence where allowed (published bounds, pinned literature values).

Every instrument declares what it costs, and its value is measured by the decisions it changes (`science/design.py`:
expected decision improvement), not by the entropy it removes. B20_R129 measured exactly this distinction: entropy
gained did not predict accuracy gained.

### 4.3 The perceptual workspace

A typed store of observations for one problem: each is an RO output with its producer, inputs, uncertainty and cost.
The workspace supports:
- **relations between observations**: consistency, conflict, dependence;
- **derived observations**: an RO applied to others; where the types do not fit directly, Genesis searches for a
  typed intermediate transformation, just as `representation/compile.py` searches for a gadget a relation needs;
- **counterfactual comparisons**: the same sense on a perturbed instance;
- **missing information**: a hypothesis whose discriminating observation is not yet in the workspace is a question
  for the experiment designer (§7).

Observations are never concatenated into one vector by default. Composition must type-check.

## 5. Composition

A composition operator is an RO of kind `Composition` whose inputs are ROs and whose output is an RO. The seed
operators are sequence, condition, hierarchy, bounded recursion, ensemble and fusion by a learned weighting. New
operators are programs in the same language, so Genesis can invent the way it combines things, not only the things
it combines.

## 6. Synergy discovery (parts that are weak alone, strong together)

A greedy search discards capabilities that show no gain alone. Synergy discovery must not. The protocol:

1. **Candidate sets.** From the vault, capabilities with credible but unproven value. These include `dormant` and
   `promising` ones, and ones whose solo tests were NOT_DISTINGUISHABLE.
2. **Bounded higher-order screening.**
   - Fractional factorial and group-testing designs over subsets of size 2–4, at a fixed budget.
   - Then knock-out ablations from the best sets: remove one part and measure the loss.
   - Interaction is estimated against the additive model of the parts.
3. **Preservation.** Partial combinations with positive interaction estimates are archived as `promising`, with the
   design that found them, even when their total gain is not yet significant.
4. **Controls:**
   - random combinations of the same size;
   - the best single capability;
   - simple fusion (average, majority);
   - the full cost of discovering the combination, charged to it.
5. **Claims.**
   - An interaction is a statistical claim until a preregistered ablation on fresh tasks shows the combination's
     gain and each part's necessity.
   - Even then it is a claim of joint usefulness, not of a causal mechanism.

## 7. The capability-gap scientist (why is progress stuck?)

The capability-gap scientist is `science/design.py` with a domain whose **hypotheses are explanations of a
stagnation** and whose **experiments are diagnostic probes**. The explanations, which grow with the kinds of §1:

| Explanation | Its discriminating instrument (examples) |
|---|---|
| No headroom (already near-optimal) | Long runs, bounds, best-known comparisons |
| Evaluation insensitive | Planted gains of known size; power curves of the judge's threshold |
| Search ineffective | Planted reachable improvements; the true gains of what the search proposed |
| Language not expressive enough | A fixed pool and an oracle-style search confirmed on fresh data |
| Representation poor | The same method on an alternative encoding (the representation language) |
| Information missing | The value of an instrument's observation for the decision |
| Missing prerequisite or concept | A capability-dependency query (§12): which dormant work names this as its block |
| Too expensive | Cost scaling probes; the metabolism model |
| Proof or certification weak | The gap between the best answer and the best certified bound |
| The diagnoser is wrong | Its past diagnoses checked against what fixing them did (below) |

Each experiment is chosen by its expected decision improvement at its cost, and the scientist picks the cheapest
experiment that separates the explanations still standing.

**First real instance: B20_R132** (preregistered `c0431f6`). Its four instruments are hand-designed; its diagnosis
rule is fixed.

**Diagnosing the diagnoser.** Every diagnosis is stored as an RO with its prediction: "fixing X will move the outcome
by at least Y". When the fix is later tried, the prediction is scored. A diagnoser whose predictions fail is
improvable like any RO (§10), measured by the accuracy of its predictions on later, unseen stagnations.

## 8. Problem attack as invention

An attack strategy is an RO of kind `AttackStrategy`: a workflow over typed steps.
- **Seed steps:** construct, decompose, relax, dualise, propagate constraints, change representation, probe
  experimentally, search for counterexamples, transfer by analogy, synthesise an algorithm, conjecture and prove,
  run a portfolio, revive a historical discovery.
- **New steps and new orders** are programs in the workflow language.
- **The choice of attack** belongs to the allocator (§13). It includes the choice between *attacking the problem*
  and *improving the machinery needed to attack it*.

**Example in Genesis's own terms.** On Gset, 45 of 54 best-known values are matched and none is beaten. Further
search has stagnated (B20_R123). The certification gap is the open question: for most instances no proof says the
best known value is optimal. A strategy that redirects effort from more search to stronger upper bounds would:
- extend the certified bounds of `bounds_large.py` with SDP and Goemans–Williamson relaxations and cutting planes;
- turn the question into "how far from optimal is Genesis", which more tours (or cuts) cannot answer.

Such a redirection earns credit only if it improves verified outcomes, such as certified gaps closed, or future
research productivity.

## 9. Mathematical concept invention

The progression observation → abstraction → definition → conjecture → counterexample search → proof → algorithm →
transfer is one workflow among many. It is implemented over existing parts:
- abstractions are `Concept` ROs (definitions in MRDL, or as Lean definitions in `formal_research`);
- conjectures are tested against counterexamples by `interpret.test_conjecture` and by solvers;
- proofs are checked in the pinned Lean workspace;
- a proved property becomes an `Invariant` or `Bound` RO that algorithms can use;
- transfer is a test on another family.

**Seven levels, never conflated in any claim:**
1. a new expression;
2. a new program;
3. a new theorem (formally verified under stated assumptions);
4. a useful abstraction (verified useful on fresh tasks);
5. a historically novel concept (equivalence checks and a literature review);
6. a substantial theory;
7. a recognised branch of mathematics (independent expert assessment).

Formal verification establishes level 3, never levels 5–7. The vault's novelty ladder records the rung with its
evidence.

## 10. Recursive improvement by typed self-application

`objects.improve(target, objective, budget)` is itself an RO of kind `Improver`.
- **Its target** may be any RO whose definition has a declared variation space, including another `Improver`, a
  `Diagnoser`, an `Allocator` or a workflow. There is no fixed number of levels.
- **Fuel.** Every level draws on one fuel budget, and a depth limit stops runaway recursion (`autonomy/process.py`,
  already tested).
- **Each improvement produces a concrete artifact** (a new RO) **and a measured effect**. Wrappers that produce
  nothing are refused, because they have no artifact to measure.

**The measure** (directive item 11, and Daniel's G_t):

G_t = verified discovery value on fresh tasks ÷ total research compute (including the compute that produced the
generation's improvers).

- A generation t+1 counts as an improvement only if G_{t+1} > G_t on a comparable fresh-task distribution, with
  uncertainty, in a preregistered comparison.
- Sustained recursive improvement needs several independently replicated generations across unfamiliar domains.
- One generation's gain is reported as one generation's gain.
- **Promotion gate** (already built for synthesisers in `representation/processes.py`): a descendant replaces its
  ancestor only if it is strictly better on tasks neither saw, at matched compute.

## 11. Research-paradigm invention

A research paradigm is a `Workflow` RO at the top: which kinds of RO to run, in what order, with which feedback.
Examples:
- diagnose → experiment → invent;
- retrieve historical failures → combine → test;
- counterexamples → abstraction → proof;
- invention of a representation → sense → algorithm;
- evaluator sensitivity → re-assessment of old discoveries;
- prerequisite discovery → return to the original problem.

Paradigms are versioned and compared on fresh problem families at matched compute, by G_t. A paradigm may change
anything in the research plane. It may change nothing in the kernel, the judge, the resource supervisor or the
promotion rules.

## 12. The capability dependency network

The vault's edges (`requires`, `enables`, `improves`, `failed_due_to`, `reactivated_by`, ...) are the network. An
edge stays inferred, with confidence below 1, until a test supports it:
- **A enables B**, tested by knock-out: without A, does B's verified gain disappear?
- **A unlocks dormant D**, tested by the cascade with its controls: fresh search, random retrieval, a null trigger
  (B20_R131's design).

The network is used to rank opportunities: which missing capability, if built, would reactivate the most valuable
dormant work.

## 13. Allocation

The persistent queue (`autonomy/queue.py`, `research_queue.json`) is the allocator's state:
- directions, with their dependencies;
- capability tags;
- stagnation of a line after repeated negative results, and its diagnosis;
- bounded reactivation.

**The allocator itself** becomes an RO. It starts as a bandit over directions: expected verified value per CPU hour,
with an exploration bonus and reserved exploration. Its improvements are judged by G_t.
- **Its baselines:** uniform allocation, greedy allocation, and the builder's own queue order (Ω10).
- **Every branch has** a budget, a termination condition, checkpoints and recovery.
- **Meta-research is capped** by a fixed share of compute, so that improvement never displaces the original
  objective.

## 14. The judge and the kernel (non-negotiable)

No RO, improver or paradigm may modify any of the following:
- the judge and its thresholds;
- the feedback contract (`autonomy/feedback.py`, its digest pinned by `test_contract_v3`);
- the kernel, custody, sealed tests and resource accounting;
- the promotion criteria;
- this boundary itself.

Candidate judges (`autonomy/contract_v3.py`) live in the research plane and are adopted only by the human supervisor.

**What every claim is evaluated with:**
- fresh unseen tasks;
- strong established baselines;
- equal total compute, including invention, experimentation and compilation overhead;
- independent correctness checkers;
- uncertainty;
- ablations;
- transfer;
- replication where feasible.

**Controls against reward hacking:**
- zero-signal controls (no release on noise);
- planted positive controls (a release on a known gain);
- adversarial tasks (`autonomy/adversary.py`);
- null triggers;
- the record tests, which recompute every verdict.

Selecting or tuning a human design is reported as selection, never as invention.

## 15. The decisive experiments (A–I)

Each becomes a preregistered study with its own success criterion, baselines, budget, controls and failure condition.

| | Question | Genesis study | State |
|---|---|---|---|
| A | Sense invention: a synthesised observation procedure, not in the initial library, that improves a downstream decision on fresh tasks | **B20_R136**: senses over graphs choose the engine's program and configuration per instance; against the best fixed configuration and hand-made features at matched compute; planted-structure positive control; transfer to the compiler's families | to design (the first vertical slice, §16) |
| B | Sense synergy: individually weak senses that are strong together | B20_R137, on A's archive | to design |
| C | Representation invention that enables a stronger method | **B20_R135** (encodings for colouring; reductions synthesised for four families) | preregistered `7040a3c` |
| D | Autonomous problem attack on unfamiliar problems | B20_R138: attack workflows as ROs on held-out families (`compiler` and `representation.families`), including the redirection to bounds | to design |
| E | A new capability unlocks an old failure | **B20_R131** (cascade on R129's rules); B20_R135 part C (families parked, reactivated) | preregistered; R131 running |
| F | Improving an improver (engine inventor, gadget synthesiser, allocator) | **B20_R128** (the engine inventor's process); `representation/processes.py` on fixtures | preregistered |
| G | Several generations each improve G_t on fresh tasks | B20_R140+ after A–F give something to improve | later |
| H | A mathematical abstraction, proved and transferred | B20_R139: concepts as Lean definitions over the max-cut and colouring worlds, conjectures tested and proved, used as bounds | later |
| I | A research paradigm that beats the previous one on fresh families | After G | later |

**The diagnosis track runs beside them.** B20_R132 is the capability-gap scientist's first real use.

## 16. The order of work, adapted to the repository

The smallest vertical slice that tests the central hypothesis comes first, before general abstractions:

**sense → combine perspectives → choose or synthesise the method → verify the gain → preserve → transfer → improve
the inventor.**

1. **Batch R1, the RO layer** (`src/genesis/objects/`), engineering on fixtures:
   - the schema;
   - the type and kind registry, with new kinds as data;
   - `run` with contracts, fuel and recording;
   - `improve` as an RO;
   - adapters registering the existing languages (mcx2 programs, acquisition programs, gadgets, encodings,
     instruments, processes) as RO kinds, with no change to their behaviour.
2. **Batch R2, senses**: the graph sense language, its interpreter and its contracts; synthesis by the same
   evolutionary and library-learning machinery; a perceptual workspace for one instance.
3. **B20_R136 (experiment A)**, the vertical slice:
   - per-instance choice of the engine's program and configuration from synthesised senses;
   - fresh graphs, matched total compute, planted structure, transfer, judged and recorded;
   - then its improver, the synthesiser improved and gated on unfamiliar families (F on senses).
4. **Synergy** (B), **attack workflows** (D), the **allocator as an RO** (Ω10), then **generations** (G),
   **concepts** (H) and **paradigms** (I).

The order changes if the evidence says so. For example: if B20_R132 says headroom is the limit, the attack track
(bounds, certification) moves ahead of more engine invention.

## 17. What counts

**Never counted as progress:**
- numbers of senses, algorithms, expressions, objects, levels or batches;
- architectural complexity;
- a passing unit test, for any scientific claim;
- a planned capability reported as built.

**Counted:** independently verified, reusable problem-solving and discovery capability under finite resources, and
its growth across generations.

**The decisive achievement**, not yet attempted:
1. Genesis meets an unfamiliar problem and finds the capability it lacks.
2. It invents and combines the senses it needs.
3. It constructs a new representation.
4. It develops a method and verifies its advantage.
5. It preserves the discovery and transfers it.
6. It improves the process that made the discovery.
7. Later generations show further verified gains.

## 18. Change log

- 24 Oct 2026, 20:45: written and adopted from Daniel's two attachments and his instruction, adapted to the
  repository: the audit (§2); capabilities beyond senses as an open set of typed kinds (§1, §3.3); the RO layer over
  the vault and the processes (§3); the gap scientist built on `science/design.py`, with diagnosis of the diagnoser
  (§7); the decisive experiments mapped to studies (§15); the order of work with the vertical slice first (§16).
- 24 Oct 2026, 20:50: Batch R1 built on fixtures: the RO layer (`src/genesis/objects/`; `test_research_objects`).
