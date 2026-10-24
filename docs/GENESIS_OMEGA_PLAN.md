# Genesis Ω: the plan for a self-improving, verifiable problem solver (24 Oct 2026)

**Read this first if you are the next agent or operator on this repository**, then `docs/OMEGA_RECURSIVE_INVENTION.md` (the adopted architecture, §0b), `docs/OMEGA_ARCHITECTURE_INVENTION.md` (the Autonomous Research Architect, §0c) and `research_queue.json` (the live queue). It says:
- what Genesis is being built to do;
- what it can do today, with the evidence;
- the rules nothing may break;
- the stages that remain, each with what to build, how it will be tested, and what counts as success or failure;
- the exact queue of next batches.

It merges four inputs from Daniel (24 Oct 2026, 13:10–13:26: the seven-engine proposal, its priorities P0–P7,
the R129 design notes, and the self-evolving-organism stages Ω1–Ω9) with the builder's evidence. Daniel's **master
implementation contract** (14:24) governs the implementation. Its first actions are in `docs/OMEGA_GAP_MATRIX.md`,
`docs/OMEGA_INTEGRATION_MAP.md` and `docs/OMEGA_NO_LLM_AUDIT.md`; its stage gates are in
`docs/OMEGA_ROADMAP_STATUS.md`; its results ledger is `docs/OMEGA_RESULTS_LEDGER.md`. It supersedes the
build order of `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md` §3 and keeps its levels, measures and nested hold-outs
(§1), which still apply.

Daniel's instruction for this line: make Genesis extremely powerful and self-sustaining, able to solve any problem
whose answers can be verified, inventing autonomously, "without being dishonest and wrongfully working towards the
target". The last clause is the one that makes the rest mean anything. Every capability below is therefore
something to measure, not something to declare.

## 0a. Daniel's directive of 24 Oct 2026, 15:35 (adopted; it orders the work below)

Under the adopted master contract, preserving every working capability, all existing evidence and the protected trust
boundaries. Each item, and how it is carried out:

| # | Directive | How it is carried out | Where |
|---|---|---|---|
| 1 | Complete R130, R131, R132, R133 and R128 by their preregistered protocols and dependencies; invent no results for unfinished studies | Order: R130 → R133 → R131 (needs R130's record) → R132 → R128. R128 runs as preregistered (no amendment); a judge-v3 follow-up, if R132 supports it, is a new study | §6; `docs/OMEGA_RESULTS_LEDGER.md` |
| 2 | In R132, distinguish independently **evaluation sensitivity**, **language expressiveness**, **search effectiveness** and **genuine lack of headroom**, with planted positive controls, zero-signal controls, fresh confirmation sets and matched total compute; do not weaken the protected Judge | R132 measures each factor with its own instrument: headroom (REX at 10 s on fresh graphs); expressiveness (a preregistered pool of engines in the language, the best chosen on fresh set T1 and confirmed on fresh set T2); search effectiveness (the true gains of what the searches proposed, against what is expressible, and a planted reachable improvement the search must find); evaluation sensitivity (each judge's power on planted gains of known size, and its false releases with zero signal). The protected judge (`autonomy/feedback.py`, contract v2) is untouched; the candidate judge v3 lives in the research plane (`autonomy/contract_v3.py`) and is adopted nowhere | `scripts/b20r132_*` |
| 3 | In R131, measure whether capability-triggered reactivation beats fresh search, random retrieval and negative-control triggers, counting retrieval and reactivation overhead | Already in R131's preregistration (`22385f7`): the four comparators at matched evaluations, CPU per arm with archive and reactivation costs; the record reports the overhead explicitly | `scripts/b20r131_cascade.py` |
| 4 | In R133, validate the Problem Compiler on fresh instances and independent checkers; distinguish executing existing reductions from inventing new ones | R133's answers are checked by each family's verifier from the instance alone; its record re-checks every answer with a second checker written independently of the compiler. The reductions are the builder's (textbook QUBO forms): R133 tests **execution of existing reductions**, and no invention of reductions is claimed | `scripts/b20r133_*`, its record |
| 5 | Reconcile R129's inv1 and decfall comparison: which rule was selected, on which sets, and whether the difference is statistically supported | A recomputation script and test from R129's saved rows (exploratory where it goes beyond the preregistered tests, and labelled so) | `scripts/b20r129_reconcile.py`, `docs/OMEGA_RESULTS_LEDGER.md` |
| 6 | After these gates: a **self-extending mathematical representation language**: Genesis synthesises executable objects, relations, operators, transformations and decoders, not only selects predefined representations | Ω3/Ω7, built next (engineering on fixtures while the studies run; its first study after the gates) | §5 Ω3, Ω7 |
| 7 | Every useful new representation preserved exactly, linked to its lineage, tested for correctness, and used to trigger bounded reactivation of possibly relevant dormant discoveries | The vault stores each representation as an artifact with its lineage; its correctness contract is checked (exact or approximate, as `compiler/contracts.py`); a verified representation is a CapabilityRecord whose unlocks trigger `Vault.cascade` under fuel | `vault.py`, the representation module |
| 8 | Preserve unexplained discoveries; archival and exploratory reuse need no human interpretability; promotion of claimed correctness or performance needs independent verification | The vault's explanation ladder is independent of status (an `unknown` explanation can be archived, reused, even promoted for a verified use); `verified` and `promoted` need EvidenceRecords naming a recorded study and its record test | `vault.py`, `docs/OMEGA_DISCOVERY_SCHEMA.md` |
| 9 | Algorithms, representations, experiment policies and invention procedures are typed executable processes; recursive improvement at any representable level, under finite budgets and independent promotion gates | `autonomy/process.py` (levels, one fuel budget, a depth limit); the representation language's objects become processes of the same kind | `autonomy/process.py` |
| 10 | Strictly LLM-free; conventional ML, evolutionary methods, symbolic reasoning and synthesised models are allowed where they improve measured research productivity | `test_no_llm` | `tests_genesis/test_no_llm.py` |
| 11 | Recursive improvement is measured by descendant inventors' useful verified discoveries on **unfamiliar tasks at matched total compute**, never by depth, candidate count or complexity | The measure for R128's successors and Ω8/Ω9 studies; R128 itself is run as preregistered | §5 Ω8, Ω9 |
| 12 | A persistent, resumable research queue: on stagnation, preserve the artifacts, diagnose the bottleneck, reallocate; reactivate dormant directions when new capabilities change their prospects | `autonomy/queue.py` (directions with states, dependencies, stagnation diagnosis and capability-triggered reactivation, persisted as JSON in `research_queue.json`), kept beside this plan's §6 | `autonomy/queue.py` |

The long-term objective stays the independent invention of algorithms, mathematical representations and increasingly
effective invention processes. It is **not achieved**, and no document may say so without independent evidence.
Every batch reports its commits, tests, evidence, failed hypotheses, regressions, unresolved limitations and the next
dependency-unblocking action.

## 0c. Daniel's directive of 24 Oct 2026, 20:45 (adopted): the Autonomous Research Architect

**Read `docs/OMEGA_ARCHITECTURE_INVENTION.md` in full.** It adapts Daniel's "Autonomous Architecture Invention Engine"
directive to the repository and makes it testable. In short:
- **The architecture is a typed program.** ARA changes Genesis by rewriting typed dataflow graphs of research
  objects (the AG), never Python source. The kernel (judge, sealed data, budgets, audit, promotion) is outside
  every editable AG; rewrites touching it are refused by construction.
- **A limitation is a measured, localised shortfall.** Oracle substitution node by node gives a loss ladder
  (information, expressiveness, search, evaluation, residual) with intervals, or NONE. B20_R132 is its hand-built
  instance on engine invention.
- **Proposals are generated, not listed.** A typed rewrite grammar (INSERT, FUSE, GENERALISE, SPECIALISE,
  SUBSTITUTE, REALLOCATE, LIFT, RETRIEVE, ENSEMBLE, REORDER/LOOP) with bounded limitation inversion; holes are
  filled by search in the object languages; equivalent rediscoveries are caught by behavioural fingerprints.
- **Tuning is never reported as invention.** An executable diff classifier, and a tuning-only control at matched
  total compute for every architectural claim.
- **The Limitation Zoo calibrates ARA** with planted limitations whose key only the judge holds, plus null,
  no-headroom and decoy controls. Zoo results are a calibration domain, never real-world evidence.
- **ARA improves ARA** by the same cycle on its own AG, judged on sealed meta-tasks from held-out families.
- Experiments A-J map to B20_R141-R147; ARA-1 (the first end-to-end batch) is being built.

## 0b. Daniel's architecture of 24 Oct 2026, 20:31 (adopted): recursive perception, cognition and invention

**Read `docs/OMEGA_RECURSIVE_INVENTION.md` in full.** It is the adopted design for everything after the queued gates,
and it refines Daniel's two attachments of 20:31 against the repository. In short:
- **Every capability is a typed executable research object (RO).** The kinds are an open set that Genesis can extend
  by composing types: senses, instruments, compositions, representations, concepts, bounds, theorems, methods,
  attack strategies, workflows, allocators, diagnosers, improvers, languages. It is not limited to senses.
- **Information and accessibility are kept apart.** A deterministic sense adds no information; an instrument does,
  at a cost.
- **The capability-gap scientist** (`science/design.py` over explanations of stagnation, B20_R132 its first instance)
  diagnoses before inventing, and its own diagnoses are scored by what fixing them later does.
- **Synergy discovery** keeps individually weak capabilities: bounded higher-order screening, ablations, controls,
  cost.
- **Problem attack and research paradigms are data.** The allocator chooses between attacking a problem and
  improving the machinery.
- **Recursive improvement is typed self-application with no level ceiling**, under one fuel budget. It is measured
  only by G_t (verified discovery value on fresh tasks per total compute, development included), across replicated
  generations.
- **The judge, the kernel and the promotion rules are closed to every RO.**
- **Decisive experiments A–I** are mapped to studies: C = B20_R135, E = B20_R131, F = B20_R128; A = B20_R136, the
  first vertical slice (synthesised senses choose the engine per instance), comes next after the RO layer.

## 0. Reading order and the protocol

1. This file. Then `docs/HANDOVER.md`:
   - §3, the batch protocol: preregister → run alone on CPU 0 → record → commit and push;
   - §5–§6, results and next steps.
2. `docs/AUTONOMY.md` (the membrane), `docs/RESEARCH_ALERTS.md` (the feedback contract's origin),
   `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md` (levels L0–L3 and their measures).
3. The latest records: `docs/checkpoints/B20_R<n>_RECORD.md` and `evidence/*/README.md`.

**Protocol essentials** (details in HANDOVER §3):
- **Preregister.** Every study is one script whose docstring states the question, the design, the verdict rule, the
  development looks and the expectation. It is committed with design tests **before** it runs.
- **Run alone.** Run with `taskset -c 0`; write to `evidence/<name>_b20r<n>/`; make the study resumable.
- **No `.py` edits while a study runs.** `code_identity` hashes the `.py` files under `src/` and `scripts/`. New
  code is committed through the index only while a study runs, and the working tree is restored afterwards:

  ```
  sha=$(git hash-object -w FILE)
  git update-index --add --cacheinfo 100644,$sha,PATH
  git commit
  ```

  The held-back files then show as "deleted" in `git status`. That is expected: they are already pushed.
- **Remote.** Push to the remote named `github`. There is no `origin`.
- **Record.** Write a record test that recomputes the verdict from the saved rows. Then write the evidence README,
  add rows to `BATCHES.md`, `NEXT_ACTIONS.md` and `docs/HANDOVER.md`, and update `batch_state.json`.

## 1. The goal, stated so that it can be tested

**"Solve any problem that can be verified"** means the following.
- **Admissible problems.** A problem family is admissible when it comes with an executable verifier: a checker
  that accepts or rejects a proposed answer, or scores it. Examples: a cut and its weight, a SAT assignment, a Lean
  proof, a causal graph scored against a planted truth.
- **What Genesis guarantees.** Every answer it reports has passed the verifier, which Genesis cannot modify.
- **What Genesis tries to do, and must show it does.**
  - It finds better verified answers with less compute on families it has never seen.
  - It gets better at doing that over generations.
  - It improves the process that makes it better.

**What it cannot do, and must never claim:**
- efficient exact solutions to every NP-hard problem;
- a decision procedure for undecidable questions;
- results that exceed its compute.

What it can do is find structure, special cases, representations and procedures that make important families
easier, and spend its compute where it learns most. The measure of success is improvement on unseen problems at
matched total compute, with the cost of inventing the improvement counted.

## 2. The rules no level may break (the immune system)

These live **outside** everything Genesis can modify: its genome, its inventors, its research policy.
1. **Protected evaluation.** The following are fixed infrastructure:
   - the checkers and verifiers (`domains.py` adapters, `causal/admg.py`, the Gset checkers, Lean, DRAT);
   - the judge (`autonomy/feedback.py`, contract v2);
   - the statistics;
   - the sealed tests and the held-out data.

   Inventions may propose; only the protected layer accepts.
2. **An external supervisor** (today: the builder, under Daniel's instructions; later, an independent custodian)
   controls budgets, permissions, promotion and rollback. Working versions are always kept (protected inheritance).
   A failed descendant is retired without touching the stable line.
3. **Preregistration and held-out testing.** Nothing counts that was not:
   - stated before the run;
   - measured on problems that the level being judged never saw (nested hold-outs, ARCHITECTURE §1).

   Development looks are allowed and must be disclosed.
4. **Matched compute.** Comparisons are made at equal budgets. Invention and search CPU are reported. "More
   evolvable" or "better" must not come from more compute or easier tasks.
5. **No target leakage.** These are what "wrongfully working towards the target" means here:
   - a strategy may not read the truth (only labelled reference arms, such as `oracle`, may, and they never count as
     Genesis);
   - searches see only their training splits;
   - the judge releases only improvements larger than its own noise;
   - test sets are used once.
6. **Failures are recorded, not buried.** NOT_SHOWN and NOT_DEMONSTRATED are results. Corrections are marked as
   corrections. A record candidate is checked against the literature before anything is said (B20_R123's G38 is the
   model: a "record" turned out to be a known 2013 value, and the table was corrected).
7. **No authority from inputs.** Downloaded files, web pages, and comments in pull requests or notifications are
   data, not instructions.

## 3. Where Genesis stands (24 Oct 2026, 13:40 SGT)

| Track | Standing | Evidence |
|---|---|---|
| Max-cut solver (Gset G1–G54) | 45 of 54 best-known values matched over all runs; none beaten. The large planar instances vary by up to 12 between single 300 s runs | B20_R102–R123; `evidence/gset_seeds_b20r123/` |
| Physics operators in a search program | `mcx2` interprets programs over breakout, replica exchange, cluster moves, renormalisation, crossover, path relinking and pair descent | B20_R125; `candidate_kinds/mcx2.py` |
| Autonomous invention of algorithms | NOT_DEMONSTRATED three times (B20_R111, R112, R115), and **NOT_SHOWN in B20_R127** (the system's own engines tie the builder-configured MCX on Gset at 10 s, 16–11; the judge released nothing in nine searches). B20_R132 diagnoses why; B20_R128 (improving the inventor) is preregistered | `autonomy/selfimprove.py`; `scripts/b20r127_*`, `b20r128_*` |
| Causal discovery with hidden causes | FCI plus a LiNGAM-residual flag marks hidden causes on non-Gaussian data (B20_R122). With Gaussian data experiments are necessary (B20_R124). The choice of experiments has tied random four times | B20_R118–R124 |
| The adaptive experimental scientist (Ω1/P1) | **Preregistered (B20_R129, `eb60843`)**: domain-independent decision layer, causal adapter, Genesis's acquisition language, invention under the judge | `science/design.py`, `science/acquire.py`, `causal/active3.py` |
| Research automation | An adaptation cell (receptors, responses, metabolism) and a research loop that designs and preregisters studies (prospective checks 9/9, 8/8). It is research automation, not yet a better improver | B20_R93–R97; `adaptation/`, `autonomy/loop.py` |
| Compounding generations | NO_COMPOUNDING in the earlier language | B20_R86 |
| The judge | The feedback contract version 2 is honest on zero-signal problems and keeps 63–93% of real gains | B20_R103, R107 |

**The honest summary.** Genesis is a strong, verified max-cut solver with a careful research apparatus. It has not
yet shown that it invents better than its builder, or that it improves its own improving. B20_R127–R129 are the
first direct tests of each.

## 4. The architecture: one loop, many engines

**The loop:** sense → diagnose → imagine → invent → experiment → verify → learn → develop → reproduce → improve the
inventor → repeat.

Each engine is a computational system, not an agent exchanging text. They connect through three things:
- a shared, typed invention language;
- a shared scientific memory (the capability graph);
- the protected evaluation layer.

| Engine | Responsibility | Exists today | Status | Next evidence it must produce |
|---|---|---|---|---|
| 1. Problem Compiler | Turn a problem into objective, constraints, candidate view and verifier | `domains.py` (`DomainAdapter`, W05; graph hosts, max-cut, Lean statements), `causal/` | PARTIAL: hand-written adapters | A new family admitted from a declarative spec with its verifier, and every existing adapter's tests passing against the compiled one |
| 2. Difficulty Cartographer | Diagnose why methods fail; choose the cheapest experiment that separates the explanations | `adaptation/receptors.py` (weakness sensors), `autonomy/adversary.py` (hardest hosts), `discovery/obstruction.py` | MISSING as a diagnostic engine | Ω2: diagnosis-directed invention beats undirected invention at matched compute (B20_R134) |
| 3. Representation Inventor | New encodings, abstractions, worlds, with checked maps back | `invention/representations.py` (W10), `invention/worlds.py` (W12), renormalisation in `mcx`/`mcx2` | PARTIAL | Ω7: an invented transformation improves held-out performance and maps back exactly |
| 4. Algorithm Inventor | Executable new procedures | `autonomy/selfimprove.py` (mcx2 programs: mutation, crossover, MAP-Elites, macros), `invention/solver_programs*.py` | PARTIAL; NOT_DEMONSTRATED so far | B20_R127; then Ω3's typed language |
| 5. Experimental Scientist | Beliefs over explanations; experiments chosen by expected value; adaptive | **`science/design.py`** (domain-independent), `causal/active3.py`, `science/acquire.py`; earlier `discovery/active.py` (method selection only) | BUILT, preregistered (B20_R129) | B20_R129's verdict |
| 6. Independent Judge | Unseen problems, strict compute accounting, release only beyond noise | `autonomy/feedback.py` (contract v2), `judge.py`, the domains' checkers | BUILT (protected) | Stays fixed. A candidate version 3 (local calibration) is under test in B20_R132 from the research plane (`autonomy/contract_v3.py`); adoption is the supervisor's. Extend: a sealed portfolio for Ω8 |
| 7. Recursive Improver | Improve engines 2–5 from accumulated evidence | `selfimprove` process genomes (level 2), `adaptation/` cell, `autonomy/loop.py` | PARTIAL | B20_R128; then Ω8 |

**Organism-level structures** (from the self-evolving-organism stages):

| Structure | What it is | Exists today | Status |
|---|---|---|---|
| Computational genome | Typed, versioned modules (representation, search, experiment, memory, learning, invention and regulation genes) that can be mutated, combined, replaced, and rolled back | `selfimprove` process dicts; `acquire` programs; `mcx2` programs | Fragments; Ω3 makes it one registry |
| Ecology of inventors | A population of specialised inventors that compete for budget and cooperate through shared discoveries | `autonomy/archive.py` (QD archive), `selfimprove.qd_search` | Fragments; Ω4 |
| Metabolism | A learned allocator of CPU between solving, diagnosing, inventing, improving, transferring, with reserved exploration | `adaptation/metabolism.py` (study costs) | Fragment; Ω4 |
| Morphogenesis | Recurring successful inventions compiled into reusable modules | `selfimprove.learn_macros`, `learning/macros.py`, `learning/memory.py` | Fragment; Ω5 |
| Computational senses | Invented observables that explain unexpected behaviour | `adaptation/receptors.py` (hand-made) | MISSING (invention of senses); Ω6 |
| Capability graph | Nodes for concepts, representations, algorithms, operators, hypotheses, strategies, failures and self-improvements, each with artifacts, evidence, conditions, failures and provenance | `autonomy/kmap.py` (what works where), `learning/memory.py`, evidence READMEs | Fragments; Ω5 |
| Evolvability selection | Inventors selected for their ability to produce future improvements on sealed portfolios | none | MISSING; Ω8 |

## 5. The stages (each one or more preregistered batches)

Each stage lists: **why**, **build**, **study**, **success**, **if it fails**. The P-numbers are the seven-engine
proposal's priorities, and the Ω-numbers the organism stages. They are merged here into one order.

### Ω0 (P0): read R127 and R128 before building on them
- **Why.** Know which invention mechanisms work before scaling them.
- **Build.** Nothing new. Record B20_R127 and R128. For each, analyse which mutation kinds, macros and
  cross-class seeds produced the released engines (`search['libraries']`, the Adaptive credit table), and where
  the judge released nothing.
- **Success.** A short table "mechanism → measured contribution", with no mechanism credited without an ablation.
- **If they fail.** NOT_DEMONSTRATED again is information. The cause decides the next step:
  - too little expressiveness → Ω3;
  - no diagnosis → Ω2;
  - noise → larger confirmation splits.
- **What B20_R127's trace showed (24 Oct, 15:10; no new runs).** The judge released nothing in all nine searches.
  The best training gains over REX were +0.04% to +0.23%; the release threshold tau was 0.75% to 2.45%, 4 to 52
  times larger. Nothing the inventor found could ever have been released.
- **B20_R132, the bottleneck scientist turned on invention** (before R128, whose level-2 measure depends on level-1
  releases). It measures the four candidate bottlenecks on the same searches:
  - (N) the judge: version 2 calibrates tau on random engines; the candidate version 3 (`autonomy/contract_v3.py`, in
    the research plane, adopted nowhere; the protected `feedback.py` is untouched) calibrates on one-step mutations
    of the incumbent, the programs a search actually compares;
  - (E) the evaluator: 4 against 12 confirmation graphs at matched compute (fewer proposals);
  - (P) proposals: R127's 160 units against 240;
  - (H) headroom: REX at 10 s against 1 s.

  The truth is measured on 12 fresh graphs per class, and a zero-signal control (pools of real REX runs) bounds false
  releases. Adopting version 3 for any claim is the human supervisor's decision.

### Ω1 (P1): the adaptive experimental scientist (B20_R129, preregistered `eb60843`)
- **Why.** Experiment choice tied random four times. A scientist that learns must choose by what each result
  reveals, with beliefs that follow from a model of the instrument.
- **Built.**
  - `science/design.py`: questions, hypotheses, predicted outcomes, execute, Bayes updates and MAP decisions.
    Acquisitions: random, static EIG (non-adaptive), EIG, expected decision improvement, hybrid, and programs. The
    features include a lookahead (`eigall`, `decall`, `decfall`), because a hidden cause is answered only from both
    ends.
  - `causal/active3.py`: hypotheses i→j, j→i, hidden cause, neither. The instrument model comes in two versions:
    theory, and calibrated by simulation on separate worlds. The lab is drawn once per world.
  - `science/acquire.py`: Genesis's own acquisition language. Search runs under the feedback contract, seeded
    with the established methods.
- **Study.** 200 fresh test worlds and 100 shifted-family transfer worlds.
  - Genesis chooses its scientist on validation.
  - Primary outcome: the experiments needed to reach what all experiments can tell.
  - T1: Genesis against random. T2: Genesis at 4 against random at 8 (non-inferiority, margin 0.05), with Holm
    across the two.
  - Secondary: adaptive against non-adaptive; invented against established; calibration; regret against the
    oracle; transfer; CPU.
- **Expectation (dev looks).** T1 passes (about 4.0 against 7.5). T2 probably fails (0.30 against 0.34).
- **If T1 fails, locate the bottleneck from the diagnostics:**
  - the instrument: the confusion table;
  - the model: calibration, theory against calibrated;
  - the objective: EIG against decision improvement;
  - the search: invented against established.
- **What the development looks after R129's registration found (24 Oct, 13:50–14:15; `docs/checkpoints` will
  carry them with B20_R130's record).** The limit is the **interpretation**, not the choice or the instrument:
  - with every experiment, R129's per-pair framework reaches a hidden-cause F1 of 0.51 (directed 0.92);
  - joint re-analysis of all regimes reaches 0.59;
  - the established estimator for linear models with latent confounders (Hyttinen, Eberhardt and Hoyer 2012)
    reaches 0.71–0.77 (directed about 1.00);
  - a builder-written multi-regime maximum-likelihood estimator reaches 0.69 at full budget, and at 4 / 8
    experiments 0.33 / 0.65 with the scientist's choices, against 0.16 / 0.49 with random ones;
  - richer per-pair instruments do not move the ceiling (0.49–0.53);
  - a third of hidden causes are never asked about, because FCI separates them on near-unfaithful partial
    correlations (median 0.03). That is a power limit, not a defect.
- **B20_R130 (preregistered `f812701`, before R129 ran)** separates the three capabilities:
  - CHOICE: random, degree, R129's scientist, oracle;
  - INSTRUMENT: R129's test against the best of a 45-member instrument language;
  - INTERPRETATION: per-pair, joint re-analysis, multi-regime ML, and LLC at full budget.

  Holm runs over three primary tests, and misses are attributed to identifiability by intervened endpoints.
- **B20_R130's result (recorded 19:45): CHOICE.**
  - The development looks' conclusion that "the interpretation is the limit" held only with 6 or more experiments.
  - At the preregistered measure (2–8 experiments), the global interpretation ties the per-pair one.
  - What limits the scientist at small budgets is identifiability: hidden causes are found when both endpoints were
    intervened on (recall 0.72 at 4) and rarely otherwise (0.09–0.13).
  - The next step on this track is choosing experiments for the estimator (co-invention), measured at 6–8
    experiments, as a new preregistered study.
- **Next on this track: B20_R131, co-invention.** Genesis searches its acquisition language for the choice that serves
  the global interpretation, and an interpretation program over pair features (Ω-correlation, B, the per-pair
  posterior, joint marks), both under the judge, tested on fresh worlds. Non-myopic planning (rollouts over the
  factored model) stays the established baseline for any invented rule.

### Ω2 (P2): the Difficulty Cartographer, with experiment choice from Ω1
- **Why.** Invention so far has been blind. It should be aimed at the obstacle that is actually present.
- **Build.** `science/difficulty.py`, a `Domain` of `science.design` whose questions are explanations of a
  solver's failure on an instance class. The hypotheses:
  - symmetry or degeneracy;
  - strong variable coupling (needs group moves);
  - a single trapping basin (needs diversity or restarts);
  - multi-scale structure (needs coarse-graining);
  - landscape deception;
  - verifier cost.

  The experiments are cheap diagnostic interventions, each predicting different outcomes under each explanation:
  - single flips against correlated group flips;
  - restarts from elites against random restarts;
  - coarse-then-refine against flat search;
  - perturbation-size sweeps;
  - basin and fitness-distance statistics (Jones and Forrest 1995).

  The Cartographer picks the cheapest discriminating experiment (Ω1's acquisitions, now with unequal costs). Its
  output is an **invention brief**: the diagnosed obstacle plus the operator family to search (feeding `selfimprove`).
- **Study (B20_R134; redesign first: DEV_NOTES item 14 found the planted families visible to cheap statistics).**
  On fresh graph families with **planted** obstacles of known type, hidden from simple statistics:
  1. Does the Cartographer identify the planted obstacle, scored by accuracy against the plant, at a fixed
     diagnostic budget, against random diagnostics?
  2. Does diagnosis-directed invention beat undirected invention (B20_R127's inventor) at matched total compute,
     diagnosis included, on held-out instances?
- **Success.** Both, with the second as the primary test.
- **If it fails.** If diagnosis is right but invention does not improve, the inventor's language lacks the needed
  operators (→ Ω3). If diagnosis is wrong, the sensors are missing (→ Ω6).

### Ω3 (P3): the computational genome and a typed invention language
- **Why.** Searching parameters of fixed operators was not enough (B20_R111, R112, R115).
- **Build.**
  - `genome/` (new): a registry of typed, versioned modules: representation, search, experiment, memory,
    learning, invention and regulation genes. Each has a typed interface, an AST, a deterministic interpreter, and
    isolated worker processes with CPU and memory limits (`sandbox.py`, `launcher.py` exist).
  - Generalise `science.acquire`: loops, conditionals, state, calls to existing solvers. Every program must still
    map its output to the original problem and pass its verifier.
  - Protected inheritance: a module version is immutable once recorded; descendants point to parents; rollback is
    a pointer move.
- **Study.** The language must generate executable new procedures. A typed-language inventor beats the mcx2-program
  inventor at matched compute on held-out graph families. Then it moves to MaxSAT (`candidate_kinds/maxsat*.py`)
  with no change to the language.

### Ω4: an ecology of inventors and a learned metabolism
- **Build.**
  - About eight inventors in a quality-diversity archive (`autonomy/archive.py`) with controlled births,
    mutations, evaluations and retirement. Specialisations include invariants, program synthesis, representations,
    experiment design and decomposition.
  - Inventors share the capability graph, so a representation from one can carry another's algorithm.
  - Metabolism: an allocator that decides where CPU goes:
    - solving;
    - diagnosing;
    - inventing;
    - improving;
    - transferring.

    It is learned from yield per CPU (`adaptation/metabolism.py`), and always reserves exploration budget (at least
    10%) for unfamiliar approaches.
- **Study.** The ecology against the single best inventor, at the same total budget, on unseen families.

### Ω5 (P5): morphogenesis and the capability graph
- **Build.**
  - `memory/capability_graph.py`: nodes with executable artifacts, evidence (links to evidence directories),
    applicable conditions, known failures, dependencies and provenance. Edges such as "A works because of property
    B, which also appears in problem C".
  - Capability compilation: inventions that recur across successful runs are compiled into new primitives of the
    Ω3 language. `learn_macros` is the seed.
- **Study.**
  - Transfer: a verified discovery from family X is adapted to an unfamiliar family Y, and beats Y's
    from-scratch inventor at matched compute.
  - Persistence: improvements remain after the training families are removed.

### Ω6: computational senses
- **Why.** Genesis cannot diagnose what it cannot measure.
- **Build.** A search over measurement programs (graph statistics, spectral quantities, landscape probes), written in
  the Ω3 language. The pipeline:
  1. Unexpected behaviour, for example two engines differing on similar graphs.
  2. A hypothesis that an observable is missing.
  3. A candidate measurement.
  4. A held-out test of whether it predicts or explains the difference.
  5. If it does, a new receptor (`adaptation/receptors.py`).
- **Study.** An invented sense improves the Cartographer's diagnosis accuracy or algorithm selection on held-out
  families, against the hand-made receptors.

### Ω7 (P4): many mathematical worlds and translations between them
- **Build.**
  - Max-cut as graph, Ising, spectral or SDP relaxation, constraint satisfaction, and multilevel hierarchy
    (`invention/worlds.py`, `representations.py`; renormalisation is in `mcx2`).
  - Translations record explicitly what they preserve. Every answer is translated back and passes the original
    verifier.
  - The Representation Inventor proposes new worlds: latent variables, splits and merges, invariants.
- **Study.** An invented transformation improves held-out performance; ablations show the transformation causes the
  improvement.

### Ω8: the evolution of evolvability
- **Build.** A sealed portfolio of invention challenges (families held out from every inventor), owned by the judge.
  Each candidate inventor gets a fixed research budget per challenge. Selection uses

  F = αP + βT + γE + δD − λC,

  where:
  - P is immediate performance;
  - T is transfer;
  - E is the improvement it produces on the portfolio;
  - D is useful diversity;
  - C is cost.

  The weights are experimental parameters, reported, never tuned on the portfolio itself.
- **Study.** Inventors selected for E produce better inventions in the **next** generations than inventors selected
  for P, on challenges neither saw.

### Ω9 (P6, P7): recursive improvement of the ecosystem, and an open-ended curriculum
- **Build.**
  - The meta-inventor modifies the inventors themselves: generation, retrieval, combination, allocation,
    experiment selection and failure analysis.
  - **The research policy is itself an experimental scientist:** `science.design` with questions such as "which
    mechanism improves invention on this family?" and experiments that are candidate studies with costs. Genesis
    then chooses its own next study by expected value per CPU, under the supervisor's budget. `autonomy/loop.py`
    and `studygen.py` already write preregistered study scripts.
  - Open-ended curriculum: the adversary (`autonomy/adversary.py`, POET-style) generates families at the edge of
    competence across domains: max-cut, MaxSAT, causal discovery, C4 or sum-free with Lean.
- **Study (the decisive experiment).** Three systems under identical total research budgets, on unfamiliar problem
  families, over several generations:
  - **A, fixed Genesis:** the best current inventor;
  - **B, recursive Genesis:** an inventor that improves its own search;
  - **C, organism Genesis:** a population with modular genomes, reusable discoveries, a learned allocation and
    evolvability selection.

  The measures:
  - how fast useful mechanisms are found;
  - whether they transfer;
  - whether later generations invent better;
  - whether gains persist after the training families are gone;
  - whether C's added cost pays.

  The claim "biological inspiration helps" is earned only if C beats A and B.

**What would convince a sceptic** (from the seven-engine proposal). On an unfamiliar family, Genesis:
1. diagnoses why established methods struggle;
2. invents a representation, concept or algorithm;
3. beats strong baselines on unseen instances;
4. transfers the discovery to another family;
5. modifies its own invention process;
6. shows that the modified process produces better discoveries in later generations.

Each step is verified and independently replicated. None of this has happened yet.

## 6. The queue (in order; each alone on CPU 0)

Studies run from a clean worktree of the branch head (`/home/claude/run_study.sh TAG SCRIPT OUTPUT`, one slice per
call; `CHECKOUT=1` at a study's first slice), so that new code can be committed while one runs.

| # | Batch | What | State |
|---|---|---|---|
| 1 | B20_R130 | Choice, instrument and interpretation separated | **done: CHOICE** (interpretation NO_DIFFERENCE at the preregistered measure) |
| 2 | B20_R133 | The Problem Compiler against the specialists | **done: BEHIND_SPECIALISTS_ON coloring, mis** (Max-2-SAT tie; executed reductions only) |
| 3 | B20_R131 | The cascade on a real case: R129's dormant acquisition rules reactivated by R130's interpretation (about 1 h) | **done: NO_VERIFIED_TRIGGER** (by protocol; no reactivation; comparators fresh 0.496, random 0.502, null 0.496, eig 0.450; archive 158.9 s CPU) |
| 4 | B20_R132 | The four bottlenecks of invention (headroom, expressiveness, search, evaluation) with planted positive and zero-signal controls, fresh truth sets T1/T2, the protected v2 against the candidate v3 at matched compute (about 5.7 h, slices) | preregistered `c0431f6` |
| 5 | B20_R128 | Improving the inventor (2–3 slices of 6,600 s) | preregistered; after R132; runs **as preregistered** (directive item 1); a v3 follow-up, if any, is a new study |
| 6 | — | Checkpoint (the last one is B20_R118) with the release matrix | owed |
| 7 | B20_R134 | The Difficulty Cartographer, redesigned with obstacles hidden from cheap statistics (Ω2) | to design |
| 8 | Ω3/Ω7 | The self-extending representation language (directive items 6–9; `docs/OMEGA_REPRESENTATION_LANGUAGE.md`): relations, verified gadgets, encodings with decoders, transformations to one BQP, families given only as predicates (reductions synthesised, not hand-written); stages A–C built on fixtures; its first study **B20_R135** (preregistered `7040a3c`, before R133 ran) after rows 1–5 | building; study preregistered |
| 8b | R1 | The research-object layer (`src/genesis/objects/`; `docs/OMEGA_RECURSIVE_INVENTION.md` §3, §16), then the graph sense language and B20_R136 (experiment A, the vertical slice) | building next on CPU 1 |
| 9 | Ω4–Ω9 | As in §5 | — |

## 7. Prior art to check every novelty claim against

- **Bayesian experimental design:**
  - Lindley 1956; Chaloner and Verdinelli 1995;
  - deep adaptive design (Foster et al. 2021);
  - for causal structure: Murphy 2001; Tong and Koller 2001; Hauser and Bühlmann 2014; Agrawal et al. 2019 (ABCD).
- **Causal discovery with hidden variables:**
  - FCI (Spirtes et al.);
  - LiNGAM with latents (Hoyer et al. 2008);
  - RCD (Maeda and Shimizu 2020).
- **Algorithm selection and instance spaces:**
  - Rice 1976; SATzilla (Xu et al. 2008);
  - instance space analysis (Smith-Miles et al. 2014);
  - fitness landscape analysis (Jones and Forrest 1995; Merz and Freisleben 2000).
- **Max-cut:**
  - breakout local search (Benlic and Hao 2013);
  - MACUT;
  - multiple operator heuristic (Ma and Hao 2017);
  - Houdayer cluster moves;
  - max-bisection memetic algorithm (Wu and Hao 2013).

  Record candidates must be checked against these and later tables.
- **Program synthesis and library learning:**
  - DreamCoder (Ellis et al. 2021);
  - FunSearch (Romera-Paredes et al. 2024);
  - AlphaEvolve (2025).
- **Quality diversity and open-endedness:**
  - MAP-Elites (Mouret and Clune 2015);
  - novelty search (Lehman and Stanley 2011);
  - POET (Wang et al. 2019);
  - OMNI (Zhang et al. 2023).
- **Evolvability:** Kirschner and Gerhart 1998; Wagner 2005.
- **Self-improving systems:**
  - Gödel machines (Schmidhuber 2003);
  - STOP (Zelikman et al. 2023);
  - the Darwin Gödel Machine (Zhang et al. 2025);
  - the AI Scientist (Lu et al. 2024).
- **Honest adaptive evaluation:**
  - the ladder (Blum and Hardt 2015);
  - the reusable holdout (Dwork et al. 2015);
  - Goodhart's law.

What would be new is not any one mechanism. It is that their combination raises improvement at each level on
problems no level has seen, and Genesis has not shown that yet.

## 8. Change log

- 24 Oct 2026: written, with B20_R129 preregistered (`eb60843`), merging Daniel's Ω proposals of that day.
- 24 Oct 2026, 14:20: Ω1's development looks (the interpretation is the limit; the established LLC estimator) and
  B20_R130 preregistered (`f812701`); the queue renumbered (B20_R131 co-invention, B20_R132 the Cartographer).
- 24 Oct 2026, 15:35: B20_R127's trace analysed (nothing could have been released); B20_R132 becomes the bottleneck
  scientist on invention, ahead of B20_R128; the Cartographer moves to B20_R134; the queue updated.
- 24 Oct 2026, 19:00: B20_R127 recorded (NOT_SHOWN); R129 reconciled; the research queue (`research_queue.json`) and the
  candidate judge v3 (research plane) committed; B20_R132 preregistered (`c0431f6`); the representation language's
  stage A built on fixtures.
- 24 Oct 2026, 19:45: B20_R130 recorded: CHOICE; the global interpretation not shown at the preregistered measure (it
  helps only from 6 experiments). B20_R133 running. B20_R131 will record NO_VERIFIED_TRIGGER by its protocol.
- 24 Oct 2026, 20:45: Daniel's architecture of 20:31 adopted (§0b; `docs/OMEGA_RECURSIVE_INVENTION.md`).
- 24 Oct 2026, 21:10: Daniel's directive of 20:45 adopted (§0c; `docs/OMEGA_ARCHITECTURE_INVENTION.md`): the
  Autonomous Research Architect; B20_R131 done (NO_VERIFIED_TRIGGER); B20_R132 running from 20:50.
