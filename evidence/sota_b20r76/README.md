# B20_R76 evidence: E1d's candidate and the system's best engine against CP-SAT and BURER2002: **UNRESOLVED**

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r76_sota.py`, preregistered at `1b01159` (SHA-256 `39509fd3…bdf0`, sent to Daniel before
  the run; unchanged since). Alone, pinned to CPU 0, 3,306 s; 1,260 runs in runc plus Part B. `code_identity`
  `f8d7c3b9…ef0c`, the committed tree.
- **Tools:** MQLib BURER2002, binary SHA-256 `9e760cb7…c4e3` (commit `5854962`); OR-Tools CP-SAT 9.15.6755, tree
  SHA-256 `fb5ef9ac…67f9`, 8 workers on the one core.

## Verdict: **UNRESOLVED** (preregistered rule, recomputed independently from the rows)

Valid: every arm's median CPU at t = 0.5 s was 0.674–1.0 s (threshold 0.45 s), and no run of any arm failed
(BURER2002 now runs; B20_R75's defect is fixed). The overall rule reads the system's engine at n63 against both
tools; both pairs are UNRESOLVED.

Per pair at n63: median log2(TTS*_tool / TTS*_x) over 6 hosts, bootstrap 90% interval (positive = x faster).

| x | vs BURER2002 | vs CP-SAT (anytime, ≤ 2 s) |
|---|---|---|
| the system's engine (cross_2, descent) | 0.0 [−0.5, 10.0] UNRESOLVED | 10.0 [0.0, 10.0] UNRESOLVED |
| E1d's candidate | 0.0 [−1.79, 10.0] UNRESOLVED | 10.0 [0.0, 10.0] UNRESOLVED |
| simulated bifurcation | 6.29 [0.0, 10.0] UNRESOLVED | 10.0 [5.0, 10.0] **X_FASTER** |
| tabu search | 0.0 [0.0, 5.0] UNRESOLVED | 5.0 [0.0, 10.0] UNRESOLVED |
| HiGHS (anytime) | 0.0 [−10.0, 0.0] UNRESOLVED | 0.0 [0.0, 0.0] COMPARABLE (both never) |

At n60, against CP-SAT: the system, the candidate and simulated bifurcation are X_FASTER (intervals [10, 10],
[5, 10], [10, 10]); against BURER2002 every pair is UNRESOLVED.

**Why it is unresolved.** Six hosts per size is few for a median of capped ratios. A host where neither method
reaches the target within 2 s counts as a tie (0), and one where only one does counts ±10. BURER2002 is the fastest
method on the hosts it solves (0.05 s on three) and never reaches the target on 7 of 12, so its ratios with the
other heuristics are ±10 in both directions. Against CP-SAT, two n63 hosts were reached by neither the system nor
CP-SAT (one where the system's best was 297 of 298, and the 490-edge host whose 315 no method reached within 2 s),
and those ties keep the lower end of the interval at 0. The bootstrap seed does not matter: 20 other seeds give
the same verdict for every pair.

## Descriptive (never decisive)

Time-to-solution TTS* in CPU s (median / 75th percentile) and hosts where the target was reached at some rung
within 2 s:

| | n60 (6 hosts, 405–438 edges; 5 certified) | n63 (6 hosts, 444–490 edges; 5 certified) |
|---|---|---|
| simulated bifurcation | 0.1 / 0.25, **6** | 1.2 / 6.0, **5** |
| the system's engine | 0.5 / 3.0, **6** | 3.0 / ∞, 4 |
| E1d's candidate | 1.2 / 24, 5 | 6.0 / ∞, 4 |
| tabu search | 0.05 / ∞, 4 | 1.25 / ∞, 3 |
| BURER2002 | 0.1 / ∞, 3 | ∞ / ∞, 2 |
| CP-SAT (anytime) | never, 0 (7–18 edges short at 2 s) | never, 0 (9–16 short) |
| HiGHS (anytime) | never, 0 | never, 0 |

**Part B, exact (60 s each, on the pinned core).** CP-SAT reached the target on 2 of 12 hosts and HiGHS on none;
neither claimed optimality on any host. On the others CP-SAT ended 2–7 edges short and HiGHS 1–8 short, while on
each of them some heuristic reached the target in a run of at most 2 s. But on the largest host (n63, 490 edges) CP-SAT's 60 s run
found 315, certified optimal by the reference, which no heuristic found within 2 s (all ended at 312–314). The
system's own checked route (exact LP dual plus SAT/DRAT, 120 s) certified 10 of 12 targets, median 34 s; on the
other two it timed out one edge above the target.

## How to read it

- At budgets up to 2 CPU s, the max-cut heuristics (simulated bifurcation, the system's engine, the candidate, tabu,
  BURER2002) reach the best known value far more often than CP-SAT or HiGHS run anytime; that is where they are
  strong. CP-SAT's strength is the long run: given 60 s, it found an optimum none of them found in 2 s.
- Among the heuristics, the preregistered test cannot order the system and BURER2002. Simulated bifurcation and the
  system reach the target most often, BURER2002 fastest when it does.
- Every heuristic arm here solves max-cut and completes the cut greedily (BURER2002 through MQLib, then the shared
  completion); CP-SAT and HiGHS solve the stated problem itself.
- CP-SAT ran its portfolio of 8 workers on one core, so its CPU equals the other arms'. On a multi-core machine it
  would run them in parallel; this is a CPU-matched comparison, not CP-SAT's best wall-clock configuration.
- **Expectation, stated before running:** SYSTEM_BEATS_SOTA. It was not borne out. A provisional reading the builder
  gave Daniel during the run, from the first n63 hosts, also said SYSTEM_BEATS_SOTA; it was wrong, and the verdict
  is the preregistered one.
- Scope: one host family (planted clusters, p_in 0.8, p_out 0.06), n60 and n63 (the task model's maximum), 6 DEV
  hosts per size, builder-run.

## Tests

`tests_genesis/test_sota_v2.py`: Design (5); Record (5): valid, and the analysis and verdict recompute; who reached
the target within 2 s, and the 315 host; values bounded by the target and isolation; the tools are the pinned ones
and the descriptors the recorded ones; the hosts are fresh and in the e1/e1b exposure addenda.
