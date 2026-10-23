# B20_R101 record (engineering): the max-cut domain and the pinned Gset benchmark; setup of B20_R102

- **Run by:** the builder, on 23 Oct 2026.
- No claim, rule, comparator or package changes.
- The open-record track of `docs/OPEN_RECORDS_PLAN.md`.

## Why

Every Genesis result so far is on hosts generated for its own studies. There, the best values are either reached by
every method (planted n63) or known only to the study itself. Gset (G1–G54; Helmberg and Rendl 2000) has published
best-known values set by published methods, so a result on it can be checked by anyone. Simulated-bifurcation machines
and other Ising hardware also report on it.

## Engineering

**Domain `maxcut_v1`** (DEV only, not sealed, not in `ADAPTERS`):
- **Task models (`models_maxcut.py`).** `MaxCutTask` and its candidate view: up to 20,000 vertices, non-zero
  integer weights, sorted simple edges.
- **Checking (`graphs_maxcut.py`).** A strict reader for `.rud` files. The cut value is computed two independent ways,
  edge-driven and vertex-driven; a disagreement is a checker error. The exposure identity is a weighted
  colour-refinement invariant.
- **Adapter (`domains.MaxCutAdapter`).**
  - Views; refusals (no exact reference, no certificate).
  - Generated families for held-out tests later: `erdos`, `erdos_pm1`, and `torus_pm1` (toroidal ±1 grids, as G11–G13).
- **Runner (`candidates_maxcut.py`).** Registry v2's discipline under its own schema and identity, so no existing
  descriptor changes:
  - a runc child that sees only the view;
  - strict output decoding (`{side, value}`);
  - every cut is re-checked, and a claimed value that differs from the checked one fails the run.

**Kinds:**
- `mqlib-maxcut-v1`: MQLib's eleven max-cut heuristics, BURER2002 first. It is the pinned MQLib binary of `mqlib-v1`,
  on the weighted instance, with no completion step.
- `dsb-maxcut-v1`: `ising-dsb-v1`'s discrete simulated bifurcation with weighted, sparse couplings.

**Data (`data/gset/`):**
- `set1.zip` (Daniel's download of OPTSICOM's set 1, 22 Oct 2026; SHA-256 `18e00bfc…2e71`), with `MANIFEST.json`
  pinning the archive and all 54 members.
- `best_known.json`, which holds three sources, each with its value and how it was obtained. Per instance, the best
  known value is the highest among them.
  - **OPTSICOM's 2009 table** (`maxcut_bestvalues.xls`, SHA-256 `1831bdc4…c018`).
  - **Breakout local search** (Benlic and Hao 2013): its improvements from the authors' page (18 of G25–G54), and its
    published values for G14, G15, G22, G49 and G50 as tabled by RLSolver.
  - **Policy:** a result is a fraction of the best known value, never a record claim, until it has been checked
    against the paper that set the record. Later papers may hold higher values for G1–G24.
- `gset.tasks()` refuses an archive or member that is not the pinned one, and instances outside set 1.

**Tests** (`tests_genesis/test_maxcut_domain.py`, 15):
- the reader, against malformed files;
- the two cut computations, against each other and against brute force;
- isomorphism invariance of the identity, and sensitivity to weights;
- the generated families;
- the pinned benchmark: published sizes and families, best-known values with sources, tampering refused;
- descriptors and refusals;
- both kinds in the sandbox, optimal on a 16-vertex graph;
- BURER2002 on G11, within OPTSICOM's upper bound.

**Development look (disclosed in B20_R102).** BURER2002 and dSB ran in-process at 2 s on seven instances. Both reached
98.6–100% of the best known value. The toroidal ±1 grids (G11, G32) were the furthest below: frustrated spin glasses.

## Setup: B20_R102 (preregistered)

`scripts/b20r102_gset_standing.py`: where the pinned tools stand on G1–G54 at equal, short budgets on one core. The
arms are:
- BURER2002 at 1 s and 10 s;
- dSB at 1 s and 10 s;
- MQLib's other ten max-cut heuristics at 10 s, for the per-instance virtual best.

It reports fractions of the best known value overall and per family, how many instances reach it, and validity. A run
above a best known value is flagged RECORD_CANDIDATE for checking, never claimed. It is a calibration: the numbers a
Genesis method has to beat on public instances. Design tests: `tests_genesis/test_gset_standing.py` (5).
Script SHA-256 `afaf0719…bee0`.

## Setup: B20_R103 (preregistered): the feedback contract and the zero-signal battery

The first item of Daniel's research alert of 22 Oct 2026 (`docs/RESEARCH_ALERTS.md`):
- `src/genesis/autonomy/feedback.py` (SHA-256 `312e9c5e…6139`): the contract. The search trains on A. A judge holds
  confirmation data B and judges each program on it once, with a fixed threshold (Z = 3 times the 90% upper confidence
  limit of the A − B noise over 32 calibration programs). The search stops after 40 generations without a release.
  The final number comes from held-out data. Inside the contract is `solver_search`'s algorithm, with the evaluation
  passed in.
- `scripts/b20r103_zero_signal.py` (SHA-256 `335669c5…12f7`): the battery.
  - Genesis's real search and language, run against an oracle with known truth: no signal, or a planted effect of up
    to 8 sigma_e.
  - Persistent per-program quirks of 0, 1 or 2 sigma_e, where sigma_e (about 0.15 edges) is measured from the four
    recorded searches.
  - Each search run in the open protocol and in the contract protocol.
  - The research loop's analyses run on identical arms.

Development looks on development-only seeds set the threshold before this preregistration; they are disclosed in the
script. Design tests: `tests_genesis/test_feedback_contract.py` (9).

**Why it matters now.** B20_R86 found NO_COMPOUNDING. In the recorded searches, the top tenth of programs spans about
twice one evaluation's noise. Whether the search can see real differences at all is the question B20_R103 answers
before any more generations are run.

