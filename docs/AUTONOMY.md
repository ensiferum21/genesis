# The autonomy layer: how Genesis runs and improves its own research (B20_R96)

Daniel (21 Oct 2026): make the system more powerful; let it "recursively but properly improve and discover and make
itself better", and "use novel ways to solve the system issues".

## The loop

```
 evidence ──► adaptation cell (B20_R93)        senses caveats, remembers what answered them, composes the next design
                 │                               under its own cost model and the membrane
                 ▼
            studygen                             writes the design as a preregistered study script (fresh seeds,
                 │                               the design embedded, how each request is carried out, a cost
                 │                               estimate, what was looked at before; the runner pinned by the tree)
                 ▼
            loop.preregister                     commits it; docs/PREREGISTRATIONS.md; the SHA-256 goes to Daniel
                 │                               before anything runs
                 ▼
            loop.run → qet.main                  every arm in the runc sandbox; interim looks that stop when decided;
                 │                               time slices that pause before the background limit and resume
                 ▼
 evidence ◄── record (README, record, tests)     the cell reads the new study on the next pass
```

What improves at each level:

| Level | What changes | How it is judged |
|---|---|---|
| 0. Solving | `tfx-v1` (n ≤ 63), `tfxw-v1` and `tfxw-v2` (n ≤ 1023) | time to target (B20_R90, R92); quality at equal time (from B20_R97) against the 13 MaxSAT champions |
| 1. Configuring | successive-halving races over the engine's space (B20_R89, R95) | fresh training hosts, then fresh test hosts |
| 2. Operators | `tfxw-v2`'s grammar: five acceptance rules, population annealing, heavy-tailed kicks, a removal choice; the quality-diversity archive keeps every configuration that is best somewhere | the archive's cells (family × size × budget) and its Pareto front |
| 3. Research | the cell's response memory (which answers to a weakness worked), its cost model, the adversary's hard hosts | the cell's own prospective checks (B20_R93: 9 of 9 on B20_R92) |
| 4. The improver | an improver that has improved itself against a frozen one, with the same compute, on fresh problem classes (GV4, then three generations: GV5) | preregistered, sealed hosts; not yet run |

## The system's issues, and the new ways they are answered

| Issue (the cell's caveat) | Since | Answer in B20_R96 |
|---|---|---|
| SATURATION: every strong method ends at the same value | B20_R70 | the large domain (n up to 1023), where values separate methods; the adversary searches for the hosts where the system does worst |
| SIZE_CAP | B20_R75 | `models_large`, `graphs_large`, `candidates_large`, `tfxw` (B20_R94) |
| UNCERTIFIED_TARGETS: certification never got more time, and the n ≤ 63 route does not scale | B20_R75 | a **fractional Mantel clique packing**: weights on cliques with each edge covered at most once give `edges − Σ y_C (e(C) − ⌊k²/4⌋)` as a bound on any triangle-free subgraph; found by a linear program over greedily grown cliques, rounded to integers and re-checked exactly. Large cliques certify close to half the edges, which dense hosts need; triangles certify only a third |
| INTERRUPTED: the 2-hour limit on background jobs | B20_R81 | studies pause between hosts before the limit and resume from their rows; interim looks stop a study as soon as it is decided |
| COMPONENT_EFFECT_UNRESOLVED | B20_R92 | comparisons of configurations where there is room to differ (large hosts): each generation against the previous one and, when the cell asks for a dedicated ablation, the frozen configuration without each component it uses and the engine's first design; such a study does not stop before those comparisons are decided (`decide`, B20_R97) |
| ARM_NOT_RESPONDING (DeepDist-c) | B20_R92 | a probe at its home budget (60 s) on a few hosts |
| over the cost limit | B20_R93 | budgets staged (10 s first, 60 s next) and sequential stopping |
| GV4 without headroom | B20_R13 | a search space with real room (the operator grammar on large hosts) and an archive that keeps stepping stones |

## The membrane (what no level may do)

Edit a checker, threshold, scorer or the evaluator; run a study that is not preregistered; reuse hosts; let selection
see a sealed panel; record a negative result as anything else; defer a high-severity or chronic caveat to save time.
The known failure of self-improving code is gaming its own evaluator (the authors of the Self-Taught Optimizer measured
how often generated code tried to get around its sandbox); here the evaluator, the checkers and the bounds are outside
everything the loop can change, and every witness and bound is re-checked from its data.
