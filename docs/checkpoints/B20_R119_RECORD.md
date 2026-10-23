# B20_R119 record: FCI and Genesis's active procedure for hidden causes (engineering); setup of B20_R120

- **Built by:** the builder, on 23 Oct 2026, while the B20_R118 checkpoint's release matrix ran (the files were
  committed after it, so the checkpoint does not contain them).
- **Why:** B20_R118 found that the established methods without hidden variables turn hidden common causes into
  causal edges (CONFOUNDING_MISLEADS). Daniel's research alert asks for more: whether the system proposes the
  measurement or intervention that resolves a hidden cause.

## What was built (`src/genesis/causal/`)

- **`fci`:** FCI, written from Spirtes, Glymour and Scheines (2000) and Zhang (2008). It is the established method
  that allows hidden variables, and so the comparator for any method that flags them.
  - PC-stable's adjacency search, unshielded colliders, the Possible-D-SEP stage with separating sets capped at
    four variables, and rules R1–R4 (R4 by discriminating paths).
  - R8–R10 are omitted. They only turn circles into tails, so they cannot add or remove a bidirected mark.
  - Output in the benchmark's format: tail-arrow → directed, arrow-arrow → bidirected, everything else undirected.
- **`active`:** the step FCI cannot take: a budget of hard interventions do(X_t).
  - **What an intervention shows.** In a linear model a neighbour still depends on X_t only if t causes it. One
    intervention showing dependence gives t → j. Two interventions, one on each end of a pair, showing no
    dependence either way give a hidden cause alone (↔).
  - **The suspicion of a hidden cause, per adjacent pair.** It combines FCI's marks with whether each variable's
    regression slope on the other changes across environments (Cochran's Q). A direct cause's slope does not change
    when only noise variances do; a hidden cause's does.
  - **Strategies for choosing targets.** `random`; `degree`, a standard heuristic; `suspicion`, Genesis's choice;
    and the reference `oracle`, which is told the truth and serves as a ceiling.

**Tests** (`tests_genesis/test_causal_active.py`, 12):
- **FCI, with the oracle:**
  - it marks the textbook hidden cause (A → B ← L → C ← D gives B ↔ C);
  - with no hidden variable it gives no bidirected mark and the exact adjacencies;
  - it is sound on 12 random models with hidden variables: every ↔ is a pair with no ancestral relation, every →
    an ancestral one. A builder check on 300 more models found no unsound mark among 222 bidirected and 1,099
    directed ones;
  - every adjacency it keeps is inseparable;
  - its answers on data are valid.
- **The procedure:**
  - the heterogeneity test;
  - interventions turn a pure hidden cause into ↔ and direct causes into →;
  - budgets are respected without repeats;
  - budget zero is FCI;
  - the suspicion strategy goes to the suspected pair;
  - the oracle goes to the hidden causes first;
  - unknown strategies are refused.

## B20_R120 (preregistered here)

`scripts/b20r120_propose_interventions.py` (SHA-256 `64939a15…e041`), design tests in
`tests_genesis/test_propose_interventions.py`.
- **Instances:** 40 fresh instances (p = 10, 3 hidden confounders, 3 environments).
- **Arms:** FCI, and for budgets 2 and 4 the four target strategies.
- **Primary test:** `suspicion` against `random` at budget 2, on bidirected F1 (paired Wilcoxon). The verdict is
  GENESIS_PROPOSES_BETTER / GENESIS_PROPOSES_WORSE / NOT_SHOWN.
- **Secondary tests:** against `degree`, at budget 4, and interventions against FCI alone.

## What it is not

The ingredients are known: FCI, invariance across environments (as in invariant causal prediction), and
interventions for orientation. What is tested is a capability, choosing experiments well. It is not a claim of a
new algorithm.
