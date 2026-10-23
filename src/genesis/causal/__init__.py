"""Causal discovery with hidden variables (B20_R117; `docs/RESEARCH_ALERTS.md`, item 2): a DEV-only benchmark.

Multi-environment linear structural equation models over observed variables, some of them confounded by planted
hidden variables. A method sees only the observed data (one matrix per environment) and answers with a mixed graph:
directed edges (direct causes), undirected edges (adjacent, direction not decided) and bidirected edges (a hidden
common cause). The answer is scored against the planted truth.

Modules:
  * `sem`: the generator (graphs, weights, non-Gaussian noise, environments, interventions);
  * `admg`: the truth as an acyclic directed mixed graph, answer validation, d-separation, scoring;
  * `methods`: established baselines written from their papers (PC with Fisher-z tests; DirectLiNGAM), an oracle
    PC that is told the true conditional independences, and an empty graph.

Not a sealed domain and not yet a `DomainAdapter`: DEV studies only. Nothing here is a claim about real data.
"""
