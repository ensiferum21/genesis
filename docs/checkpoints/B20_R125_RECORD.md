# B20_R125–R126 record: an engine the system can rewrite, and the machinery to improve it and its own process (engineering); setup of B20_R127 and R128

- **Built by:** the builder, on 24 Oct 2026, at Daniel's request:
  - 09:26: "Use novel techniques mixing multiple diff ways of physics and reality principles … adapt to invent
    definitely better than specialist of humans";
  - 09:29: "I want it to be able to invent to improve itself multiple times better than us doing this process and
    the process itself to be improved".
- **Running at the time:** B20_R123. Everything was committed through the index only, so its working tree was
  unchanged.

## B20_R125: `mcx2-v1`, the max-cut engine as an interpreter of search programs

`src/genesis/candidate_kinds/native/mcx2.c` keeps every function of `mcx.c` and replaces its fixed loop with a
program. A population of replicas runs at LEVELS temperatures, two per level, and shares mcx's elite pool. The
program repeats until the CPU budget is spent. Its statements are physics operators:

| Statement | Operator | Source |
|---|---|---|
| `B<k>` / `b<k>` | k attractors of breakout local search per replica (all levels / coldest only) | Benlic and Hao 2013 |
| `X` | replica exchange between adjacent temperatures | parallel tempering: Swendsen and Wang 1986; Hukushima and Nemoto 1996 |
| `I` | isoenergetic cluster moves within each level | Houdayer 2001; Zhu, Ochoa and Katzgraber 2015 |
| `C` | renormalisation of the coldest replica | mcx's coarse-graining (B20_R104) |
| `M` | multi-parent grouping crossover into the hottest replica | MACUT, Wu and Hao 2012 |
| `H` | Houdayer's exchange of two elites into the hottest replica | mcx -rs 1 |
| `R` | random restart of the hottest replica | — |
| `D` | pair descent in every replica: the best pair of adjacent vertices flipped together while it improves | the double-transfer move of Ma and Hao's multiple search operator heuristic (2017) |
| `L` | path relinking of the coldest replica towards a random elite, keeping the best state on the path | Glover's path relinking, for max-cut within global equilibrium search (Shylo, Glover and Sergienko) |
| `S<k>` | run the next statement only after k attractors without a new best | — |
| `P<k>` | run the next statement only every k-th pass | — |

- **The default** is the builder's hybrid, **REX: `B100 X I S2000 C` at 4 levels.** It is parallel tempering over
  breakout local search, with isoenergetic cluster moves and renormalisation on stalls. It is the human-designed
  baseline the system's programs must beat.
- **None of the operators is new;** the language and REX are the builder's.

**Checks.**
- On small graphs, every operator, alone and mixed, at one and three levels, reaches the brute-force optimum:
  560 of 560 in a first check, 800 of 800 with `D` and `L`, and the kind's tests after it.
- AddressSanitizer and UndefinedBehaviorSanitizer runs on generated 600–800-vertex graphs found no error.
- Malformed programs and options are refused, by the kind and by the binary (exit 2).
- The build is deterministic and pinned (`c6a797c8…`, after `D` and `L` were added; the first pin was
  `892b896b…`), and it runs in the runc sandbox.
- Tests: `tests_genesis/test_mcx2_kind.py` (7). `test_mcx_kind.py`'s membership test now lists `mcx2-v1`.

## B20_R126: `autonomy/selfimprove.py`, self-improvement on two levels

- **Level 1, the inventor:**
  - A genome is an `mcx2` configuration: program and options.
  - Random engines, seven kinds of mutation (`arg`, `insert`, `delete`, `replace`, `swap`, `option`, `duplicate`)
    and a one-point crossover, all always valid.
  - The search is the feedback contract version 2's: the judge holds two confirmation splits and releases only
    improvements larger than its own noise.
- **Level 2, the process:**
  - The inventor's own settings are data: population, children, leaders, tournament, crossover rate, and the weight
    of each mutation.
  - `search(process, …)` runs the contract's search with them. With ORIGINAL it is exactly the contract's search; a
    test checks this.
  - Processes can be drawn at random, mutated and crossed.
- Tests: `tests_genesis/test_selfimprove.py` (5).

## Development looks (disclosed)

At 1 s, on six generated graphs of another seed, REX was about equal to breakout local search's published setting.
It was below the builder-configured mcx on planar graphs:

| Graph | BLS | MCX | REX |
|---|---|---|---|
| random 1 | 13,313 | 13,332 | 13,322 |
| random 2 | 13,362 | 13,361 | 13,364 |
| planar 1 | 2,373 | 2,396 | 2,367 |
| planar 2 | 2,384 | 2,402 | 2,384 |
| toroidal 1 | 1,406 | 1,408 | 1,408 |
| toroidal 2 | 1,420 | 1,420 | 1,422 |

No search was run.

## Preregistered here

- **B20_R127**, `scripts/b20r127_self_invented_engine.py`: the system invents an engine from scratch under the
  contract (300 split evaluations at 1 s on 6-graph splits).
  - The engine is then held against three human designs: BLS (published setting), MCX (builder-configured; it led
    the published heuristics on Gset) and REX (the builder's hybrid).
  - They are compared on 15 held-out graphs at 1 s and 10 s, and on Gset at 10 s.
  - Primary: the system's engine against MCX on Gset (sign test). The verdict is INVENTED_BETTER_THAN_HUMAN_DESIGN
    or NOT_SHOWN.
- **B20_R128**, `scripts/b20r128_improve_the_improver.py`: the system improves its own inventor.
  - A process's yield is the held-out score of the engine its inventor returns.
  - The meta-search runs generation 0 (ORIGINAL and 5 random processes), then 2 generations of 4 children.
  - Final test: EVOLVED against ORIGINAL over 8 repetitions on fresh graph sets (paired Wilcoxon). The verdict is
    SELF_IMPROVEMENT_SHOWN or NOT_SHOWN.

## Amendments before any run (24 Oct 2026, 09:47–09:58; Daniel: "use this to adapt and make it even better", "we can learn from failures too", "check research and compound", "different types of thinking")

All were made before any of B20_R124–R128 ran, and are disclosed in the scripts' docstrings.
- **The language:** `D` and `L` were added after a literature check:
  - Ma and Hao's multiple search operator heuristic (2017) gave the pair move;
  - Shylo, Glover and Sergienko's global equilibrium search with path relinking gave path relinking.

  Both are prior art, now available as operators. The check also found Cosm (2025), which reports new cuts on the
  largest Gset instances (G72, G77, G81, beyond G1–G54) and is not yet peer-reviewed. Any Genesis value above a best
  known value must be checked against the methods published after 2013, including MOH's six improved instances,
  before anything is said.
- **The process level (`selfimprove`)** can choose:
  - its search algorithm: the steady-state search or a MAP-Elites archive;
  - its calibration effort: how many extra engines calibrate the judge;
  - adaptive operator selection, learning from failure: kinds of mutation that keep failing are tried less.
- **The inventor** can learn macros, new building blocks drawn from the recurring runs in its own best engines.
- **B20_R127:**
  - one engine per class;
  - three generations, each starting from the previous generation's engine of its own class and of the two other
    classes (analogy);
  - learned macros from generation 2 on;
  - Gset at 60 s for the system's engines, against B20_R110's;
  - templates for the new operators.
- **B20_R128:** processes also choose the algorithm and the calibration effort, and whether to adapt.
