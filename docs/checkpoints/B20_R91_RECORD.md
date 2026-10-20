# B20_R91 record (engineering): the MaxSAT Evaluation 2026 anytime entrants, built from their submitted sources

- **Run by:** the builder, after Daniel downloaded the 2026 Evaluation's archives (Zenodo record 21358014, which
  this workspace's proxy refuses) and attached them (20 Oct 2026).
- **No claim, rule, comparator or package changes.**

## The archives

Eleven files arrived in three messages. Each was copied into its own directory and its MD5 checked against the one
Zenodo publishes; all match. Their SHA-256 are recorded in `scripts/b20r91_mse2026_tools.py` (solver archives) and
below (`results.zip` `661a3ac4…f52c`, `slides.pdf` `0531dc42…4dff`). Contents were listed, run scripts read as text;
no shipped binary was run.

## Who won 2026 (unweighted anytime track; slides and `results.zip`)

| Time limit | Ranking (anytime score) |
|---|---|
| 60 s | PASMaxSAT-c 0.861, SGAT-NuWLS-c 0.858, Aperture-GBG 0.856, NuWLS-c-2026-UB 0.855, Aperture-KBG 0.853, Aperture-IBI 0.841, DeepDist-c 0.808, NuWLS-c-2026 0.807, BouMS-CaDiCaL 0.771, BouMS 0.735, Loandra 0.705, … |
| 300 s | Aperture-KBG 0.907, PASMaxSAT-c 0.905, SGAT-NuWLS-c 0.903, Aperture-GBG 0.899, NuWLS-c-2026-UB 0.898, … |
| 1707 s | PASMaxSAT-c 0.948, Aperture-KBG 0.946, Aperture-GBG 0.944, SGAT-NuWLS-c 0.943, Aperture-IBI 0.938, … |

px-tt-open-wbo-inc is not in the ranking (two submissions were disqualified); SPB-NIM-c entered the weighted track
only.

## Builds (`scripts/b20r91_mse2026_tools.py`)

The eight ranked configurations above BouMS come from six archives; all six are built:

| Installed | From | SHA-256 | Notes |
|---|---|---|---|
| PASMaxSAT-c | solver-PASMaxSAT-c.zip | `825594bd…94f5` | bundled GMP deleted |
| SGAT-NuWLS-c | solver-SGAT-NuWLS-c.zip | `1d1b9bdc…06cd` | its learned weight file (text) installed read-only, `25e62115…d800` |
| NuWLS-c-2026 | solver-NuWLS-c-2026.zip | `ddfc30ea…a359` | |
| NuWLS-c-2026-UB | solver-NuWLS-c-2026-UB.zip | `7a9bebe4…f239` | |
| DeepDist-c | solver-DeepDist-c.zip | `7ee4555c…a9ad` | |
| Aperture-2026 | solver-Aperture.zip | `0fb72956…b511` | three configurations: GBG, KBG, IBI |

- Every shipped binary, object file, library and bundled GMP header was deleted before building (including a
  `runsolver` binary and a prebuilt Rust library); each solver was built with its own Makefile's static release
  target, against the GMP from Daniel's Ubuntu packages (B20_R87), in a fixed directory.
- **Build fixes, disclosed, none in search code:** (1) the open-wbo-based sources use std::function without
  `<functional>` (older compilers included it indirectly); their build passes `-include functional`. (2) Aperture:
  B20_R87's pipe-input patch (its reader seeks to the end of the input; the same three lines as hermax's copy), and
  its IPAMIR wrapper (the incremental C API; nothing in the command-line solver refers to it) is left out of the build
  because it does not compile under gcc 13. (3) `zipfile` drops Unix file modes; the script restores them (Aperture's
  bundled SAT solvers have configure scripts).
- **Not built:** Loandra 2026 (needs Rust crates from crates.io, which this workspace cannot reach; its prebuilt Rust
  library is not used; ranked 11th–12th), px-tt-open-wbo-inc (disqualified), SPB-NIM-c (weighted only).
- Hermax's Aperture (B20_R87) and the 2026 submission differ in 20+ source files; both are kept (`aperture` in
  `maxsat-anytime-v1`, `aperture-*` in the new kind).

## The kind: `maxsat-anytime-2026-v1`

`candidate_kinds/maxsat2026.py` (files: itself and `maxsat.py`, whose encoding and decoding it reuses unchanged).
Each solver runs with its Evaluation run script's arguments; the 2026 rules' timeout hint is passed in whole seconds
(the solvers refuse fractions), rounded up, and the run is ended at the budget by SIGTERM as in the Evaluation. The
input is the post-2022 WCNF format the 2026 instances use (`h` hard clauses, no `p` line, the standardised header),
built from `maxsat.wcnf` so a seed means the same isomorphic copy in both kinds.

**Development look (disclosed; B20_R76's first host, target 265, seed 3; 0.01 / 0.02 / 0.05 s):** PASMaxSAT-c
262 / 262 / 264; NuWLS-c-2026 263 at all three; DeepDist-c 180 (its first phase is SAT-based search); SGAT-NuWLS-c and
hermax's Aperture printed no assignment at 0.01–0.02 s (still in their first stage). tfx with B20_R89's configuration
on all 12 hosts: 13, 24, 30 and 35 of 36 runs at 0.005, 0.01, 0.02 and 0.05 s. This is why B20_R92's ladder starts at
0.005 s and counts a short run without an assignment as unsuccessful rather than failed.

## Tests

`tests_genesis/test_maxsat2026_kind.py` (7): the post-2022 text is the same instance and the same seeded copy as
`maxsat-anytime-v1`'s; the hint is whole seconds rounded up; binaries and the weight file are pinned and changes are
refused, as are bad parameters; every solver finds K10's optimum and returns checked witnesses for two seeds (one
study-sized); failures are loud; a metered runc run of every solver returns a checked witness.

## Setup of B20_R92 (preregistered with this record)

`scripts/b20r92_vs_mse2026.py`: tfx (B20_R89's configuration) against all thirteen champions (the eight 2026
configurations above and B20_R90's five) and their per-host virtual best, on 24 fresh planted and 12 fresh G(63, 0.5)
n63 hosts (seeds 20269201, 20269202); ladder 0.005–2 s (3 seeds, runc); 10 s long-budget part for tfx, the 2026 top
five, DeepDist and SPB-MaxSAT-c-FPS; CP-SAT 60 s and (planted) the checked reference; ablations of tfx's operators
(no simulated bifurcation, no parallel tempering, no crossover, no relinking and restarts, and the first design).
Labels and expectations in its docstring. Tests: `tests_genesis/test_vs_mse2026.py` (5, design).

**Toy smoke run, disclosed (dev-only seeds 99880021–99880022, one host per family).** It ran while the builder's
rebuild check of the 2026 binaries occupied the other core. The maxsat kinds pin their solver to the sandbox's first
core, which was the busy one, so the wall-clock-budgeted champions received less CPU (median 0.42–0.50 s at 0.5 s) and
tfx's 10 s run overran its wall guard: every label read INVALID_CPU_DELIVERY. That shows the validity check works and
that the study must run alone (as every study here does). It also showed SGAT-NuWLS-c and Aperture printing no
assignment at 0.05 s on some runs, so before preregistration the failure check was moved to runs at 0.5 s and above
(below that, no assignment counts as unsuccessful). On its planted host Aperture-KBG and NuWLS-c-2026 had TTS* 0.06 s
and tfx 0.02 s; the expectation was revised accordingly (in the script).
