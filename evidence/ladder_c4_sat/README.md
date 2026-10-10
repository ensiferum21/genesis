# Known-answer ladder, C4 — specialist SAT baseline (commit 6dfbb26)

Arm `sat_cadical`: cheap greedy warm start (charged) + CaDiCaL SAT-model climb,
10 CPU-seconds per rung, test rungs n = 21–40, same seed and budget as
`evidence/ladder_c4_b1/`.

Total shortfall vs published optima over n = 21–40: sat_cadical 225;
multistart 194; low_cycle 194; exchange 232 (from ladder_c4_b1). Against the
best of the three greedy arms per rung, SAT is better on 1 rung, worse on 16,
tied on 3. On complete hosts at this budget, the greedy arms are the
strongest conventional baselines; on random hard hosts (30–64 edges) SAT
certifies optima in seconds (`evidence/hard_panel_calibration/`). Comparisons
should include both kinds of baseline.
