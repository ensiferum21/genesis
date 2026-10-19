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
}
