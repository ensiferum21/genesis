# Genesis Ω: the self-extending representation language (Daniel's directive of 24 Oct 2026, items 6–9)

**The goal.** Genesis should synthesise executable mathematical representations, not choose from a fixed list:
- objects;
- relations;
- operators;
- transformations;
- decoders.

Each must be preserved exactly with its lineage and checked for correctness. Each must be able to wake dormant work
it makes possible.

**What is claimed.** Nothing yet. Everything below is engineering on fixtures (`tests_genesis/test_representation_*`).
The first study, B20_R135, preregistered (`7040a3c`), ran on 27 Oct 2026: **INVENTED_REPRESENTATION_BETTER**
(`docs/checkpoints/B20_R135_RECORD.md`). Encodings chosen by the encoding search and a pilot beat one-hot for 3 and
4 colours through the same pipeline; such encodings are known, so no novelty is claimed.

## The language (package `src/genesis/representation/`, research plane, LLM-free)

| Layer | What Genesis synthesises | Correctness | Module |
|---|---|---|---|
| Relations | Predicates on binary variables, as values, with canonical forms under renaming and negation (one address per orbit). Operators build new relations from old ones: negate, permute, project (∃), complement, extend, conjoin. Partial relations care only about some assignments | Equality of truth tables | `relations.py` |
| Gadgets (operators on relations) | An exact quadratic penalty polynomial with ancillas for any relation: zero on members, at least the gap off them; optionally *uniform* (every violation costs exactly the gap, so sums count violations) | Exhaustive enumeration, by two independent evaluators; a synthesiser is only a proposer | `gadgets.py` |
| Objects and decoders | Encodings of finite-domain variables in bits: any injective code table (one-hot, binary and unary are points of the space), its decoder and its validity relation; relations on values *lifted* to relations on bits | Decoding is a table inverse; lifted relations are recomputed from the values | `encodings.py` |
| Transformations | A constraint problem → one BQP of the Problem Compiler's form (satisfy, Max-CSP, constrained optimisation). Finite-domain problem → binary problem through an encoding. The decoder back, and an independent checker on the original problem | Exact by construction from exact gadgets; brute force on small instances in the tests; the checker never reads the BQP | `compile.py`, `encodings.py` |
| The library | Immutable versions (parent chain, rollback = using an earlier value). Two slots per orbit (best exact, best uniform). Admission only of exact improvements, with lineage (synthesiser, parameters, what it was made for) | Re-checked at admission, independently of who proposed it | `library.py` |
| Memory and reactivation | Every admitted representation stored exactly in the vault (WorldSpec, `reproducible`, explanation `unknown` allowed). Each is announced as a CapabilityRecord unlocking `relation:<orbit id>`. Uncompilable problems are parked as dormant ProblemSpecs (`failed_due_to tag:relation:<id>`) and reactivated through the vault's bounded cascade (fuel, depth, never twice by a trigger) | The vault's integrity checks; promotion to `verified` only through a recorded study | `library.py`, `vault.py` |

**Synthesisers.**
- An MILP: HiGHS through `scipy.optimize.milp`, fewest ancillas first, then the smallest sum of |coefficients|.
- A stochastic local-search baseline.
- The encoding search: over code tables up to bit symmetries, each scored by what the problem would pay (variables,
  then non-zero coefficients). Every gadget a table needs is synthesised on demand.
- None is trusted: admission re-checks everything.

**What the fixtures show:**
- The MILP rediscovers known gadgets with the fewest ancillas:
  - none needed: 2-clauses, exactly-one, the AND gate (Rosenberg 1975), NAE-3;
  - one ancilla: 3-clauses and 3-parity.
- A *uniform* exactly-one gadget needs one ancilla, where the textbook (Σx − 1)² needs none but is not uniform.
- For 3 colours, the encoding search prefers a 2-bit code over one-hot when it counts variables first:
  - the 2-bit code needs 2 bits per vertex and no ancillas; its validity "not 11" is one term, and its
    colour-difference gadget has 11 terms;
  - one-hot needs 3 bits per vertex; its validity is a hard exactly-one with no ancilla, and it uses the textbook
    3 terms per edge.
- For 4 colours, "different 2-bit codes" has a uniform gadget with one ancilla and 13 terms.
- Whether these invented representations make the engine better is an empirical question for the study below.

**Added since (fixtures):**
- **Relation factorisation**, an operator Genesis applies to its own relations (`encodings.factorize`). It discovers
  a conjunction of small relations equal to a lifted relation on valid codes, and reports whether it is uniform.
  - For one-hot colours it rediscovers the textbook decomposition (not both of colour c) with no hand-written rule.
  - This is what lets one-hot encodings of four or more values (lifted arity above six) be represented.
- **Synthesis as a process** (`representation/processes.py`). The synthesiser is a level-1 process.
  - Levels 2 and 3 improve it, and its improver, under one fuel budget.
  - A descendant is admitted only by a promotion gate: strictly more verified gadgets on unfamiliar relations at
    matched fuel (directive item 11).
- **The first study, B20_R135**, was preregistered (`7040a3c`) before B20_R133's colouring results were seen, and ran
  on 27 Oct 2026: INVENTED_REPRESENTATION_BETTER for k = 3 and 4 (k = 5 kept one-hot); PASMaxSAT-c still ahead; the
  cascade reactivated exactly the four parked families.

## Not yet built (the next stages, in order)

1. **Relation discovery from problem families.** Read a family's checker, extract the relations its constraints use
   (from a declarative spec), synthesise what is missing, and park what cannot be synthesised within limits. This is
   reduction *invention* for families the compiler has no hand-written reduction for (`reduction-invention` in the
   queue). Candidates: 1-in-3 SAT, NAE-3SAT, XOR-SAT, Max-3-SAT, exact cover, k-colouring for every k.
2. **Operators that make operators.** Degree reduction of higher-order terms as synthesised gadgets (products of
   three or more variables), and composition rules (the gadget of a conjunction from its parts) checked against
   direct synthesis.
3. **Representations as processes, beyond the synthesiser.** Encodings and the encoding search become processes too.
   The gate is then run on real families, not only on relations.
4. **Sharing with the genome.** One registry shared with the acquisition language (`science/library.py`) and the mcx2
   programs (the plan's Ω3).

## The first study (to preregister after the gates; a draft, not a commitment)

1. **Synthesis.**
   - Held-out relations: random arity-3 and arity-4 relations, and named families.
   - The MILP against the local-search baseline at matched evaluations.
   - Measures: success, ancillas and size.
   - Every admitted gadget exact (validity).
2. **Invented against textbook representations.**
   - Colouring with k = 3, 4, 5 on fresh graphs.
   - The encoding Genesis chooses against one-hot, both through the same engine (REX via max-cut) at the same CPU.
   - Measure: verified conflicts, from the family's checker and a second checker.
   - Paired sign test per k, Holm.
   - B20_R133's colouring result (if SPECIALIST_BETTER) is the baseline this tries to move.
3. **Reactivation.**
   - Families parked for missing relations, reactivated by newly admitted gadgets.
   - Solved and checked against the MaxSAT 2026 entrants on natural encodings.
   - Value per total compute, against a fresh synthesis of every gadget and against no reactivation.

**Prior art to check before any novelty claim:**
- penalty-function synthesis by MILP or SMT (Bian et al. 2016, *Mapping constrained optimization problems to quantum
  annealing*);
- QUBO formulations (Lucas 2014; Glover, Kochenberger and Du 2019);
- reductions of higher-order pseudo-Boolean functions (Rosenberg 1975; Ishikawa 2011; Boros and Hammer 2002);
- encodings of finite domains in SAT and QUBO (one-hot, binary/log, unary/order encodings; Tamura et al. 2009;
  Chancellor 2019 on domain-wall encodings).
