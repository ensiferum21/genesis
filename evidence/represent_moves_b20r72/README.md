# B20_R72 evidence: physics move rules in the system's representation engine: **NO_GENERAL_IMPROVEMENT**

Builder-run on DEV. It licenses nothing, and no package, rule or comparator changes.
- **Script:** `scripts/b20r72_represent_moves.py`, committed with its design, rule and expectation before any run
  (`3d69ae5`; SHA-256 `5af84e42…64a2`, sent to Daniel before the run).
- **Run:** alone on the machine, pinned to CPU 0, 1,257 s; 240 runs in runc, none failed. `code_identity`
  `32d14372…b8f0`.
- **Development looks:** none.

## Question

Every representation the system invents becomes a solver through one engine, zero-temperature descent over
encodings plus greedy repair, which stops at local optima. Does a move rule from statistical physics
(τ-extremal optimization or simulated annealing, `represent-search-v1`, B20_R71) improve that engine for every
sound invented representation? A yes would be an improvement the system could apply to whatever it invents next
(docs/PHYSICS_INSPIRED_PLAN.md, idea 3).

## Design (fixed before running)

20 fresh n60 planted (0.8, 0.06) hosts (409–452 edges), excluding all 3,111 hosts named in the evidence. Arms in
runc under E1's profile at 0.5 s: `represent-search-v1` for each of `cross_2`, `adjacent_3`, `ordered_2` × `descent`,
`eo`, `anneal`; context: the frozen candidate, tabu, dSB. Primary: physics move − descent per representation,
bootstrap 90% interval, MUE 0.5.

## Result: **NO_GENERAL_IMPROVEMENT**

Validity holds (median cgroup CPU 0.66–0.68 s for every arm).

| Representation | eo − descent | anneal − descent |
|---|---|---|
| cross_2 | −0.15 [−0.45, +0.15] NO_MATERIAL_DIFFERENCE | −0.20 [−0.60, +0.15] UNRESOLVED |
| adjacent_3 | −0.05 [−0.45, +0.30] NO_MATERIAL_DIFFERENCE | −0.05 [−0.35, +0.20] NO_MATERIAL_DIFFERENCE |
| ordered_2 | −1.25 [−1.95, −0.55] **WORSENS** | −2.50 [−3.80, −1.40] **WORSENS** |

The builder expected annealing to improve every representation. It improves none.

**Secondary.**

| | Mean edges | Optimum hits (16 certified) | Mean gap to the proven bound |
|---|---|---|---|
| dSB | **273.05** | **13** | **0.40** |
| cross_2/descent (this kind) | 272.60 | 6 | 0.85 |
| adjacent_3/descent | 272.55 | 8 | 0.90 |
| tabu | 272.50 | 5 | 0.95 |
| best physics-move arm (adjacent_3/eo) | 272.50 | 6 | 0.95 |
| frozen candidate | 272.15 | 3 | 1.30 |
| ordered_2/descent | 253.25 | 0 | 20.2 |

- `cross_2/descent` here − the frozen candidate: **+0.45 [0.25, 0.65]**, 9 / 11 / 0. The rule is the same; the
  difference is this kind's faster repair.
- The best physics-move arm ties tabu (0.00 [−0.10, 0.10]) and trails dSB (−0.55 [−0.80, −0.30], 0 / 11 / 9).

## Reading

**Changing the move rule does not help; making the engine faster does.** On these hosts, at 0.5 s, the
representation engine is not held back by being stuck in local optima: extremal and annealed moves explore more but
reach no better encodings. What does help is speed. The same descent with a faster repair beats the frozen candidate
on 9 of 20 hosts and never loses, because it completes more restarts in the same budget.

**For a representation that decodes a strict subset of the cut, more exploration hurts.** `ordered_2` keeps only
the edges oriented with the class order, so its decoded set is a poor proxy for the final, repaired subgraph;
moves that accept losses wander further from good repairs.

**The strongest search remains the physics method that moves all spins at once.** Discrete simulated bifurcation
is best on every measure here, as in B20_R70. The physics idea that helps is whole-configuration dynamics, not a
different single-variable move rule.

**Limits.** One budget (0.5 s), one size (n60), one fixed annealing schedule and τ. A longer schedule or larger
budgets could change the annealing result; this study does not show that annealing cannot help, only that the
preregistered version does not.

**What it means for the system.** The negative result is useful: the next improvement to the invention engine is
not a new move rule but a faster engine (the repair alone is worth +0.45 at n60) or a whole-configuration search
over encodings in the style of simulated bifurcation. Neither is adopted; both are candidates for a later batch.

## Tests

`tests_genesis/test_represent_moves.py`.
- **Design (5):** fresh seeds; the arms; the verdict rule; the overall rule on synthetic rows, including CPU
  delivery; pinning.
- **Record (3):** the analysis and every verdict recompute from `rows.jsonl`; the arms are the recorded descriptors,
  all in runc, never above a certified optimum; the hosts are fresh and in the e1/e1b exposure addenda.
