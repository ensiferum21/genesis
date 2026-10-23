# Recursive improvement: levels, measures and mechanisms from nature and physics (DRAFT architecture, 22 Oct 2026)

Daniel asked, on 22 Oct 2026, for a system that is extremely good at improving itself, at improving its improving
process, and at improving that. He also asked for many ways to represent and view things, and the ability to find
what it doesn't know it needs to know. This document turns that into levels with measures, mechanisms taken from
nature and physics, and a build order of preregistered batches.

One rule governs the whole document: **every level's improvement is measured on problems that level has never seen.
Nothing counts otherwise.** The evidence so far is the reason for the rule. The system's program search ties random
programs of its own language (B20_R80, R81), and its library adds nothing on the training hosts (B20_R84). Power has
to be earned and shown at each level; it cannot be assumed.

## 1. The levels and how each is measured

| Level | What it is | Exists today | Measured by (always on held-out problems) |
|---|---|---|---|
| L0, solvers | Programs that solve instances | `tfxw` (beats the 13 MaxSAT champions on DEV, B20_R97); the language programs | Anytime score; time-to-target at quantiles (Rønnow et al. 2014) on fresh instances |
| L1, improvers | Processes that produce solvers: program search over a language, configuration search, the discovery loop | B20_R78–R85, R89, R95; `docs/DISCOVERY_PLAN.md` | *Invention efficiency*: the quality of the best solver produced per CPU hour on a problem family the improver never saw (the area under its discovery curve) |
| L2, research policy | Decides what to study and build, designs and preregisters studies, chooses improvers and representations | The adaptation cell and research loop (B20_R93–R97: prospective checks 9/9 and 8/8) | *Research yield*: the gain in L1 invention efficiency per study, on held-out families; and *calibration*: how often its stated expectations come true |
| L3, policy revision | Changes L2's own rules: receptors, responses, cost model, priorities | Not built | L2's research yield after a revision against before it, on families held out from both |

**Nested hold-outs.** Each level keeps problem families the levels below it never see. L1 trains on family A and is
judged on B. L2 is judged on how L1 does on C, where neither L1's training nor L2's design saw C. L3 is judged on D.
Families come from different generators and from public benchmarks (Gset, `docs/OPEN_RECORDS_PLAN.md`), so "new"
means new structure, not just new seeds.

**The fixed point no level may touch** (the immune system's "self"):
- the checkers;
- witness custody;
- preregistration;
- sealed evaluation;
- the statistics.

A self-improving system that can edit its own judge improves the judge's opinion, not itself (Goodhart's law). Every
L2 or L3 change is itself preregistered and evaluated by the fixed layer. Invented concepts may guide search, but
may never prune solutions or certify results until proved.

## 2. Mechanisms from nature and physics, each tied to a level and a test

| Inspiration | Mechanism in Genesis | Level | The test that would show it works |
|---|---|---|---|
| **Renormalization and coarse-graining.** A gas is described by temperature and pressure, not by its molecules | Coarse views: contract groups of vertices that behave alike (communities, planted clusters, frustrated plaquettes) into super-vertices, solve the coarse problem, lift, refine. The system must discover which details to compress: a coarse view is kept only if it predicts which fine moves succeed (the discovery plan's recognizers) | L1 | On held-out families, coarse-then-refine reaches a target sooner than the best single-scale view at equal CPU. Every view is removed in turn to see what it contributes |
| **Dual descriptions** (wave and particle; primal and dual) | Many views of one problem, each with encode, decode and moves: the edge set; vertex labels (the cut, `cross_2`); the triangle hypergraph's independent sets (MaxSAT); continuous relaxations (spectral, dSB dynamics); coarse views. Solutions pass between views (project and lift), and a selector learns which view to start from, using instance features | L1 | Per-instance view selection beats the best fixed view on held-out families. Passing solutions between views beats running the views separately |
| **Symmetry and conservation** (Noether) | Search for invariants of good solutions (degree classes, automorphism orbits, quantities that improving moves conserve). Use them to propose moves along symmetry orbits, and to canonicalize only when the symmetry is proved (soundness licensing, B18) | L1 | The rate of improving moves along proposed orbits beats random moves of the same size; no pruning without a proof |
| **Evolution and evo-devo** (evolvability, gene duplication) | The operators and the language evolve, not only programs. Lineages are selected by their *rate of improvement* (evolvability), not by today's fitness. Library entries are duplicated and then diverge (B20_R82's library is the start) | L1→L2 | Operator-evolving search reaches a higher invention efficiency than fixed operators on held-out families, with the cost of evolving the operators counted |
| **Ecology and open-endedness** (quality-diversity: MAP-Elites; POET's co-evolution of problems and solvers) | An archive of diverse solvers indexed by behaviour: which instance features each one wins on. The system generates problem variants at the edge of its competence, following learning progress, to keep stepping stones | L2 | On held-out families, solvers drawn from the archive beat a single-objective search, and generated curricula raise L1's invention efficiency over a fixed training family |
| **Predictive coding and curiosity** (prediction error drives learning; Oudeyer's learning progress; Bayesian experimental design) | A *knowledge map*: for every (method, instance region) cell, a predictive model of the outcome with its uncertainty, fitted on all recorded evidence. The next experiment is chosen by expected information gain on decisions that matter. A large prediction error (surprise) raises a caveat and triggers hypotheses. **This is "finding what it doesn't know it needs to know":** the map shows where its knowledge is thin, and surprises show where it is wrong | L2 | Prospective accuracy of the map on the next studies beats a naive baseline. Choosing experiments by information gain reaches the same decisions in fewer studies (checked first by replaying the recorded history, then prospectively) |
| **The immune system** (diversity, clonal selection, memory, telling self from non-self) | Anomaly detection over the system's own results: an outcome that contradicts the knowledge map, a tuned solver collapsing (B20_R97 → B20_R98), a pin that does not reproduce. Each triggers an automatic harness check. Past defects are kept as memory, the defect library | L2/L3 | The share of real defects caught before a result is recorded, against the historical record of defects found late |
| **Thermodynamics and annealing** | A research temperature: exploration across research directions falls with confident progress and rises on stagnation (re-heating). Several agendas run at different risk levels and swap, as in parallel tempering | L2 | Over replayed history and then prospectively, research yield per CPU against a fixed-schedule policy |
| **Homeostasis and the cell** | The adaptation cell's receptors and responses (B20_R93) gain *receptor calibration*: each receptor's threshold is tuned by its historical precision (did the caveat it raised turn out to be real?) | L3 | L2's research yield with calibrated receptors against fixed ones, on held-out families |
| **The scientific community** (competing hypotheses, adversarial review, replication) | Every L2 proposal carries at least two competing hypotheses and the experiment that separates them. A reviewer agent that has not seen the design attacks it before preregistration. Replication by a second operator (GV7) | L2/L3 | The share of preregistered expectations that come true (calibration). The share of review findings that were real |

**Prior art, stated plainly.** Each mechanism is known on its own:
- DreamCoder;
- CEGAR;
- option discovery;
- multilevel graph methods;
- MAP-Elites;
- POET;
- learning progress;
- Bayesian experimental design;
- evolvability;
- FunSearch and AlphaEvolve.

What would be new, and must be shown, is that combining them raises improvement *at each level* on problems no level
has seen.

## 3. Build order (each item a preregistered batch; runs one at a time, alone)

1. **The queue now:**
   - B20_R85, generation 3;
   - B20_R98, the harness check of two collapsing solvers;
   - B20_R86, do the generations compound;
   - B20_R99, is there structure left where the searches stop;
   - B20_R100, the knowledge map's first prospective test: its predictions for B20_R86, committed before B20_R86 runs;
   - B20_R101, the Gset max-cut domain with Daniel's files: 54 instances checked, best-known values with sources.
2. **The feedback contract and the zero-signal battery (B20_R103; Daniel's research alert of 22 Oct 2026,
   `docs/RESEARCH_ALERTS.md`).** Before any level is allowed to improve itself on repeated feedback, it is shown not
   to mistake noise for progress. The contract has a fixed threshold, gives restricted feedback, uses confirmation
   evaluations and a stopping rule, and keeps final numbers on held-out hosts only. It is tested by searches and study
   analyses on problems with no signal, which must stop, and with a planted signal, which must still be found.
   **Done (B20_R103):** with no signal the contract stops and its final numbers are unbiased, where the open
   protocol over-reports by up to 6.6 sigma_e; it misses real effects below one confirmation's noise (TOO_STRICT); the
   headline reads CONTRACT_LEAKS by a ratio rule mis-specified for a negative reference (one false release in 180).
   **2a. The solver track on a public benchmark (B20_R104-R106; Daniel, 23 Oct 2026: "adapt them and make the solver
   more strong").** Three of the mechanisms above, applied to Genesis's own max-cut engine `mcx-v1`:
   - renormalisation: a restart that contracts every edge all elite solutions orient alike, searches the contracted
     problem and projects back;
   - order parameters choosing the method: two statistics of the degree sequence place a graph in a class, one
     configuration per class;
   - germinal-centre selection (clonal selection): successive halving of configurations, each round on fresh graphs.
   Configured on graphs generated as Gset's were (B20_R105), then judged once on Gset against the published
   heuristics' recorded runs (B20_R106). The engine's parts are published methods combined by the builder; what the
   system contributes, and is measured on, is the configuration and the class choice.
   **B20_R105:** the class choice was exact (24/24) and germinal-centre selection beat the published method's
   setting at 1 s (tied at 10 s); of the physics moves only the cluster exchange was selected (planar graphs).
   **B20_R106:** on Gset, once, the configured engine leads every pinned published tool and their virtual best at
   both budgets (MCX_LEADS); the system's configuration adds to BLS's setting there, but not significantly.
3. **The knowledge map (L2), beyond B20_R100.** Widen it from the eight time-to-solution and equal-time studies to
   every recorded row. Replay the history: would choosing studies by information gain have reached the recorded
   decisions sooner? Then let it choose experiments, with its predictions written before each study.
4. **The view portfolio (L1).** Five views of the triangle-free problem and max cut, with project and lift between
   them. Per-instance view selection, judged on held-out families (G(n, 0.5) against planted, Gset toroidal against
   random).
5. **The discovery loop (L1)**, if B20_R99 finds structured headroom: invented concepts become new statements of the
   language. Otherwise, coarse-graining views as the first invented representations.
6. **Evolvability-selected search (L1→L2):** operators and language evolve, and lineages are selected by their
   improvement rate on held-out families.
7. **Open-ended curricula (L2):** generate problem variants at the edge of competence, keep a quality-diversity
   archive of solvers.
8. **Receptor calibration and policy revision (L3):** judged by L2's research yield on families held out from all
   levels below.
9. **A causal-discovery checkpoint** (research alert item 2): multi-environment linear systems
   with planted hidden confounders, Genesis against LinADMG and established baselines, scored on edge recovery and
   on proposing the measurement or intervention that resolves a confounder.
10. **With Daniel's resources:**
   - a code model as an operator and representation proposer inside the sandbox, with the fixed layer judging (needs
     API access from the run machine);
   - a many-core persistent machine, so that the levels' studies run in parallel.

## 4. What would make the whole claim true, and what would end it

- **True:** at least L1 and L2 each show a preregistered gain on held-out families, with ablations attributing the
  gain to the mechanism, and the gain survives replication by a second operator.
- **Partial:** gains at L1 only (a better improver, not a better research process).
- **Ends a mechanism:** no gain on held-out families in its preregistered test plus one powered retry. It is then
  recorded as a negative result and removed from the build order.
