"""Graph conjectures and constructions with exact certificates: the Frontier's first domain (F2,
`docs/OMEGA_FRONTIER.md` §5-§6; Daniel's directive of 27 Oct 2026, 19:55).

Research plane: `expr` (a safe expression language for bounds, evaluated in floating point for search and in exact
rational interval arithmetic for verification) and `graphs` (small simple graphs, degrees d_v, average neighbour
degrees m_v, the Laplacian). Kernel side: `sealed` (the sealed calibration set: the Brankov-Hansen-Stevanovic
bounds with their transcription sources, tiers and statuses) and `verify` (exact refutation certificates). The
research plane never imports the kernel side (`test_conjecture_boundary`).
"""
