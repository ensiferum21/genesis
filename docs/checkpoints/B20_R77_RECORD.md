# B20_R77 record (part 1, engineering and setup): a new engine from B20_R76's diagnosis, and a powered comparison

- **Run by:** the builder. Asked for by Daniel (19 Oct 2026): fix the unresolved comparison, advance the system with
  the builder's best knowledge and intuition, and give a verdict.
- **No claim, rule, comparator or package changes.**

## Environment incident after B20_R76 (not a code defect)

The first commit matrix after the B20_R76 record ran 1,007 tests with 15 errors and 1 failure. The pinned toolchain
(E prover, CaDiCaL, DRAT-trim, Lean, zstd) was intact at `/srv/toolchain`, but the link to it from the home directory
(`~/toolchain`, where `verification/tools.py` looks) had disappeared from the workspace after B20_R76 had run (its log
records the CaDiCaL and DRAT-trim identities). The link was restored; every pinned tool resolves to its pinned
identity (CaDiCaL `24fb9928…`, as in B20_R76's log). The erroring module and the failing test pass, and the matrix
re-run passed: 1,009 tests, no failure, no skip.

## Diagnosis: why every fast arm missed the hardest B20_R76 host (development looks, disclosed)

All on B20_R76's evidence hosts, none of this study's. On the n63 host with 490 edges, every arm with 2 s stopped at
312–314, and CP-SAT with 60 s found 315 (certified optimal by the reference).
- CP-SAT, 90 s, 8 workers: 315 again (bound 333). **The optimum is not bipartite:** its largest bipartite part has
  300 edges, so 15 of its edges lie inside the two sides. The host's largest cut found in 60 s: 308 (bound 329).
- The optimum's own two-colouring, with all of that colouring's cut edges kept (305), completes to only 314. To reach
  315 it gives up 5 cut edges to admit 6 more same-side edges. dSB's colourings: cut 305 + 8, or 303 + 10 (313).
- So a search over cuts optimizes the wrong objective there; reaching such optima needs moves in the space of edge
  sets. (On the other hosts cut searches can reach the target, but on one n63 host dSB, the system's descent and the
  candidate each reached 295 in only 1 of their 15 runs in B20_R76; in the looks below, adding one-flip descent
  restarts to the portfolio took the hybrid there from 0 to 3–4 of 4 runs.)

## The engine: `hybrid-swap-v1` (registry v2)

A portfolio of cut searches, then iterated local search on the problem itself (`candidate_kinds/hybrid_swap.py`):
1. For 80% of the budget, alternate a batch of simulated bifurcation (exactly `ising-dsb-v1`'s dynamics) with an equal
   share of one-flip descents from random colourings; keep the 4 best distinct completed colourings.
2. For the rest, on each: (1,2)-swaps (remove one chosen edge, add two edges only it blocked; Andrade, Resende and
   Werneck 2012's move for independent sets, on the hypergraph whose vertices are host edges and whose hyperedges are
   host triangles), then iterated local search round-robin (force in one random edge, repair, swap; keep if no
   smaller, else with probability 0.1).

The ideas are published ones (dSB; descent; algorithm portfolios, Huberman et al. 1997, Gomes and Selman 2001; ARW
swaps). The builder combined them from the diagnosis; the system's own representation search did not propose it.
Its constants were chosen on the looks below and frozen before this study's hosts were drawn.

**Development looks, disclosed (B20_R76's 12 hosts, 4 seeds each unless stated; "hits" = runs reaching the target):**

| Variant | Budget | Hits |
|---|---|---|
| edge-space annealing from scratch (3 seeds) | 2 s | 0 of 36 (10–25 edges short) |
| dSB alone | 2 s | 38 of 48 |
| dSB 1.3 s, then (1,2)-swap ILS | 2 s | 41 of 48 |
| dSB 0.7 s, then (1,2)-swap ILS | 2 s | 39 of 48 |
| dSB with a pool of 4, then swaps and ILS (65% / 35%) | 2 s | 40 of 48 |
| the same with descent alternating (half the portfolio), 65% / 35% | 2 s | 44 of 48 |
| the same, 80% / 20% (chosen) | 2 s | 45 of 48 |
| chosen, at 0.5 s; without descent; dSB alone | 0.5 s | 38; 36; 35 of 48 |
| `hybrid-swap-v1` as written (witnesses re-checked) | 2 s / 0.5 s | 45 / 40 of 48 |

On the 490-edge host the kind as written reaches 315 in 4 of 4 runs at 2 s and 2 of 4 at 0.5 s; dSB alone in none
(0 of 4 at 2 s).

**Tests:** `tests_genesis/test_hybrid_swap.py` (9): registered and bound to its module, adding it changes no other
kind's identity; closed parameters; dSB's constants; a (1,2)-swap on its own (K4 minus an edge); kicks and swaps keep
the set triangle-free (300 rounds, each re-checked); optima against brute force (C5, the wheel W5, K5, four random
7-vertex hosts); Turán (K10: 25); the budget; a metered runc run with a checked witness.

## The study (preregistered): `scripts/b20r77_engine_vs_sota.py`

24 fresh n63 hosts (seed 20267711); arms engine, system, dsb, tabu, candidate, BURER2002, CP-SAT (anytime) on the
ladder 0.05–2 s with 3 seeds each; Part B CP-SAT 60 s and the checked reference. **Primary:** Rønnow et al.'s
speedup of quantiles, log2(TTS*_tool(q) / TTS*_engine(q)) at q = 0.5 and 0.75, paired bootstrap over hosts; overall
ENGINE_BEATS_SOTA only if the engine is more than twice as fast as both tools at both quantiles. The statistic was
chosen after B20_R76 (whose per-host median has no power when each method fails on some hosts); B20_R76's statistic is
kept as a secondary. A design test shows the primary is honest about the case that matters: if BURER2002 solves 9 of
24 hosts at 0.05 s and the engine all of them at 0.25 s, the typical-host comparison is UNRESOLVED, because a
resample can have BURER2002 solve half.

**Expectation, stated before running:** ENGINE_FASTER than CP-SAT at both quantiles; against BURER2002 ENGINE_FASTER
at q = 0.75, unsure at q = 0.5; overall ENGINE_BEATS_SOTA or MIXED, MIXED slightly more likely.

**Tests:** `tests_genesis/test_engine_vs_sota.py` (7, design).

# B20_R77 record (part 2, the study): the new engine against CP-SAT and BURER2002, **ENGINE_BEATS_SOTA**

- **Run by:** the builder. DEV only.
- **Before the run:** the commit matrix re-run with the toolchain link restored passed (1,009 tests, no failure, no
  skip). **Setup:** `b295c2a`; script SHA-256 `9da9935d…c1e0`, sent before the run. Alone, pinned to CPU 0, 5,475 s;
  `code_identity` equals the committed tree's. **Evidence:** `evidence/engine_vs_sota_b20r77/` (README with tables).

## Result: **ENGINE_BEATS_SOTA**

Valid (CPU delivered, no failed run). On 24 fresh n63 hosts the engine is more than twice as fast as both tools at
both quantiles: against BURER2002 log2 10.0 [1.32, 10.0] (typical host) and 10.0 [10.0, 10.0] (hard host); against
CP-SAT run anytime 10.0 [10.0, 10.0] at both. B20_R76's per-host statistic agrees. An independent recomputation from
the rows (no study code) reproduces every value, interval and verdict; 20 other bootstrap seeds give the same
primary verdicts.

Descriptive: the engine reached the best known value within 2 s on 24 of 24 hosts (median TTS* 0.1 s, 75th
percentile 0.25 s); dSB 21, the system's B20_R76 engine 19, tabu 15, E1d's candidate 15, BURER2002 10, CP-SAT 0.
On 3 hosts only the engine reached it (two certified optimal), CP-SAT with 60 s included; CP-SAT at 60 s reached 3
targets and proved none optimal.

**What the result does not say.**
- **dSB alone also beats both tools** on this statistic; the engine's lead over dSB is UNRESOLVED (more targets, 24
  against 21, but not resolved as faster). Over the system's B20_R76 engine the improvement is resolved: about 12
  times faster on the typical host and 40 times on the hard host.
- **The edge is the last edge:** with "within one edge of the best known value" as the target (exploratory), the
  typical-host comparison with BURER2002 is UNRESOLVED.
- **The arena is the engine's:** anytime, up to 2 CPU s on one core; CP-SAT is built for proofs with time and cores,
  and BURER2002 solves max-cut, a relaxation. One host family, n63, builder-run DEV; the target includes the engine's
  own values (certified on 16 hosts).

**Against the expectation.** The builder expected ENGINE_BEATS_SOTA or MIXED, MIXED slightly more likely. During
the run the builder gave Daniel a running tally of hosts reached, explicitly not a verdict.

## Consequence

- The first preregistered DEV result in which a solver of the system beats the state-of-the-art tools tested, on
  their shared measure (time to the best known value), in this regime. It licenses nothing; a claim needs a frozen
  descriptor, a calibration under a rule whose strong baselines include these tools, an independent custodian and
  replication (B20R77-OPEN-1).
- Physics plan idea 2 (physics-inspired solvers) is confirmed again: simulated bifurcation carries much of the
  advantage. The diagnosis-led addition (portfolio and (1,2)-swaps) is what reaches the targets dSB misses.

## Tests

`tests_genesis/test_engine_vs_sota.py`: Design (7); Record (5).
