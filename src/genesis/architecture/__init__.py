"""The Autonomous Research Architect, ARA-1 (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §16).

Research plane: `graph` (the Architecture Graph), `policies` (the policy, search and evaluator libraries the graph
runs), `model`, `assumptions`, `diagnose`, `rewrite` and `ara` (the cycle). Kernel side: `zoo` (the Limitation Zoo's
generator) and `judge` (the sealed harness). No research-plane module imports the kernel side
(`tests_genesis/test_architecture_boundary.py`); ARA receives an environment only as a view that charges units.
"""
