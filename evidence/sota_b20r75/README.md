# B20_R75 evidence: E1d and the system against state-of-the-art tools: **INVALID_CPU_DELIVERY** (a builder defect in the BURER2002 kind)

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r75_sota.py`, preregistered at `fc8f950` and amended before any arm ran at `1f04796`
  (the task model caps hosts at 63 vertices, so the larger size became n63; the first run stopped while drawing
  hosts, with nothing run: `run1_stopped/run.log`). SHA-256 of the run's script `c2c1e54d…2f2b`, sent to Daniel
  before the run. Alone, pinned to CPU 0, 2,570 s; 1,080 runs in runc plus Part B. `code_identity` `afdb6b01…737b`.

## Verdict: **INVALID_CPU_DELIVERY**, and why

The preregistered validity check requires every arm's median cgroup CPU at t = 0.5 s to be at least 0.45 s.
BURER2002's was 0.166 s (every other arm: 0.665–0.726 s), so nothing of the primary comparison is read.

**Cause (found after the run, a builder defect):** MQLib accepts seeds only in 0..65535 (its option parser,
`src/main.cpp`), and `mqlib-v1` passed the study's seeds modulo 2^31. MQLib printed a usage error and exited; the
kind then returned an empty witness instead of failing, so every one of the 180 BURER2002 runs "succeeded" with
value 0 and almost no CPU. The unit tests used seeds below 65,536 and missed it. The CPU-delivery check is what
caught it. The kind is fixed in B20_R76 (seed modulo 65,536; any MQLib failure is now a failed run, not an empty
answer) and the comparison is repeated there on fresh hosts.

## What is still descriptive (never decisive)

The other five arms ran as designed (no failures; CPU delivered). Time-to-solution TTS* in CPU s (median /
75th percentile; "solved" counts hosts where the target was reached at some rung):

| | n60 (6 hosts, 404–434 edges) | n63 (6 hosts, 433–477 edges) |
|---|---|---|
| simulated bifurcation | **0.1 / 0.1**, 6 solved | **0.25 / 1.25**, 6 solved |
| the system's engine (cross_2, descent, fast repair) | 1.2 / 1.25, 6 | 1.2 / 3.0, 6 |
| E1d's candidate | 1.2 / 2.0, 6 | 3.0 / 24, 6 |
| tabu search | 0.5 / ∞, 4 | 0.5 / ∞, 3 |
| HiGHS (anytime, ≤ 2 s) | never | never |

**Part B (exact).** HiGHS with 60 s claimed optimality on none of the 12 hosts and reached the target on 1 (it ended
1–6 edges short on the others). The system's own checked route (exact LP dual plus SAT/DRAT, 120 s) certified 4 of
6 hosts at n60 and 2 of 6 at n63, in about 28–38 s where it succeeded.

These agree with B20_R70: simulated bifurcation is the fastest method, the system's engine (with the faster repair)
beats the frozen candidate on the larger hosts, and an exact MILP is far from proving optimality at this size.

## Tests

`tests_genesis/test_sota.py`: Design (5); Record (3): the verdict is INVALID_CPU_DELIVERY and the summary recomputes;
the cause (every BURER2002 run returned an empty witness, every other heuristic arm a non-empty one); the hosts are in
the e1/e1b exposure addenda.
