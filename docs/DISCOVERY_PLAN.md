# Discovering the "physics" of a problem: objects, relations and transformations (B20_R99 onward; DRAFT plan)

This plan follows Daniel's note of 22 Oct 2026. Nothing in it is preregistered yet. Each batch below is
preregistered in its own script docstring when it is set up, and follows the usual protocol: DEV, run alone and
pinned, nothing promoted.

## 1. The idea and the hypothesis under test

Daniel's note asks Genesis to discover the useful objects, relationships and transformations that make a problem
easier: *"What new object could I discover that would turn this difficult search into a simpler calculation?"* The
loop it proposes has five steps:

1. treat failed searches as evidence;
2. run distinguishing experiments;
3. invent a representation (an executable recognizer that predicts something about moves, refined whenever two
   situations look alike under it but respond differently);
4. invent procedures that operate on the new objects;
5. keep the concepts that help on unfamiliar problems, and measure whether they also make later invention cheaper.

Until an abstraction is proved sound, it may guide search but never justify discarding solutions or claiming
optimality.

**Hypothesis (the note's, verbatim).** *Can jointly discovering representations, executable transformations and
distinguishing experiments produce transferable algorithms more efficiently than evolving code with a fixed
representation?*

**Prior art (the note's, and the builder's additions).**
- DreamCoder (Ellis et al., PLDI 2021): library learning of program abstractions. B20_R82's library language
  already uses this idea.
- Counterexample-guided abstraction refinement (Clarke et al., CAV 2000).
- Representation-driven option discovery (Machado et al., eigenoptions, 2017 onward).
- Learned coarse-graining of physical systems.
- For the moves themselves:
  - closed exchanges and ejection chains (Glover, 1996);
  - Lin–Kernighan (1973);
  - very large-scale neighbourhood search (Ahuja et al., 2002).
- Evolving code with a fixed representation, the comparison arm of the hypothesis: FunSearch (Romera-Paredes et
  al., Nature 2024) and AlphaEvolve (2025).

Combining these ideas is not itself a novelty claim. The claim to test is the comparison in the hypothesis: transfer,
with every cost counted.

## 2. Where Genesis already is, and what the loop would add

| Loop step | What exists | What is missing |
|---|---|---|
| 1. Failed searches as evidence | Program search logs every evaluation (`history.jsonl`, B20_R79–R85). The adaptation cell reads results and designs studies (B20_R93–R97) | Nothing records *where* a search stalls: the state at stagnation, which moves were tried and failed, which decisions interfere |
| 2. Distinguishing experiments | Paired designs, same-host repeats, and ablations in every study | No experiment at the level of search states: repeat from the same state, change one feature, try coordinated changes |
| 3. Representations | B18's invented, licensed encodings (`cross_2`, the cut) and `represent_and_repair`. The soundness module licenses representations before use | Recognizers of *objects inside a state* (a group of interdependent decisions, an obstruction) with predictions about moves; refinement on counterexamples |
| 4. Procedures on the objects | A closed solver language (B20_R78) and its library extension (B20_R82): loops, branching, time splits, macros | No statement can act on an invented object. Every move is a fixed primitive (one relabel, one edge drop or force) |
| 5. Keep what transfers; measure invention cost | Generations with a library (B20_R83–R86), and random-program controls (B20_R80) | Concepts stored with applicability and evidence; a measure of *invention* cost; transfer to an untouched family |

**Why now: the evidence points at the representation.**
- The system's program search finds a good iterated local search, but random sampling of the same language does as
  well (B20_R80, R81: 287.30 against 287.34).
- A library of the previous generation makes no difference on the training hosts (B20_R84: 291.61 against 291.59).

Two readings fit these results:
- the language's primitive moves leave no headroom that search could exploit; or
- the headroom exists but lies in coordinated changes that the fixed primitives cannot express compactly.

The builder's engine `hybrid-swap-v1`, which beats CP-SAT, BURER2002 and the MaxSAT champions on DEV, owes its
lead partly to such a coordinated move: the (1,2)-swap, which removes one chosen edge and adds two edges that only
that edge blocked. The solver language deliberately left the swap out (B20_R78). B20_R99 distinguishes the two
readings before anything is built.

## 3. B20_R99: the headroom pilot (DEV; about 1 CPU hour; no engineering beyond an analysis script)

**Domain and states.** triangle_free_host_v1, 24 fresh planted-cluster hosts at n63 (p_in 0.8, p_out 0.06),
excluding every exposed identity. The study runs the following on each host:
- frozen programs: generation 1 (B20_R79), generation 2 (B20_R83), generation 2's control (B20_R84), and
  generation 3 (B20_R85) if it is recorded;
- the builder's engine `hybrid-swap-v1`;
- 2 seeds per program, at 0.25 s and 1.0 s.

Each run's returned edge set S is a *stagnation state*: the point at which that search stopped making progress
within its budget. That gives 24 hosts × 5 arms × 2 budgets × 2 seeds = 480 states. S should be maximal, because every
step ends with a greedy completion; the analysis counts free additions (r = 0) anyway and reports any.

**Coordinated changes.** An *anchor* R is a set of r chosen edges. An *(r, r+1)-exchange* removes R and adds r+1
unchosen edges, so the result stays triangle-free and |S| grows by one.
- An unchosen edge f = uv is *blocked* at each vertex w with uw and vw in S. Removing R frees f exactly when every
  blocking wedge of f has an edge in R.
- For r ≤ 2 the exchanges are enumerated exhaustively: freed edges come from the inverted wedge lists, and a small
  exact check confirms compatibility among the edges added.
- r = 1 is the engine's (1,2)-swap. r = 2 is beyond anything the builder supplied.

**Q1, headroom.** At what fraction of stagnation states does an improving exchange exist, for r = 1 and r = 2,
separately for each arm and budget? And how much does an *exchange descent* gain on average? Exchange descent
applies improving exchanges (r = 1 first, then r = 2) until none remains.
- The engine's states have no improving r = 1 exchange by construction. The engine's r = 2 headroom is the number
  that matters most: it measures structure the builder's best solver does not exploit.

**Q2, structure.** Are the improving anchors concentrated in a class that a short description recognizes?
- *Recognizers* are conjunctions of at most 3 threshold predicates over a typed grammar G_low of primitive local
  features of the anchor's edges and endpoints:
  - degrees in S and in the host;
  - codegrees in S and in the host;
  - the number of host triangles through an edge;
  - the endpoints' labels under the `cross_2` encoding;
  - whether the anchor's edges share a vertex.
- G_low deliberately leaves out derived constraint quantities such as blocker or freed counts. Those are what a
  discovery loop should invent, not be handed. A richer grammar G_rich that includes them is reported only as a
  descriptive upper bound.
- Recognizers are fitted on 12 hosts and judged on the other 12 by:
  - held-out *lift*: precision divided by the base rate of improving anchors;
  - held-out *recall*.
- The null comparison is 1,000 recognizers drawn at random from G_low with the same number of predicates, thresholds
  at feature quantiles, and support at least as large as the fitted one's.

**Q3, calculation instead of search** (descriptive). Compare two ways of finding an improving exchange at the
engine's states: enumerating only recognized anchors against enumerating all anchors in random order. The measure is
CPU time to the first improving exchange. This is the "turn search into a calculation" test in its simplest form.

**Verdict (to be fixed at setup; proposed).**
- NO_HEADROOM: improving r = 2 exchanges exist at fewer than 10% of the engine's states *and* at fewer than 10% of
  the programs' states after exchange descent with r = 1. Coordinated exchanges of size ≤ 3 hold no usable
  structure here.
- HEADROOM_UNSTRUCTURED: there is headroom (not NO_HEADROOM), but no recognizer reaches held-out lift ≥ 2 with
  recall ≥ 0.3 above the 95th percentile of the random recognizers.
- HEADROOM_STRUCTURED: headroom, and such a recognizer exists. The loop is worth building (§4).

**Expectation (stated now).** The programs' states will show r = 1 headroom often. That is the swap, already known,
and the reason the engine wins. The engine's states will show r = 2 headroom on a minority of hosts, more often at
0.25 s than at 1.0 s. Whether that headroom is recognizable in G_low is genuinely open; slightly more likely
HEADROOM_UNSTRUCTURED than STRUCTURED.

**What each outcome means for GV4.**
- NO_HEADROOM: this route on this domain is closed. The next probe is a larger domain (triangle_free_large_v1,
  n ≤ 1023), where fixed budgets leave more room, or a different problem.
- HEADROOM_UNSTRUCTURED: try one richer grammar (pairs of anchors, paths of wedges) once, then stop.
- HEADROOM_STRUCTURED: §4.

## 4. If there is structured headroom: the discovery loop (engineering, B20_R100–R101)

A *concept* is stored as four parts:
- **recognizer:** a G_low program over an anchor, plus the state it reads;
- **operation:** a bounded exact completion that, given an anchor, finds the best (r, r+1) or plateau exchange it
  enables;
- **applicability:** the domains and encodings for which the recognizer is defined;
- **evidence:** states, predictions, outcomes, and the counterexamples that refined it.

The loop:
1. **Collect evidence.** Run the current programs, and log stagnation states and the moves they tried and rejected.
2. **Experiment.** From a stored state, run every exchange of size ≤ 3 (Q1's enumeration) and record which
   succeed. Re-run the search from the same state with one feature perturbed. This is the distinguishing experiment.
3. **Propose.** Enumerate recognizers in G_low by size, keeping those with lift and recall above thresholds on the
   evidence (minimum description length, so short ones first).
4. **Refine (CEGAR-style).** When two anchors have the same features but opposite outcomes, add the feature
   predicate that separates them, or split the concept. Concepts that cannot be separated are dropped.
5. **Compile.** Each kept concept becomes one new statement in the solver language,
   `["concept", I, ACC, N]`: find up to N recognized anchors, apply the operation, and judge the result by ACC.
   It only proposes moves. The domain checker still checks every witness, and a concept never prunes or certifies.
6. **Search.** The program search runs over the extended language, exactly as in B20_R83.

The engineering is tested on a planted case: on hosts where improving (1,2)-swaps are known to exist, the loop must
rediscover a recognizer equivalent to "removing this edge frees two compatible edges" from G_low, without the
blocker count being supplied. This is a known-answer calibration, not evidence for the hypothesis.

## 5. The two-arm study (B20_R102 or later; the GV4 policy comparison)

| Arm | Gets | Purpose |
|---|---|---|
| F, fixed representation | Program search over B20_R82's language, budget B | the hypothesis's comparison arm (evolving code, fixed representation) |
| D, discovery | Same search, plus the loop of §4; the loop's CPU is charged to B | the hypothesis |
| C, random concepts | Same search, plus the same number of concept statements with recognizers drawn at random from G_low (matched size and support) | separates *discovered* concepts from merely *having* an extra coordinated operator |
| P, random programs | B20_R80's random-program control at each arm's final language | separates the search from the language |

**Untouched evaluation.** No arm sees the evaluation family before the evaluation:
- *Stage 1:* another host generator within the domain (Erdős–Rényi and random geometric hosts at n63 and n128;
  triangle_free_large_v1 at n256).
- *Stage 2*, after the concept machinery has been made independent of the domain: another domain (C4-free hosts,
  `cuts_c4`).

**Measures** (all costs counted: discovery, verification, execution).
1. **Solving cost:** time-to-target on fresh hosts of the untouched family (Rønnow-style quantiles, as in B20_R77).
2. **Invention cost:** on the untouched family, a short program search with and without the concept library. The
   measure is the CPU needed to reach a target quality fixed before the run (arm F's median final value). This is
   the note's "does it reduce the cost of discovering useful procedures on fresh problems?".
3. **Ablation:** remove each kept concept in turn and re-measure 1 and 2; a gain is attributed to a concept only if
   removing that concept loses it.

**Verdict labels (proposed).**
- DISCOVERY_HELPS: D beats F and C on solving cost *and* on invention cost on the untouched family, and the ablation
  attributes the gain to at least one concept.
- OPERATOR_ONLY: D ≈ C, and both beat F. Any coordinated operator helps; discovery adds nothing.
- NO_EFFECT.
- UNRESOLVED.

Only DISCOVERY_HELPS supports the note's hypothesis. The other three are recorded as they come.

## 6. Risks and stopping rules

- **Rediscovery is not discovery.** The (1,2)-swap is known. A loop that only rediscovers it calibrates the
  machinery. Novelty requires concepts beyond what the builder supplied: r = 2 objects, or objects on another domain.
- **Leakage through the grammar.** G_low excludes blocker and freed counts. A test checks that no G_low feature is
  computed from them.
- **Cost accounting.** Arm D's discovery CPU is charged to its budget. A study that leaves it out is invalid.
- **Stopping.** NO_HEADROOM here, and again on the large domain, closes this route for GV4. The plan then records
  it as a negative result.
