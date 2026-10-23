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

## 3. B20_R99: the headroom pilot (DEV; about 1 CPU hour; an analysis script, no engineering)

**Result (23 Oct 2026; `evidence/headroom_b20r99/`): HEADROOM_UNSTRUCTURED.** Where tfxw stops, no exchange of one or
two edges improves, and CP-SAT improved 4 of 1,536 small regions, at 2 of its 32 states (random 4-sets as often as
4-balls). The language programs leave a (2,3)-exchange at 23 of 64 states: the swap they lack, not a new concept. The
only pattern found for improving anchors (high host-degree imbalance) has held-out lift 11 but recall 0.22, under the
0.3 required; improving regions are too few to judge. The best states differ globally (improving gap pieces of about
8,000 edges). By §3.3: the discovery loop of §4 is not built on these hosts; one richer grammar may be tried once; the
evidence points to global, coarse-grained moves (renormalisation and crossover, tested on max-cut in B20_R104-R106).

### 3.1 Development looks (22 Oct 2026; exposed hosts only; disclosed)

The first draft of this section (commit `ba2b052`) put the pilot on 24 fresh n63 planted hosts, with exchanges of
at most 3 edges. Before preregistering anything, the builder checked the pipeline on hosts that earlier studies had
already exposed. The draft code sits in the builder's scratch area and will be committed with the study script.

1. **The enumerator is exact.** It agrees with brute force on 60 random small graphs (r ≤ 2). The gap decomposition
   (point 4) agrees with an independent implementation on 200 graphs, and every piece it finds can be swapped in on
   its own.
2. **Planted n63 leaves nothing to find.** Generation 2 and `hybrid-swap-v1` ran on 3 of B20_R83's training hosts
   (0.25 s and 1.0 s, 2 seeds each). Both reached the same value on each host (291, 279–280, 285). One state out of
   24 had an improving (1,2)-exchange; none had a strict (2,3)-exchange. The first draft would therefore have
   returned NO_HEADROOM for a reason that has nothing to do with the hypothesis.
3. **Large hosts (n128, n256, from B20_R97).**
   - `tfxw` is the engine that beat the 13 MaxSAT champions (`DEFAULT`, which B20_R97 found equivalent to the frozen
     configuration). At 2 s and 10 s it left no improving (1,2)- or (2,3)-exchange in any of 6 states, even when 16
     edges below the best known value (4,446 against 4,462).
   - `hybrid-swap-v1` at 2 s and 10 s left 1–4 strict (2,3)-exchanges on planted hosts (exchange descent +1 to +6).
     On G(256, 0.5) it left none: there, every unchosen edge has at least 3 blocking wedges, so no removal of 2 edges
     frees anything.
   - Generation 2 at 2 s on a planted n256 host left 7 improving (1,2)-anchors (descent +9).
4. **The gap to the best known value is global.** A state XOR the best-known witness was decomposed into
   independently swappable pieces, on 4 hosts. Each time, one giant component (462–4,830 edges, touching nearly every
   vertex) carries all the gain, beside a few gain-0 or gain-1 pieces of 2–7 edges. The better solution sits in a
   globally different arrangement, not a set of local fixes away.
5. **Small neighbourhoods still hold improvements at the strongest engine.** CP-SAT (1 s, one worker) re-optimized
   the edges touching a vertex set of `tfxw`'s 2 s state on one planted n256 host. It improved 2 of 10 neighbourhood
   balls of 4 vertices (+1 each), and none of 10 random 4-sets. At 8 and 16 vertices it found nothing, but there it
   rarely proved optimality within 1 s.

**What the looks change.**
- **The domain** becomes `triangle_free_large_v1` (n128 and n256, planted and G(n, 0.5)). There the strongest arms
  still differ by up to about 20 edges at 10 s.
- **The move classes.** Exchanges of at most 3 edges stay, because they are exact and cheap. But the strongest engine
  exhausts them, so the pilot adds small neighbourhoods re-optimized exactly. These count only when CP-SAT proves the
  region optimal.
- **The gap decomposition** becomes a descriptive part.
- **The thresholds of §3.3** were written before any look and are unchanged.

### 3.2 Design (proposed; fixed at setup)

**States.**
- **Hosts:** 16 fresh hosts, 4 per cell (planted or G(n, 0.5), crossed with n128 or n256), excluding every exposed
  identity.
- **Arms:**
  - the language programs: generations 1–3 and generation 2's control, through their kinds;
  - `hybrid-swap-v1`;
  - `tfxw` in B20_R95's frozen configuration (the strongest arm).
- **Budgets:** 2 s and 10 s, one seed.

That gives 16 hosts × 6 arms × 2 budgets = 192 states. Each returned edge set S is a *stagnation state*: where that
search stood when its budget ended. S should be maximal, because every step ends with a greedy completion. The
analysis counts free additions (r = 0) anyway and reports any.

**Part A: exchanges.**
- An *anchor* R is a set of r chosen edges. An *(r, r+1)-exchange* removes R and adds r+1 unchosen edges, keeping
  the set triangle-free and growing |S| by one.
- An unchosen edge f = uv is *blocked* at each vertex w with uw and vw in S. Removing R frees f exactly when every
  blocking wedge of f has an edge in R. So freed edges come from inverted wedge lists, and a small exact check
  confirms that the edges added are compatible.
- Exchanges are enumerated exhaustively for r ≤ 2 at every state. *Exchange descent* applies improving exchanges
  (r = 1 first, then r = 2) until none is left; the pilot reports its gain.
- A single edge that frees 3 compatible edges is an r = 1 anchor of gain 2, not an r = 2 anchor. A *strict* r = 2
  anchor is one where neither edge improves alone.
- r = 1 is the engine's (1,2)-swap. r = 2 goes beyond anything the builder supplied.

**Part B: neighbourhoods, at the strongest arm's states.**
- Each state gets 16 seeded centres v. The regions are:
  - *balls* {v plus k − 1 random host neighbours} for k ∈ {2, 4};
  - as a control, random 4-sets.
- CP-SAT (pinned, one worker, 2 s) re-optimizes every edge touching the region, holding the rest of S fixed.
- Outcomes: IMPROVES (any gain), PROVED_NONE (optimal, no gain) or UNKNOWN. UNKNOWN never counts as headroom.

**Part C (descriptive).** At each host, the gap decomposition against the best value any arm found: component sizes,
gains, vertices touched.

**Q1, headroom.** At the strongest arm's states:
- the fraction of states with an improving exchange (Part A) or an improving neighbourhood (Part B);
- the fraction of balls that improve, against the fraction of random sets that do.

For the other arms: Part A's fractions and exchange-descent gains.

**Q2, structure.** Are the improving anchors and regions concentrated in a class that a short description
recognizes?
- *Recognizers* are conjunctions of at most 3 threshold predicates over a typed grammar G_low of primitive local
  features of the vertices and edges involved:
  - degree in S and in the host, and their ratio;
  - codegree in the host;
  - host triangles through a vertex or edge;
  - S-edges among a vertex's neighbours;
  - whether an anchor's edges share a vertex.
- G_low deliberately leaves out derived constraint quantities such as blocker counts, freed counts or tightness.
  Those are what a discovery loop should invent, not be handed. A richer grammar G_rich that includes them is
  reported only as a descriptive upper bound.
- Recognizers are fitted on 8 hosts (2 per cell) and judged on the other 8 by held-out *lift* (precision divided by
  the base rate) and held-out *recall*.
- The null is 1,000 recognizers drawn at random from G_low, with the same number of predicates, thresholds at
  feature quantiles, and support at least that of the fitted recognizer.

**Q3, calculation instead of search (descriptive).** At the strongest arm's states, compare two ways to the first
improvement: trying only recognized regions or anchors, against trying them in random order. The measure is CPU time.

### 3.3 Verdict (proposed before any look; fixed at setup)

- **NO_HEADROOM:** improving changes (Part A or B) exist at fewer than 10% of the strongest arm's states, *and* at
  fewer than 10% of the programs' states after exchange descent with r = 1.
- **HEADROOM_UNSTRUCTURED:** there is headroom, but no recognizer reaches held-out lift ≥ 2 with recall ≥ 0.3 and
  above the random recognizers' 95th percentile.
- **HEADROOM_STRUCTURED:** headroom, and such a recognizer exists. The loop is worth building (§4).

**Expectation (stated after the development looks, which inform it).**
- The programs' states will show r = 1 headroom often. That is the swap, already known.
- `hybrid-swap-v1` will show r = 2 headroom on planted hosts and none on G(n, 0.5).
- The strongest arm will show no exchange headroom. It will show improving 4-balls at a minority of its 2 s states,
  fewer at 10 s, and more than random sets give.
- Whether the improving regions are recognizable in G_low is open; HEADROOM_UNSTRUCTURED is slightly more likely than
  HEADROOM_STRUCTURED.

**What each outcome means for GV4.**
- **NO_HEADROOM:** this route is closed at the scales probed.
- **HEADROOM_UNSTRUCTURED:** try one richer grammar once (paths of wedges, pairs of regions), then stop.
- **HEADROOM_STRUCTURED:** go on to §4. The gap decomposition (point 4 of §3.1) also says what a loop would face:
  the best known solutions are globally different, so local concepts can at most speed the climb within a basin. They
  cannot replace the global search that finds the basin.

**Order.** B20_R99 needs a pinned CP-SAT. The current tree is byte-identical to the wheel, but it fails its pin,
because the pin includes pip's record of the wheel's path (repair: B20_R98 engineering). B20_R99 runs after B20_R86.

## 4. If there is structured headroom: the discovery loop (engineering, after B20_R102)

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

## 5. The two-arm study (after the loop is built; the GV4 policy comparison)

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
