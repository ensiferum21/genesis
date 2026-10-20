# B20_R94 record (engineering): a large triangle-free domain, an engine that scales to it, and the champions on it

- **Asked by:** B20_R93's adaptation cell, whose work orders after B20_R92 were a task model and engine beyond n = 63
  (SIZE_CAP, SATURATION: chronic), quality at equal time and sequential stopping (the last two are `genesis.anytime`,
  B20_R93). Daniel's milestone: show that Genesis solves problems that other solvers cannot solve as well within the
  same time budget.
- **Built by:** the builder. **No claim, rule, comparator or package changes; every existing identity unchanged.**
- **Preregistered with this record:** B20_R95 (`scripts/b20r95_configure_tfxw.py`), the configuration race below.

## The domain: `triangle_free_large_v1` (DEV only)

| Part | What |
|---|---|
| `models_large.py` | `LargeGraphTask` and `LargeCandidateGraph`, n <= 1023, DEV split only. Separate models on purpose: code for the n <= 63 domains validates `GraphTask` (and some of it treats any domain that is not triangle-free as the 4-cycle domain), so it can never receive a large task |
| `graphs_large.py` | two independent edge-driven triangle predicates (merged sorted neighbour lists; neighbour bitsets), a disagreement being a checker error; a certified upper bound from an edge-disjoint triangle packing (greedy, re-checked from its data); the colour-refinement exposure identity (isomorphic hosts always collide, so a seen host is never admitted as fresh) |
| `domains.TriangleFreeLargeAdapter` | parse, view, validate, the packing bound, seeded generation (planted_cluster and G(n, p) from 64 to 1023 vertices), no certified optimum; in `DEV_ADAPTERS`, not in the sealed `ADAPTERS` (and not in kernel.receipts.DOMAINS), so no sealed receipt can name it |
| `candidates_large.py` | registry v2's discipline (closed kind map, bounded child that sees only the view, runc with the cgroup meter or rlimits, strict decoding, the domain re-checks every witness) under its own schema `genesis-candidate-descriptor-large-v1` and identity, with ceilings sized for large hosts (CPU up to 600 s, output up to 8 MiB). `candidates_v2.py`, `graphs.py` and `models.py`, which every v2 identity hashes, are untouched: B20_R92's 160 frozen descriptors still build to the recorded ids (tested) |

## The engine: `tfxw-v1`

tfx-v1's search (`native/tfxw.c`), rebuilt to scale past 64 vertices, every operator and parameter kept:
- vertex sets of W = ceil(n / 64) words;
- per member and host edge, the **tightness** t (common member neighbours of its endpoints: an edge outside the member
  is free at 0 and a swap candidate at 1), updated in O(W + degree) per change (the technique of Andrade, Resende and
  Werneck's independent-set local search, on the triangle hypergraph);
- per member edge, **c1**: how many swap candidates its triangle alone blocks; a (1,2)-swap needs two, so the local
  search skips every member edge with fewer without looking at its neighbourhood;
- local search from a work list (only edges near a perturbation are re-examined); undo logs instead of copies;
  members loaded in bulk (O(m W)) for crossover, restarts and cut completion;
- one new choice, **kpick**: a kick forces in the least tight of kpick sampled unchosen edges (1 is tfx-v1's uniform
  choice).

A checked build (`-DTFXW_CHECK`) recomputes t, c1, sizes and memberships from scratch after every iteration and
aborts on any difference: 48 runs over four configurations and hosts of 9–130 vertices, clean. Built as tfx-v1 is
(`scripts/b20r94_build_tfxw.py`; gcc 13.3, `-O3 -static`, deterministic: a rebuild gives the same bytes), pinned
`9e6ac3d6…5311`.

## The champions on large hosts: `maxsat-anytime-large-v1`

All thirteen (the 2024 five and the 2026 eight) on the large domain, without touching their kinds (whose files are in
B20_R87–R92's identities): their encodings, commands, arguments, timeout hint, SIGTERM at the budget, parsing and
hard-clause re-check. One change in their favour: encoding a large instance takes the harness a second or more
(1.2 s of Python for G(256, 0.5), 350,231 triangles), which the n <= 63 kinds charge to the solver; here the solver's
budget starts after the encoding, and descriptors allow 5 s for it.

## Development looks (disclosed; dev-only hosts drawn with Python's `random` and seeds that no study uses)

- **Correctness:** 120 of 120 runs on hosts of 7 vertices at the brute-force optimum; Mantel's value on K_n for n = 5,
  10, 20, 64, 65, 100, 128, 200.
- **Against tfx-v1 on 12 n63 hosts** (planted and G(63, 0.5), B20_R89's configuration, 3 seeds at 10, 50, 250 ms):
  equal values at 50 and 250 ms; at 10 ms within one or two edges (tfx's one-word operations are faster).
- **Speed, G(256, 0.5) (16,395 edges):** the first draft managed about 60 iterations per second. A profile put the
  time in looking for swaps at member edges that had none; the candidate counts raised it about 6×, bulk loading
  further. kpick barely changed the rate here.
- **Against the champions, the same G(256, 0.5) host** (before the encoding fix, so each champion lost about 1.2 s of
  its budget to encoding): at 5 s PASMaxSAT-c 8,535, DeepDist 8,585, NuWLS-c-2026-UB 8,520, Aperture-KBG 8,431,
  SPB-MaxSAT-c-FPS 8,431; at 30 s 8,816, 8,811, 8,520, 8,791, 8,767. tfxw (B20_R89's configuration): 8,943 at 1 s
  (first draft), 8,971 at 30 s; after the speed-ups 8,962–8,984 at 3 s. On this one host, tfxw at 1 s found more than
  every champion found in 30 s. This is why B20_R95 races at 1 and 5 s and the head-to-head after it compares values
  at equal time.

## Tests

`tests_genesis/test_large_domain.py` (14): the separate models and their caps, the sealed registry unchanged, both
predicates against brute force, witness checks, the packing bound valid against brute force and its tampering refused,
the identity invariant under relabelling, seeded DEV-only generation with exclusion, the view and purposes, both kinds'
parameters, B20_R92's descriptors unchanged, the large runner's descriptors and refusals, tfxw and two champions end to
end through the runner in runc and under rlimits. `tests_genesis/test_configure_tfxw.py` (5): B20_R95's design.

## Setup of B20_R95 (preregistered with this record)

`scripts/b20r95_configure_tfxw.py`: successive halving over 64 configurations of `tfxw-v1` (62 drawn, B20_R89's frozen
configuration, DEFAULT) on 16 fresh training hosts (planted_cluster and G(n, 0.5) at n = 128 and 256; seed 20269501),
scored by the Evaluation's anytime score against targets (B20_R89's configuration at 10 s, two seeds; PASMaxSAT-c and
DeepDist at 10 s), at 1 and 5 s. Expectation in its docstring.
