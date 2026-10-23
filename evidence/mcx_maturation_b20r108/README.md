# B20_R108 evidence: affinity maturation of the engine's configurations: NO_DIFFERENCE at both budgets

Builder-run on DEV (the open-record track). It licenses nothing; Gset was not touched.
- **Script:** `scripts/b20r108_mcx_maturation.py`, preregistered at `f844e1e` (SHA-256 `ae99b342…`), with
  `mcx.WIDE` (L0 up to 0.2, tenure divisors down to 2, pools up to 32; B20_R105's draw space unchanged).
- **Run:** alone on CPU 0, 2,583 s, on 23 Oct 2026 (15:19–16:02 SGT). `code_identity` `11a61541…`, the committed tree
  (`f844e1e`). The later batches' scripts were committed through the index only and kept out of the working tree
  until it ended.
- **The other core.** While it ran, the builder recorded B20_R106 and B20_R107 (documents and test runs of under a
  second each). It also wrote and tested the designs of B20_R109–R112 in separate worktrees: a few short tests, and
  eight 0.2 s program runs on a development host.
- **Incumbents:** B20_R105's `configs.json` (`7c9e9aca…`).

| File | What |
|---|---|
| `runs.jsonl` | 784 runs, each keyed by graph, configuration and budget |
| `configs.json` | B20_R105's classifier and the matured configurations, in B20_R105's format |
| `summary.json` | The races round by round, held-out values, labels, which classes kept their incumbent, validity |
| `run.log` | The run |

None of the 96 graphs shares an identity with Gset or with B20_R105's graphs: 148 identities were excluded.

## Result: NO_DIFFERENCE at 1 s and at 10 s

**What maturation changed** (mutants of B20_R105's choices, raced on fresh graphs):

| Class | 1 s | 10 s |
|---|---|---|
| random | pool 8 → 4 | kept (the incumbent won) |
| toroidal | P 0.8 → 0.5, tenure divisor 5 → 10 | P 0.8 → 0.5 |
| planar | L0 0.05 → 0.01, restart period 2,000 → 20,000 | L0 0.05 → **0.2**, cluster exchange → **renormalisation**, BLS's perturbation rules, pool 8 → 16, restart period 20,000 → 2,000 |

**Held out** (24 fresh graphs; Wilcoxon signed-rank on per-graph gaps, alpha 0.025):

| Budget | Matured vs incumbent | Label |
|---|---|---|
| 1 s | wins 6, losses 7 (p = 0.79); mean gap 0.10% vs 0.06% | NO_DIFFERENCE |
| 10 s | wins 5, losses 0, all 5 on planar graphs (the rule needs 6 decided graphs, so p = 1) | NO_DIFFERENCE |

At 10 s, the planar configuration with renormalisation won all five planar graphs that were not tied (three tied).
The two other classes were tied or kept their incumbent. That is a signal for one class, not a result: five graphs
are below what the preregistered test can decide.

**Validity:** median metered CPU 1.21 of the budget at 1 s and 1.02 at 10 s; 0 failed runs of 784.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| Maturation changes the configuration in at least two classes, moving to L0 = 0.1 or 0.2 in at least one | Yes: changes in all three classes at 1 s and two at 10 s; L0 = 0.2 for planar graphs at 10 s |
| MATURED_BETTER at 1 s possible but unlikely to reach significance | NO_DIFFERENCE (6–7) |
| NO_DIFFERENCE at 10 s | NO_DIFFERENCE (5–0, too few decided graphs) |

## What it means

- **B20_R105's configurations are near a local optimum of the widened space,** at least at these budgets and on
  these families. A second round of mutation and selection found nothing it could show to be better.
- **One lead for later:** renormalisation, the physics move that clonal selection never picked in B20_R105, was
  picked by maturation for planar graphs at 10 s. It won every decided planar graph there. A study aimed at planar
  graphs, with enough graphs to decide, could test it.
- **Consequence fixed in advance:** B20_R110 uses B20_R105's configurations, because B20_R108's 10 s label is not
  MATURED_BETTER (the rule in `scripts/b20r110_gset_long.py`).
