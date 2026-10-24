# Genesis Ω: process IR and its contracts (master implementation contract §4, §10, §18)

Genesis's executable invention languages today, each a typed tree interpreted (never `eval`), deterministic and
bounded:

| Language | Objects | Type and safety checks | Interpreter | Search operators |
|---|---|---|---|---|
| Research IR (`ir.py`, `dsl.py`) | Typed values and bounded graph programs | Signatures, bounded actions | `Interpreter`, replay | `research.py` |
| mcx2 programs (`candidate_kinds/mcx2.py`) | Statements over physics operators (B, b, X, I, C, M, H, R, S, P, D, L) | `check_config` (canonical form) | The pinned C binary, in the runc sandbox for judged runs | `autonomy/selfimprove.py` (seven mutations, crossover, macros, adaptive credit, MAP-Elites) |
| Acquisition programs (`science/acquire.py`) | {agg, expr}, with expr over features, constants, + - * max min, sqrt sq inv1 | `check(prog, features)`: types, at most 15 nodes, depth 4 | `scores` (numpy) | `ops(seeds, features)`: random, six mutations, crossover |
| Primitive library (`science/library.py`) | Named expressions over features and earlier primitives | `register`: new name, known names only, a valid tree; contract = type, value range by interval reasoning, purity, totality, lineage | `expand` (exact substitution) | Primitives are leaves of the search (`features(lib)`) |
| Instruments (`causal/instruments.py`) | A set of binary tests at a level | `check`: canonical subset of TESTS, a level from ALPHAS | `outcome`, `lab` | Exhaustive (45 members) |
| Processes (`autonomy/process.py`) | {level, kind, params, lineage} | A level-L process transforms only level L-1 processes | `step` under one `Fuel` budget and `MAX_DEPTH` | `mutate` (one parameter of the target's space, moved by the transformer's step) |
| BQP (`compiler/bqp.py`) | Binary quadratic programs with four constraint kinds | `check` | `evaluate` | — (a compilation target; transformations checked in `compiler/contracts.py`) |

**Semantic contracts.**
- Every program is a pure function of its inputs: features, a graph, or a world.
- Every transformation declares exact or approximate. Exact ones are checked (`compiler/contracts.py`, brute force
  in `test_compiler`); answers from approximate ones are re-scored in the original problem.
- Every primitive carries its range and lineage.
- A program written against a library version is refused against an earlier one.
- Every execution is bounded: CPU budgets (engines), size and depth limits (trees), fuel and depth (processes).

**Not yet:**
- one registry shared by all languages;
- loops and conditionals in the acquisition language;
- equivalence fingerprints across languages (only within acquisition programs, `interpret.fingerprint`);
- e-graph rewriting.
