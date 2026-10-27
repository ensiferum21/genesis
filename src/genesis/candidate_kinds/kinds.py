"""The registry v2 kind map (B20_R67): kind name -> module under genesis/candidate_kinds/.

Why this file exists. Until B20_R67 the map lived in `candidates_v2.py`, which is one of the core files every v2
descriptor's implementation identity hashes. Adding a kind therefore changed the identity, and so the descriptor id,
of every other v2 kind, contrary to the registry's design statement ("adding a kind module changes no other kind's
identity", docs/CANDIDATE_REGISTRY_V2.md). The map now lives here, and this file is not part of any identity.

Why that is safe. A kind's identity hashes the module that is actually dispatched for it: `candidates_v2` requires
the module's first declared file to be its own source file and hashes it (see `implementation_identity`). Pointing
a kind name at a different module therefore changes that kind's identity, so every frozen descriptor of the kind is
refused (IMPLEMENTATION_CHANGED). What this file decides is only which kinds exist.

The map is closed and code-controlled: no module name, path or code comes from data.
"""
KINDS = {
    'milp-highs-v1': 'milp_highs',        # B20_R40: exact HiGHS MILP, a time-matched exact baseline
    'maxcut-tabu-v1': 'maxcut_tabu',      # B20_R67: a standard max-cut tabu search with triangle-free completion
    'ising-dsb-v1': 'ising_dsb',          # B20_R69: discrete simulated bifurcation (classical-mechanics Ising solver)
    'maxcut-eo-v1': 'maxcut_eo',          # B20_R69: tau-extremal optimization (self-organized-criticality search)
    'represent-search-v1': 'represent_search',  # B20_R71: the representation engine with a choice of move rule
    'mqlib-v1': 'mqlib',                  # B20_R74: MQLib's BURER2002, the best single max-cut heuristic of Dunning et al.
    'cpsat-v1': 'cpsat',                  # B20_R76: Google OR-Tools CP-SAT, 8 workers on one core (MiniZinc Challenge 2025 gold)
    'hybrid-swap-v1': 'hybrid_swap',      # B20_R77: cut portfolio (dSB + descent), then (1,2)-swap local search
    'solver-program-v1': 'solver_program',  # B20_R78: a program in the closed solver language, found by program search
    'solver-library-v1': 'solver_library_program',  # B20_R82: a solver program calling earlier generations' programs
    'maxsat-anytime-v1': 'maxsat',        # B20_R87: the strongest anytime MaxSAT solvers on the exact MaxSAT encoding
    'mqlib-heuristic-v1': 'mqlib_heuristic',  # B20_R87: any of MQLib's 38 heuristics (for the per-host virtual best)
    'tfx-v1': 'tfx',                      # B20_R88: native population search on edge sets, operators chosen by data
    'maxsat-anytime-2026-v1': 'maxsat2026',  # B20_R91: the MaxSAT Evaluation 2026 anytime entrants, from their sources
    'tfxw-v1': 'tfxw',                    # B20_R94: tfx-v1's search scaled past 64 vertices (multiword, tightness)
    'maxsat-anytime-large-v1': 'maxsat_large',  # B20_R94: the 2024 and 2026 champions on the DEV large domain
    'tfxw-v2': 'tfxw2',                   # B20_R96: tfxw-v1 with an operator grammar (acceptance, annealing, kicks)
    'mqlib-maxcut-v1': 'mqlib_maxcut',    # B20_R101: MQLib's max-cut heuristics on the DEV max-cut domain (Gset)
    'dsb-maxcut-v1': 'dsb_maxcut',        # B20_R101: discrete simulated bifurcation on weighted max-cut
    'mcx-v1': 'mcx',                      # B20_R104: Genesis's max-cut engine (breakout tabu, cluster moves, coarsening)
    'mcx2-v1': 'mcx2',                    # B20_R125: the engine as an interpreter of search programs (physics operators)
    'mcx3-v1': 'mcx3',                    # B20_R153: mcx2 with a construct algebra (targets, ?-guards, repeats, blocks)
}
