# The Frontier: divergence and convergence, without handholding (adopted 27 Oct 2026, 20:00 SGT)

**Read this if you are the next agent picking up the Frontier line.** It holds the directive, the reasoning that
chose the approach, the protocol that makes "without handholding" testable, the full design of the engine and its
first domain, the sealed calibration set with its sources, the batches with their acceptance tests, the handoff
state, and what does not count. Nothing here is built yet unless a section says BUILT. Nothing here is a result.

**State (27 Oct 2026, 21:15 SGT):** F1 built (B20_R160); F2 started (§6 done, exact certificates); B20_R151 running.

Contents: §0 the directive · §1 reading · §2 branching and converging over approaches (why this approach) · §3 the
No-Handholding Protocol · §4 the engine (F1) · §5 the first domain: graph conjectures (F2) · §6 the sealed
calibration set · §7 batches and acceptance tests · §8 how it plugs into what exists · §9 risks · §10 what does not
count · §11 prior art · §12 handoff state.

## 0. The directive (Daniel, 27 Oct 2026, 19:55 SGT, verbatim)

> Genesis-Ω is an autonomous, open-ended scientific intelligence that continuously discovers and transcends the
> limits of its own understanding. It invents new mathematical structures, concepts, representations, questions,
> experiments, and research methods—including methods for improving its own intelligence.
>
> Through independent verification, causal experimentation, cumulative learning, and cross-domain synthesis, it
> transforms discoveries, failures, and unexplored possibilities into new capabilities. It autonomously constructs
> the conditions that make previously inaccessible discoveries possible, recursively improves its own discovery
> processes, and expands the frontier of what can be conceived, investigated, understood, and proven.
>
> Its ultimate objective is sustained, verifiable growth in its capacity to generate new knowledge and unlock
> further discoveries, without requiring humans to specify each problem, concept, or method in advance.
>
> Work it out towards this
> Use never before used and imagine mutate find super powerful extrapolate and branch out and see convergence and do
> the best approach
> Adapt and make sure our system can do it without handholding or teaching

Then (20:01 SGT): "Push the idea to the branch in detail pls so next agent can pick up". This file is that.

Then (20:12 SGT), on the open items of §6: "Do them and continue". They are done (§6).

Then (20:22 SGT), **the test that proves out the system**, adopted as §7b:

> Remember that : Give Genesis an unfamiliar mathematical problem family where its existing representation is
> inadequate. Without specifying the missing concept, require it to: 1. Discover a useful new representation.
> 2. Establish a nontrivial mathematical consequence. 3. Extract the procedure that enabled the discovery. 4. Use
> that procedure to discover something independently useful in another mathematical family. 5. Demonstrate that
> the improved inventor outperforms its predecessor under matched total compute. This test to be done to prove out
> system

It does not replace the direction of 27 Oct, 14:33 (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`). B20_R151, B20_R152 and
B20_R141 keep CPU 0 in the order set there. The Frontier is built on CPU 1 meanwhile, and its studies queue after
them (§7, §12).

## 1. Reading

The message asks for two things.
1. **A way of working:** imagine directions, including ones never tried; mutate and recombine them; extrapolate where
   each is heading; branch out from what works; see where independent branches converge; put the effort behind the
   best.
2. **Genesis must work that way itself, without handholding or teaching.** The builder supplies verifiers, primitives,
   compute and the sealed judge. The builder does not choose the problem, the method or the mechanism, and gives no
   worked examples or curated curriculum.

Read against the vision, that is a **divergent–convergent research engine** that runs over every kind of research
object Genesis has. It needs a domain where its discoveries can be verified exactly and where headroom does not
run out. Its claims about itself need a protocol that a test can check (§3).

The builder applied the way of working to the choice of approach as well (§2). The engine of §4 makes the same
process Genesis's.

## 2. Branching and converging over approaches (why this approach)

### 2.1 The branches

Eight candidate directions toward the vision. For each: what the studies so far say about it, and what the evidence
suggests it could reach.

| # | Branch | Evidence so far | Extrapolated reach |
|---|---|---|---|
| B1 | Keep enriching the max-cut engine language (the 14:33 line: X1–X3, B20_R151, B20_R152, B20_R155) | B20_R151's gate: only planar2000 of three classes has 1 s headroom above 0.2% (0.572%). B20_R132: nothing confirmed better than REX on fresh graphs; the protected judge is blind below about 1% | At most about 0.5% on one class, near a mature solver's optimum. Little new knowledge even if it works |
| B2 | An allocator that extrapolates each direction's discovery curve instead of ranking current values | B20_R148: the portfolio was ahead early on the curve and behind at the full budget. Successive halving cuts slow starters | Compute efficiency across all lines; a direct repair of a measured failure |
| B3 | Convergence (consilience) as an internal signal of what is real | X2 (B20_R154): search luck twice passed for a language effect, and replicate agreement is what caught it. B20_R132: the judge cannot see gains under about 1% | Fewer false leads before the judge is spent; a general version of the replicate test |
| B4 | Novelty-driven imagination of never-tried directions | B20_R148: five different processes were each best on some task; no fixed choice wins | Coverage of approach space; finds what a fixed portfolio cannot |
| B5 | Genesis poses its own problems, chosen by learning progress (an open-ended curriculum) | Every study so far was posed by the builder. B20_R135: Genesis synthesised reductions for families given only as predicates | The directive's "without requiring humans to specify each problem" |
| B6 | A domain with exact verification and unbounded headroom: mathematical conjecture and construction | Genesis's positives come where verification is exact and the signal is large: B20_R135 (representations), B20_R129 and B20_R130 (experiment choice) | Real, checkable new knowledge (a refuted open conjecture is a theorem about a counterexample) |
| B7 | Meta-evolution of the inventor process (the B20_R128 line) | B20_R128: NOT_SHOWN; no inner search released anything, so level 2 had no level-1 signal to select on | Blocked until a lower level produces a dense signal |
| B8 | Cross-domain transfer through the vault (the B20_R131 line) | B20_R131: NO_VERIFIED_TRIGGER | Needs capabilities worth transferring first |

### 2.2 Convergence

Independent lines of evidence point the same way.
- **The failures share one root cause: the signal is below the noise where Genesis has been aimed.**
  - B20_R127 and B20_R132: engine gains near a mature solver's optimum are too small to see.
  - B20_R128: the meta-level had nothing to select on.
  - B20_R148: the allocator ranked noisy early values.
  - B20_R131: the capability that was to trigger reactivation was not itself verified (B20_R130's global
    interpretation did not beat the per-pair one), so nothing was reactivated.
- **The successes share the opposite condition: exact verification and a large signal.**
  - B20_R135: invented encodings, checked exactly.
  - B20_R129 and B20_R130: experiment choice scored against a planted truth.

B2, B3, B4 and B5 are not separate projects. They are four parts of one engine: directions, extrapolated curves,
convergence, novelty and learning progress. B6 is where that engine's signal is strong, and B7 and B8 become usable
once a level below produces a dense signal. B1 stays as one domain the engine can allocate to, and the 14:33 line is
unchanged.

### 2.3 The choice

The choice is **the Frontier**:
- the engine (F1, §4);
- a first domain with exact verification and open headroom: graph-theory conjectures and constructions (F2, §5);
- a sealed external calibration that Genesis is never told about (§6);
- then open-ended generations in which Genesis poses its own conjectures (F5).

The 14:33 line's mechanism (library learning, a sealed judge, consolidation) is reused there on graph constructions.

**What would change this choice.** If F3 shows that the engine's allocation does not beat successive halving and
uniform allocation on planted worlds, the engine's design is wrong and is repaired before any real study. If F4
shows that a single prior-art method (NRPA, GBFS) does as well as the engine at matched compute on every sealed
bound, the engine adds nothing in this domain, and that is reported.

## 3. The No-Handholding Protocol (NHP)

The protocol makes "without handholding or teaching" a property that tests check. It applies to every Frontier study.

**3.1 What the builder may provide.** Each item is listed in the study's manifest with its digest, and labelled as the
builder's in every record:
- the verifiers (kernel side);
- primitive objects and primitive invariants, all prior art (§5.2);
- a generic library of methods, all prior art (§5.4);
- budgets;
- the kernel judge;
- sealed sets, whose keys only the kernel reads.

**3.2 What the builder may not do:**
- choose problems for Genesis in an open-ended study;
- give per-problem hints, representations, parameters or starting points;
- give curated curricula, worked examples or solutions;
- let any research-plane code read sealed statuses;
- tune anything on sealed data;
- edit Genesis's outputs, except to record them.

**3.3 The mechanics, each a test:**
- The research plane receives its inputs only through one `Manifest` object, whose digest is recorded.
- Boundary tests, as `test_expressive_boundary` does:
  - research-plane modules import no kernel-side module;
  - they never reach private attributes;
  - they never call getattr, vars, eval or exec on judge objects;
  - a planted reach is detected.
- **The relabelling audit.** Given the same seed, the engine's decisions are identical when the sealed set's ids are
  renamed and its order shuffled. So nothing about a problem's sealed status can leak through its id or its
  position.
- **The teaching ban.** Every datum the research plane learns from is generated by Genesis (its own enumerations,
  constructions and searches) or is a public problem statement. The engine logs the source of each dataset.

**3.4 What counts as Genesis's.** These are Genesis's:
- which problems it poses;
- which directions it imagines and runs;
- how it allocates;
- which constructions and concepts it abstracts and admits;
- every certificate it finds.

The primitives, the method library, the construction language's base operations and the engine's own code are the
builder's. They are never reported as Genesis's invention. This is the same rule as the construct algebra
(`docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §4).

## 4. The engine (F1): `src/genesis/frontier/`

It is domain independent. The research plane holds the engine; the kernel side holds verifiers, planted worlds and
sealed sets. It is LLM-free.

### 4.1 Objects
- **Problem.** An opaque id with a public statement and a verifier held by the kernel. A problem may be posed by
  Genesis (F5) or by a sealed set (F4).
- **Approach.** A typed research object `{representation, method, params}` drawn from the domain's grammar
  (`domain.approaches(problem)` returns the representations, methods and parameter spaces).
- **Direction.** `{id, problem, approach, parent, op, generation}`, where `op` is one of `imagine`, `mutate`,
  `recombine`, `branch_out` or `seed`. Its `descriptor` is `(problem, representation, method, bucketed params)`. It is
  used for novelty, and for deciding whether two branches are independent.
- **Branch.** One execution of a direction with a seed. It has a discovery curve: points `(t, y)`, where t is compute
  in the domain's unit and y is the best internal score so far, monotone. It also has its artifacts, each with a
  `fingerprint` (exact identity, such as a canonical-form hash) and a `signature` (coarse structure, such as a rounded
  invariant vector).
- **Discovery.** An artifact the kernel verifier accepted: a certificate. Only discoveries count.

### 4.2 Divergent operators (`direction.py`)
- **`imagine(grammar, problem, rng, archive, k)`.** Draw k approaches uniformly from the grammar and keep the most
  novel: the largest minimum distance to the archive's descriptors.
  - The distance is Hamming on the categorical parts plus normalised L1 on the parameters.
  - **"Never before used" is operational:** a descriptor not in the archive (novelty above 0).
  - Novelty search: Lehman and Stanley 2011.
- **`mutate(direction, grammar, rng)`.** Change one component: the representation, the method, one parameter, or the
  problem, moving to a neighbouring problem from `domain.neighbours`.
- **`recombine(a, b, rng)`.** Take components from two directions, for example a's representation with b's method. A
  planted "recombination vein" (§4.7) tests that this is ever worth doing.
- **`branch_out(direction, result, domain)`.** Ask the domain for the problems a result suggests (`domain.successors`).
  Examples:
  - a refuted conjecture spawns refined ones (TxGraffiti's TicTac and Red Burton rules);
  - a surviving conjecture spawns stronger ones;
  - a construction that works at n spawns the same problem at larger n. This is the problem-side "extrapolate".

### 4.3 Extrapolation (`curves.py`)

Forecast where a branch will be at a horizon H, with honest uncertainty, so that slow starters are not cut (the
B20_R148 failure).

**Families,** each linear in (a, b) once its shape parameter is fixed:

| Family | Form | Shape parameter |
|---|---|---|
| pow | y = a − b(t + t0)^(−c) | c on a grid in [0.1, 3] |
| exp | y = a − b·e^(−t/τ) | τ on a log grid relative to t_max |
| log | y = a + b·log(1 + t/t0) | none; unbounded, capped by the domain's ceiling if it has one |
| flat | y = a | none |

**Fitting.**
- For each family and each grid value: least squares for (a, b), with b ≥ 0.
- Score by AICc, and average the families by Akaike weights. This is a light version of Domhan, Springenberg and
  Hutter 2015, who averaged 11 families by MCMC.

**Uncertainty.**
- A residual block bootstrap, B = 200, refits each sample.
- Output: `forecast(H) → {lo, mid, hi}` at the 5%, 50% and 95% quantiles.

**Calibration (an F1 acceptance test).** On held-out synthetic curves of every planted type, the empirical coverage of
the 90% interval at H lies in [0.80, 0.97]. Coverage is reported per family.

**For refutation problems** (y is minus the slack), it reports P(y crosses 0 by H) from the bootstrap.

### 4.4 Convergence (`converge.py`)
- **Clusters.** Artifacts are clustered by fingerprint (exact), and separately by signature (structural).
- **Consilience of a cluster.** The number of independent branches that reached it. Branches are independent when
  their descriptors differ in representation or method and their seeds differ.
- **Three uses:**
  1. *Credibility* (noisy domains): the allocator gives a bonus to directions whose artifacts lie in clusters reached
     by two or more independent branches.
  2. *Structure* (exact domains): a cluster reached independently is an attractor. `domain.abstract(cluster)` proposes
     a concept from it, such as a named construction learned from the cluster's constructions by X2's library learner
     (§8). That is how discoveries become capabilities.
  3. *Divergence alarm:* if no cluster forms after a set fraction of the budget, the exploration share rises (§4.5).
- **Prior art:**
  - AlphaCode clustered sampled programs by behaviour to choose submissions (Li et al. 2022);
  - observational equivalence in enumerative synthesis (Udupa et al. 2013; Albarghouthi et al. 2013);
  - consilience (Whewell 1840).

### 4.5 Allocation (`allocate.py`)

The index of branch b:

  I_b = (hi_b(H_b) − y*) / cost_b + λ_lp·LP_b + λ_nov·novelty_b·[b young] + λ_con·consilience_b

where:
- **hi_b(H_b)** is the 95% forecast at the horizon b would reach with its fair share of the remaining budget;
- **y*** is the incumbent's verified value;
- **LP_b** is learning progress: the slope of the curve over its last window (Oudeyer, Kaplan and Hafner 2007);
- **cost_b** is the compute per step.

The rules:
- **Pausing.** A branch is paused when its hi is below the incumbent's lo: dominated with confidence. It is kept
  dormant, not deleted, and reactivated when a new capability changes its approach (§8, the vault's cascade).
- **Reserved exploration.** A share ε of compute goes to new directions from the four operators.
  - ε adapts: it rises when the incumbent has not improved for a window, or the divergence alarm fires, and falls
    while progress is steady.
  - Its floor is 10%, the plan's metabolism rule.
- **Comparators** (F3), all from `autonomy/portfolio.py`:
  - uniform allocation;
  - successive halving across directions (G2);
  - UCB1 on current values (the portfolio's bandit);
  - random.

### 4.6 The cycle (`engine.py`)

`Frontier(manifest, budget, seed, params, state_path).run()` is resumable, and every decision is logged so that a
study can replay it. One step:
1. **Allocate:** choose to advance a branch, or to open a new direction.
2. **Step:** `domain.step(branch, quantum)` returns new curve points and artifacts. Methods are the portfolio's
   pausable generator harnesses, so stepping means pulling the next quantum of evaluations.
3. **Verify:** artifacts the domain's own cheap check marks as candidates go to the kernel verifier through the
   manifest's `verify` callback. The engine never sees the verifier's internals. Submissions are budgeted and
   counted.
4. **Record:** each discovery with its certificate and lineage.
5. **Consolidate:** write to the vault (§8).
6. **Converge:** update the clusters; abstract concepts from attractors (§4.4).
7. **Spawn:** open new directions with the operators of §4.2.
8. Repeat until the budget is spent.

### 4.7 The planted world (`frontier/world.py`, kernel side; F3's calibration domain, as the Limitation Zoo is ARA's)

`PlantedWorld(seed, problems, null=False)`. Each (problem, approach) pair has a hidden curve
y(t) = C·(1 − exp(−(t/τ)^κ)), plus observation noise σ. The planted types:

| Type | Its hidden curve |
|---|---|
| vein | High ceiling C, moderate τ |
| slow starter | High C, large τ, κ > 1: sigmoidal, flat early (the B20_R148 trap seen from the other side) |
| decoy | Fast rise (small τ), low C: early high, then a plateau |
| dead end | C ≈ 0 |
| recombination vein | High C only for one (representation, method) pair whose parts are mediocre alone |

The world also has:
- **Attractors.** Each problem has hidden true clusters. Branches with C > 0 emit artifacts from a true cluster with
  a probability that rises with progress, and spurious ones at a low rate.
- **Successors.** Some problems unlock harder successor problems with higher ceilings, so branching out can pay.
- **A null world.** Every ceiling is 0. The engine must report no discoveries: the kernel's verified value is 0.

The kernel computes each artifact's true value and the oracle's best value at the budget, from which regret is
measured.

### 4.8 Adapting the engine itself (`meta.py`)

The engine's parameters form a research-object space of their own: λ_lp, λ_nov, λ_con, the ε schedule, the family
set, the quantum, k and the pause margin.
- A meta-direction is an engine configuration.
- A meta-task is a sealed planted world drawn by the kernel from held-out families.
- The same Frontier runs over meta-directions, under one fuel budget (`autonomy/process.py`).
- A new configuration is promoted only by the kernel on held-out worlds, at matched total compute with the
  meta-search counted. This is the directive's "recursively improves its own discovery processes", bounded.

**The machinery is built** (28 Oct 2026, 00:43 SGT; `frontier/meta.py`, tests in
`tests_genesis/test_frontier_meta.py`). The meta level is the same engine; no second one was written.
- `MetaDomain` is a domain whose problems are meta-tasks. A study poses each as a factory that returns a fresh inner
  manifest: a domain and its kernel verifier.
- Its approaches are configurations:
  - representation: the inner allocation policy;
  - method: `run`;
  - params: a grid over ε, λ_lp, λ_con, k_imagine, patience and stall, with the current defaults on the grid.
- A step runs an inner Frontier `quantum` inner compute units further. The curve point is its total verified value
  per problem.
- The meta verifier is the study's. It answers from the kernel's own record of what the inner verifier confirmed
  for that run.
- `inner_compute()` is the meta-search's true compute. A study charges it to any configuration it promotes.
- Tested on planted worlds:
  - the kernel record confirms every best score;
  - two runs from one seed are identical;
  - a meta-search saved and resumed ends where an uninterrupted one does, with inner runs replayed;
  - a forged artifact gets 0.
- Not yet: the study (sealed meta-worlds, promotion against the defaults on held-out worlds at matched total
  compute). It belongs after F3, which calibrates the engine on planted worlds.

## 5. The first domain (F2): graph conjectures and constructions (`src/genesis/conjecture/`)

### 5.1 Why this domain
- **Verification is exact.** A counterexample is a finite object with an exact certificate (§5.5).
- **Headroom is open.** New conjectures can always be posed. A refuted open conjecture is new, checkable knowledge.
- **Strong, LLM-free prior art exists to measure against** (§11): TxGraffiti, AutoGraphiX, Wagner 2021, Ghebleh et al.
  2024, Roucairol and Cazenave 2025, Duhamel and Cazenave 2026.
- **A sealed external calibration exists with known answers** (§6).
- **It exercises every clause of the directive:**
  - questions (conjectures);
  - structures and concepts (named constructions and invariant expressions);
  - representations (encodings of graphs for search);
  - experiments (attacks);
  - research methods (allocation, and the engine's own adaptation);
  - cumulative learning (the vault);
  - "the conditions that make previously inaccessible discoveries possible": the large counterexamples of 2026 need
    structured constructions that bit-string search cannot reach.

### 5.2 Primitives (the builder's, prior art, labelled)
- **Graphs.** Simple undirected graphs:
  - adjacency as Python-int bitsets for n ≤ 64 in search;
  - edge lists for larger constructions;
  - graph6 for records.
- **Fingerprints.**
  - Weisfeiler–Leman hashes for clustering;
  - exact identity checked with `networkx.is_isomorphic` within equal-hash buckets.
- **Invariants.** n, m, the degrees, d_v and m_v (the average degree of v's neighbours), Δ, δ, diameter, radius,
  girth, triangles, matching number, independence and clique numbers, domination number, the Randić and Wiener
  indices, and the spectra of the adjacency, Laplacian, signless Laplacian and distance matrices.
  - Exact algorithms where n is small (matching by Edmonds; independence by branch and bound).
  - Floating point for search only.
  - Exact arithmetic for verification (§5.5).

### 5.3 The construction language Γ (`construct.py`)

**Base graphs:** P_k, C_k, K_k, S_k, K_{a,b}, the empty graph E_k.

**Operations:** disjoint union, join, cartesian product, corona, attaching a pendant path at a vertex, subdivision,
complement, line graph, adding or removing an edge.

**Not in Γ: equitable partitions, quotients, blow-ups or any symmetry operation** (changed at 20:30 SGT, for the
proving test of §7b).
- The 2026 counterexamples (20 to 352 vertices) are realisations of equitable partitions. The realisability
  conditions are Damnjanović, Ha and Stevanović 2026, Lemma 2.3:
  - b_ii ≤ n_i − 1, and b_ii or n_i is even;
  - n_i·b_ij = n_j·b_ji, with b_ij ≤ n_j.
- Putting that operation in Γ would hand Genesis the missing concept, which the proving test forbids.
- It exists **only on the kernel side**, in two places:
  - in `verify.py`'s tests, to rebuild published counterexamples;
  - as the proving test's hidden reference.
- Representation (5) of §5.4 is removed from Genesis's starting set for the same reason.

**Who owns what.**
- Γ's base operations are the builder's.
- Named constructions that Genesis abstracts from converged counterexamples, through X2's library learner over Γ
  programs, are Genesis's.
- They compound: a construction of generation 2 can call one of generation 1. This is the 14:33 direction's
  mechanism in a domain with a large signal.

### 5.4 Attacks (`attack.py`)

**The objective.** For a conjecture LHS ≤ RHS, slack(G) = RHS(G) − LHS(G), minimised. A refutation is an exact
certificate that slack < 0.

**Representations:**
1. the edge bit-string on n vertices;
2. Prüfer codes (trees);
3. bounded-degree graphs (Ghebleh's subquartic class);
4. Γ programs;
5. ~~equitable-partition parameters~~: removed from Genesis's starting set; kernel side only (§5.3, §7b). Any
   representation of that kind must be invented by Genesis.

**Methods** (all prior art; re-implemented LLM-free as pausable generators, the `autonomy/portfolio.py` harness
interface):
- the portfolio's six harnesses;
- NMCS and NRPA (Cazenave 2009; Rosin 2011);
- greedy best-first search;
- the deep cross-entropy method (Wagner 2021: a small MLP trained from scratch, which is not a language model);
- exhaustive enumeration for small n.

### 5.5 Exact verification (`verify.py`, kernel side)

A refutation certificate for "μ(G) ≤ max f(...)" is a pair (G, x) with x a rational vector. The kernel checks it in
exact rational arithmetic.

**Lower side.** The Rayleigh quotient q = xᵀLx / xᵀx is computed exactly in `fractions.Fraction`. Since L is real
symmetric, q ≤ μ(G) (Rayleigh–Ritz). So q is a proven lower bound on μ, at O(m) cost, for any n. The 352-vertex
graphs of 2026 are cheap. x comes from the float eigenvector, rounded.

**Upper side.** The right-hand side is evaluated in rational interval arithmetic.
- d_v is an integer and m_v is an exact rational.
- √ and fourth roots are enclosed by integer square roots at a precision of 2^-64, refined on demand.
- The maximum of the upper ends bounds the right-hand side from above.

**The verdict.**
- REFUTED with the certificate's digest if q is greater than the upper end.
- Otherwise NOT_CERTIFIED: the search may retry with a better x.

There are no floating-point verdicts. Duhamel and Cazenave count a refutation when a float difference exceeds
0.001; that does not count here (§10).

**Optional cross-check for small n:** the exact characteristic polynomial (Berkowitz's division-free algorithm over
the integers) and Sturm sequences give μ's isolating interval.

**Which way the certificate points.** The Rayleigh quotient only bounds a spectral radius from below. That suffices
for refuting an upper bound on it, which is every bound in §6. A conjecture that bounds a spectral radius from
below, such as Aouchiche–Hansen's λ₁ + matching number ≥ √(n − 1) + 1 (Wagner's rebuild test), needs an upper
certificate instead. Two exact options:
- **Collatz–Wielandt:** for a nonnegative irreducible matrix A and a positive rational vector x, λ₁ ≤ max_i (Ax)_i / x_i.
- **Sturm:** for small n, a Sturm sequence on the exact characteristic polynomial.

Integer invariants (the matching number, α, the diameter) are recomputed exactly by the kernel. `verify.py` dispatches
on the direction of each term.

### 5.6 Genesis's own conjectures (`generate.py`; F5)
- **The data:** Genesis's own enumerations (every graph up to 7 or 8 vertices, generated, not taken from a curated
  list) and samples of Γ programs. The teaching ban applies (§3.3).
- **Linear and power bounds,** as TxGraffiti does:
  - fit target ≤ a·f + b by linear programming (`scipy.optimize.linprog`) for each pair of invariants and each
    property;
  - keep fits with a positive touch number;
  - apply a static Dalmatian filter (new sharpness sets only).
- **Bounds of the Brankov–Hansen–Stevanović form,** μ ≤ max_v f(d_v, m_v) and max_{uv} f(...):
  - f is drawn from an expression grammar over the local invariants, with +, −, ×, ÷, √ and powers up to 4, at
    bounded depth;
  - a bound is kept if it holds on all of Genesis's data and no kept bound dominates it.
- **Pepper's rule:** a conjecture is assumed false until an attack at the full budget fails.
- **Rediscoveries:** the kernel's sealed database (§6, plus classical theorems) labels a conjecture that is a known
  result. It is reported as a rediscovery, never as new.

## 6. The sealed calibration set (kernel side: `conjecture/sealed.py`, F2)

**The source family.** Brankov, Hansen and Stevanović, "Automated conjectures on upper bounds for the largest
Laplacian eigenvalue of graphs", *Linear Algebra and its Applications* 414 (2006) 407–424 (GERAD G-2005-20).
- It gives **68 candidate upper bounds on μ, the Laplacian spectral radius.**
- Bounds 1–32 are vertex bounds, μ ≤ max_v f(d_v, m_v).
- Bounds 33–68 are edge bounds, μ ≤ max_{ij∈E} f(d_i, m_i, d_j, m_j).
- d is a degree; m is the average degree of the neighbours.

**Status as of June 2026,** from Damnjanović, Ha and Stevanović, arXiv 2606.14550 (12 Jun 2026), "Upper bounds for
the Laplacian spectral radius: Proofs and counterexamples":

| Status | Bounds | Count | Source |
|---|---|---|---|
| Refuted, 2024 | 2, 3, 15, 17, 28, 29, 31, 32, 36, 41, 43, 49–55, 57–68 | 30 | Ghebleh, Al-Yakoob, Kanso, Stevanović, arXiv 2403.18429 (reinforcement learning at n ≈ 20; exhaustive search of subquartic graphs, n ≤ 14, mostly 12) |
| Refuted, 2025 | 45, 48 | 2 | Taieb, Roucairol, Cazenave, Harutyunyan, *LION 2025*, LNCS 15744 (2026) 52–63, doi 10.1007/978-3-032-09156-7_4 (Monte Carlo search; cited as [23] in arXiv 2606.14550). They report P₃ as a counterexample to 48, 57 and 61, and 14 vertices for 45 |
| Refuted, 2026 | 11, 13, 18, 19, 20, 21, 22, 24, 30, 40, 47, 56 | 12 | arXiv 2606.14550. Equitable-partition constructions on 20 to 352 vertices: 19 and 20 on 20 vertices; 11 on 29; 22 on 30; 56 on 36; 13 on 46; 47 on 59; 18 on 158; 21 and 24 on 164; 30 on 253; 40 on 352 (not necessarily the smallest counterexamples) |
| Proved, 2026 | 1, 4–10, 12, 14, 16, 23, 25–27, 33–35, 37–39, 42 | 22 | arXiv 2606.14550 (bound 23 is identical to bound 10) |
| **Open** (June 2026) | **44, 46** | 2 | arXiv 2606.14550: "the only candidate bounds left open are Bounds 44 and 46" |

The counts add to 68.

**Transcription: done on 27 Oct 2026, 20:40 SGT** (Daniel, 20:12: "Do them and continue").
- Every formula, with its sources, tier, status and notes, is in `src/genesis/conjecture/sealed.py` (kernel side).
- The semantic checks are in `evidence/bhs_transcription_f2/` (`scripts/f2_bhs_transcription.py`); tests are in
  `tests_genesis/test_conjecture_domain.py`.
- The 2006 text could not be reached: its DOI page is not on this session's allowlist, and the shell's egress
  refuses arXiv and publishers. So the formulas come from five later sources, each read one bound at a time:

| Source | What | Coverage |
|---|---|---|
| S1 | Damnjanović, Ha, Stevanović, arXiv 2606.14550v1 (12 Jun 2026), Tables 1–2 | the 36 bounds open before it |
| S2 | Taieb, Roucairol, Cazenave, Harutyunyan, "Automated Refutation with Monte Carlo Search of Graph Theory Conjectures on the Maximum Laplacian Eigenvalue", *LION 2025*, LNCS 15744 (Springer 2026) 52–63, doi 10.1007/978-3-032-09156-7_4, Appendix B of the authors' PDF | all 68 (the extraction flattens radicals) |
| S3 | Ghebleh, Al-Yakoob, Kanso, Stevanović, arXiv 2403.18429v1, Appendix B (HTML and PDF) | OCR-damaged; some labels shifted by one (its "45" is bound 46's formula, its "39" bound 40's); used only where it matches under the same number, or as noted |
| S4 | Bouffard, Breen, "Reinforcement learning for graph theory: Parallelizing Wagner's approach", arXiv 2509.01607v1 (LaTeX HTML) | 2, 3, 15, 28, 29, 31, 32, 36, 43, 49, 52–55, 57–60 |
| S5 | `google-deepmind/formal-conjectures` issue #7282 (13 Oct 2026) | bound 44 |

**The tiers:**

| Tier | Rule | Bounds |
|---|---|---|
| **A1** | Two or more sources give the identical formula | 51 bounds: all except those below |
| **A2** | One source exact; a second compatible up to an extraction artefact (a missing parenthesis, a stray character, a flattened nested radical, an inferred root index); the semantic checks pass | 10, 13, 19, 22, 24, 25, 27, 32, 40, 52, 53 |
| **B** | One source only. Descriptive use only | 45, 48 (S2's transcription is confirmed by its reported P3 counterexample), 50, 51 |
| **X** | Sources disagree. Excluded until the 2006 text is read | 28 (S4: √(4m⁴/d² + 2dm); S2: √(2m⁴/d² + 2dm)); 41 (S2 and S3 differ in structure) |

**Notes on individual bounds:**
- **Bounds 19, 22, 24 and 25:** both extractions infer the fourth root. A square root there would make the bound
  quadratic in the degrees.
- **Bound 27:** S2's reading, √(3d² + 5dm)/2, is below μ(C₄) = 4 at C₄, so it could not be a proved bound. S1's
  reading, √((3d² + 5dm)/2), is kept.

**The semantic checks** (`evidence/bhs_transcription_f2/README.md`) cover every connected graph on 2 to 7 vertices,
995 graphs, with each violation certified exactly:
- No proved or open bound is violated, under either reading of undefined terms.
- 48, 57 and 61 are refuted exactly by P₃, as Taieb et al. report.
- Every formula equals 2r at d = m = r (μ of r-regular bipartite graphs), except 28's S4 reading.

**The primary sealed set** is A1 and A2, minus the duplicate 23 and minus the proving test's family A
(18, 21, 24, 30, 40): **56 bounds**, `sealed.sealed()`. Of those:
- 21 are proved (the nulls);
- 33 are refuted;
- 2 are open (44 and 46).

**Classical nulls** (S1's Lemmas 2.6–2.9, to add when F4 is preregistered):
- μ ≤ 2Δ;
- μ ≤ max over edges ij of (d_i + d_j) (Anderson and Morley 1985);
- μ ≤ max over vertices of (d_v + m_v) (Merris 1998);
- μ ≤ max over vertices of √(2d_v² + 2d_v·m_v) (Li and Pan 2001).

S1's standing assumptions are simple graphs without isolated vertices. Disconnected graphs are allowed, because a
component with the largest μ gives a connected counterexample. m_v is the average degree of v's neighbours.

**The literature check for bounds 44 and 46 (27 Oct 2026).** Searches of arXiv, the web and GitHub for work after
S1 (June 2026):
- **Bound 44: still open as far as found.**
  - `google-deepmind/formal-conjectures` issue #7282 (opened 13 Oct 2026, a "statement intake pending review";
    linked PR #7396 open) states it as μ(G) ≤ 2 + √(2R(G)), with R(G) the maximum over edges of
    (d_u − 1)² + (d_v − 1)² + m_u·m_v − d_u·d_v. That is identical to the sealed formula.
  - The issue claims proofs of two restricted variants: graphs with signless spectral radius at most 11, by a
    computer-assisted Collatz–Wielandt argument; and graphs with all degrees in {1, b}.
  - The author reports that OpenAI Codex was used for proof reading and replay. None of this has been verified
    here, and the issue reports no counterexample.
- **Bound 46: nothing found after S1.** Still open as far as found.
- **Related but different:** arXiv 2610.29048 proves other conjectures, Li, Wang and Guo's, on (signless)
  Laplacian spectral radius.
- **Also found:** `google-deepmind/formal-conjectures` formalises about 60 of Graffiti's conjectures in Lean
  (`FormalConjectures/WrittenOnTheWallII/`, seen at commit `c0c5380`; not executed). It is a transfer-family
  candidate with machine-checked statements (§7b).
- Any certificate Genesis finds for 44 or 46 is checked against the literature again before anything is said.

## 7. Batches and acceptance tests

Each study is preregistered (script, design tests, SHA-256 sent to Daniel) before it runs. Each runs alone on CPU 0
from a clean worktree, in slices, after the queue ahead of it.

| Batch | Kind | What | Acceptance or verdict rule | Rough cost |
|---|---|---|---|---|
| **F1** (BUILT: B20_R160, `docs/checkpoints/B20_R160_RECORD.md`) | engineering (CPU 1) | `frontier/`: direction, curves, converge, allocate, engine, meta; the kernel-side planted world; NHP boundary and relabelling tests | On development planted worlds (disclosed): (a) 90% forecast coverage at least 0.80 per curve type on held-out curves (the upper limit of 0.97 was dropped before acceptance; over-coverage is conservative; disclosed in the record); (b) the null world gives no discoveries; (c) a recombination vein is found in at least half of the worlds that have one; (d) a stopped run resumes to the identical result; (e) the boundary, relabelling and teaching-ban tests pass. Development numbers are reported but license nothing | 1–2 sessions |
| **F2** | engineering (CPU 1) | `conjecture/`: graphs, invariants, Γ with equitable-partition realisation, attack representations and methods (NMCS, NRPA, GBFS, CEM, exhaustive), the exact verifier, the generator, the sealed set (§6, two-source rule) | The verifier accepts certificates for **published counterexamples rebuilt from their papers** (for example Wagner's 19-vertex graph against Aouchiche–Hansen, and one 2026 equitable-partition graph); it never certifies against the proved nulls on 10⁴ random and extremal graphs; mutated certificates are rejected; every method runs as a pausable harness | 2 sessions |
| **F3 = B20_R156** (PREREGISTERED: `scripts/b20r156_frontier_worlds.py`, amended before it ran, sha256 `9ae034dbf8bd…`; runs after B20_R141) | study (DEV, calibration) | The engine against uniform, successive halving, UCB1 and random, at matched compute, on sealed planted worlds from held-out families (including null worlds) | Primary: regret ratio at the full budget (the engine below halving and below uniform, one-sided Wilcoxon over worlds, Holm). Secondary: forecast coverage, false discoveries on null worlds (must be 0, else INVALID), recombination-vein rate, early versus late curve | under 1 h |
| **F4 = B20_R157** (PREREGISTERED: `scripts/b20r157_laplacian_bounds.py`, sha256 `49b171f9be58…`; runs after B20_R156) | study (DEV) | The sealed Laplacian bounds: the 56 of `sealed.sealed()` (tiers A1 and A2; without the duplicate 23 and without the proving test's family A, 18, 21, 24, 30, 40). Each bound is posed by formula only, under an opaque id; its status is sealed. Arms at matched CPU per bound: the Frontier (allocating over representations, methods and n), NRPA, GBFS, CEM and the uniform portfolio | Primary: the number of known-false bounds refuted by exact certificate within the budget, the Frontier against the best single baseline (paired by bound; exact sign test); time to refutation (a rank test with censoring). Validity: no certificate against a proved bound. **Bounds 44 and 46:** any certificate is a candidate new result, checked against the literature before anything is said | about 8–12 h (to set by a timing pilot) |
| **F5 = B20_R158** (PREREGISTERED: `scripts/b20r158_open_conjectures.py`, sha256 `50d2de64a7ad…`; runs after B20_R157) | study (DEV) | Open-ended generations: Genesis poses its own conjectures from its own data, attacks them, abstracts named constructions from converged counterexamples, and reuses them in the next generation | Measures: verified refutations per CPU hour by generation (Page's trend); rediscoveries labelled by the sealed database; surviving conjectures (candidates, never theorems); construction reuse and compounding. Controls at matched compute: no abstraction, no extrapolation (halving), and a fixed curriculum. NHP audits pass | about 10 h |
| **PT-1 = B20_R159** | study (DEV) | **The proving test (§7b):** an unfamiliar family A with an inadequacy gate; a new representation, a nontrivial consequence, the extracted procedure, its independent use in family B, and the improved inventor against its predecessor at matched total compute on families C | PROVED_OUT only if all five parts pass; otherwise the parts that passed and the first failure | to set after F5 |
| F6 (later; machinery BUILT 28 Oct: the meta level, `frontier/meta.py`; several domains as one, `frontier/multi.py`) | engineering and study | The meta level (§4.8) on sealed meta-worlds; then the engine's other domains (the max-cut lines B1, the representation language, the causal scientist) as direction sources, so that Genesis allocates across domains too | as each is preregistered | — |

## 7b. The proving test (Daniel, 27 Oct 2026, 20:22 SGT): the acceptance test of the whole system

> Give Genesis an unfamiliar mathematical problem family where its existing representation is inadequate.
> Without specifying the missing concept, require it to:
> 1. Discover a useful new representation.
> 2. Establish a nontrivial mathematical consequence.
> 3. Extract the procedure that enabled the discovery.
> 4. Use that procedure to discover something independently useful in another mathematical family.
> 5. Demonstrate that the improved inventor outperforms its predecessor under matched total compute.
>
> This test to be done to prove out system

Everything in F1–F5 is built toward this test, and it is reserved as **B20_R159 (PT-1)**. Nothing short of passing
all five parts may be called "proving out the system". Each part is kept apart and scored separately. Its design,
to be preregistered when F1–F5 have run:

**The families (all sealed; chosen by the kernel, never shown before the test):**
- **A, the unfamiliar family.** Its defining property is that the predecessor's representations are inadequate. That
  is measured by an **inadequacy gate**, like the headroom gate:
  - the predecessor inventor, at the full budget with its starting representations, certifies nothing in A;
  - a known-good representation exists in the literature, so success is possible.
  - The first candidate: the Laplacian bounds refuted in 2026 only by large equitable-partition constructions:
    - 18 (158 vertices);
    - 21 and 24 (164);
    - 30 (253);
    - 40 (352).
  - They are held out of F4 and F5 for this purpose: F4's sealed set excludes them; see §12.
- **B, the transfer family.** It has a different object or invariant, with exact statements and known statuses.
  Candidates:
  - **Graffiti's conjectures as formalised in Lean** in `google-deepmind/formal-conjectures`
    (`FormalConjectures/WrittenOnTheWallII/`, about 60 files, seen 27 Oct 2026). Their statements are machine
    checked, so there are no transcription errors.
  - Adjacency-spectrum conjectures of AutoGraphiX.
  - A non-graph family: 0/1 matrices, such as the Brualdi–Cao permanent question for 312-avoiding matrices that
    Wagner 2021 answered.
- **C, held-out families** for part 5.

**"Without specifying the missing concept," made checkable:**
- The research plane's starting representations and Γ contain no quotient, partition, blow-up, orbit or symmetry
  operation (§5.3).
- A **forbidden-concept audit** scans the research-plane sources used in the test and the manifest's contents. It
  fails if the hidden reference's concept is named or encoded. The list of forbidden names is kernel side.
- ARA may diagnose the class of a bottleneck, for example that expressiveness is the limit. Its stand-ins in the
  test must be research-plane ones, never the kernel's hidden reference.

**The five parts, scored separately:**

| Part | Required | How it is checked |
|---|---|---|
| 1. A useful new representation | An encoding with an exact decoder to graphs, created by Genesis during the test (by abstraction over its own artifacts, the representation language of `representation/`, or the Frontier's operators) and absent from the starting set | **Useful:** an ablation inside the run at matched compute. With the representation, the attack reaches certificates in A that the starting representations do not |
| 2. A nontrivial mathematical consequence | At least one exact refutation certificate for a bound in A that the predecessor could not refute. Stronger, and optional: a parametric infinite family with an exact symbolic certificate | `verify.py` (exact). Then a literature comparison: a rediscovered published counterexample counts for the test but is reported as a rediscovery |
| 3. The procedure, extracted | The successful branch's lineage, compiled from the Frontier's event log into a **procedure research object**. It is a typed, executable program of research steps (for example: solve small instances exhaustively → cluster extremal artifacts → abstract their shared structure into a parameterised construction → search its parameters at large n), kept in the vault with its contract and provenance | It is extracted by code from the log, not written by the builder. It runs unchanged on a new family. A replay on A reproduces the discovery |
| 4. Independent use in B | The procedure, run on B, yields an exact certificate (a refutation or a better construction) that the predecessor does not get there at matched compute | Exact verification in B. The procedure gets no B-specific changes. B is sealed until then |
| 5. The improved inventor beats its predecessor | On fresh sealed tasks from C: the inventor with the extracted procedure in its method library against the predecessor (the same Frontier without it), at matched **total** compute. The improved arm is charged the full cost of discovering the procedure in A | Primary: certificates per task, a paired one-sided test over tasks, Holm across the test's claims. Validity: NHP audits, the forbidden-concept audit, no certificate against a proved null |

**Machinery for parts 3–5 is built** (27 Oct 2026, 21:55 SGT; `frontier/procedure.py`, tests in
`tests_genesis/test_frontier_procedure.py`).
- `extract(engine, problem)` compiles the procedure behind a problem's best verified result from the engine's own
  records:
  - explore: the approaches whose branches converged, with their shares;
  - converge;
  - abstract;
  - exploit: the new representation with the discovering method.
  Nobody writes the procedure by hand, and it names no problem and no template.
- `ProcedurePolicy` (the policy `procedure`) is the improved inventor of part 5: the Frontier's policy plus a library
  of procedures. Within a share ρ of compute, it runs the library's procedures on new problems first.
- These are mechanics only. What they are worth is the test's question.

**Family B is transcribed** (27 Oct 2026, 23:15 SGT; PT-1 groundwork). The candidate is the Graffiti.pc conjectures of
"Written on the Wall II" as formalised in Lean in `google-deepmind/formal-conjectures`, read at commit `c0c5380`
(a shallow clone, used as data only; nothing in it is run).
- `conjecture/invariants.py` (research plane): about 50 exact invariants, each following the Lean definition it
  names. Examples are the independence number, the largest induced bipartite subgraph, forest and tree, the induced
  path number, Ls, the dominations, the Havel–Hakimi residue, distances to sets, and Hamiltonian paths. The
  independence number uses exact branching on vertex masks. The rest use exhaustive subset search, which is
  practical to about 16 vertices.
- `conjecture/wowii.py` (kernel side): all 63 statements, transcribed into exact evaluators.
  - Statuses: 29 proved, 25 disproved, 9 open. They were checked against the Lean categories and each statement's
    leading negation.
  - Ten were first left out and added on 28 Oct 2026, 00:57 SGT: 103, 160, 291, 309, 314, 315, 316, 322, 327 and
    438b. They needed a logarithm decided exactly, well-total-domination, triangles, the Havel–Hakimi zero step,
    even-horizontal edges and 2-independence.
  - The new statements' checks:
    - the proved ones hold on all 995 small graphs;
    - none of the new disproved ones has a counterexample that small;
    - the documented counterexamples of 103 (11 vertices), 309 (C5[K3]) and 327 (12 vertices) violate their
      statements with the stated values, under both implementations and in the posed text. That makes 18
      documented counterexamples in all.
  - Lean's conventions are kept: real division by zero is 0; natural subtraction and division truncate; ceilings of
    square roots are exact.
- **Semantic checks** (`tests_genesis/test_wowii.py`):
  - Every proved and open statement holds on all 995 connected graphs of 2 to 7 vertices.
  - Of the disproved statements, only 32 has a counterexample that small: P5, the one the source gives.
  - 15 of the 21 disproved statements have an explicit counterexample in their Lean file. Each was rebuilt, and each
    violates its statement with the invariant values the file states. For 59 the text does not fix the chain graph:
    six of the 252 chain graphs give the stated values, and all six violate.
  - 34 is checked in part. Its 39-vertex tree is beyond exhaustive search, so the check uses path = diameter + 1,
    which holds for trees.
- **A transcription error found by these checks:** 100 first read ceil((maxL + √S)/4) where the statement is
  ceil((2·maxL + √S)/4). It failed on 116 small graphs and is fixed.
- **One rename, disclosed.** WOWII's "path cover number" is `min_spanning_paths` in the research plane, because the
  forbidden-concept audit forbids the stem *cover*. The concept, the fewest vertex-disjoint paths that contain every
  vertex, is unrelated to the hidden reference. The audit itself is unchanged and was not relaxed.
- **Posed as text, with a domain** (28 Oct 2026, 00:20 SGT):
  - `conjecture/statement.py` (research plane) is a statement language: `[condition ->] condition` over the
    invariants by name, set functions, `@complement` and `@square`, and Lean's conventions (x / 0 = 0, natural
    floor division, remainder and truncated subtraction). Values are exact: numbers p + q√s decide the ceilings,
    floors and comparisons of square roots.
  - `wowii.TEXT` (kernel side) poses each of the 53 statements as text, written a second time from the Lean text.
    The two transcriptions agree, in verdict and, for plain inequalities, in margin. They were compared on all 995
    connected graphs of 2 to 7 vertices, on 60 random graphs of 8 to 10 vertices, and on the 15 counterexamples.
    The comparison first caught a bug in the language: √1 evaluated to 0. Both transcriptions are the builder's, so
    this is a consistency check, not an independent source.
  - `conjecture/invariant_domain.py` (research plane) is the conjecture domain with the statement as the objective.
    The score is positive exactly when the statement is violated. The representations, methods, abstraction and
    procedures are unchanged; sizes are 6 to 12, and graphs above 16 vertices score −∞ (14 before the faster invariants). `attack.Runner` now takes
    any objective (`objective=`).
  - `wowii.verifier` (kernel side) checks a claimed counterexample with the kernel's own transcription, computed
    twice: with the research plane's `invariants.py` and with `conjecture/invariants_ref.py`. Both must say
    violated, and any disagreement is logged.
  - `invariants_ref.py` (kernel side, 28 Oct 2026, 00:25 SGT) is an independent implementation that shares no code
    with the research plane. It imports only `fractions`, `itertools` and `networkx`, which a test enforces. It is
    written from the Lean definitions by different means:
    - networkx for distances, girth, bipartiteness, forests, trees and domination;
    - subset enumeration with `itertools`;
    - independence as a maximum clique of the complement;
    - backtracking for Hamiltonian paths;
    - recursion over edges for matchings;
    - Lean's definition of vertex connectivity;
    - the standard Havel–Hakimi process.

    The checks:
    - All 33 invariants, the set distances and the graph operations agree with `invariants.py` on all 995
      connected graphs of 2 to 7 vertices and on 30 random graphs of 8 to 10 vertices.
    - Ls equals the most leaves of a spanning tree, enumerated by Lean's definition, on every connected graph up to
      6 vertices.
    - The 53 evaluators agree under both implementations.
    - The documented counterexamples of up to 18 vertices violate under both. 194 is left out because its 18
      vertices defeat the backtracking path search.
  - End to end, on invented statements only (B stays sealed), the Frontier refuted the two false ones (α ≤ Δ;
    girth ≤ 4 → Hamiltonian path) and none of the three true ones.
- **Faster exact invariants** (28 Oct 2026, 00:35 SGT). The values are unchanged; only the searches are shorter.
  - Each search for a largest induced subgraph starts at a valid upper bound:
    - b ≤ 2α;
    - forest ≤ b;
    - tree ≤ forest;
    - path ≤ tree.
  - Results are cached per graph.
  - Hamiltonian paths:
    - rejected at once when the graph is disconnected or has more than two vertices of degree at most 1;
    - otherwise a budgeted depth-first search runs, with the bitmask DP when the search does not settle.
  - The spanning-paths number is 1 exactly when there is a Hamiltonian path. Otherwise it tries k = 2, 3, …,
    starting from half the number of leaves.
  - Effect:
    - the documented counterexamples on 17 to 21 vertices are evaluated in under 0.05 s each (C5[K4] took 15 to
      20 s before);
    - all 53 statements on one random 16-vertex graph take about 0.6 s.
  - The search limit is raised from 14 to 16 vertices. Both implementations agree on the Hamiltonian path and the
    spanning-paths number on all 1,253 atlas graphs and on 200 random graphs of 8 to 11 vertices.
- **Faster still** (28 Oct 2026, 02:57 SGT). Exact branch-and-bound or enumeration searches replace the
  subset searches:
  - the induced path: a depth-first search over induced paths;
  - the induced tree: ESU enumeration of connected sets, with non-trees cut;
  - the induced forest: branch and bound with component tracking;
  - b: branch and bound with two-sided components;
  - 2-independence: branch and bound under the bound 2α;
  - the Hamiltonian path: a depth-first search that cuts on connectivity and dead ends, after exact necessary
    conditions: removing one or two vertices leaves at most one or two more components, and a bipartite graph's
    sides differ by at most one;
  - the spanning-paths number (open statement 40): G has k covering paths exactly when G joined to k − 1 new
    independent vertices has a Hamiltonian path. That is tried first, with the exact split search behind it.
  Each agrees with the subset search, or with the kernel's reference, on all atlas graphs and on 400 to 500
  random graphs.
  - **The cost of one statement on a random graph:** 2.7 ms at 16 vertices (was 22.5), 6.6 ms at 18 and 12 ms at
    20. The search limit is raised to 18.
  - **The kernel's reference:** it gains valid upper bounds from its own α, and Held–Karp for Hamiltonian paths
    above 10 vertices, so it now double-checks all documented counterexamples up to 18 vertices, 194 included
    (2.5 s).
- **Still to build before PT-1 can be preregistered:**
  - the PT-1 study script: the inadequacy gate on A, parts 1–5, and family C.

**An open design question for part 1 (for Daniel; 28 Oct 2026, 00:50 SGT).**

*The problem.* Abstraction today generalises converged graphs into Γ templates, and it only compresses: a
template, or a library of named sub-programs in the manner of X2, reaches the same closure of graphs as Γ itself,
only at a shorter description length. Γ's operations (union, join, complement, cartesian product, corona, pendant
paths) can express complete multipartite graphs. They do not, in general, express equitable-partition
constructions where the parts meet in regular but incomplete patterns, nor blow-ups of a base graph with an
induced P4, beyond the special cases its products and coronas happen to produce. This is the builder's reading;
it is not proved.

Family A's references are of that kind. So for part 1 to pass, something must take Genesis outside Γ's closure,
and the audit checks names, not ideas.

*The candidate mechanisms, by how much they hand over:*
1. Library learning over Γ (X2's mechanism, ported): hands over nothing, but cannot leave the closure. It would
   likely fail A.
2. Program synthesis over lower-level adjacency primitives. Examples are maps over vertex pairs with predicates,
   and matrix products. This is generic, but a block-constant matrix language is the hidden concept under another
   name, so the primitive set must be chosen with care, and Daniel should approve it.
3. MDL compression of Genesis's own best artifacts: a generic dictionary coder over canonically ordered adjacency
   rows, whose repeat counts the existing size generalisation turns into parameters. It is generic machinery, but
   "rows that repeat, scaled" is close to the concept.
4. Operators that act on the operators of Γ. Γ's own operations would be mutated and recombined, with an exact
   decoder kept.

*Recommendation, to be decided before PT-1 is preregistered.* Take 1 and 4 as the honest starting point, report 2
and 3 as variants, and let the inadequacy gate and the audit judge. Whatever is chosen is labelled as the
builder's, and the test reports which mechanism produced part 1. This decision is Daniel's: it sets what "without
specifying the missing concept" means in practice.

**Decided (Daniel, 28 Oct 2026, 00:53 SGT): "Do the hardest so it proves it can find its way."** PT-1 allows only
mechanisms 1 and 4, the two that hand over nothing.
- **Mechanism 1, library learning over Γ:** named pieces abstracted from Genesis's own constructions.
- **Mechanism 4, operators acting on Γ's operations:**
  - an operation such as the cartesian product is a rule on pairs of vertex pairs, in terms of equality and
    adjacency in each factor;
  - Genesis may mutate and recombine such rules over the whole rule space, with no rule favoured and an exact
    decoder kept.

Mechanisms 2 and 3 are excluded from PT-1 entirely. If part 1 fails, they may run afterwards as diagnostics,
labelled as such, and they never count toward PROVED_OUT. The risk is accepted: Genesis may not find its way, and
that is then the recorded result. Both allowed mechanisms are the builder's machinery and are labelled so. What
they produce on A is Genesis's.

**Mechanism 4 is built** (28 Oct 2026, 01:05 SGT; `conjecture/operations.py`; tests in
`tests_genesis/test_operations.py`; B20_R164).
- **The space.** A product-type operation on pairs (u, v) is a rule: the set of state pairs, each coordinate equal,
  adjacent or neither, that make two pairs adjacent. That gives 256 tables. Γ's cartesian product is one of them.
  The decoder is a sum of Kronecker products and is exact.
- **The operators:**
  - mutation flips one of the 8 bits, chosen uniformly (checked: about 500 of 4,000 per bit);
  - recombination takes each bit from either parent.
- **In the domain.** `ConjectureDomain.derive(problem, representation, seed)` gives a Γ representation one more
  operation, a mutation or recombination of its product-type ones. It is deterministic in the seed, gives one name
  per operation set, and returns None for representations that are not Γ.
- **In the engine:**
  - a policy may return a `derive` action. The engine asks the domain, logs the event, and opens the new
    representation on the leader's method;
  - a resumed run replays the derivations and ends where an uninterrupted one does;
  - `PublicDomain` treats `derive` as optional, so the planted world answers None;
  - the setting `p_derive` is 0 by default, which leaves earlier behaviour unchanged. PT-1 sets it as part of the
    engine's configuration.
- **In procedures.** A discovery in a derived representation compiles to a procedure that carries its lineage: the
  starting representation and the seeds. The improved inventor replays it on a new domain and obtains the same
  operations. Tested: the replay on a fresh domain reproduces the operation set.
- **Disclosure.** As a check of the decoder, the tests compare four points of the space with the products networkx
  names: cartesian, tensor, strong and lexicographic. The lexicographic product with a complete or empty second
  factor builds uniform blow-ups, so the space contains a uniform special case of family A's concept. Nothing in
  the research plane names or favours that point; Genesis reaches it only by its own mutation, recombination and
  selection, if at all. The audit is clean.

**Mechanism 1 is built** (28 Oct 2026, 01:10 SGT; `conjecture/library.py`; tests in `tests_genesis/test_operations.py`;
B20_R164).
- **What is learned.** The attack runners now keep their best programs. When abstraction finds no new template,
  `ConjectureDomain.learn` compresses the best Γ programs of all branches.
- **The rule.** A piece, a subtree rooted at an operation with 2 to 7 nodes and its sizes blanked, becomes a macro
  when two conditions hold:
  - it recurs in at least two independent branches;
  - it saves the most description length among such pieces.
- **The new representation.** It is Γ plus every macro learned so far. A macro is a leaf ('m<k>', sizes …) that
  expands exactly. New leaves come from the library 30% of the time. Macros may contain earlier macros.
- **Checked:**
  - a piece recurring in two sources is learned, and one seen in only one source is not;
  - an expanded macro builds the same graph as its expansion;
  - learning from the domain's own runners is deterministic; in a probe it learned a product of two complete
    bipartite graphs, then a pendant path on one;
  - the domain's inventions save and restore (`state`, `restore`). A study saves them with the engine, as F5 does
    for templates.
- What Genesis's searches repeat is what the library holds. Nothing in it is the builder's.

**Verdicts.**
- PROVED_OUT only if all five pass.
- Otherwise the parts that passed are listed, for example `PARTS_1_2`, along with the first failure.
- The test may fail, and that is a result. It is recorded like any other.

## 8. How it plugs into what exists

| Existing module | Its role in the Frontier |
|---|---|
| `autonomy/portfolio.py` | The `Task` interface and the six pausable generator harnesses become methods. Its arms (uniform, halving, bandit) become F3's comparators |
| `autonomy/process.py` | One fuel budget and a depth limit for `meta.py` |
| `vault.py` | Consolidation of discoveries, conjectures (open, refuted, surviving), constructions and concepts with lineage. `Vault.cascade` reactivates paused branches when a new capability (a construction, a representation) changes their approach |
| `expressive/library.py`, `consolidate.py` | Library learning and capability records over Γ programs. It needs an adapter: the learner is written over mcx3's parse trees; generalise it to any token tree with a guard rule |
| `architecture/` (ARA) | Diagnoses a stagnant line by oracle substitution. In this domain: exhaustive search for small n stands in for the search oracle; the richest representation (Γ with partitions) stands in for expressiveness; exact checking stands in for evaluation |
| `research_queue.json` (`autonomy/queue.py`) | Directions that Genesis opens can be persisted as queue entries tagged `origin: genesis`, so the queue itself becomes Genesis-driven |
| `representation/` | Its verified-gadget and encoding machinery is a model for Γ's equitable-partition realisation (realisability checked, decoder exact) |

## 9. Risks (known before building)

- **Transcription errors in the sealed set.** Mitigated by the two-source rule and the proved nulls.
- **Large counterexamples.** The 2026 counterexamples, up to 352 vertices, are out of reach of bit-string search.
  Only Γ's partition operation reaches them, and Genesis has to choose it. NOT_SHOWN there is a legitimate result.
- **Bounds 44 and 46 may be true.** Then no refutation exists.
- **Strong baselines.** NRPA and GBFS refute many conjectures in seconds (Roucairol and Cazenave 2025). The Frontier
  may add nothing on easy bounds. Its value, if any, shows on the hard ones and in the open-ended setting.
- **Novelty claims.** The parts are prior art (§11). Conjecture generation plus Monte Carlo refutation, LLM-free, at
  scale, already exists (Duhamel and Cazenave 2026). Nothing is claimed as new until a study shows something prior
  art does not.

## 10. What does not count

- Floating-point "refutations" of any kind. Only exact certificates count.
- Refuting a conjecture that Genesis or the builder mis-stated. The sealed formulas follow the two-source rule.
- A rediscovered known theorem or counterexample presented as new.
- Anything said about an open bound before a literature check.
- Gains from more compute, easier problems or development data.
- The builder's primitives, Γ's base operations, the method library or the engine's code presented as Genesis's
  invention.
- Any result obtained while an NHP audit fails.

## 11. Prior art (read 27 Oct 2026; none claimed)

| Area | Work | What it did | Relevance |
|---|---|---|---|
| Automated conjecture | Fajtlowicz, Graffiti (1988); Caporossi and Hansen, AutoGraphiX (2000); Brankov, Hansen and Stevanović, LAA 2006 | Conjectures from data and from algebraic manipulation | The source of the sealed set; generation of the F5 kind |
| Automated conjecture | Davila, TxGraffiti (arXiv 2409.19379) | Linear-programming bounds over invariant tables; touch number; static Dalmatian; Pepper's rule; several conjectures later proved (α ≤ μ for regular graphs, Caro et al.) | The model for `generate.py` |
| Counterexample search | Wagner, "Constructions in combinatorics via neural networks" (arXiv 2104.14516) | The deep cross-entropy method refuted Aouchiche–Hansen (n = 19, about 5,000 iterations, hours) and others; failed at n = 30 on one conjecture | Baseline CEM; a rebuild test for the verifier |
| Counterexample search | Ghebleh, Al-Yakoob, Kanso, Stevanović (arXiv 2403.18429) | Reimplemented Wagner faster; refuted 30 of the 68 bounds (RL at n ≈ 20; exhaustive subquartic, n ≤ 14) | Sealed statuses; the exhaustive baseline |
| Counterexample search | Roucairol and Cazenave, IASE 2025 | NMCS, NRPA, GBFS, UCT and beam search; 12 of 13 refuted Graffiti conjectures in seconds; Graffiti 197 (then open) refuted; "much faster than Wagner" | The strong baselines for F4 |
| Conjecture generation and refutation at scale | Duhamel and Cazenave, AAAI 2026 | Grammar over 12+ invariants, 2.5 million deduplicated conjectures, progressive GNRPA; about 1.9 million refuted and 0.3 million open; refutation is a float difference above 0.001 | Closest prior art to F5. **Its float criterion is what §5.5 avoids** |
| Proofs and counterexamples | Damnjanović, Ha and Stevanović (arXiv 2606.14550, Jun 2026) | Proved 22 bounds, refuted 12 by equitable partitions, left 44 and 46 open; SageMath exact verification; "AI-assisted tools were used for search" | The current status; the partition construction |
| Local and global learning | Charton, Ellenberg, Wagner, Williamson, PatternBoost (arXiv 2411.00566) | Local search alternated with a transformer trained on the best constructions; a 30-year conjecture refuted | Alternation of search with learned generation (the transformer is a trained model; using it here would need an LLM-free check) |
| Extrapolation | Domhan, Springenberg and Hutter, IJCAI 2015; Swersky, Snoek and Adams 2014 (freeze-thaw); Adriaensen et al., NeurIPS 2023 (LC-PFN); Li et al. 2017 (Hyperband) | Learning-curve extrapolation for early stopping and allocation | `curves.py`, `allocate.py` |
| Learning progress and open-endedness | Oudeyer, Kaplan and Hafner 2007; Wang et al. 2019 (POET); Lehman and Stanley 2011 (novelty search); Clune 2019 (AI-generating algorithms) | Curricula by learning progress; co-generated problems and solutions; novelty | `allocate.py`, `imagine`, F5 |
| Behavioural convergence | Li et al. 2022 (AlphaCode); Udupa et al. 2013; Albarghouthi et al. 2013 | Clustering by behaviour; observational equivalence | `converge.py` |
| Library learning | Ellis et al. 2021 (DreamCoder); Bowers et al. 2023 (Stitch); Zenkner et al. 2024 (AbstractBeam: no gain on an unlike distribution) | Abstraction by compression | Named constructions (§5.3) |
| Self-improvement | Zhang et al. 2025 (Darwin Gödel Machine; LLM-based); Schmidhuber 2003 | Open-ended self-modification | The meta level (§4.8), LLM-free and bounded |

## 12. Handoff state (27 Oct 2026, 22:00 SGT; updated 28 Oct 2026, 01:15 SGT)

**What exists now** (all pushed to `continuation-b20-rx`):

| Piece | State | Where |
|---|---|---|
| F1, the engine | BUILT, v1.1 (B20_R160) | `src/genesis/frontier/`; `docs/checkpoints/B20_R160_RECORD.md`; `tests_genesis/test_frontier.py` |
| F2, the conjecture domain | BUILT (the Wagner rebuild test added 28 Oct 2026: an exact Collatz–Wielandt certificate against Aouchiche–Hansen on Wagner's 19-vertex tree, rebuilt from its stated λ₁ = √10 and μ = 2) | `src/genesis/conjecture/` (`expr`, `graphs`, `attack`, `domain`, `abstraction`, `generate`; kernel side `sealed`, `verify`); `tests_genesis/test_conjecture_domain.py` |
| The sealed set | DONE: 68 bounds tiered, semantic checks | `conjecture/sealed.py`; `evidence/bhs_transcription_f2/` |
| F3 = B20_R156 | PREREGISTERED, amended before it ran (`4a7e193`, sha256 `9ae034db…353a`) | `scripts/b20r156_frontier_worlds.py` |
| F4 = B20_R157 | PREREGISTERED (`bdf0c57`, sha256 `49b171f9…1904`) | `scripts/b20r157_laplacian_bounds.py` |
| F5 = B20_R158 | PREREGISTERED (sha256 `50d2de64a7ad…`; runs after B20_R157): FULL (procedures, abstraction, templates carried over) against PLAIN on Genesis's own conjectures, three generations, McNemar | `scripts/b20r158_open_conjectures.py` |
| F6 = B20_R163 | PREREGISTERED (sha256 `e71bfb69365b…`; runs after B20_R158): a meta-search over 729 engine configurations on one sealed meta-training world; the promoted configuration against the defaults given the meta-search's compute (matched total) and at equal budget, on 24 held-out worlds of two new families; machinery `frontier/meta.py` (B20_R162) | `scripts/b20r163_frontier_meta.py` |
| F6-adjacent: PT-1's family B | BUILT (B20_R161): 53 Graffiti statements, posed text, domain, double kernel check | §7b |
| PT-1 = B20_R159 | Parts 3–5 machinery BUILT (`frontier/procedure.py`); the forbidden-concept audit BUILT (`conjecture/audit.py`, kernel side: identifiers and non-docstring strings of the research plane and the manifest, scanned for the hidden concept's stems; the research plane is clean); family B TRANSCRIBED (`conjecture/invariants.py`, `conjecture/wowii.py`: 53 Graffiti statements, semantic checks in `tests_genesis/test_wowii.py`) and POSED as text, with its domain (`conjecture/statement.py`, `conjecture/invariant_domain.py`, `wowii.verifier`, checked by two independent invariant implementations, `invariants.py` and kernel-side `invariants_ref.py`; faster exact invariants, search up to 16 vertices); part 1's two allowed mechanisms BUILT (B20_R164: library learning over Γ, `conjecture/library.py`; operators acting on Γ's operations, `conjecture/operations.py`; the engine's derive action, procedures carrying derivations); the study is still to write | §7b |

**Run each study from a clean worktree of its preregistration commit** (`git worktree add --detach <path> <commit>`).
The study scripts check their module pins at run time. The design tests check the pins at the preregistration
commit through `git show`.

**CPU 0 (studies, in order):**
1. **B20_R151 is RECORDED** (27 Oct, 17:47 UTC): NOT_SHOWN, reading NO_LANGUAGE_EFFECT
   (`docs/checkpoints/B20_R151_RECORD.md`).
2. **B20_R152 is running in slices** (from 27 Oct, 17:48 UTC).
   - From the clean worktree `/home/claude/r152-wt` at `3d88ad6`.
   - Resume after each exit 3 with: `/home/claude/run_slice.sh /home/claude/r152-wt scripts/b20r152_self_extension.py evidence/self_extension_b20r152 /home/claude/logs/r152_slices.log`
   - Check progress by `grep -c 'slice exit'` only; never read the log's lines.
   - Up to about 15 h. Then record it with the RecordB20R152 draft in `docs/handoff/RECORD_TEST_DRAFTS.md`.
2b. **B20_R165**, the replication of B20_R151's S5 (preregistered 28 Oct; about 1.2 h), from a worktree of its
    preregistration commit, output `evidence/planar_replication_b20r165`.
3. **B20_R141** from a worktree at `a3b3eda`, about 3 h.
4. **B20_R156 (F3)** from a worktree at `4a7e193`, under 1 h.
5. **B20_R157 (F4)** from a worktree at `bdf0c57`, about 2 h.
6. **B20_R158 (F5)** from a worktree at `703b2ee`.
7. **B20_R163 (F6)** from a worktree of its preregistration commit, under 1 h.
8. Then PT-1, once preregistered (§7b). Daniel decided part 1's mechanisms on 28 Oct, and both are built (B20_R164).
   A design draft, not preregistered, is in `docs/handoff/PT1_DESIGN_DRAFT.md`.

**CPU 1 (engineering):** light tests only.
- No sandboxed (runc) test while a study runs on CPU 0: the sandbox resets the affinity
  (`docs/OMEGA_OPERATIONS.md`).
- Never edit `.py` files in a worktree a study runs from.
- **Before every commit, run every test that touches a changed module and check its exit status.** Twice today a
  failing test was pushed (`aa89b6a`, then `cb04bbd`/`7f2e7ff`). Both were fixed and disclosed.

**F2's first items are done** (27 Oct 2026, 20:40 SGT; §6):
- the Taieb et al. reference;
- all 68 formulas tiered (A1 51, A2 11, B 4, X 2);
- the literature check for 44 and 46 (both still open as far as found; partial claims for 44 unverified).

Built: `src/genesis/conjecture/` and its tests (`tests_genesis/test_conjecture_domain.py`, 16):
- `expr`, `graphs`;
- `attack`: the objective, four starting representations (edges, trees, bounded degree, Γ programs) and six methods
  (hill, anneal, evolution, GBFS, CEM, NRPA), as pausable, deterministic runners;
- `domain`: the Frontier's view, with no abstraction yet;
- kernel side: `sealed`; `verify`, with its study verifier.

End to end, on invented bounds only, the Frontier refutes `d + 1` and `di + dj − 1` by exact certificate. It never
refutes the proved `2d` or `d + m` (Merris).

**Development look on the sealed set (disclosed).** While the attacks were smoke-tested on 27 Oct 2026 (13:10 UTC),
six sealed bounds already known to be refuted (2, 3, 36, 48, 57, 61) were attacked for 3,000 evaluations with each
of six representation and method pairs.
- 48, 57 and 61 were certified by several pairs, 3 and 36 by GBFS on bounded graphs and by Γ.
- 2 was not certified (best score 0.0: equality).
- No setting was tuned on these results.
- F4 will report its primary result with and without these six bounds.

**Abstraction is built** (27 Oct 2026, 21:35 SGT; `conjecture/abstraction.py`). When the Frontier sees independent
branches converge on a structure, the domain does three things:
- it parses the converged graphs into Γ programs (union by components, join by complement components, recognised
  bases, pendant paths; opaque leaves elsewhere). Rebuilt graphs are isomorphic, checked on 300 random programs;
- it generalises their sizes into parameters;
- it registers the result as a **template**: a new representation, on every problem, searched up to 400 vertices.

There is one template per shape. The machinery is the builder's and generic: it carries no partition, quotient,
blow-up or symmetry concept. The templates themselves are what Genesis abstracts. On invented bounds, the Frontier
converged on complete bipartite graphs, where Merris's bound is tight, abstracted the template K_{a,b} and searched
it. Proved bounds stay unrefuted.

**Genesis's own conjectures are built** (27 Oct 2026, 21:40 SGT; `conjecture/generate.py`):
- the data are graphs Genesis draws itself;
- the candidates come from a 4,122-formula grammar of degree-1 local bounds;
- a candidate is kept if it holds on all the data, is sharp somewhere, is not dominated, and is one formula per
  function.

**A development look, disclosed.** On 500 of its own graphs, the generator kept 25 conjectures. Reading them, the
builder recognised several published bounds among them:
- Merris's d + m;
- Brankov–Hansen–Stevanović bound 10 (√(d² + 3dm), proved);
- bound 29 (refuted 2024);
- **bounds 18 and 21, which are the proving test's family A.**

**Consequence (a rule for F5):** before Genesis attacks its own conjectures, the kernel withholds any that is
equivalent, on random points, to a bound held out for the proving test. Family A must stay unfamiliar until the
test. The withheld ones are logged; the research plane is not told why.

Open in F2:
- the remaining items of §5: invariants beyond the Laplacian; Γ; the attacks; the generator;
- ~~a Collatz–Wielandt upper certificate for the Wagner rebuild test~~ done (28 Oct 2026, 00:36 SGT; `UpperCertificates.test_the_wagner_rebuild`). Wagner's Figure 4 was not seen. The tree, two stars K₁,₈ whose centres share a neighbour, was rebuilt from the values the abstract page states (n = 19, a tree, λ₁ = √10, μ = 2): λ² = 10 solves 1 = 2/(λ² − 8);
- reading the 2006 text for bounds 28 and 41, if Daniel can attach it (DOI 10.1016/j.laa.2005.10.017).

**Rules that carry over.** Everything in `docs/HANDOVER.md` §3 and the plan's §2. The protected judge
`autonomy/feedback.py` stays untouched (`2ff4a5ab…dd6`). It is all LLM-free. Push only to `continuation-b20-rx`.
