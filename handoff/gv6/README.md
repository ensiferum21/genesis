# GV6 (meaningful transfer): study design, DRAFT

**Status.** A DRAFT by the builder, 17 Oct 2026. It is not frozen and not registered with any
custodian, and it licenses no claim. The choice of target domain is a reviewer's (B20R46-OPEN-1).

**Gate (roadmap).** A learned capability helps in a structurally different domain within a
registered adaptation budget. The evaluation has to include:
- fresh target-domain evaluation;
- transfer controls;
- retention checks.

W24 adds: "Begin with a structurally different formal domain rather than only changing the forbidden
graph motif." E5 adds three requirements:
- freeze transferable components before seeing the target confirmation panel;
- compare transferred capability, target-only learning and conventional reuse with equal adaptation
  resources;
- inspect whether gains come from a shared duplicate or a memorized solution.

## Evidence so far: near-domain transfer (all DEV, builder-run, preregistered)

| Batch | Step | Result |
|---|---|---|
| B20_R46 | The triangle-free row-invention procedure (generate small graphs, keep by LP gap, prove each bound in Lean from the LP's dual), with a registered C4 adaptation of about 300 lines; search and kept rule unchanged | 34 patterns, **37/37 obligations Lean-CHECKED** |
| B20_R47 | The rows alone, as a certification route on 40 fresh C4 hosts | no coverage gain (22 vs 22); 80% of the LP gap closed; faster |
| B20_R48 | The rows with certified branch and bound (exact tree checker) | **38 vs 26 of 40**, p = 0.00024, median 2.1 s vs 46.9 s |
| B20_R49 | Registered ablation: the same route without the rows | **36 vs 24 of 40**, p = 0.00024: the utility is the rows' |
| B20_R50 | The rows make C4 settings calibratable; E1b's C4 arm under a DRAFT rule | two calibrated C4 settings; E1b READY_FOR_REVIEW against DSL baselines (an exact C4 MIP dominates) |

**What this shows.** A capability the system invented, the procedure and its Lean-checked output,
carries over to a different forbidden motif and causes a measured utility there.

**What it does not show.** By W24 and E5, a motif change is near-domain transfer. Three things are
missing:
- a structurally different target;
- a target-only learning control at equal adaptation resources;
- sealed target panels from a custodian.

## Second target: sum-free sets of integers (B20_R55, R56; DEV, builder-run, preregistered)

| Batch | Step | Result |
|---|---|---|
| B20_R53, R54 | Equational target first: is there research headroom on Wolfram's axiom at B20's hard settings? | **NO_HEADROOM** and **NO_CEILING_HEADROOM**: no library research moves the successor by more than 1 of 15; nothing to transfer into |
| B20_R55 | The same procedure, with a registered adaptation to sum-free sets (additive combinatorics; `invention/cuts_sf.py`, new trusted `SFDefs`) | 17 patterns, **20/20 obligations Lean-CHECKED** |
| B20_R56 | The rows with certified branch and bound on 40 fresh hosts, against the same tree over Schur rows only (the conventional route and the ablation) | **NO_CERTIFICATION_UTILITY**: 28 vs 26 certified (p 0.25), wall saving −1.6 s [−4.1, +1.4]; the rows lower the root bound by 5–10 and cut nodes 3×, but slow easy hosts |

**What this adds.** The procedure transfers to a different theorem family (its search, kept rule and proof method
unchanged), and its rows strengthen the relaxation there too. On these settings they give no preregistered
utility. After the fact, the benefit concentrates on hosts that are hard for the conventional route. B20_R57 tests
that, preregistered.

## Candidate structurally different targets

The source capability is frozen as follows:
- the procedure in `invention/cuts_v2.py` (generator v2) and `invention/cuts_c4.py`;
- the proof method (`lp-certificate-sum` recipes);
- the tree certificate (`verification/lp_dual_tree_c4.py`).

Each target below needs a registered adaptation: its motif rows, its Lean definitions, and its
pattern statements.

1. **Additive combinatorics: sum-free or Sidon subsets of [n] or Z_n.**
   - **The problem.** A sum-free set has no solution of a + b = c. Its rows are Schur triples,
     x_a + x_b + x_{a+b} ≤ 2. The patterns are small sets of integers with additive relations.
   - **Lean.** It needs a new definitions module (sets of naturals, sums). Statements become "for
     every sum-free S, and every injective, sum-preserving assignment…".
   - **Why it fits.** It is a different theorem family (Schur, Erdős–Moser). The objects are
     integers under addition, not edges of a host graph, and the symmetry group differs
     (translations and dilations).
   - **Risk.** The constraint structure is again a 3-uniform packing, close to triangle-freeness. A
     reviewer may judge it "near" too.
   - **Measured (B20_R55, R56).** Built on sets of positive integers (hosts are random subsets of {1..N}). The
     procedure transfers (20/20 Lean-CHECKED); certification utility is not shown on the first two settings (see
     the section above).
2. **Equational theories (the B20 environment, `learning/equational.py`).**
   - **The setting.** Boolean algebras and groups in several axiomatizations, with exact deciders, E
     proofs and Lean replay. This is a structurally different formal domain by any reading.
   - **Mapping the procedure.** "Keep a fact that is true but not derivable by the cheap relaxation"
     becomes "keep an equation that the decider says is true but bounded E with the current library
     cannot prove". It is then proved with a larger budget and replayed in Lean.
   - **Risk.** B20's research-policy studies found no headroom there (B20_R3, R6, R9), and the
     failure-driven curriculum is already a B20 baseline. The transferred procedure may be the same
     thing in disguise, which a reviewer must judge.
   - **Measured (B20_R53, R54; DEV design pilots).** On Wolfram's axiom at B20's hard settings, the one
     equational setting where research matters, no library-building research moves the successor by more
     than 1 of 15 on eight fresh seeds: selection, keeping, 6-node conjectures, or this mapping of the keep
     rule (which reaches the oracle with 1-5 lemmas). The target has nothing to transfer into at these
     scales.
3. **Coding theory: binary codes with minimum distance d.**
   - **Rows.** A clique-type packing over the Hamming graph, with Delsarte's LP as the conventional
     bound.
   - **What would transfer.** The patterns are small code configurations whose LP exceeds their
     maximum.
   - **Risk.** Delsarte's LP is very strong, so headroom may be small. The Lean definitions are
     larger.

## A structural caveat, added on reflection (17 Oct 2026)

All three targets fit the procedure because they are, abstractly, the same problem: the largest subset
of a ground set that contains no hyperedge of a given uniform hypergraph.
- **Triangle-free subgraphs.** The ground set is the host's edges, and the hyperedges are its
  triangles (3-uniform).
- **C4-free subgraphs.** The ground set is the edges again, and the hyperedges are the 4-cycles
  (4-uniform, at most 3 of 4).
- **Sum-free subsets of a host set of integers.** The ground set is the host's elements, and the
  hyperedges are its Schur triples {a, b, a + b} (3-uniform). The 2-element hyperedges {a, 2a} are a
  degenerate case.
- **Codes with minimum distance d.** The ground set is the words, and the hyperedges are pairs at
  distance below d (2-uniform: independent sets).

A pattern row is a bound on a small sub-hypergraph, and the procedure's search, kept rule, proof
method and tree certificate all live at that level. So targets 1 and 3 are different theorem families
in their *objects*, but not in their *abstract structure*. A reviewer could reasonably call them near
again, and the builder now thinks they are.

Of the three, only target 2, equational theories, is structurally different. There the procedure maps
only by analogy, onto failure-driven lemma invention, which B20 already has as a baseline.

**Consequence.** GV6 proper may need a transferable capability that is not tied to hypergraph-free
packing. One example is a research policy or a proof-search heuristic learned in one formal domain and
used in another. The infrastructure exists: B20's learned conjecture-selection policy, the generic
formal-research loop, and B20_R22's retention and negative-transfer protocol. No such capability has
shown utility in its own domain yet: B20's learned policy was 1W/7T/0L against the fixed one. This is
the reviewer's decision (item 1 below), and the builder's recommendation is to say so plainly rather
than to count a hypergraph re-encoding as structural transfer.

## Proposed protocol (to be reviewed; nothing frozen)

- **Freeze.** The source procedure and code at a named commit. The target adaptation is one module,
  with its line count and CPU budget registered before any target data is seen.
- **Arms**, at equal adaptation resources (builder hours are not measurable, so the budget is code
  size and CPU):
  - **transferred:** the frozen procedure with the registered adaptation;
  - **target-only:** a generator written for the target alone at the same code budget, for example
    the target's own conventional relaxation tightened by standard cuts;
  - **conventional reuse:** the target's standard LP and solver (for example HiGHS on the
    target's MILP, or Delsarte's LP).
- **Endpoint.** Certification coverage and time on sealed fresh target instances, with the tree
  certificate's checker adapted to the target's rows and re-reviewed. A second endpoint is the
  construction value, if the rows are used for rounding.
- **Retention.** The source domain's certification coverage (B20_R48's design, fresh hosts), re-run
  after the transfer, must not drop.
- **Duplication check.** No target instance or pattern may be a relabelled copy of a source pattern.
  The patterns are compared up to isomorphism of their constraint hypergraphs.
- **Decision rule.** SUPPORTED only if the transferred arm beats both controls with the clustered
  lower bound above a minimum useful effect fixed in advance, and retention holds. The attempt is one
  hypothesis in the BY family of the GV4 draft.

## What is needed from a reviewer

1. Whether target 1, 2 or 3 (or another) counts as structurally different for GV6. Note that 1 and 3 share the
   source's abstract structure (see the caveat above).
2. The adaptation budget: code size and CPU.
3. Whether certification utility counts as "helps" for GV6, or only construction utility. This
   parallels B20R35-OPEN-1 for GV4.
4. A custodian for the sealed target panels.
