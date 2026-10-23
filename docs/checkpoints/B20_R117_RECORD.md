# B20_R117 record: a hidden-confounder causal-discovery benchmark (engineering) and the setup of B20_R118

- **Built by:** the builder, on 23 Oct 2026, while B20_R116 ran (committed through the index only, so B20_R116's
  working tree was unchanged).
- **Why:** Daniel's research alert of 22 Oct 2026, item 2 (`docs/RESEARCH_ALERTS.md`): can a system tell when its
  measurements cannot explain what it sees, and propose the measurement that would? The decision was a benchmark
  after the feedback contract and the Gset track. Both are now far along (B20_R103, R107; B20_R104–R116).

## What was built

`src/genesis/causal/` (DEV only; not a sealed domain and not yet a `DomainAdapter`):
- **`sem`:** planted linear structural equation models.
  - A random DAG over p observed variables, with weights sign × U(0.5, 1.5).
  - h hidden variables, each confounding one pair.
  - Laplace, uniform or Gaussian noise.
  - K environments: in each one beyond the first, a third of the variables have their noise scaled by U(1.5, 3).
  - Hard interventions on request.
  - The hidden part has its own random streams. For one seed and K, adding hidden variables leaves the graph, the
    environments and the observed noise unchanged, so studies can pair instances with and without them.
- **`admg`:** the truth as an acyclic directed mixed graph (the exact latent projection, since each hidden variable
  has two children); answer validation; d-separation; scores. The scores are directed, adjacency and bidirected
  F1, the spurious rate on confounded non-adjacent pairs, whether a hidden cause is flagged, and SHD.
- **`methods`:** established baselines, written from their papers. None of them is Genesis's.
  - PC-stable with Fisher's z test and Meek's rules.
  - An oracle PC told the true conditional independences.
  - DirectLiNGAM with the Hyvärinen–Smith pairwise measure, pruned by t tests.
  - The empty graph.

**Tests** (`tests_genesis/test_causal_domain.py`, 16):
- the generator:
  - reproducible;
  - acyclic by its order;
  - two children per hidden variable;
  - environments scale a third of the variables;
  - the sample covariance matches the model's;
  - interventions cut every incoming edge, hidden ones included;
  - refusals;
- scoring and validation on hand-built cases;
- d-separation on a chain with a hidden cause, including a collider opened by conditioning;
- the baselines:
  - the oracle PC is exact up to equivalence with no hidden variable and fooled by a hidden cause;
  - PC recovers adjacencies at large samples;
  - DirectLiNGAM orients non-Gaussian data and a chain;
  - every method's answers are valid.

## B20_R118 (preregistered here)

`scripts/b20r118_causal_calibration.py` (SHA-256 `92858c1c…66f9`), design tests in
`tests_genesis/test_causal_calibration.py`.
- **Question:** a calibration, as B20_R102 was for Gset. How often do established methods draw a causal edge where
  there is only a hidden common cause? Do three environments, pooled naively, help them?
- **Instances:** 40 seeds × (h = 0 or 3) × (K = 1 or 3), with p = 10 and N = 3,000.
- **Tests:** paired Wilcoxon tests and a headroom label (CONFOUNDING_MISLEADS / PARTIAL / MOSTLY_SAFE).
- **Development looks:** the domain's tests only.

## What it is not

There is no Genesis method yet and no claim. The benchmark's next step, after the calibration, is a method that
detects hidden causes and proposes the intervention that resolves one, scored on both.
