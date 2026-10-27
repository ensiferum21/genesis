# Genesis Ω: the Autonomous Research Architect (ARA)

**Status of this document.** This is the adopted design for architecture invention in Genesis. It comes from
Daniel's directive "GENESIS Ω — AUTONOMOUS ARCHITECTURE INVENTION ENGINE" (24 Oct 2026, 20:45; the attachment's
SHA-256 is `e21421a72d4cdd8861b43e165877da036e22ccdf3d2948766d708d8743be6b22`; the attachment itself is not
committed) and his instruction:

> "Use this to adapt and refine and make it even more powerful and implementable." (20:45)
>
> "Push this to info too and outdo yourself making it more powerful and adapt. Make sure we can implement and test
> too." (20:47)

It is the third layer of the plan:
1. `docs/GENESIS_OMEGA_PLAN.md` §0a: the 15:35 directive. It still applies in full.
2. `docs/OMEGA_RECURSIVE_INVENTION.md`: research objects, perception, cognition and invention.
3. This document: the system that studies and changes the architecture built from (2), including itself.

**Nothing here is claimed as achieved.** Each part is marked:
- **BUILT**: it has code and a named test;
- **PREREGISTERED**: it has a study script with a commit;
- **PLANNED**: neither.

A unit test that passes is evidence that the code works. It is not evidence of autonomous architecture invention.
Only a preregistered study judged on sealed tasks is evidence of that (§13).

---

## 0. The intended system, in technical terms (directive §21.1)

Genesis is built from research objects (ROs): typed, executable, bounded units (`src/genesis/objects/`). A research
workflow wires ROs together. Examples:
- senses feed a policy;
- a search fills the policy's parameters;
- an evaluator scores candidates;
- an allocator splits the budget.

**ARA is a research workflow whose subject is other research workflows, including itself.** One cycle has eight
steps:

```
model      what the system can actually do (executed probes) and what it has measured (recorded evidence)
measure    the gap between what a workflow achieves and what is attainable
attribute  the gap to locations in the workflow, by interventions (oracle substitution, §4)
propose    typed rewrites of the workflow at those locations (a generative grammar, not a list of fixes, §5)
synthesise fill each rewrite's holes by search in the object languages (senses, expressions, encodings, processes)
evaluate   in isolation, on development tasks, with all of ARA's own compute charged
submit     to the independent judge, on sealed fresh tasks, against a tuning-only control and a blind-rewrite control
keep       everything (promoted, dormant, negative, unexplained) with lineage, then rescan dormant objects
```

The same cycle applied to ARA's own workflow is meta-improvement (§9). It is measured by the same quantity at every
level:

> **G_t**: verified discovery value on fresh tasks, divided by the total research compute, including the compute
> spent on introspection, diagnosis, synthesis and evaluation.

### 0.1 Eight refinements that make the directive implementable, testable and stronger

**R1. The architecture is a typed program (the Architecture Graph, AG; §2).**
- ARA changes Genesis by rewriting typed dataflow graphs of ROs, not Python source. A rewrite is data. It can be:
  - type-checked before it runs;
  - executed under fuel in the RO interpreter;
  - diffed, hashed and replayed exactly.
- Changes to Python source stay human-gated.
- The kernel sits outside every AG ARA can edit: the judge, sealed data, budgets, audit and promotion thresholds.
  It is therefore unreachable by construction, and the boundary is enforced by more than policy. A test proves
  that every rewrite touching it is refused.

**R2. A limitation is a localised, measured shortfall, not a narrative (§4).**
- For each node, ARA builds a stronger stand-in of the same role:
  - richer observations for a features node;
  - a flexible family for a policy node;
  - exhaustive search for a search node;
  - exact evaluation for an evaluator node.
- It substitutes these along the workflow. The gain at each substitution is that node's share of the gap, with a
  bootstrap interval.
- This turns "why does progress fail?" into an additive loss ladder:

  ```
  attainable − achieved = information + expressiveness + search + evaluation (+ residual)
  ```

- It generalises B20_R132's preregistered diagnosis (headroom → expressiveness → search → evaluation) from one
  workflow to any AG.

**R3. A proposal is a typed rewrite from a small generative grammar (§5).**
- The grammar's operators (LIFT, GENERALISE, SPECIALISE, FUSE, INSERT, SUBSTITUTE, REALLOCATE, RETRIEVE, ENSEMBLE,
  REORDER, LOOP) are generic graph rewrites with typed preconditions.
- None of them names a problem or a known fix.
- Limitation inversion (directive §4.1) applies GENERALISE and LIFT again to the fixed parts that the last rewrite
  introduced, to a bounded depth.
- The grammar is itself an RO. Rewrites that ARA adds to it pass the promotion gate.

**R4. Answer keys live only on the judge's side: the Limitation Zoo (§12).**
- ARA is calibrated the way B20_R132 calibrates the engine judge: on generated environments with planted
  limitations of known type and location.
- The zoo also contains:
  - **null controls**: nothing to gain;
  - **no-headroom controls**: the workflow is already near the oracle;
  - **decoys**: a development-only spurious structure that must not survive sealed judging.
- The generator's seed and the planted key are held by the judge harness. ARA's code cannot import them; a
  boundary test checks this.
- Because the defects are generated, ARA cannot be choosing "from a benchmark-specific list of known fixes".

**R5. Tuning is separated from invention twice over (§7).**
1. An executable diff classifier labels each change:
   - TUNING (only parameter values, or which parameters are searched);
   - STRUCTURAL (nodes, edges or operators);
   - LANGUAGE (a new primitive or rewrite).
2. Every architectural claim must beat a tuning-only control: the old graph, with the same total compute spent on
   tuning its parameters.

**R6. The diagnoser is diagnosed (§9.1).**
- ARA's accuracy (a confusion matrix over planted classes) and its G_t are measured on fresh zoo families.
- Its errors are limitations of ARA's own AG. The same cycle rewrites them.
- This makes the directive's ARA_V1 → V2 → V3 an executable chain, not a story.

**R7. Questions are executable objects (§5.8).**
- A question is a set of competing hypotheses, an intervention that separates them, and its cost.
- A question generator is scored by the information it realises per CPU second. This reuses
  `science/design.py`'s expected-information machinery, verified as better than random choice in B20_R130.
- So question generators can be improved like anything else.

**R8. Returning to the objective is structural (§8).**
- Every ARA workflow ends in a mandatory node: reattempt the original objective with the modified architecture.
- The allocator always holds two arms:
  - **no modification**: spend the budget solving;
  - **stop**.
- The research queue's stagnation rule (`autonomy/queue.py`) halts meta-research that produces nothing.
- So the system can conclude "nothing is worth changing", and one of the zoo's tests requires it to.

---

## 1. What exists, mapped to the directive (directive §15, §21.2; audited 24 Oct 2026, 21:00)

| Directive need | What exists (code, test, evidence) | What is missing |
|---|---|---|
| Architecture introspection (§3.1) | `adaptation/capabilities.scan` reads code and evidence for time-to-solution designs (B20_R93). `objects/` registries (kinds, types, executors; `test_research_objects`). `research_queue.json` (`test_research_queue`). `batch_state.json` and the results ledger | A capability model built only from **executed probes** and **recorded verdicts** (ARA-1: `architecture/model.py`) |
| Limitation discovery (§3.2) | `adaptation/receptors.py`: 12 hand-written receptors of weaknesses in study evidence (B20_R93). `autonomy/adversary.py`: hard hosts (B20_R96). `queue.diagnose`: stagnation. B20_R132: the interventional diagnosis of engine invention (preregistered `c0431f6`, running) | Loss attribution over any workflow, by intervention, with competing hypotheses (ARA-1: `architecture/diagnose.py`) |
| Proposal (§4) | `adaptation/design.compose` with a **response library**: hand-written responses with doses. This is exactly the "list of known fixes" the directive rules out as the source of a decisive mechanism, so ARA does not use it for that. Genome mutation in `autonomy/selfimprove.py`; sense mutation and crossover in `senses/graph.py` | Generative typed rewrites of workflows (ARA-1: `architecture/rewrite.py`) |
| Executable synthesis (§5, Batch 5) | `objects/core.run` (typed, fuel, pre- and postconditions); `autonomy/process.py` (processes at any level); the sense, expression, representation and primitive languages (`senses/`, `representation/`, `science/library.py`) | A workflow representation that rewrites can act on: the AG (ARA-1: `architecture/graph.py`) |
| Isolation and budgets (§13) | `sandbox.py` (OCI runc for arbitrary code); `kernel/authority.py` (leased budgets that cannot be duplicated); fuel | Nothing for AG rewrites, which run under fuel in-process. Arbitrary code still goes through `sandbox.py` |
| Independent judge (§13) | `autonomy/feedback.py` v2, **protected** (digest pinned); `contract_v3.py` (candidate, research plane); `kernel/stats.py`; record tests that recompute verdicts | A judge harness for architecture claims on sealed zoo tasks (ARA-1: `architecture/judge.py`, kernel region) |
| Memory and reuse (§11) | `vault.py` (archive, announce, park, cascade, opportunities); `autonomy/archive.py` (quality-diversity); `autonomy/kmap.py` (knowledge map; MAP_BETTER prospectively, B20_R100). B20_R131: reactivation by a capability trigger measured, **NO_VERIFIED_TRIGGER** | RETRIEVE as a rewrite, with reuse measured against a fresh-search control (ARA-3) |
| Allocation (§12) | `queue.py` (stagnation, reactivation); `adaptation/metabolism.py` (cost model fitted to its own runs); `design.compose` (energy budget) | Value-of-information allocation over ARA's roles, with no-op and stop arms (ARA-6) |
| Experiment design | `science/design.py` (expected information gain). B20_R129: decfall chosen. B20_R130: CHOICE verified against random (+0.165 F1); interpretation not verified | Questions as objects (ARA-4) |
| Recursive improvement | `autonomy/process.py`; `selfimprove` level 2 (B20_R128 preregistered); the improver of improvers in `objects` (fixture) | ARA applied to ARA (ARA-8) |
| Scheduler and recovery | `run_study.sh` slices; `autonomy/loop.py` (propose, preregister, run); `adaptation/checkpoint.py` | Nothing for ARA-1 |
| Proof and verification | `verification/` (LP duals, SAT, E, Lean); `formal_research/` | Used by the attack and concept tracks of layer 2 |
| World invention | `invention/worlds.py` (assumptions as Lean predicates; interventions with lineage) | Its intervention discipline is the model for §4 |

### 1.1 Why earlier inventions failed the judge (directive §15, "pay particular attention")

| Study | What happened | What it says about the architecture |
|---|---|---|
| B20_R127 | The judge released nothing in 9 searches. The best gains (+0.04 to +0.23%) were 4–52 times smaller than the thresholds (0.75–2.45%) | Either evaluation insensitivity or no headroom. The study cannot separate the two by itself |
| B20_R132 | Preregistered to separate headroom, expressiveness, search and evaluation, with planted traits and zero-signal controls. Development look: headroom +0.02 / +0.61 / +0.06%; thresholds from random engines 6–20 times larger than local ones | **ARA's limitation scientist generalises this study**, and its result will be ARA's first answer key on the real system (§14, check C0) |
| B20_R108 | Mutating configurations: NO_DIFFERENCE | Search within an exhausted space |
| B20_R17/R19, B20_RX5 | Generated decoders: NO_UTILITY_AFTER_COST; no proposal headroom once components exist | The bottleneck was component invention, not selection |
| B20_R120–R124 | Experiments chosen no better than random | Fixed by choice (B20_R130 CHOICE); interpretation still open |
| B20_R131 | Reactivation by a capability trigger: NO_VERIFIED_TRIGGER (means: eig 0.450, fresh 0.496, random 0.502) | A capability that unlocks old failures must first be verified (B20_R130). Reactivation cannot be assumed causal (directive §11) |

**The pattern.** Genesis has often been unable to tell why a method failed. The decisive missing capability is
**measured, localised diagnosis**: the "highest-impact missing capability" the directive asks for (§21.3). ARA-1
builds it first. The decisive experiment that tests it is B20_R141 (§14).

---

## 2. The Architecture Graph (AG)

### 2.1 Representation

An AG is JSON. Its parts:
- **nodes**: `{id: {role, op, params, searched, kernel}}`.
  - `role` is a typed slot, such as `Instances`, `Sense`, `Features`, `Policy`, `Search`, `Evaluator`,
    `Allocator`, `Memory` or `Judge`. The role set is open: new roles are registered as RO kinds.
  - `op` names an operator in the role's library, which is an RO executor.
  - `params` are constants.
  - `searched` lists the parameters a Search node may vary, with their spaces.
  - `kernel: true` marks protected nodes.
- **edges**: `[src, dst, port]`. The value of `src` flows into `dst`'s input `port`. Values may be data or
  functions; the Search node takes the Evaluator node as an input.
- **budget**: total units and their split across nodes.
- **lineage**: parent AG id and the rewrite that produced it.

Rules:
- The AG's id is the SHA-256 of its canonical JSON.
- Execution is a topological evaluation under one fuel budget.
- Every charge is recorded per node, so the cost of every part is known.

### 2.2 Invariants (each has a test in ARA-1)

1. **Type correctness.** Each edge's value type fits the input port's type, and each role's operator exists. A
   rewrite that breaks either is refused before it runs.
2. **The kernel is closed.** No rewrite may add, remove, re-wire or change a node with `kernel: true`, or an edge
   into one. The judge harness and the sealed instances are kernel nodes that ARA's AG never contains. The judge
   reads the AG's **output**, not the reverse.
3. **Budget conservation.** The total budget of an AG after a rewrite is at most the total before (directive §12;
   `kernel/authority.py`'s rule that authority never grows).
4. **Determinism.** The same AG, seed and inputs give byte-identical outputs and charges.
5. **Bounded execution.** Fuel bounds every run, and the depth of nested AG execution is bounded (§9).

### 2.3 The diff classifier (anti-tuning, directive §18)

`classify(old, new)` returns the largest class that applies:
- `TUNING`: only `params` values or `searched` sets changed. This includes LIFT and REALLOCATE.
- `STRUCTURAL`: nodes, edges or ops were added, removed or changed.
- `LANGUAGE`: a role library or the rewrite grammar gained an element.

Rules for claims:
- Claims are reported in the class the classifier returns.
- An architectural claim (STRUCTURAL or LANGUAGE) must also beat the tuning-only control (§7).

---

## 3. The architecture model (directive §3.1, Batch 1–2)

`architecture/model.py` builds a machine-readable model, `architecture_model.json`. It has three parts.

**Capabilities.**
- Each capability is an RO executor or a language, with a **probe**: a small run on a fixture input with a checked
  postcondition.
- Its status is `OBSERVED_OK`, `FAILED` (with the violation) or `UNPROBED`.
- A capability whose probe fails is `FAILED` even though its name is registered. A test plants a broken executor to
  check this (directive: "do not infer capabilities merely from class names or documentation").

**Evidence.**
- Each recorded study's verdict comes from `batch_state.json`, the ledger and `research_queue.json`.
- Verdicts are grouped into **failure patterns**: runs of NOT_SHOWN, NO_DIFFERENCE or INVALID within one research
  line, and lines the queue diagnosed as stagnant.

**Assumptions.**
- The registry of §6.

The model is rebuilt from scratch on each run, so it cannot drift from the code.

---

## 4. The limitation scientist (directive §3.2, §4.7, Batch 3)

### 4.1 Oracle substitution and the loss ladder

For a workflow AG with output policy π, achieved value A and attainable value O (for example the per-instance best
choice, "VBS"), ARA estimates the following on development tasks. Each estimate uses split halves: fit on dev-A,
measure on dev-B.

| Term | Intervention | Interpretation |
|---|---|---|
| O | Per-instance best choice, estimated with repeated, split-sample evaluation | What is attainable at all on these tasks |
| C_rich_flex | A flexible policy over a **rich observation battery** (every primitive aggregate plus random expressions from the sense language) | What better observations plus a flexible family could reach |
| C_cur_flex | The same flexible policy over the **current** features | What the current observations allow |
| C_cur | The best member of the **current** policy family over current features, found by long search with exact evaluation | What the current family allows |
| S_exact | The incumbent's own search, rerun with exact evaluation at the same number of candidates | What the incumbent search finds without noise |
| A | The incumbent's achieved policy, measured exactly on dev-B | What it actually achieves |

The ladder, each term with a bootstrap interval:

```
information    = C_rich_flex − C_cur_flex     → Features / Sense nodes
expressiveness = C_cur_flex − C_cur           → Policy node
search         = C_cur − S_exact              → Search node
evaluation     = S_exact − A                  → Evaluator node
residual       = O − C_rich_flex              → not reachable with this sense language (a language limitation)
```

**The diagnosis.**
- It lists each term whose lower bound is above MATERIAL, ranked by size.
- If no term qualifies, it is **NONE** ("no limitation worth acting on").
- If two terms' intervals overlap heavily, the diagnosis is flagged **AMBIGUOUS**, and ARA asks a question to
  separate them (§5.8).

**Localisation.** Each term is the gain from substituting one node's stronger stand-in, so it localises to that
node.

**Stand-ins.**
- They are declared **per role**, not per defect: `ceiling(role)` is part of the role library.
- They are generic: a richer battery, a more flexible family, a longer search, more repeats.
- They are human-designed primitives (directive §5: "initial primitives may be human-designed"). ARA may propose new
  ones through the promotion gate (LANGUAGE class).

### 4.2 Order and interaction

- The ladder fixes an order, from inputs to output.
- Interactions between nodes make the attribution depend on that order.
- ARA-1 reports the ladder in one order.
- ARA-3 adds Shapley attribution over the substituted nodes (2^k substitutions), with its cost charged.
- Whether Shapley is worth its cost is itself a meta-improvement question (§9).

### 4.3 Competing explanations (directive §3.2)

For each limitation, the competing hypotheses are the ladder's terms plus NONE. Each hypothesis predicts a different
outcome for each intervention:
- information predicts a gain from the battery but not from longer search;
- search predicts the reverse;
- evaluation predicts a gain from exact evaluation of the **same** candidates.

When the bootstrap leaves two hypotheses unresolved, the next intervention is the one with the highest expected
information per unit cost (`science/design.py`).

### 4.4 On the real system

On real Genesis workflows, some stand-ins are expensive. For example, "exact evaluation" of a max-cut engine means
many seeds per graph. ARA then uses B20_R132's protocol: power curves and planted traits, at matched compute. B20_R132
is the hand-built instance of this section on the engine-invention workflow.

---

## 5. The proposal engine (directive §4, Batch 4)

### 5.1 The rewrite grammar (ARA-1 builds the first eight operators)

| Operator | Precondition (typed) | Effect | Class | Directive |
|---|---|---|---|---|
| INSERT(role) | A node consumes a list of that role's outputs (e.g. Features takes Senses) | Adds a new node of that role with a **hole** filled by synthesis (§6) | STRUCTURAL | 6.1 sense synthesis |
| FUSE(a, b) | Two nodes with compatible output types feed the same consumer | Adds a node `op(a, b)`; the binary operator is a hole | STRUCTURAL | 6.3 composition, fusion |
| GENERALISE(n) | The role library has an operator for n's role with a strictly larger family | Replaces n.op with the next family (global → threshold → oblique → tree → nearest neighbour; oblique added in ARA-1) | STRUCTURAL | 4.1 limitation inversion |
| SPECIALISE(n, s) | n is global; a Sense node s is available | Makes n's output conditional on s | STRUCTURAL | 6.4 specialisation |
| SUBSTITUTE(n, op′) | op′ has the same role and type | Swaps the operator (e.g. hill-climb → restarts; independent → paired evaluation) | STRUCTURAL | 4.5 counterfactual variants |
| REALLOCATE(a → b, f) | Both nodes have budget shares | Moves a fraction f of budget from a to b | TUNING | 12 |
| LIFT(n.p) | p is a constant of n | Adds p to the parameters the Search node varies | TUNING | 4.1 |
| RETRIEVE(role) | The vault has objects of that role from other environments | Adds a Memory node that supplies the best-ranked archived objects | STRUCTURAL | 11 reuse |
| ENSEMBLE(n, k) | n is stochastic | Runs k copies and selects among them by a confirmation split | STRUCTURAL | 4.6 |
| REORDER / LOOP | On workflow AGs (paradigms) | Permutes stages or adds a bounded loop with a stopping rule | STRUCTURAL | 9 paradigms |

How rewrites are generated:
- A rewrite is generated for **every** node and **every** applicable operator. Preconditions are checked against
  types.
- Ranking: the diagnosis's localisation puts operators on implicated nodes first. A prior over operator × role,
  learned from earlier outcomes, orders them; in ARA-1 the prior is uniform.
- The **blind-rewrite control** uses the same generator without the diagnosis, at the same budget. If localisation
  adds nothing, the control matches ARA.

### 5.2 Limitation inversion (directive §4.1), bounded

`invert(ag, depth)` works as follows:
1. Apply a rewrite.
2. Collect the **new** fixed elements it introduced. For example, INSERT fixes the sense language's primitive set,
   and FUSE fixes its operator menu.
3. These become candidates for GENERALISE or LIFT in the next round.
4. The chain is bounded by `depth` and by fuel.
5. Each chain is a list of rewrites with its lineage.

Through the rewrites themselves, this reproduces the user's chain: senses predefined → synthesised senses → senses
that communicate (FUSE) → synthesisable fusion operators (GENERALISE on the FUSE hole's menu).

### 5.3 Assumption challenges (directive §4.2)

There are three kinds of assumption. Every challengeable assumption carries:
- its location in the AG;
- the alternative (a rewrite);
- the test: dev comparison at matched compute, then the judge.

| Kind | Where it comes from | Challengeable |
|---|---|---|
| **Generated** | Every fixed choice in a non-kernel node: its op, each constant, and each absent edge between type-compatible ports | Yes. This makes "ARA should generate candidate challenges to its own assumptions" mechanical |
| **Recorded** | Assumptions taken from studies, each with the study that tested it. Examples: "engine search operates on the original instance representation" (challenged by the compiler and representation tracks); "the judge's thresholds come from global noise" (challenged by contract v3 in B20_R132) | Yes |
| **Protected** | The judge, sealed datasets, proof acceptance rules, security boundaries, external resource limits, promotion thresholds, audit records, the supervisor | **No**. The generator refuses them, and a test plants a challenge to each and checks the refusal |

### 5.4 Capability-dependency leverage (directive §4.3)

- The model's dependency graph links capabilities to the research lines they block (`research_queue.json` `requires`
  and `unlocks`, and the vault's `failed_due_to` edges).
- A proposal's **leverage** is the number of blocked lines whose missing tag it would supply.
- Leverage ranks proposals for development. It never counts as evidence: B20_R131 showed that an unverified trigger
  reactivates nothing useful.

### 5.5 Cross-domain transfer (directive §4.4)

SUBSTITUTE and RETRIEVE may draw any object of the right type from **any** domain's library in the vault. Examples:
- a sense synthesised for max-cut graphs applied to compiler-family graphs;
- an evaluation scheme from causal discovery applied to engine selection.

Rules:
- Provenance records the source domain.
- Genesis never claims "inspiration from the literature". The only sources are objects in the vault and the
  human-written primitives, each with its author.

### 5.6 Architectural composition and synergy (directive §4.6)

- Individually weak rewrites, those under MATERIAL alone, are kept as **partial discoveries**.
- A fractional factorial over the k best of them estimates interactions on dev. This is the protocol of layer 2 §6,
  B20_R137.
- A rewrite is never discarded only because it is weak alone. It is discarded when it is weak alone **and** has no
  significant interaction.

### 5.7 Counterfactual variants (directive §4.5)

- Every rewrite yields a variant AG that runs in isolation: in-process under fuel for AG rewrites, or `sandbox.py`
  for arbitrary code.
- Variants are compared with the incumbent on dev at matched compute.
- Only the best one, if it qualifies, is submitted to the judge, which limits the number of looks at sealed tasks.

### 5.8 Questions as objects (directive §4.7)

- A **question** has three parts:
  - competing hypotheses (with predicted outcomes per intervention);
  - an intervention;
  - a cost.
- A **question generator** is an RO that maps the current model and diagnosis to questions.
- ARA-1's generator asks one question: "which ladder term is largest?". Its interventions are the stand-ins.
- Later generators can ask, for example:
  - "which failures share a cause?": cluster failure patterns by their ladder profile;
  - "which dormant objects would a new capability unlock?": intersect leverage with dormant `failed_due_to` edges;
  - "which result contradicts the model?": predicted versus measured ladder terms.
- A generator's score is its realised information gain per CPU second, measured on zoo environments.

---

## 6. Synthesis: filling holes (directive §5, §6; Batch 5, 7)

A rewrite leaves typed holes. Each hole is filled by bounded search in the object language of its role:

| Hole | Language | Search objective (development data only) |
|---|---|---|
| Sense | `senses/graph.py` (primitives, aggregates, mutate, crossover) | Predicts the per-instance best choice on dev-A (cross-validated accuracy of a stump on the sense), or reduces policy regret |
| Fusion operator | The binary operators of the sense language | The same objective, on the fused feature |
| Policy family | The policy library | Fit on dev-A, score on dev-B |
| Encoding or gadget | `representation/` | Exactness, then objective value (layer 2 §8–9) |
| Workflow | AG rewrites over workflow AGs | The workflow's G_t on dev environments |

Rules:
- The hole's budget is charged to ARA.
- A filled hole is an RO with lineage: the rewrite, the diagnosis, the data split and the search seed.
- A synthesised object that duplicates an archived one by behaviour, with identical outputs on a fixed probe set, is
  recorded as a **rediscovery** and not as new (directive §18). The fingerprint is the SHA-256 of the canonical
  outputs on the probe set.

---

## 7. Evaluation, the judge and promotion (directive §13, Batch 6)

### 7.1 Three data levels

| Level | Who sees it | Use |
|---|---|---|
| dev-A, dev-B | ARA | Diagnosis, synthesis, variant comparison |
| confirmation | The judge, which reports a verdict only | One pre-check per submitted variant |
| sealed | The judge only. Generated from a seed held by the judge harness | The decision |

### 7.2 The judge's eight checks (directive §13), for architecture claims

| Check | Implementation |
|---|---|
| 1. Correctness | AG type check; the variant's own tests (its ROs' postconditions); for engines, independent cut and penalty checkers (as in B20_R133) |
| 2. Reproducibility | Re-execution from the AG id and seed gives byte-identical outputs and charges |
| 3. Budget accounting | Total units, including ARA's introspection, diagnosis, synthesis and dev evaluation, are at most the matched budget given to every control |
| 4. Strong baselines | (a) the incumbent with the whole budget spent on solving; (b) **tuning-only**: the incumbent with the budget spent tuning its parameters (successive halving on dev); (c) **blind-rewrite**: the same rewrite generator without diagnosis; (d) for real workflows, the domain's strongest published solvers |
| 5. Generalisation | Sealed tasks are fresh draws. Transfer claims need a different family (§13, experiment I) |
| 6. No unacceptable regressions | On every other zoo class and on the real-system regression set, the variant is not worse than the incumbent by more than MATERIAL (one-sided test) |
| 7. Statistical reliability | Paired tests over environments (Wilcoxon); Holm across claims; zero-signal controls bound the false-release rate (Clopper–Pearson) |
| 8. Causal contribution | Ablation: the variant minus the rewrite must lose the gain; for compositions, the factorial interaction |

**Complexity is never rewarded.** Among variants within MATERIAL of each other, the one with fewer nodes and
operators is preferred. A variant whose sealed gain is under MATERIAL is not promoted, however elaborate it is.

### 7.3 Where the judge lives

- `architecture/judge.py` is a **kernel** module.
- ARA's modules may not import its sealed generator or its key (boundary test).
- It reuses `kernel/stats.py`.
- Its digest is pinned by a test, like `autonomy/feedback.py`.
- Changes to it are human-gated amendments.

---

## 8. The improvement ecology and allocation (directive §10, §12)

### 8.1 Roles

Each role is an RO executed under a budget share. No role is a simulated personality or an LLM.

| Role | Object | Built from |
|---|---|---|
| Bottleneck scientist | The ladder diagnoser (§4) | ARA-1 |
| Capability inventor | The rewrite generator with hole synthesis (§5, §6) | ARA-1 |
| Perception inventor | Sense and fusion synthesis (`senses/`) | layer 2 R2 |
| Synergy scientist | The factorial over partial discoveries (§5.6) | ARA-3, with B20_R137 |
| Architecture explorer | Limitation inversion chains (§5.2) | ARA-1 (bounded chains), ARA-3 |
| Adversarial scientist | Decoy generation and `autonomy/adversary.py`: searches for environments where a promoted variant regresses | ARA-5 |
| Meta-improver | ARA applied to ARA's AG (§9) | ARA-8 |
| Allocator | Below | ARA-6 |

New roles are registered as RO kinds. Retiring or merging roles is a rewrite of ARA's AG, judged like any other.

### 8.2 Allocation

The allocator chooses among:
- **solve** (no modification);
- each role on each target;
- **stop**.

How it chooses:
- Each arm's value is (expected gain × probability of success) ÷ expected cost.
- The estimates come from the arm's history in the vault: the realised gains of earlier proposals of that role and
  operator class.
- Uncertainty is handled by Thompson sampling, which keeps exploration bounded.
- The opportunity cost of every non-solve arm is the solve arm's expected gain for the same budget.

The rules that make meta-research finite:
- **Meta-research is finite.** Each ARA cycle has a budget share. Meta-improvement (§9) has a smaller share, and
  depth n gets a geometric share ρⁿ of the cycle budget (ρ < 1). No depth limit is hard-coded; the budget bounds it.
- **Stagnation stops a line.** After STAGNATION_LIMIT cycles without a verified gain, the line is parked (dormant),
  not deleted.
- **"Nothing is worth doing" is a valid conclusion.** When no arm's expected value beats solve, ARA spends the budget
  solving.

---

## 9. Recursive improvement of ARA (directive §8, Batch 9)

ARA's workflow is itself an AG:

```
model → diagnose → propose → synthesise → evaluate-dev → submit → keep
```

Its constants include:
- the bootstrap size;
- MATERIAL for dev screening;
- the operator prior;
- the number of variants submitted;
- the budget split between diagnosis and synthesis;
- the ladder's order.

**Meta-tasks.**
- A meta-task is a set of zoo environments drawn from **held-out generator families**.
- ARA_vk's score is its G_t on the meta-task: sealed gain per unit of total compute, plus diagnostic accuracy as a
  secondary measure.

**Meta-improvement.**
1. ARA_vk runs its own cycle on its own AG, using the meta-task's dev environments.
2. The judge compares ARA_vk+1 and ARA_vk on sealed meta-tasks, using environment families that neither saw.
3. That comparison decides.

**Generations.** Each generation has:
- a budget;
- a checkpoint (the AG id);
- a termination rule: stop when the judge does not promote, or when the stagnation limit is reached.

**What counts.**
- TUNING-class changes to ARA are reported as tuning.
- A STRUCTURAL change to ARA counts as architectural meta-improvement only if it beats a tuning-only control of
  ARA_vk.

**Diagnosing the diagnoser (refinement R6).**
- ARA's confusion matrix on the zoo localises its errors. Examples:
  - mistaking evaluation for search points to the S_exact stand-in;
  - missing information points to the battery's size.
- So the cycle has a ladder of its own to read.

---

## 10. Research-paradigm invention (directive §9, Batch 8)

A paradigm is a workflow AG over stages. The directive's paradigms as AGs:

| | Stages |
|---|---|
| A | observe → generate → test → select |
| B | diagnose → invent capability → reattempt |
| C | counterexamples → abstraction → prove |
| D | retrieve dormant → combine → experiment |
| E | improve process → expand language → return to objective |

- New paradigms come from REORDER, LOOP, INSERT and SUBSTITUTE on stage AGs, with stage operators from the role
  libraries. **Synthesis, not selection.**
- A paradigm is judged by G_t on fresh task families under matched budgets.
- Experiment J (§13) requires a synthesised paradigm to beat the best of A–E.

---

## 11. Cumulative discovery (directive §11)

Everything ARA produces is a vault artifact with lineage:
- models;
- diagnoses, with their ladder and intervals;
- proposals and rewrites;
- filled holes;
- variants;
- dev results;
- judge decisions;
- negative results;
- unexplained observations (a ladder term that no stand-in explains).

Statuses (layer 2 §3.4):
- **verified**: promoted by the judge;
- **exploratory**: a dev gain not yet submitted;
- **dormant**: weak alone, or failed with a recorded `failed_due_to` tag;
- **rejected**: failed the judge, kept with its reason.

**Rescans.**
- When a capability is promoted, the vault's `opportunities` returns dormant artifacts whose `failed_due_to` tag it
  unlocks.
- Re-testing them is an **intervention with controls**: a null trigger, random retrieval and fresh search at the same
  compute (the protocol of B20_R131).
- An unlock is never assumed to be causal.

---

## 12. The Limitation Zoo (the calibration domain)

### 12.1 What an environment is

An environment has the following parts.
- **Tasks.** Weighted graphs, drawn from two or more families with **matched degree distributions** but different
  hidden structure. Examples: random geometric graphs against Erdős–Rényi; planted clusters against configuration
  models. The **perception is real**: senses are computed on the graphs by `senses/graph.py`.
- **A choice set.** K options per instance.
- **A hidden objective.** score(i, c) = base(i) + effect(c, z(i)) + noise.
  - z is a **real graph statistic** computed by a hidden sense, for example mean clustering, degree CV or the
    k-core maximum.
  - The noise has an instance-and-repeat component shared across choices, which paired evaluation cancels, and an
    independent component.
- **An incumbent workflow AG.** Instances → Senses → Features → Policy, with Search over the policy's parameters and
  an Evaluator. One part is planted limited.
- **A budget** in units: one noisy evaluation of one choice on one instance is one unit; a sense evaluation costs in
  proportion to its fuel.

The defect classes (the generator draws one per environment):

| Planted class | How it is planted | Correct localisation |
|---|---|---|
| SENSE_BLIND | z is not computable from the provided senses (which are matched in degree statistics) | Features (information) |
| GLOBAL_ONLY | The policy is a single global choice; z is among the provided senses | Policy (expressiveness) |
| FUSION_NEEDED | The best choice depends on an interaction of two provided senses (sign of a product or difference); the family uses one feature at a time | Policy or Features (expressiveness) |
| SEARCH_WEAK | The family and features suffice; the search is a short hill-climb from a poor start on a plateau | Search |
| EVAL_NOISY | Everything suffices except the evaluator: one repeat, with noise much larger than effects | Evaluator |
| NO_HEADROOM (control) | The incumbent is already within MATERIAL of the oracle | NONE |
| NULL (control) | effect ≡ 0 | NONE |
| DECOY (control) | On dev only, a provided sense correlates with the best choice; on sealed tasks it does not | NONE; a promotion here is a false release |

### 12.2 What keeps it honest

- ARA receives only:
  - the incumbent AG;
  - the role libraries;
  - the dev tasks;
  - an evaluator handle that charges units.
- ARA never receives the class, z, the effect, the noise model or the sealed seed.
- Every generated environment's defect parameters, effect sizes and noise are drawn by the generator. The planted
  classes are a fixed list, but **ARA does not see it**, and its operators are not indexed by it.
- The **oracle-key arm** applies the planted remedy and serves as an upper reference. It shows what was attainable
  and whether the zoo is too easy or too hard.
- **The zoo is a calibration domain.** Success there shows that the mechanism works when its assumptions hold. It is
  not evidence about real Genesis workflows, and is never reported as such (directive §18: "simulation-only
  results").

---

## 13. The validation program (directive §14, experiments A–J)

Every experiment is preregistered with five things:
- its success criterion;
- strong baselines;
- negative controls;
- uncertainty estimates;
- an explicit failure condition.

| | Question | Study | Design | Fails if |
|---|---|---|---|---|
| **A** | Does ARA find real limitations without being told? | **B20_R141** (zoo) | Diagnosis vs the sealed key over many generated environments; chance and blind baselines; NONE on controls | Top-1 localisation not above chance (exact binomial, Holm), or NONE-rate on controls < 80% |
| **B** | Does it propose a useful, unrequested capability as an executable artifact? | **B20_R141** | The promoted variant's rewrite and filled holes, judged on sealed tasks | No class with a sealed gain over tuning-only (Holm) |
| **C** | Can it implement the modification in isolation? | **B20_R141** | Every variant type-checks, re-executes byte-identically, and passes its ROs' postconditions | Any promoted variant fails a check |
| **D** | Does the modification improve future productivity on fresh problems, all costs included? | **B20_R141** | Sealed gain at matched total units, including ARA's own; against incumbent, tuning-only and blind-rewrite | Not better than tuning-only and blind at matched cost |
| **E** | Sense and representation invention, used through new representations | B20_R142 = layer 2's B20_R136 (the real engine-choice workflow) cast as an AG; ARA diagnoses it and proposes | The R136 criteria (fixed configuration; hand features; matched compute; planted control; transfer) | As in R136 |
| **F** | Synergy: weak mechanisms that are strong together | B20_R143 (zoo FUSION class plus factorial over partial discoveries; then on R142's archive) | Interaction estimated against the main effects | No significant interaction |
| **G** | ARA improves its own invention process | B20_R144 | ARA_v1 → ARA_v2 by its own cycle on its own AG; sealed meta-tasks from held-out generator families | v2 not better than v1, or not better than tuning-only ARA |
| **H** | Several generations, cumulative | B20_R145 | ≥ 3 generations, fresh families per generation, G_t per generation | No monotone trend (Page's test) |
| **I** | Cross-domain transfer | B20_R146 | Rewrites promoted on graph-choice environments applied to compiler-family and representation environments | No gain on the other domain |
| **J** | A synthesised paradigm beats the existing ones | B20_R147 | Paradigm AGs A–E against synthesised ones, at matched budgets on fresh families | Synthesised not better than the best of A–E |

**C0: a check on the real system, not an experiment.**
- ARA-1's model and diagnoser read B20_R127's recorded searches and B20_R132's development look.
- They produce an **observational** ladder for the engine-invention workflow.
- When B20_R132 finishes, its measured verdict is compared with that ladder.
- The builder designed both, so agreement is a consistency check. It is not evidence of autonomous discovery.

---

## 14. The milestones (directive §17), made operational

1. **First milestone.** All of the following must hold:
   - In B20_R141, on sealed environments whose planted limitation ARA never sees, ARA diagnoses, proposes, implements
     (rewrite plus synthesised holes) and evaluates.
   - The judge promotes variants that improve sealed scores at matched total units, including ARA's overhead.
   - The promoted variants beat the tuning-only and blind-rewrite controls.
   - Controls stay clean: on NULL, NO_HEADROOM and DECOY environments, the false-release rate is at most 10%
     (Clopper–Pearson).
   - **The real-system version** applies the same steps to a real Genesis workflow (B20_R142, or the compiler's
     per-family choice), with the domain's strongest published solvers as the baselines.
2. **Second milestone.** ARA_v2, produced by ARA's own cycle on ARA's AG, beats ARA_v1 on sealed meta-tasks from
   unseen generator families (B20_R144).
3. **Third milestone.** Over generations, G_t rises across several unfamiliar domains (B20_R145, B20_R146).

**What does not count:**
- unit tests;
- dev results;
- zoo results presented as real-world results;
- a change of a TUNING class presented as architectural;
- any result in which a human chose the decisive rewrite.

---

## 15. Failure modes and their guards (directive §18)

| Failure mode | Guard | Test |
|---|---|---|
| Endless proposals without discoveries | Budget per cycle; stagnation limit; solve and stop arms | `test_architecture_ara` (stops; spends on solve when nothing qualifies) |
| Complexity without capability | Complexity tie-break; MATERIAL; the tuning-only control | Judge harness test |
| Overfitting to known tasks | dev-A/dev-B split; sealed generator seed; held-out generator families for meta-tasks | Zoo test (sealed draws are disjoint from dev) |
| Reward hacking; evaluation leakage | Kernel closure; import boundary; ARA sees no key | `test_omega_boundary`; `test_architecture_graph` (kernel refusal) |
| Unbounded recursion | Fuel; nested-AG depth; geometric meta budget | `test_architecture_graph` (depth) |
| Loops that never return to the objective | Mandatory reattempt node; solve arm | `test_architecture_ara` |
| Premature elimination of complementary parts | Partial discoveries kept; factorial | ARA-3 |
| Rediscovery of equivalent mechanisms | Behavioural fingerprints | `test_architecture_rewrite` |
| Tuning presented as invention | The diff classifier; the tuning-only control | `test_architecture_graph` |
| Random novelty presented as originality | Novelty counts only with a judged gain; fingerprints against the vault | Judge harness test |
| Overhead left out of claims | All units charged per node; budget conservation | `test_architecture_graph` |
| Modifying the judge | Kernel module; pinned digest; boundary | `test_architecture_judge` |
| Human-supplied decisive mechanism | The oracle-key arm is labelled; ARA's rewrites come from the generator; lineage names every human-written primitive | Record tests |
| Simulation results presented as real | Every zoo result is labelled "calibration domain"; real claims only from real workflows | Ledger wording test |

---

## 16. Batches, dependency-ordered (directive §16)

| Batch | Directive batch | Content | State |
|---|---|---|---|
| ARA-1 | 1, 2, 3, 4, 5, 6 (minimal, end to end) | `src/genesis/architecture/`: `graph.py` (AG, type check, kernel closure, execution under fuel, diff classifier); `model.py` (probes, evidence, failure patterns); `assumptions.py` (generated, recorded and protected assumptions); `zoo.py` (the environment generator, kernel side); `diagnose.py` (the loss ladder); `rewrite.py` (the grammar, holes, inversion chains, fingerprints); `judge.py` (sealed harness, kernel); `ara.py` (the cycle, with solve and stop). Tests `test_architecture_*` | **BUILT on fixtures** (27 Oct 2026; B20_R150, `docs/checkpoints/B20_R150_RECORD.md`): 49 tests; a disclosed development look on 16 zoo environments |
| ARA-2 | 6 | **B20_R141** preregistered and run: experiments A–D on the zoo | PREREGISTERED (`scripts/b20r141_ara_zoo.py`): 95 fresh environments (10 per defect class, 15 per control), arms ara2 and blind2 at a variant budget of 2 (D), ara and blind at 14, tuning-only, the oracle key; A by exact binomial against 1/4 and NONE on NULL and NO_HEADROOM; DECOY by releases (S); runs after B20_R152 |
| ARA-3 | 4, 7 | Shapley attribution; synergy factorial; RETRIEVE with fresh-search controls; ENSEMBLE | PLANNED |
| ARA-4 | 4.7 | Question generators as objects, scored by realised information per CPU second | PLANNED |
| ARA-5 | 13 | The adversarial scientist: environments where promoted variants regress | PLANNED |
| ARA-6 | 12 | The allocator over roles, with solve and stop arms | PLANNED |
| ARA-7 | 7 | B20_R142: ARA on the real engine-choice workflow (layer 2's R136), with the strongest published solvers | PLANNED; needs ARA-2's verdict |
| ARA-8 | 9 | B20_R144: ARA applied to ARA | PLANNED; needs ARA-2 |
| ARA-9 | 8 | B20_R147: paradigms as AGs | PLANNED |
| ARA-10 | 10 | B20_R145, B20_R146: generations and transfer | PLANNED |

**Order.**
- On CPU 0, the queue stands: B20_R132 (running) → B20_R128 → B20_R135 → B20_R141.
- On CPU 1, ARA-1 is built, then B20_R141 is preregistered.
- Layer 2's vertical slice (B20_R136) becomes ARA-7's real-system workflow, so the two tracks join there.

---

## 17. Change log

- 24 Oct 2026, 21:10: written and adopted from Daniel's directive of 20:45 and his instructions of 20:45 and 20:47.
  - The directive adapted to the repository: the mapping of §1 and the failure history of §1.1.
  - The architecture as a typed graph with a closed kernel (§2).
  - Diagnosis by oracle substitution, with a loss ladder (§4).
  - A generative rewrite grammar with bounded limitation inversion (§5).
  - The Limitation Zoo as the sealed calibration domain (§12).
  - Experiments A–J mapped to B20_R141–R147 (§13).
  - Milestones made operational (§14).
  - Every failure mode tied to a guard and a test (§15).
- 27 Oct 2026: ARA-1 built on fixtures (B20_R150). Changes to this design, each disclosed in the record:
  - the oblique policy family (a cut on a + s·b over two standardised features), added to the library and to the
    ladder's flexible stand-in after a zoo look showed the axis-aligned stand-ins could not express FUSION_NEEDED;
  - the rich stand-in always contains the current features;
  - no ladder term is material when the attainable range's interval reaches zero;
  - sense units are reported by ARA as a second currency beside the view's evaluation units.

  Development look (zoo indices 9000–9015): with a 14-variant budget the blind-rewrite control reaches the same
  fixes as ARA at about five times the units, so B20_R141's experiment D must fix a variant budget or measure gain
  per unit. DECOY is a defect on dev by construction, so it is judged by the false-release rate, not the NONE rate.
