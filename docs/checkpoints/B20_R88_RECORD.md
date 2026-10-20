# B20_R88 record (engineering and development looks): `tfx-v1`, a native engine with operators from physics, biology and the independent-set literature

- **Run by:** the builder, for Daniel's request (20 Oct 2026) to beat the most tuned solvers, drawing on nature and
  physical systems. B20_R89 (the system configures the engine) and B20_R90 (the head-to-head) are preregistered with
  this record.
- **No claim, rule, comparator or package changes.**

## Development looks (disclosed; B20_R76's 12 evidence hosts, never a study's fresh hosts)

Direct calls, alone on one core, 3 seeds per host (36 runs per cell; "hits" = runs reaching B20_R76's target, a
certified optimum on most hosts). The MaxSAT solvers' seeds pick isomorphic copies (B20_R87).

| Arm | 0.05 s | 0.1 s | 0.25 s | 0.5 s | 2 s |
|---|---|---|---|---|---|
| `tfx` first design (C; cut warm starts: dSB + descent, then (1,2)-swap ILS, K 4) | **30** | **33** | **32** | **34** | **36** |
| DeepDist (ECAI 2025) | 9 | 16 | 27 | 31 | 36 |
| SPB-MaxSAT-c-FPS (MSE 2024 winner) | 4 | 6 | 11 | 16 | 31 |
| NuWLS-c-IBR (MSE 2024 podium) | 6 | 8 | 9 | 11 | 20 |
| TT-Open-WBO-Inc 2024 (IntelSAT) | 6 | 7 | 10 | 13 | 20 |
| Aperture (SOFT 2026) | 0 | 0 | 0 | 0 | 19 |
| `hybrid-swap-v1` (B20_R77's engine, Python) | 23 | 26 | 27 | 30 | 33 |

Readings. The strongest champion here is the pure clause-weighting local search, DeepDist; the SAT-based hybrids
(SPB-MaxSAT-c, NuWLS-c, TT-Open-WBO-Inc, Aperture) pay for their SAT phases at these budgets. The C rewrite of
B20_R77's idea is ahead of every champion up to 0.5 s and ties DeepDist at 2 s.

**MQLib, all 38 heuristics at 0.5 s (1 seed, 12 runs each):** the table at the end of this record. The cut-based
max-cut heuristics reach 0–5 of 12: a cut plus a greedy completion is not the optimum on these hosts (B20_R77's
diagnosis).

**Variants of `tfx` (sum of hits at 0.05, 0.1 and 0.25 s, of 108; one look, noise about ±3):**

| Variant (changes from the first design) | Hits | Per budget |
|---|---|---|
| first design (ws 3: dSB + descent, frac 0.3, K 4) | 92 | 27 / 32 / 33 |
| **descent warm starts only (ws 2)** | **105** | 34 / 35 / 36 |
| dSB warm starts only (ws 1) | 75 | 22 / 25 / 28 |
| K 8 | 101 | 32 / 33 / 36 |
| crossover every 5 iterations, K 8 | 100 | 31 / 34 / 35 |
| frac 0.5 | 99 | 32 / 33 / 34 |
| path relinking 20% | 97 | 28 / 34 / 35 |
| two kicks | 96 | 31 / 32 / 33 |
| parallel tempering (K 6, both ladders) | 94 | 28 / 31 / 35 |
| restarts after 200 | 94 | 28 / 32 / 34 |
| three-body mean-field annealing added (gradient, 100 steps) | 90 | 27 / 30 / 33 |
| ant-colony memory (rho 0.1 / 0.3) | 85 / 87 | |
| K 2; frac 0.1 | 85; 77 | |

Readings, stated plainly. At these budgets, in C, **simulated bifurcation does not pay**: cut descent gives better
warm starts per CPU second (ws 2: 105; ws 1: 75). The ant-colony memory hurts. A larger population helps. Parallel
tempering, crossover, relinking and restarts are within noise of the first design. None of this is used to choose the
configuration: B20_R89 races configurations on fresh training hosts and decides.

**Other host families (8 dev-only hosts, seed 99887766, never used by a study):** G(63, 0.5), G(63, 0.3), planted
(0.8, 0.06) and planted (0.9, 0.2), 2 each: `tfx` (ws 2, K 8) and DeepDist agree on every host at 2 s and at 10 s.
At n ≤ 63 these problems saturate for the two strongest solvers within 2 s, so the contest is time to solution, which
is what B20_R90 measures (and B20_R90's long-budget part checks that no champion finds more given 10 s).

## Engineering

- `candidate_kinds/native/tfx.c`: the engine (described in its header). Phase 1: warm starts by a bitmask (dSB on the
  host's max-cut, Goto et al. 2021; one-flip cut descent; three-body mean-field annealing on the edge variables, as a
  damped mean-field iteration or as normalised gradient steps on the variational free energy after the free-energy
  machine, Shen et al. 2025), each completed greedily; a pool keeps the K best distinct. Phase 2: (1,2)-swaps
  (Andrade, Resende and Werneck 2012) and iterated local search round-robin, with acceptance by a fixed probability
  or by Metropolis at per-member temperatures with replica exchange (parallel tempering), and optional crossover
  (intersection, refill, improve), an ant-colony edge memory, path relinking toward the best, and restarts. 64-bit
  vertex bitsets (n ≤ 64).
- `candidate_kinds/tfx.py`, kind `tfx-v1`: {cpu_seconds, config}; config must give each of 20 keys a value from a
  closed list (SPACE); DEFAULT is the first design. The binary is built by `scripts/b20r88_build_tfx.py` (gcc 13.3,
  `-O3 -std=gnu11 -static`, deterministic), pinned by SHA-256 (`1b0f7733…f386`); the source and the module are the
  kind's files. The kind re-checks the returned edge set (a subset of the host, triangle-free).
- **Defect found by the new tests and fixed before any study:** with restarts on, a tiny host could make the engine
  loop for ever (the restart waited for a cut colouring not seen before, and a 5-vertex host has few). Restarts now
  complete a fresh descent colouring directly.

## Tests

`tests_genesis/test_tfx_kind.py` (10): the binary is the pinned build and rebuilds from the source to the same bytes;
the identity covers module and source; a changed binary is refused; parameters are closed (each key, extra keys,
values off the list, booleans, strings, budgets); every listed value of every key reaches the binary and K8's optimum
(16) is found; optima match brute force on C5, the wheel W5, K5 and six random 6-vertex hosts for DEFAULT and four
random configurations; Turán (K10: 25, K12: 36); 40 random configurations on random hosts (n 20–63) return checked
witnesses of at least half the edges; the budget is kept; failures are loud (a failing binary, an unknown key, a
repeated edge); a metered runc run returns a checked witness.

## MQLib, all 38 heuristics (0.5 s, 1 seed, B20_R76's 12 hosts; hits of 12, mean gap to the target)

| Heuristic | Hits | Gap |
|---|---|---|
| MERZ2004 | 5 | 1.08 |
| FESTA2002GVNSPR | 5 | 1.17 |
| FESTA2002GVNS | 5 | 1.25 |
| FESTA2002G | 5 | 1.33 |
| MERZ2002GREEDYKOPT | 5 | 1.33 |
| MERZ2002ONEOPT | 4 | 1.17 |
| GLOVER1998a | 4 | 1.25 |
| ALKHAMIS1998 | 4 | 1.33 |
| HASAN2000TS | 4 | 1.33 |
| PALUBECKIS2004bMST3 | 4 | 1.33 |
| PALUBECKIS2004bSTS | 4 | 1.33 |
| BEASLEY1998TS | 4 | 1.42 |
| HASAN2000GA | 4 | 1.42 |
| PALUBECKIS2004bMST1 | 4 | 1.42 |
| PALUBECKIS2004bMST2 | 4 | 1.42 |
| PALUBECKIS2004bMST4 | 4 | 1.42 |
| PALUBECKIS2004bMST5 | 4 | 1.42 |
| PALUBECKIS2006 | 4 | 1.42 |
| FESTA2002VNS | 4 | 1.5 |
| FESTA2002VNSPR | 4 | 1.5 |
| PARDALOS2008 | 4 | 1.5 |
| FESTA2002GPR | 4 | 1.58 |
| LAGUNA2009HCE | 4 | 1.58 |
| LODI1999 | 4 | 1.75 |
| BURER2002 | 3 | 1.42 |
| KATAYAMA2001 | 3 | 1.42 |
| LU2010 | 3 | 1.5 |
| MERZ1999GLS | 3 | 1.5 |
| GLOVER2010 | 3 | 1.58 |
| MERZ2002KOPT | 3 | 1.58 |
| KATAYAMA2000 | 3 | 1.67 |
| MERZ2002GREEDY | 3 | 1.83 |
| MERZ1999CROSS | 3 | 1.92 |
| BEASLEY1998SA | 2 | 2.25 |
| MERZ1999MUTATE | 2 | 3.33 |
| DUARTE2005 | 0 | 5.42 |
| DESOUSA2013 | 0 | 8.25 |
| LAGUNA2009CE | 0 | 9.0 |

The three best other than BURER2002 (which has its own arm), by hits then gap: MERZ2004, FESTA2002GVNSPR,
FESTA2002GVNS. B20_R90 runs them with BURER2002 as the per-host virtual best of MQLib.

## Setup of B20_R89 and B20_R90 (preregistered with this record, before either has run)

- `scripts/b20r89_configure_tfx.py` (**B20_R89**): successive halving over 128 configurations of `tfx-v1` (126 drawn
  uniformly from its space, seed 20268902, plus DEFAULT and the development pick, disclosed) on 32 fresh n63
  planted training hosts (seed 20268901); score: mean gap to the host's target at 0.02, 0.05, 0.1 and 0.25 s;
  rounds of 4, 8, 16, 32 hosts (2 seeds), then 4 seeds; the frozen configuration goes to `config.json`.
- `scripts/b20r90_beat_the_champions.py` (**B20_R90**): the frozen configuration against DeepDist, SPB-MaxSAT-c-FPS,
  NuWLS-c-IBR, TT-Open-WBO-Inc and Aperture, and against their per-host virtual best; references B20_R77's engine,
  BURER2002 and MQLib's next three heuristics (with their virtual best) and CP-SAT; 24 fresh planted n63 hosts (seed
  20269001) and 12 fresh G(63, 0.5) hosts (seed 20269002); the ladder 0.05–2 s with 3 seeds in runc, a 10 s
  long-budget part for tfx and the champions, CP-SAT 60 s and (planted) the checked reference. Labels:
  `champions_P` / `champions_D` (TFX_BEATS_EVERY_CHAMPION, A_CHAMPION_BEATS_TFX, TFX_MATCHES_CHAMPIONS, MIXED),
  `vbs_P` / `vbs_D` (TFX_BEATS_VBS, VBS_BEATS_TFX, TFX_MATCHES_VBS, UNRESOLVED), `long_budget`
  (NO_CHAMPION_FINDS_MORE or CHAMPIONS_FIND_MORE). Validity as B20_R81.
- **Expectations** are in each script's docstring.
- **Smoke runs, disclosed (toy scale, dev-only seeds 99880001–99880012, never the studies' seeds or hosts):**
  B20_R89 with 6 drawn configurations on 4 hosts, and B20_R90 with DEFAULT on one planted and one G(63, 0.5) host:
  both ran end to end in runc (no failure; median CPU at 0.5 s 0.66–0.99 s for every arm). The toy race showed many
  configurations tied at zero gap from 0.05 s, so the score's budgets gained 0.02 s before preregistration.
- Tests: `tests_genesis/test_beat_champions.py` (11, design).
