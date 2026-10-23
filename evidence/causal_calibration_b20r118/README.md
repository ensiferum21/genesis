# B20_R118 evidence: established causal-discovery methods with hidden confounders: CONFOUNDING_MISLEADS

Builder-run on DEV (Daniel's research alert of 22 Oct 2026, item 2). A calibration of the benchmark built in
B20_R117. It licenses nothing.
- **Script:** `scripts/b20r118_causal_calibration.py`, preregistered at `82e95c5` (committed through the index while
  B20_R116 ran).
- **Run:** alone on CPU 0, 38 s, on 23 Oct 2026 (23:49–23:50 SGT).
- **Code identity:** `652726f3…`, the committed tree `39f4f64`. Between the setup and the run, only the ledger
  builder and tests changed; the benchmark and the study script are as preregistered.

| File | What |
|---|---|
| `runs.jsonl` | 640 runs (160 instances x 4 methods): the answer, its scores, CPU time, and the planted truth's edges, confounded pairs and environment scales |
| `summary.json` | Means per method and cell, Test 1 and Test 2, the spurious-edge rates with intervals, the headroom label, validity |
| `run.log` | The run |

**Design, in one line:** 40 planted graphs (10 observed variables, Laplace noise, 3,000 samples). Each graph is
run with 0 or 3 hidden confounders crossed with 1 or 3 environments, and four methods: the empty graph, PC, an
oracle PC told the true independences, and DirectLiNGAM.

## Result

**Headroom: CONFOUNDING_MISLEADS.** A confounded pair here is two variables that share a hidden cause and have no
direct edge. The table gives the share of such pairs that each method connects with a causal edge (192 pairs over
the 80 instances with hidden variables):

| Method | Connected | Share (95% interval) |
|---|---|---|
| DirectLiNGAM | 191 | **0.99** (0.97–1.00) |
| oracle PC | 192 | 1.00 (0.98–1.00) |
| PC | 130 | 0.68 (0.61–0.74) |
| empty | 0 | 0 |

None of these methods can mark a hidden cause, so none flags one; that holds by construction.

**Test 1, hidden variables** (directed-edge F1 against the planted direct causes, one environment, 40 paired seeds):

| Method | No hidden variable | 3 hidden variables | Label |
|---|---|---|---|
| DirectLiNGAM | 0.98 | 0.77 | **HIDDEN_HURTS** (p = 4 x 10^-8) |
| PC | 0.66 | 0.63 | NO_EFFECT (p = 0.19) |

**Test 2, three environments pooled naively** (directed F1, three environments against one): NO_EFFECT for PC
without and with hidden variables, and for DirectLiNGAM without them. With hidden variables, DirectLiNGAM:
POOLING_HELPS, +0.024 (p = 0.014).

**Means** (directed F1 / adjacency F1):

| Method | h0, K1 | h0, K3 | h3, K1 | h3, K3 |
|---|---|---|---|---|
| DirectLiNGAM | 0.98 / 0.98 | 0.98 / 0.98 | 0.77 / 0.79 | 0.80 / 0.80 |
| PC | 0.66 / 0.97 | 0.65 / 0.96 | 0.63 / 0.84 | 0.63 / 0.86 |
| oracle PC | 0.74 / 1.00 | 0.74 / 1.00 | 0.76 / 0.86 | 0.76 / 0.86 |

PC's directed F1 is capped by what independences can tell. Even the oracle orients only 74% of the edges; the rest
stay undirected.

**Validity:** every answer valid; the oracle PC connects every confounded pair, as d-separation requires, and
recovers the true adjacencies exactly without hidden variables.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| The oracle PC connects every confounded pair | Yes (192 of 192) |
| PC connects most (about 70%) | 68% |
| DirectLiNGAM fewer (about 50%) | **Wrong:** 99%. It forces every variable into a causal order, so a hidden common cause always becomes an edge |
| CONFOUNDING_MISLEADS or PARTIAL | CONFOUNDING_MISLEADS |
| HIDDEN_HURTS for both | DirectLiNGAM yes; PC no (its directed F1 is low with or without them) |
| Pooling: NO_EFFECT for PC, POOLING_HURTS for DirectLiNGAM | PC yes; DirectLiNGAM NO_EFFECT without hidden variables and slightly helped with them |

## What it means

- **The best method without hidden variables is the most misled with them.** DirectLiNGAM recovers 98% of direct
  causes when nothing is hidden. Add three hidden confounders and it draws an edge for 99% of the confounded pairs,
  and its F1 falls by 0.21. PC is less precise but connects fewer confounded pairs. Both report every such pair as
  a cause or a possible cause, never as a hidden variable.
- **The headroom is large and well defined.** Close to 200 confounded pairs are reported as causal. Flagging them
  as hidden causes (bidirected) is what a hidden-cause-aware method must do: FCI, which allows hidden variables;
  then Genesis's procedure, which proposes interventions to resolve them.
- **Naive pooling of environments neither hurts nor helps much.** The information in the environments has to be
  used, not just pooled.
- **Next (B20_R119–R120):** FCI as the established hidden-variable baseline, and Genesis's active procedure. It
  proposes interventions, chosen by a suspicion of hidden causes, to resolve the pairs FCI leaves undecided. It is
  scored against random and degree-based choices at equal budgets.
