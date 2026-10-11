# B15 toolchain reproducibility evidence (build host only)

Before B15, rebuilding the pinned commits in a different directory reproduced only
drat-trim. zstd and E embedded absolute source paths, and CaDiCaL embedded the build
date plus `uname -srmn`. A second machine following `install_tools.sh` would have got
binaries that differ from PINS.json, and the platform check would have failed.

`toolchain/build_reproducible.sh` adds `-ffile-prefix-map`, sets `SOURCE_DATE_EPOCH`
to the commit time, and builds CaDiCaL with `-DNBUILD`. With it:

- `build_path1_hashes.txt` and `build_path2_hashes.txt`: two builds, at different
  paths and different times, gave identical hashes.
- `build_revised_recipe_hashes.txt`: a third build, after the recipe gained an input
  guard, gave identical hashes again.
- `ka_b15.json`: the known-answer suite (`toolchain/known_answers.py`) passed, 10 of
  10 cases, on the installed binaries.
- The pins changed only through `toolchain/revise_pins.py`. See
  `toolchain/PINS_HISTORY.jsonl`, entries 2 and 3. The retired hashes are no longer
  verifier anchors. The verifier binaries themselves (drat-trim and Lean) are unchanged.
- The pre-B15 binaries are kept beside the toolchain under `retired/pre-b15/`.

What this does not show:
- Byte reproducibility with a different compiler or C library. PINS records gcc 13.3.0
  and glibc 2.39. Another compiler needs a re-pin through `revise_pins.py`, with
  passing known answers.
- Anything about a second machine. That acceptance is still external (R-04).
