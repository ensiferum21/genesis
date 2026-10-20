# B20_R81 record: the system's own solver beats CP-SAT and BURER2002, but so does a random program, and the builder's engine stays about five times faster

- **Run by:** the builder. DEV only. **Setup:** `e579deb`, before B20_R79 and B20_R80 ran. Alone, pinned; interrupted
  by a container restart after 7 of 24 hosts and resumed from its saved rows (resumable by design).
- **Evidence:** `evidence/self_found_solver_b20r81/` (README with tables). Independent recomputation agrees.

## Labels

- **GV4 headline, the system's solver against the builder's engine: UNRESOLVED.** The engine is about five times faster
  (median TTS* 0.1 s against 0.5 s; 75th percentile 0.25 s against 1.2 s); both preregistered intervals end exactly at
  the −1 boundary, so the rule does not call it. B20_R76's per-host statistic calls the engine faster.
- **Search against random programs: UNRESOLVED** (0.00 [0.00, 1.26]; 0.06 [−0.74, 1.74]): on fresh hosts the search's
  program and the random one are indistinguishable (0.5 / 1.2 s against 0.5 / 1.25 s).
- **The system's solver against the state of the art: SELF_FOUND_BEATS_SOTA** (faster than BURER2002 and CP-SAT at
  both quantiles; 24 of 24 targets within 2 s against 6 and 0).
- **B20_R77 replicated: ENGINE_BEATS_SOTA** on 24 fresh hosts.

## What it means

The system, given parts and no assembly, produced a solver that beats the two state-of-the-art tools tested in this
regime, and B20_R77's builder-made result replicates. But a random program from the same language does the same, so
the credit belongs to the parts (the system's own cut representation and generic search steps), not to the program
search; and the builder's engine (simulated bifurcation plus a pooled swap search) is still about five times faster.
For GV4 this is weak evidence: the search did not beat random sampling on these hosts, which are too easy for it to
matter. Harder tasks (larger hosts, other families) are where a search could show its worth.

**Against the expectation:** expected SEARCH_HELPS, BUILDER_BEATS_SELF_FOUND and MIXED against the tools; observed
UNRESOLVED, UNRESOLVED and SELF_FOUND_BEATS_SOTA.

## Tests

`tests_genesis/test_self_found_solver.py`: Record for B20_R81 (4). Exposure addenda: 24 hosts.
