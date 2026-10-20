# B20_R87 record (engineering): the strongest anytime MaxSAT solvers, built from source and pinned

- **Run by:** the builder. Asked for by Daniel (20 Oct 2026): beat "the best of the best solver, extremely tuned over
  years", and draw on nature and physical systems to do it. This batch builds the opponents; B20_R88 develops our
  engine against them on old hosts; B20_R89 onward are preregistered.
- **No claim, rule, comparator or package changes.** B20_R85 and B20_R86 stay preregistered and paused.

## Why these solvers

The largest triangle-free subgraph of a host is an unweighted partial MaxSAT problem: one Boolean per host edge, a
soft unit clause per edge, a hard clause per host triangle. That is the problem class of the MaxSAT Evaluation's
anytime (formerly incomplete) track, where solvers have been tuned against each other every year since 2018.
- **SPB-MaxSAT-c-FPS** and SPB-MaxSAT-c-Band won the 2024 unweighted anytime track; **NuWLS-c-IBR** and
  **TT-Open-WBO-Inc** completed the podium (MSE 2024 talk, Berg and Järvisalo).
- **DeepDist** (Jiang et al., ECAI 2025, "Enhancing Local Search for MaxSAT with Deep Differentiation Clause
  Weighting") reports beating SPB-MaxSAT and USW-LS.
- **Aperture** (Nadel, Slonimski and Strichman, SOFT 2026) is an anytime SAT-based optimiser that also runs NuWLS and
  DeepDist local search; under MSE 2024 conditions it reports beating SPB-MaxSAT-c (both variants) and TT-Open-WBO-Inc
  in all four anytime categories.
- The 2026 Evaluation's archive (Zenodo record 21358014: entrants include NuWLS-c-2026, SPB-NIM-c, DeepDist-c,
  px-tt-open-wbo-inc, PASMaxSAT-c) is refused by this workspace's proxy (403, not routed around); Daniel was asked
  for the archives. Gurobi is unavailable (licence).

## Builds (`scripts/b20r87_maxsat_tools.py`)

Each solver is built from a pinned source commit with its own Makefile's statically linked release target, in a
fixed directory (`/tmp/genesis-sota-build`, so the source paths some binaries embed do not vary), installed under
`/usr/local/genesis-sota/bin` (inside `/usr`, which the runc sandbox mounts read-only), and pinned by SHA-256 in
`candidate_kinds/maxsat.py`. No shipped binary is used (DeepDist's prebuilt `DeepDist` and `runsolver`, and
TT-Open-WBO-Inc's prebuilt binaries and GMP libraries, are deleted before building).

| Solver | Source | SHA-256 of the binary |
|---|---|---|
| DeepDist | github.com/jmhmaxsat/DeepDist `4d899780` | `b0662736…f5adc` |
| SPB-MaxSAT-c-FPS | github.com/josalhor/hermax `6960f98d` | `3f55ae48…5b221` |
| NuWLS-c-IBR | hermax `6960f98d` | `c8567c39…4d2f1` |
| TT-Open-WBO-Inc (IntelSAT) | github.com/alexander-nadel-academic/tt-open-wbo-inc `5881d2de` | `f54cfaa6…7ddcf` |
| Aperture | hermax `6960f98d` | `d2d8155e…4c45d` |

- **Rebuild check:** a second build of all five into another directory (`--dest`) gave the same bytes for
  DeepDist, SPB-MaxSAT-c-FPS, NuWLS-c-IBR and TT-Open-WBO-Inc; Aperture's differs in 22 bytes only, the build date
  and host string its bundled SAT solvers' configure scripts embed (`Tue Oct 20 05:44:50 UTC 2026 Linux vm …`).
- **GMP**, which SPB-MaxSAT-c, NuWLS-c and TT-Open-WBO-Inc link, comes from the two Ubuntu 24.04 packages Daniel
  supplied (libgmp-dev and libgmpxx4ldbl 6.3.0+dfsg-2ubuntu6; checked by SHA-256, unpacked into a build-only prefix;
  nothing installed on the system). The Ubuntu archive itself does not resolve here.
- **hermax** is a Python packaging of MaxSAT solvers. The Evaluation's own site, which hosts the submitted sources, is
  refused here, so SPB-MaxSAT-c-FPS and NuWLS-c-IBR come from it. Its edits to them since their first import (its
  commit `b68a6de`) only silence output (read line by line). Its copy of TT-Open-WBO-Inc edits search files, so the
  author's own repository (the MSE 2024 submission) is used instead.
- **Two patches, disclosed, neither touching search code.** (1) DeepDist's SIGTERM handler prints the best assignment
  (the pinned source has the call commented out, so it reports only costs, which are never trusted here).
  (2) Aperture sizes its input by seeking to its end; on the pipe the sandboxed run must use (the sandbox may not
  write files, so no temporary file and no memfd), the failed seek left the stream failed and the instance read as
  empty. The patch clears the failed seek.
- **Not built.** Loandra: hermax's copy links MaxPRE objects its standalone Makefile cannot compile (hermax edited
  MaxPRE for its own CMake build), and Loandra 2024's repository needs a Rust toolchain and a Bitbucket submodule.
  TT-Open-WBO-Inc's Glucose configuration does not compile from the pinned source (std::function without
  `<functional>`, and a member only the IntelSAT wrapper has).
- **Build defects found and fixed in the script:** the Makefiles take the solver root from `$PWD` (a subprocess
  inherits the caller's), and SPB/NuWLS write into a `bin` directory the repository does not track.

## The kind: `maxsat-anytime-v1` (registry v2)

`candidate_kinds/maxsat.py`. Parameters (data only): {solver, cpu_seconds}; solvers `deepdist`, `spb-maxsat-c-fps`,
`nuwls-c-ibr`, `tt-open-wbo-inc`, `aperture` (`-s glucose`, its unweighted configuration), each otherwise with its
published defaults. The instance goes in through a pipe (`/proc/self/fd/0`) in the classic WCNF format after the
Evaluation's standardised comment header (`c "nvars": V,`, `c "ncls": C,`): **DeepDist sizes its arrays from those
two lines alone and, without them, reads no clause, reports cost 0 and crashes** (found in this batch's smoke tests).
The solver runs for the budget, then gets SIGTERM; the last "v" line is decoded, hard clauses are re-checked, and the
domain checker re-checks the witness. A missing assignment fails the run loudly.

**Seeds.** All five fix their own random seeds, so the same file gives the same run. The seed picks an isomorphic
copy instead: a seeded permutation of the variables and of the clauses and of the literals within each clause, the
usual way to sample a deterministic solver's spread. The model is mapped back to the original edges.

`mqlib-heuristic-v1` (`candidate_kinds/mqlib_heuristic.py`): any of MQLib's 38 heuristic codes on the same pinned
binary as `mqlib-v1`, so a per-host virtual best of several heuristics can be compared, not only BURER2002. MQLib's
hyper-heuristic (`-hh`) returns an empty cut in the pinned build and is not used.

## Tests

`tests_genesis/test_maxsat_kind.py` (10): the encoding is one soft unit per edge and one hard clause per triangle,
with the header; a seeded copy is isomorphic, deterministic in the seed, and decodes back to host triangles; model
parsing (0/1 strings, literal lists, the last line, short or missing lines); every installed binary is the pinned
build; a changed binary and bad parameters are refused; every solver finds K10's optimum (25) and returns checked
witnesses on a random host for two seeds (one study-sized); failures are loud (no output; an assignment violating a
hard clause); a metered runc run of every solver returns a checked witness; MQLib's codes match the binary's list and
two non-default heuristics find K10's optimum.
