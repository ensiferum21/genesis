# Genesis handover (continuation line, as of B20_R97; refreshed 22 Oct 2026)

This is the full handover of the builder's work on the `continuation-b20-rx` line. A successor operator, reviewer
or agent can resume from it with nothing else. It is refreshed at every checkpoint. The copy inside a handover zip
describes that zip's own contents (see "Package contents").

**Claim ceiling.** Engineering and DEV diagnostics only:
- builder-run, on one host, with fixture keys;
- no sealed task has been run on real panels;
- nothing has been independently reviewed or promoted to a scientific claim;
- better-improver (GV4) is UNESTABLISHED.

## 1. Where everything is

| What | Where |
|---|---|
| Canonical branch | `continuation-b20-rx` on GitHub `ensiferum21/genesis`, pushed directly. B20_R66–R97 were built by a second builder session from the B20_R65 handover; B20_R98–R135 by a third (22–24 Oct 2026). From 26 Oct 2026 the second session is the writer again, Daniel having confirmed that the third has stopped; its B20_R132 run (started 24 Oct, 20:50) left no evidence and is requeued (`research_queue.json`). From 29 Oct 2026 (21:30 SGT) the third session is the writer again, at Daniel's instruction, from the branch as pushed (`adef21f`); the second session's B20_R167 run (from 28 Oct 02:16 UTC) left no evidence on the branch and was restarted from its preregistered script (recorded 30 Oct: ARA_CALIBRATED), and B20_R157 (amended at `ff9eada`) is queued after it (`research_queue.json`). Only one session may write to this branch at a time: two writers split the line once (a duplicate B20_R66 run is kept on `side-b20r66-local-rerun`, same script and hosts, consistent: +18.75 vs +16.65 at 64×) |
| Side branch, not canonical | `side-b21-equational` (`710d26d`; equational generations W21/E4, primitives, fault routes) |
| Archive of checkpoints | the `archive` branch (zips, rehearsal reports, `SHA256SUMS`, README with one row per checkpoint) |
| Latest checkpoint | see the table in `NEXT_ACTIONS.md` ("Checkpoints"); each one is restore-verified, and its driver rehearsal on the build host is REPRODUCED (not a second machine) |
| Batch records | `docs/checkpoints/B20_R<n>_RECORD.md`; the batch table is in `BATCHES.md`; machine-readable state is in `batch_state.json` (`continuation_b20_r1`) |
| Open items | `docs/BLOCKING_DEFECTS.md` (append-only rows per update); the requirements ledger is `docs/REQUIREMENTS_LEDGER.md` (regenerate with `scripts/build_ledger.py`) |
| Decisions needed | `docs/checkpoints/B20_R57_REVIEW_BRIEF.md` (nine decisions, ordered by leverage) and `NEXT_ACTIONS.md` |
| Roadmap | the reviewer roadmap "Genesis: what remains to reach the grand vision" (gates GV0–GV8, work packages W01–W27, experiments E1–E7) |
| **The plan from here** | `docs/GENESIS_OMEGA_PLAN.md` (24 Oct 2026): Genesis Ω, the self-improving verifiable problem solver; read it first |

## 2. Resume

```
unzip GENESIS_COMPLETION_CHECKPOINT_B20_R<k>.zip -d ckpt && cd ckpt
git clone genesis/source-history.bundle genesis-work && cd genesis-work && git checkout continuation-b20-rx
#   or: git clone genesis-all-branches.bundle genesis-work   (the handover's bundle has both code branches)
GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # pinned, byte-reproducible E/CaDiCaL/drat-trim/zstd; Lean
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc); ~45 min on 2 cores
```

To reproduce a checkpoint on a second machine, see `deployment/DEPLOYMENT.md` §5:

```
bash deployment/reproduce.sh <zip> <sha256> <out> --build-toolchain
```

## 3. How a batch is run (the builder's protocol)

1. **Preregister.** Write one script whose docstring states the question, the design, the verdict rule and every
   development look. Commit it with its design tests, and record the script's SHA-256, before it runs.
2. **Run.** Pin the run to one core (`taskset -c 0`, with `GENESIS_TOOLCHAIN` set) and write output to
   `evidence/<name>_b20r<n>/`. Studies are resumable. Do not edit any `.py` file while a study that records
   `code_identity` is running.
3. **Record.** Then:
   - add record tests (the verdict recomputes from the saved rows);
   - write the evidence README and `docs/checkpoints/B20_R<n>_RECORD.md`;
   - add rows to `BATCHES.md`, `NEXT_ACTIONS.md`, `docs/BLOCKING_DEFECTS.md` and `docs/TEST_MATRIX.md`;
   - update `scripts/build_ledger.py`, then run `PYTHONPATH=src python3 scripts/build_ledger.py`;
   - run `tests_genesis.test_ledger` and `test_matrix_classes`;
   - update `batch_state.json`.

   Graph-host studies also get exposure addenda (`scripts/exposure_addendum.py`) next to the frozen E1/E1b packages.
4. **Checkpoint**, every few batches. Run `scripts/make_checkpoint.py --batch 20 --suffix _R<n> --parent <previous
   zip> --parent-ref <commit>` from a clean worktree, with `GENESIS_TOOLCHAIN` and `GENESIS_ORTOOLS_WHEEL` (the pinned
   OR-Tools wheel) set: without the wheel one integration test skips, and an undeclared skip fails the matrix. It
   refuses a dirty tree and runs the release matrix. Then:
   - restore-verify;
   - run `deployment/reproduce.sh` on the build host (about 80 min);
   - archive the zip and report on the `archive` branch;
   - regenerate the bundle.
5. **Never:**
   - act as the independent custodian or auditor, create sealed tasks, or promote claims;
   - rewrite historical evidence (corrections are marked as corrections);
   - overwrite checkpoints;
   - disable TLS or route around proxy policy;
   - run code from downloaded archives;
   - spend on paid APIs (the budget is zero);
   - use credentials pasted into chat.

## 4. Status by gate

| Gate | State | Key evidence |
|---|---|---|
| GV0–GV2 (foundations, custody, reproducibility) | Built; release matrix green (about 1,400 tests, one declared skip); checkpoints reproduce on the build host. Independent review and a second machine are missing | `NEXT_ACTIONS.md` checkpoints; `deployment/` |
| GV3 (useful discovery beyond strong baselines) | Builder side done for E1, E1b, E1b-C4 and E1d, but **E1d's case narrowed**: it beats HiGHS at 4× (+9.80, SUPPORTED rehearsal) with a crossover between 8× and 16× on calibrated hosts that grows with size (B20_R63, R64, R66), yet it only matches a textbook max-cut tabu search (B20_R68) and is slower than domain heuristics (B20_R70): its lead over HiGHS is the max-cut reduction's. The **builder-made engine** (`hybrid-swap-v1`, `tfx`, `tfxw`) beats CP-SAT, BURER2002 and all 13 MaxSAT champions on DEV (B20_R77, R90, R92, R97), which is a useful-solver result, not a discovery | `handoff/e1d`, `evidence/*_b20r6[3-8]`, `evidence/*_b20r7[0-7]`, `evidence/*_b20r9[0-7]` |
| GV4 (better improver) | **UNESTABLISHED; the main risk.** No probed domain has research-policy headroom (graph construction, nine equational settings, larger C4 rows, sum-free pattern selection). The system's own program search builds an iterated local search with a swap-like step from random programs (B20_R79), but random sampling of the same language does as well (B20_R80, R81); physics-inspired operators show no measurable effect (B20_R72, R92, R97). The adaptation cell and autonomy layer (B20_R93–R97) design and preregister studies themselves (prospective checks 9/9, 8/8): research-level automation, not yet a better-improver comparison. Autonomous invention of a new algorithm: NOT_DEMONSTRATED by the preregistered invention test (B20_R111, R112, and in a richer language, R115). Daniel's discovery note (22 Oct 2026, `docs/DISCOVERY_PLAN.md`): its headroom pilot finds headroom but no recognizable local structure where the strongest search stops (B20_R99: HEADROOM_UNSTRUCTURED); the evidence points to global, coarse-grained moves | `handoff/gv4/README.md`, `docs/AUTONOMY.md`, `docs/DISCOVERY_PLAN.md`, `evidence/headroom_b20r99/` |
| GV5 (compounding generations) | **Tested, negative in this language.** Generation 2 ties its no-library control (B20_R83, R84); generation 3 only schedules generations 1 and 2 (B20_R85); on 24 fresh hosts the three cannot be told apart (B20_R86: NO_COMPOUNDING, every comparison UNRESOLVED). Next: the feedback contract (B20_R103) and a more expressive inventor (`docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`) | `evidence/generations_b20r86/` |
| GV6 (structural transfer) | A positive near-domain chain in C4 (B20_R46–R52: invented, Lean-checked rows; utility attributed to them, 36 vs 24 of 40). Equational target: no headroom (B20_R53–R54). Sum-free target (a different theorem family): the procedure transfers, 20/20 Lean (B20_R55); NO_CERTIFICATION_UTILITY unenriched (B20_R56), **CERTIFICATION_UTILITY** on hosts hard for the conventional route (B20_R57, 22 vs 14, p 0.0039), **not replicated** (B20_R59, 23 vs 21, p 0.25); the certified-bound advantage replicated | `handoff/gv6/README.md` (DRAFT) |
| GV7 (independent replication) | Handoff package exists (B20_R21); needs a second operator and machine | `handoff/replication/` |
| GV8 (extended domains) | Out of scope so far | — |

**Distance.** About 15–20 more builder batches if a reviewer accepts claims scoped to time-matched baselines and
counts certification utility. They would cover:
- sealed-run packaging;
- custodian-run evaluations;
- compounding generations;
- replication preparation.

It is open-ended if GV4 needs a learned research procedure that beats fixed ones, since no domain with headroom has
been found. The roadmap's fallback is "report a useful solver without claiming a better improver". Every gate also
needs people: a reviewer, a statistician, an independent custodian on its own machine, and a second operator.

## 5. Results since B20_R44 (DEV, preregistered)

| Batch | Result |
|---|---|
| B20_R45 | E1d ablation rehearsed through v5 custody: SUPPORTED, +6.64 per host |
| B20_R46 | Row-invention procedure transferred to C4-free subgraphs: 37/37 Lean-CHECKED |
| B20_R47 | The rows alone: no coverage gain (22 vs 22) |
| B20_R48 | Certified branch and bound over the rows: **CERTIFICATION_UTILITY**, 38 vs 26 of 40, p 0.00024 |
| B20_R49 | Ablation: **ROWS_RESPONSIBLE**, 36 vs 24 |
| B20_R50 | E1b's C4 arm scorable under a DRAFT rule: READY_FOR_REVIEW (+1.17); MIP dominates |
| B20_R51 | C4 tree route wired opt-in with custody |
| B20_R52 | E1b-C4 DRAFT package; rehearsal SUPPORTED (+1.15) |
| B20_R53 | Wolfram at hard settings: NO_HEADROOM (selection) |
| B20_R54 | Larger conjecture spaces: NO_CEILING_HEADROOM |
| B20_R55 | Procedure transferred to sum-free sets: 20/20 Lean-CHECKED |
| B20_R56 | Sum-free certification: NO_CERTIFICATION_UTILITY (28 vs 26, p 0.25) |
| B20_R57 | Sum-free on hosts hard for the conventional route: **CERTIFICATION_UTILITY**, 22 vs 14 of 40, p 0.0039; certified bound 6.9 lower |
| B20_R58 | Sum-free pattern selection (GV4 pilot): **NO_HEADROOM**; all 17 patterns beat every subset |
| B20_R59 | Internal replication of B20_R57: **NOT_REPLICATED** on coverage (23 vs 21, p 0.25); the bound advantage replicates (+3.9) |
| B20_R60 | GV4 fallback claim **drafted** (`handoff/gv4/FALLBACK_CLAIM_DRAFT.md`): E1d as a useful solver, its ablation, and (if certification counts) the generated rows; BY table derived from the evidence |
| B20_R61 | Statistician's brief (`docs/STATISTICIAN_BRIEF.md`): every power analysis reproduces; flags E1b-C4's underpowered placebo size, four causal power analyses bound to the wrong family, and the claim-vs-rule wording |
| B20_R62 | Causal power analyses rebound to the custodian's families; at 10,000 simulations only E1b-C4's placebo changes size (10 -> 12 per stratum) |
| B20_R63 | E1d budget crossover: **CROSSOVER_AT_8S**. Candidate − HiGHS +10.30 at 4×, +6.37 at 8×, +0.43 at 16× (not material), tie at 32×–64× (HiGHS proves every optimum in about 6 CPU s). The 4× claim replicates; the advantage is speed, not quality at any budget |
| B20_R64 | E1d on larger hosts (DEV pilot): **ADVANTAGE_GROWS**. Crossover 16× at n40, 64× at n50, beyond 64× at n60 (+17.6 at 32 s, 10/0/0). Run 1 invalid (HiGHS CPU-starved); re-run alone |
| B20_R65 | E1d's unsupported rehearsal hosts are exactly those above the 200-edge certificate bound: a host-size cut, blind to both arms |
| B20_R66 | E1d at n60 (DEV replication of B20_R64): **REPLICATED_ADVANTAGE_THROUGH_120X**. +16.65 at 32 s (64×, 19/1/0), +2.00 at 60 s (120×, 17/2/1); HiGHS closing fast. Run alone after the checkpoint matrix |
| B20_R67 | Registry v2's kind map out of the hashed core (adding a kind no longer re-identifies the others); the E1d v2 baselines re-identified once, pre-R67 evidence checked through `pre_r67_id`; new domain baseline kind `maxcut-tabu-v1` |
| B20_R68 | E1d against a textbook max-cut tabu search (DEV): **E1D_MATCHES_DOMAIN_HEURISTIC** on the calibrated settings (+0.03), **HEURISTIC_AHEAD** at n60 (−1.15). E1d's lead over HiGHS is the max-cut reduction's; the GV4 fallback and review brief are corrected |
| B20_R69 | Physics-inspired domain baselines (`ising-dsb-v1` simulated bifurcation, `maxcut-eo-v1` extremal optimization) and `docs/PHYSICS_INSPIRED_PLAN.md`; an unstable SB step fixed before use |
| B20_R70 | Time-to-solution scaling (DEV): **E1D_SLOWER_THAN_SOME**. Simulated bifurcation about 9× faster than the candidate at n60, tabu about 10× at n50; the candidate scales worst |
| B20_R71 | `represent-search-v1`: the representation engine with descent, extremal-optimization or annealing moves for any licensed invented representation |
| B20_R72 | Physics move rules in the invention engine (DEV): **NO_GENERAL_IMPROVEMENT**; speed (faster repair, +0.45) and whole-configuration dynamics (simulated bifurcation) are what help |
| B20_R73 | Multiverse analysis of E1d's verdicts: 12 ROBUST, 5 MIXED, 1 FRAGILE (B20_R68 Part B); crossover points move with MUE and the estimator |
| B20_R74 | MQLib's BURER2002 built reproducibly from a pinned commit as `mqlib-v1`; CP-SAT and MaxSAT blocked (PyPI refused; B20R74-OPEN-1). The MQLib binary must be built on a fresh machine with `scripts/b20r74_sota_tools.py` |
| B20_R75 | State-of-the-art comparison (DEV): **INVALID_CPU_DELIVERY**, BURER2002 kind defect (seed range, silent empty answers) caught by the preregistered check; repeated in B20_R76 |
| B20_R76 | Against OR-Tools CP-SAT and the fixed BURER2002 (DEV): **UNRESOLVED**; only simulated bifurcation resolves (faster than CP-SAT at n63). At ≤ 2 s the heuristics reach targets CP-SAT does not; CP-SAT at 60 s finds an optimum they miss |
| B20_R77 | New engine `hybrid-swap-v1` from B20_R76's diagnosis; against CP-SAT and BURER2002 on 24 fresh n63 hosts (DEV): **ENGINE_BEATS_SOTA** (24/24 targets within 2 s; BURER2002 10, CP-SAT 0). dSB alone also beats both; scope: anytime ≤ 2 s, one family; claim path B20R77-OPEN-1 |
| B20_R79 | The system's own program search (from random programs, B20_R78's language): an iterated local search over cuts with a swap-like edge sweep, found without being given one; tested in B20_R81 |
| B20_R80 | Random-program control: 287.30 against the search's 287.34 on the training hosts (a two-statement iterated local search, no swap); decided on fresh hosts in B20_R81 |
| B20_R81 | Fresh hosts: the self-found solver beats CP-SAT and BURER2002 (SELF_FOUND_BEATS_SOTA) and B20_R77 replicates; against the builder's engine and against random programs UNRESOLVED (the engine ~5x faster; random equal) |
| B20_R82–R84 | Library language and search (GV5); generation 2 (291.59) ties its no-library control (291.61) on the training hosts; R85/R86 deferred |
| B20_R87 | DeepDist, SPB-MaxSAT-c-FPS, NuWLS-c-IBR, TT-Open-WBO-Inc, Aperture built from pinned sources as `maxsat-anytime-v1`; `mqlib-heuristic-v1` |
| B20_R88 | `tfx-v1` (native, operators by data); development looks ahead of every champion up to 0.5 s on old hosts |
| B20_R89 | Configuration race: froze #76 (dSB + descent starts, K 12, parallel tempering, crossover, relinking, restarts); judged in B20_R90 |
| B20_R90 | Head-to-head (DEV): TFX_BEATS_EVERY_CHAMPION and TFX_BEATS_VBS on planted and G(63, 0.5) hosts, NO_CHAMPION_FINDS_MORE at 10 s; ratios are lower bounds (floor 0.05 s); claim path B20R90-OPEN-1 |
| B20_R91 | MSE 2026 anytime entrants built from their archives (Daniel's download) as `maxsat-anytime-2026-v1`; B20_R92 preregistered |
| B20_R92 | Head-to-head with all 13 champions (DEV): TFX_BEATS_EVERY_CHAMPION on both families, TFX_BEATS_VBS on G(63, 0.5) (~200×), vbs_P UNRESOLVED (3× at the median); NO_CHAMPION_FINDS_MORE; ablations UNRESOLVED; interrupted twice and resumed (disclosed) |
| B20_R93 | The adaptation cell (`src/genesis/adaptation/`, `scripts/b20r93_cell.py`, `docs/CAVEATS.md`); prospective check on B20_R92 9/9; quality at equal time and sequential stopping (`genesis.anytime`) |
| B20_R94 | Large triangle-free domain (DEV), `tfxw-v1`, `maxsat-anytime-large-v1`, `candidates_large`; B20_R95 (configuration race on large hosts) preregistered |
| B20_R95 | Configuration race on large hosts (DEV): froze #29 (descent starts, K 6, kpick 4, crossover, relinking, restarts) |
| B20_R96 | The autonomy layer (`src/genesis/autonomy/`, `docs/AUTONOMY.md`), `tfxw-v2`, `bounds_large`, cell v2 |
| B20_R97 | The loop's first study (DEV): FOCAL_BETTER_THAN_EVERY_CHAMPION and FOCAL_BETTER_THAN_VBS at 10 s on large hosts (19, stopped at the first look); ablations NO_MEASURABLE_EFFECT; DeepDist-c NO_RESPONSE; prospective check on the cell 8/8 |
| B20_R85 | Generation 3 (run 22 Oct 2026, unchanged from `9aad649`): a 13-statement schedule of generations 1 and 2 with descent, no new move; 290.00 on its own hosts |
| B20_R98 (engineering) | Toolchain rebuilt in a new container; defect B20R98-PIN repaired (pins cover the tool, not the install folder or build stamp); B20_R98–R100 preregistered |
| B20_R98 | Harness check: NOT_THE_HARNESS. DeepDist-c's and NuWLS-c-2026's collapse on large hosts is their own search; B20_R97's margins stand as such; a 3% band at 10 s on G(256, 0.5) |
| B20_R86 | Do the generations compound? NO_COMPOUNDING: every transition and the library effect UNRESOLVED on fresh hosts; the builder's engine about 5x faster than every generation |
| B20_R100 | The knowledge map's first prospective test: MAP_BETTER (4x more accurate than the baseline on seen methods; 90% intervals cover 97%; much wider intervals on methods it had never seen, coverage kept); an easy test |
| B20_R99 | Headroom pilot: HEADROOM_UNSTRUCTURED. Where tfxw stops nothing local is left (2 of 32 states improvable, no small exchange); the language programs miss the swap; no recognizable pattern (lift 11, recall 0.22); best states differ globally |
| B20_R103 | Feedback contract and zero-signal battery: CONTRACT_LEAKS by its ratio rule (one false release in 180 no-signal searches, held-out numbers unbiased), TOO_STRICT at large quirks (13% of the real gain kept), CALIBRATED analyses; without the contract the program search over-reports by up to 6.6 sigma_e |
| B20_R104 (engineering) | `mcx-v1`, Genesis's max-cut engine (BLS's rules and setting as DEFAULT; cluster exchange, renormalisation and MACUT's crossover as restarts); Gset families built as rudy did; the Gset table now holds the BLS and MACUT papers' values (Daniel's PDFs); B20_R105 and B20_R106 preregistered |
| B20_R105 | The system configures `mcx-v1` on generated graphs: beats BLS's published setting at 1 s (TUNED_BETTER) and ties it at 10 s; ahead of BURER2002 at both budgets (22-0 and 17-2 on 24 held-out graphs); classifier 24/24 |
| B20_R102 | Gset standing (calibration): the best of 12 published heuristics at 10 s reaches 99.68% of the 2012-13 best known values; dSB is the best single tool (99.62%), ahead of BURER2002 (99.54%); no record candidate |
| B20_R106 | **Genesis's max-cut engine on Gset: MCX_LEADS.** Ahead of BURER2002, dSB and the virtual best of 12 published heuristics (40-3 at 10 s); 99.86% of the 2012-13 best known values at 10 s, reaching them on 24 of 54 (the virtual best: 11); no record |
| B20_R107 | Feedback contract v2: V2_FIXES_POWER. The judge's threshold from its own noise halves, power recovers (63% of the real gain at the largest quirk, against 17%), false releases stay at 1 in 180 |
| B20_R108 | Affinity maturation of the engine's configurations: NO_DIFFERENCE at both budgets (B20_R105's choices hold); a lead: renormalisation chosen for planar graphs at 10 s, 5-0 on decided graphs |
| B20_R109 | Gset replication with new seeds: REPLICATED. Ahead of BURER2002 (47-3) and dSB (47-2) on three-seed means; even its worse run beats the tools' best run 36-6; best known values reached on 30 of 54 |
| B20_R110 | The engine at 60 s on Gset: best known values reached on 27 of 54 (all nine tori), 99.91% on average; no record |
| B20_R111 | The invention test: **NOT_DEMONSTRATED.** No autonomously found program beats annealing-then-descent tuned in the same language (gen1 6-14, gen2 7-12, gen3 4-17 behind, control 9-13); a standing bar for any future claim |
| B20_R112 | The inventor under contract v2: NOT_DEMONSTRATED. The judge (honestly) released nothing: its noise with 4-host splits (2.8%) exceeds the programs' differences (0.1%); the program found is multistart descent, behind prior art |
| B20_R113 | Renormalisation on planar graphs: RENORM_BETTER on 40 fresh generated graphs (25-8) and on Gset's 20 planar instances at 60 s (13-2 against B20_R110); best known values reached on 5 of 20 (3 before); no record. With it, 29 of 54 Gset instances at their best known values at 60 s (33 over all recorded runs) |
| B20_R115 | Language v2 (elite pool, consensus and cluster recombination) and a search in it, held to the invention test: **NOT_DEMONSTRATED.** The program found is descent with annealing (its one pool statement never acts), NOT_DISTINGUISHABLE from annealing-then-descent (7-10); memetic templates with the new moves lose to it on all 24 held-out hosts |
| B20_R116 | Five minutes on each of the 21 Gset instances not yet reached: 7 reach their best known values; over all recorded runs Genesis's engine now matches the 2012-13 best known values on **40 of 54**, exceeds none (no record); 11 of the remaining 14 are one unit short |
| B20_R117 (engineering) | A hidden-confounder causal-discovery benchmark (Daniel's research alert, item 2): multi-environment linear SEMs with planted hidden confounders, the truth as an ADMG, scores, and baselines written from their papers (PC-stable, an oracle PC, DirectLiNGAM); setup of B20_R118 (their calibration) |
| B20_R118 | Causal calibration with hidden confounders: **CONFOUNDING_MISLEADS.** DirectLiNGAM (98% directed F1 with nothing hidden) draws an edge for 99% of confounded pairs and loses 0.21 F1 with 3 hidden confounders; PC connects 68%; none of the established methods marks a hidden cause; pooling 3 environments naively changes little |
| B20_R114 (checkpoint) | `GENESIS_COMPLETION_CHECKPOINT_B20_R118` (B20_R74-R118): release matrix 1,948 tests, all OK; restore-verified; archived in two parts |
| B20_R119 (engineering) | FCI as the hidden-variable baseline, and Genesis's active procedure proposing the interventions that resolve hidden causes; setup of B20_R120 |
| B20_R120 | Can Genesis propose the experiments that resolve hidden causes? **NOT_SHOWN.** Its suspicion-based choice of interventions is no better than random (hidden-cause F1 0.17 against 0.19 at budget 2); the oracle's choice shows the headroom (0.29, 0.47 at budget 4). Post hoc: the suspicion signal barely separates confounded pairs, and reading dependence under intervention as a direct cause loses correct marks |
| B20_R121 (engineering) | The active procedure, version 2: a LiNGAM-residual signal of hidden causes, a rule that tests direct causation under intervention, observational flags |
| B20_R122 | On fresh instances: **HIDDEN_CAUSES_MARKED** (hidden-cause F1 0.47 against FCI's 0.21; the spurious rate falls from 0.44 to 0.14), mostly from the prior-art observational flag; experiments add direction (directed F1 0.25 to 0.64), not detection; Genesis's choice of experiments still ties random |
| B20_R123 | Three more 300 s seeds on the 14 Gset instances still below: 5 reached; **45 of 54 matched, none beaten**; a G38 "record" (7688) was already in the 2013 max-bisection literature, so the table was corrected |
| B20_R124 | Gaussian noise: **EXPERIMENTS_NEEDED** (the observational flag goes blind; random experiments add hidden-cause marks, the oracle's choice halves the experiments needed); Genesis's choice still ties random |
| B20_R125-R126 (engineering) | `mcx2-v1` (the engine as a program over physics operators) and `autonomy/selfimprove` (an inventor of engines and a process level over the inventor), at Daniel's request; B20_R127 and R128 preregistered |

## 6. Next steps, in order

1. **Rebuild the state-of-the-art toolchain in any new container** (built tools do not survive one):
   `b20r74_sota_tools.py --ortools-wheel WHEEL`, `b20r87_maxsat_tools.py --deepdist` and `--solvers GMP_DEBS`,
   `b20r91_mse2026_tools.py ARCHIVES --gmp GMP_DEBS`, `b20r88/94/96_build_*.py`, `b20r125_build_mcx2.py` and
   `b20r153_build_mcx3.py` (from the repository's sources); then `b20r98_repin.py --wheel WHEEL`
   must report every pin matched. The wheel, the GMP packages and the 2026 archives are Daniel's downloads (the
   egress proxy refuses PyPI, the Ubuntu archive, crates.io and Zenodo); done on 22 Oct 2026.
2. **Run the preregistered studies, alone on CPU 0, in this order:**
   1. done: B20_R100 `predict` (committed before B20_R86) and B20_R98 (NOT_THE_HARNESS);
   2. done: B20_R86 (NO_COMPOUNDING);
   3. done: B20_R100 `score` (MAP_BETTER);
   4. done: B20_R99 (HEADROOM_UNSTRUCTURED);
   5. done: B20_R103 (CONTRACT_LEAKS by its ratio rule; TOO_STRICT; CALIBRATED);
   6. done: B20_R105 (TUNED_BETTER at 1 s; MCX_AHEAD at 1 s and 10 s on generated graphs);
   7. done: B20_R102 (calibration; dSB the best single tool; no record candidate);
   8. done: B20_R106 (MCX_LEADS);
   9. done: B20_R107 (V2_FIXES_POWER);
  10. done: B20_R108 (NO_DIFFERENCE);
  11. done: B20_R109 (REPLICATED);
  12. done: B20_R110 (LONGER_HELPS; 27 of 54 at the best known values; no record);
  13. done: B20_R111 (NOT_DEMONSTRATED);
  14. done: B20_R112 (NOT_DEMONSTRATED; nothing released);
  15. done: B20_R113 (RENORM_BETTER on generated graphs and on Gset; 5 of 20 planar instances at the best known
      values; no record);
  16. done: B20_R115 (NOT_DEMONSTRATED; the new moves do not help at 2 s);
  17. done: B20_R116 (7 of 21 reached; 40 of 54 over all runs; no record);
  18. done: B20_R114, the checkpoint `GENESIS_COMPLETION_CHECKPOINT_B20_R118` (B20_R74-R118; release matrix
      1,948 tests all OK; restore-verified; archived in two parts);
  19. done: B20_R118 (CONFOUNDING_MISLEADS);
  20. done: B20_R119-R120 (FCI and the active procedure; NOT_SHOWN: no better than random targets);
  21. done: B20_R121-R122 (HIDDEN_CAUSES_MARKED; experiments add direction; the choice of experiments ties random);
  22. done: B20_R129 (ADAPTIVE_SCIENTIST: 4.49 experiments against random's 6.81; Genesis's own rule beats the
      established acquisitions and ties the builder's; four as good as eight only on the larger unfamiliar family);
      next on this track B20_R130 (preregistered `f812701`: choice, instrument and interpretation separated);
  23. done: B20_R123 (5 of 14 reached; 45 of 54 matched; no record); done: B20_R124 (EXPERIMENTS_NEEDED);
  24. done: B20_R127 (NOT_SHOWN: SYSTEM ties MCX on Gset at 10 s, 16-11; the judge released nothing in nine
      searches, its threshold 4 to 52 times the best training gain). Daniel's directive of 24 Oct, 15:35 (adopted,
      `docs/GENESIS_OMEGA_PLAN.md` §0a) orders the rest: done: B20_R130 (CHOICE; the global interpretation did not
      beat the per-pair one at the preregistered measure, so B20_R131's trigger is not verified); B20_R133 (running
      from 19:33; done: BEHIND_SPECIALISTS_ON coloring, mis), B20_R131 (done: NO_VERIFIED_TRIGGER by protocol), then, first by Daniel's
      decision of 26 Oct, B20_R148 (done: NOT_SHOWN; G3_NOT_SHOWN; `docs/OMEGA_META_ADAPTIVE.md`); B20_R132 (done: NOT_SHOWN;
      diagnosis EXPRESSIVENESS in every class; its 24 Oct run left no evidence), B20_R128 (done: NOT_SHOWN; no inner search released anything), B20_R135 (done: INVENTED_REPRESENTATION_BETTER for k = 3 and 4). Studies run alone on CPU 0 from a clean worktree of the
      branch head, one slice of at most 6,600 s per call.
  25. **Daniel's architecture of 24 Oct, 20:31 is adopted**: `docs/OMEGA_RECURSIVE_INVENTION.md`. Everything
      Genesis can invent is a typed research object, an open set of kinds beyond senses. The capability-gap
      scientist comes first; synergy, attack and paradigms are data; recursive improvement is typed
      self-application measured only by G_t on fresh tasks; the judge is closed. Next build: the RO layer
      (`src/genesis/objects/`), then B20_R136 (experiment A).
  26. **Daniel's directive of 24 Oct, 20:45 is adopted**: `docs/OMEGA_ARCHITECTURE_INVENTION.md`, the Autonomous
      Research Architect. Workflows are typed graphs of ROs (AG) with a closed kernel; limitations are measured by
      oracle substitution (a loss ladder); proposals are typed rewrites with holes filled by synthesis; a sealed
      Limitation Zoo calibrates it with planted, null, no-headroom and decoy environments; tuning-only and
      blind-rewrite controls at matched total compute. ARA-1 is built on fixtures (B20_R150, `src/genesis/architecture/`);
      next, B20_R141 (experiments A-D on the zoo), preregistered for the blind control's strength.
  26b. **Daniel's direction of 27 Oct 2026, 14:33 is adopted and is the current priority**:
      `docs/OMEGA_EXPRESSIVE_LANGUAGE.md`. Richer algorithm expressiveness, measured apart from search (a
      ceiling search within a description-length bound; a language x search factorial), the builder's construct
      algebra labelled as human, Genesis growing the language from its own engines through a language judge and
      a consolidator, generation after generation. Batches X1, X2, B20_R151, B20_R152; then B20_R141.
      Done: X1 (B20_R153, engineering: `mcx3-v1` and its pinned binary, every mcx2 program identical in it; the
      Λ1 front end with named statements; the inventor's operators over Λ0 and Λ1). Done: X2 (B20_R154,
      engineering: the workflow ladder, library learning, the language judge, the consolidator and the generation
      pipeline, on a planted fixture).
      - **B20_R151 is recorded** (28 Oct, 02:00 SGT; `docs/checkpoints/B20_R151_RECORD.md`): NOT_SHOWN, reading
        NO_LANGUAGE_EFFECT. Λ1 did not express better engines than Λ0 on planar2000 at these budgets. As a secondary
        finding, every searched engine beat REX on fresh graphs by 0.45–0.78%.
      - **B20_R152 is recorded** (`docs/checkpoints/B20_R152_RECORD.md`): NOTHING_ADMITTED. The judge refused both of generation 1's statements, so B20_R155 does not run.
      - **B20_R165 is recorded** (`docs/checkpoints/B20_R165_RECORD.md`): REPLICATED_WITH_SINGLE_ENGINE. The gain over REX holds on 48 fresh planar graphs, all of it on ±1-weighted ones (+1.16%).
      - **B20_R141 is recorded** (`docs/checkpoints/B20_R141_RECORD.md`): INVALID. The script's freshness clause
        was False in every registered run (a defect; disclosed). Descriptively every experiment would have
        passed. B20_R167, the re-run with the defect repaired on fresh environments, is preregistered; B20_R142
        still requires `ara-calibrated`.
      - **B20_R156 (F3) is recorded** (`docs/checkpoints/B20_R156_RECORD.md`): FRONTIER_BETTER on sealed planted
        worlds; forecast coverage 0.66 at a nominal 0.90.
      - **B20_R157 (F4)'s first attempt was killed** (out of memory) by Γ's star-size defect (B20R157-STAR), which is
        repaired. B20_R157 is amended at `ff9eada`, and every arm runs again after B20_R167. B20_R158 is amended
        before it ran. B20_R167 started at 02:16 UTC.
      - **B20_R167 is recorded** (30 Oct 2026; `docs/checkpoints/B20_R167_RECORD.md`): ARA_CALIBRATED, valid. The
        28 Oct attempt was lost with its session and the study was restarted from scratch on 29 Oct (disclosed).
        ARA localised 42 of 50 planted limitations, said NONE on 30 of 30 null controls, beat blind rewriting at two
        tries by +0.41 of the range, and released nothing on 45 controls; FUSION_NEEDED is its weak class.
        `ara-calibrated` is unlocked: B20_R142 may be preregistered, and B20_R144 (ARA on its own settings) is
        preregistered (30 Oct), to run after B20_R136.
      - **B20_R173 is recorded** (30 Oct 2026; `docs/checkpoints/B20_R173_RECORD.md`): RELEASED. The protected judge,
        unchanged, released C0_1 over REX on ±1-weighted planar graphs (B gain 1.22% against tau 0.78%; truth +1.12%
        on 24 of 24). It is the first release by that judge of an engine Genesis's own search found, and it is narrow
        (one family; the builder's REX and L0 language). On this family 7 of the judge's 47 random L0 engines would also
        have been released, so it is not evidence that the search beats random sampling. The expectation
        (NOT_RELEASED) was wrong. Disclosed: CPU 0
        was idle from 01:50 to 07:25 SGT after it, because the builder did not launch the chain it had written.
        B20_R136 started at 07:25, with B20_R144 chained after it.
      - **B20_R136 is recorded** (`docs/checkpoints/B20_R136_RECORD.md`): NOT_SHOWN. The synthesised sense chose
        per graph and avoided C0_1's losses, but beat always-C0_1 by only +0.087% (below 0.1%) and lost to the
        builder's degree CV. B20_R144 started at 07:38.
      - **B20_R144 is recorded** (`docs/checkpoints/B20_R144_RECORD.md`): NOTHING_ADOPTED. ARA's meta-cycle located
        nothing and its six candidate settings changed no result; the fall-back order is alphabetical, so the
        variants and the ranking were never tried (fix before B20_R145). B20_R157 (F4) started at 08:23:37.
      - **B20_R157 (F4) is recorded** (`docs/checkpoints/B20_R157_RECORD.md`): PARTIAL. The Frontier beats NRPA,
        not GBFS (19 refutations to its 14), CEM, UCB or uniform; Γ-built refutations above 40 vertices were beyond
        the preregistered second check (descriptively all confirmed: the joint arms at 25–26 of 33, level with each
        other). B20_R158 (F5) started at 10:44:29, before the checkpoint window.
      - **B20_R158's first run stopped** (exit 1 at 10:50) on a template overflow (B20R158-TEMPLATE). Repaired;
        B20_R158 amended a second time before any result was looked at; it runs again after the checkpoint B20_R169,
        which started at 10:56 on CPU 0 (CPU 0 idle 10:50–10:56, disclosed).
      - **The checkpoint's first attempt failed** on one undeclared skip: `GENESIS_ORTOOLS_WHEEL` was not set (§3.4).
        Stopped at 12:29; B20_R158's second run started at 12:29:35; the checkpoint runs again after it, split by
        suite (`run_test_matrix.py --suites`, `make_checkpoint.py --reports`).
      - **B20_R158 (F5) is recorded** (`docs/checkpoints/B20_R158_RECORD.md`): NOT_SHOWN. Generation 1 posed 9 of
        Genesis's own conjectures; FULL 6 refuted, PLAIN 5; the generator posed nothing new afterwards. The
        checkpoint's integration suite started on CPU 0 at 12:53:25.
      - **PT-1 (B20_R159) is preregistered** (30 Oct 2026; sha256 `56037017…3a05`): the draft's open items fixed from
        F4's and F5's results with reasons; templates do not count for part 1 (the strict reading, after Daniel's "Do
        the hardest"; his to overrule before it runs). It runs after B20_R174, about 6 h.
      - **The checkpoint B20_R169 is made** (`5d7b7f0`, SHA-256 `dcd5a0fd…7112`): 2,664 tests all OK, restore-verified,
        archived whole on `archive` (`14a7651`). B20_R163 (F6) started at 14:38:25.
      - **B20_R163 (F6) is recorded** (`docs/checkpoints/B20_R163_RECORD.md`): NOT_SHOWN. The self-found
        configuration lost to the defaults given the meta-search's compute (−0.221) and tied them at equal budget.
        B20_R170 (G2) started at 14:59:45.
      - **Defect B20R163-META** (found after recording; `docs/BLOCKING_DEFECTS.md`): F6's meta-search compared
        configurations at unequal inner spends and promoted the first one it opened. F6's record is corrected; B20_R170
        inherits the defect. The repair (`meta.SuiteMetaDomain`, `meta.halving_bracket`) is for new studies.
      - **B20_R175 (F6b) is preregistered**: F6's question with the repaired meta-search; after PT-1, about 1 h.
      - **B20_R170 (G2) is recorded** (`docs/checkpoints/B20_R170_RECORD.md`): NOT_SHOWN. Coverage 0.655 → 0.737,
        short of the band; no value gain. B20_R172 ran 15:27-15:45 (to record); B20_R174 started 15:48:21.
      - **B20_R172 (G4) is recorded** (`docs/checkpoints/B20_R172_RECORD.md`): NOT_SHOWN. The feature generalised
        (S7 p 0.001) but bought no value. B20_R174 is running (about 3.5 h, two slices); PT-1 follows, then R175.
      - **B20_R174 is recorded** (`docs/checkpoints/B20_R174_RECORD.md`): NOT_SHOWN, RANDOM_MATCHES_SEARCH. On ±1
        planar graphs, random sampling of L0 matched Genesis's search; the released C0_1 was the weakest of six
        winners. **PT-1 (B20_R159) is running** from 19:24:33 (`/home/claude/pt1-wt` at `a775227`, about 6 h).
      - **PT-1 is recorded** (`docs/checkpoints/B20_R159_RECORD.md`): INADEQUACY_GATE_FAILED after 25 min. The
        predecessor refuted bound 40; Genesis refuted 40 and 21 from derived graph products. Not proved out; a second
        proving test is Daniel's decision. B20_R175 (F6b) started 19:50:17; nothing is preregistered after it.
      - **PT-2 (B20_R177) is preregistered** (Daniel: "Do the best", 20:06): the per-bound gate, PT-1's code otherwise;
        after B20_R175, about 6.5 h. Then the checkpoint B20_R176 (scripts `/home/claude/ckpt176_part1.sh` and
        `_part2.sh`, from a fresh single-branch clone `/home/claude/ckpt176`).
      - **B20_R175 (F6b) is recorded** (`docs/checkpoints/B20_R175_RECORD.md`): NOT_SHOWN, NOTHING_PROMOTED; the guard
        kept the defaults, and F6's procedure's configuration was harmful (−0.456). **PT-2 is running** from 20:23:09.
      - **PT-2's first attempt stopped** at 21:04 in part 3's replay (defect B20R177-LIBRARY, repaired; PT-2 amended;
        its files kept in `evidence/proving_test_2_b20r177_attempt1/`, only the traceback read). **PT-2 re-runs** from
        21:15:05 (`/home/claude/pt2b-wt` at `25eadb7`, about 6.5 h). The checkpoint B20_R176 (started 21:04:21) was
        stopped at 21:15 and is re-made after PT-2 (fresh clone; `/home/claude/ckpt176_part1.sh`, `_part2.sh`).
      - **PT-2's second attempt stopped** at 22:08 in family B's arms (defect B20R177-SEEN, repaired; amended a second
        time; files kept in `evidence/proving_test_2_b20r177_attempt2/`, only the traceback read). **The checkpoint
        B20_R176** runs on CPU 0 from 22:08:13 (`/home/claude/ckpt176` at `2e7fd2f`); PT-2 re-runs after it.
      - **Daniel's requirement of 22:52 is adopted**: `docs/OMEGA_SELF_REPAIR.md`, the obstacle loop (Genesis repairing
        its own obstacles under its Judge and Supervisor). Queued: `self-repair-build` (CPU 1), then B20_R178 (SR-1).
      - **The Foundry directive (23:09) is taken up, narrow first** (its first milestone). The obstacle loop is built
        on a state-management testbed (`src/genesis/repair/`, `src/genesis/repairkernel/`; `docs/OMEGA_SELF_REPAIR.md`
        §7): the causal obstacle model, conservation-law probes, synthesis, a kernel verifier with hidden tests, the
        Supervisor's policy with rollback, the research plane and the trial executor isolated in mount namespaces as
        unprivileged users, and the vault. **B20_R178 (SR-1a) is recorded** (`docs/checkpoints/B20_R178_RECORD.md`,
        CPU 1): MILESTONE_DEMONSTRATED (24 of 39 held-out obstacles repaired end to end), REUSE_SHOWN, and
        NOLOCAL/RANDOM/ENUM_BEATS_LOOP (unfocused search repaired more). The checkpoint B20_R176's part 1 passed
        (23:57:52); part 2 runs from 23:57:56; PT-2's third attempt follows on CPU 0.
      - **The checkpoint B20_R176 is made** (`2e7fd2f`, SHA-256 `43d8621b…bd81`): 2,723 tests all OK, restore-verified,
        archived whole (`archive` `10b01e6`). **PT-2's third attempt runs** on CPU 0 from 00:11:36 (`/home/claude/pt2c-wt`
        at `75b5bac`; slices of 6,600 s).
      - **This session stalled for about 8 h** (31 Oct, container clock 00:30 to 08:42): PT-2's first slice paused
        at 02:05:56 and its second started only at 08:42:20, **6 h 36 min of CPU 0 idle** (to disclose in PT-2's
        record). A safety-net trigger that fired at 01:30 reached the session only at 08:42.
      - **B20_R178 (SR-1a) is recorded**; the loop version 2, kernel version 2 and three larger components are built;
        **B20_R180 (SR-1a2)** is preregistered (CPU 1).
  26c. **Daniel's directive of 27 Oct 2026, 19:55 is adopted**: `docs/OMEGA_FRONTIER.md`, written in detail for
      handoff at his request (20:01). Genesis works by divergence and convergence (imagine, mutate, recombine,
      branch out, extrapolate discovery curves, detect convergence, allocate), without handholding. The
      No-Handholding Protocol (one manifest, boundary tests, a relabelling audit, a teaching ban) is the test of
      that.
      - The first domain: graph-theory conjectures with exact certificates.
      - The sealed calibration: the 68 AutoGraphiX Laplacian bounds (44 refuted, 22 proved, 2 open as of June
        2026).
      - The batches: F1 and F2 engineering on CPU 1 while the queue above runs; then B20_R156 (planted worlds),
        B20_R157 (the sealed bounds) and B20_R158 (open-ended generations).
      - **The proving test** (Daniel, 20:22; §7b, B20_R159). It is the system's acceptance test, and nothing short of
        passing all five parts is called proving out the system.
      - F2 is built (§6 done: the sealed bounds tiered from five sources; the Wagner rebuild test added).
      - PT-1's transfer family B is ready, though not yet preregistered (§7b):
        - kernel side: `conjecture/wowii.py`, with 53 Graffiti statements, and `conjecture/invariants_ref.py`;
        - research plane: `conjecture/invariants.py`, `statement.py` and `invariant_domain.py`;
        - tests: `tests_genesis/test_wowii.py`.
        B stays sealed: nothing has been run on it except the transcription checks.
      - Its §12 holds the exact resume commands for the running studies. The draft record tests are in
        `docs/handoff/RECORD_TEST_DRAFTS.md`.
  27. after them: the Genesis Ω stages in `docs/GENESIS_OMEGA_PLAN.md` §5-§6 (Ω0 analysis of R127/R128; B20_R130
      invented instruments; B20_R131 the Difficulty Cartographer; the genome and typed language; the ecology;
      evolvability selection; the decisive A/B/C experiment).

3. **Checkpoint:** the latest is B20_R148 (`012f133`, SHA-256 `bb89b23b…33e4`; archive branch, four parts;
   REPRODUCED on the build host, not yet on a second machine). Do not edit the tree while
   the release matrix runs; run timing studies alone.
4. **B20_R101, the Gset max-cut domain** (`docs/OPEN_RECORDS_PLAN.md`; Daniel's `set1.zip` and best-values file,
   pinned on arrival), then where Genesis stands against the published records.
5. **The recursive-improvement build order** (`docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md` §3): the knowledge map
   choosing experiments, the view portfolio, the discovery loop if B20_R99 finds structured headroom,
   evolvability-selected search, curricula, policy revision.
6. **The adaptation cell's next design** (the 60 s stage of B20_R97; about 12 h).
7. **Decisions and people** (unchanged): the review brief's decisions, a statistician (`docs/STATISTICIAN_BRIEF.md`),
   an independent custodian, a second operator (GV7).

## 7. Package contents (the handover zip)

| File | What |
|---|---|
| `HANDOVER.md` | this file |
| `GENESIS_COMPLETION_CHECKPOINT_B20_R<k>.zip` and `.sha256` | the latest checkpoint: source tree, history bundle, release-matrix report, SHA-256 manifest |
| `genesis-all-branches.bundle` | a self-contained git bundle (no prerequisites) of `continuation-b20-rx` and `side-b21-equational`; verify with `git bundle verify`. The `archive` branch (16 checkpoint zips, about 410 MB) is not included; its checkpoints were delivered one by one |
| `NEXT_ACTIONS.md`, `B20_R57_REVIEW_BRIEF.md` | status, decisions |
| `STATISTICIAN_BRIEF.md` | the statistician's brief (B20_R61, B19-OPEN-4) |
| `FALLBACK_CLAIM_DRAFT.md` | the GV4 fallback claim, DRAFT (B20_R60; updated with B20_R63's crossover) |
| `*.rehearsal.json` | driver rehearsal reports for the checkpoints in the zip (when present) |
| `SHA256SUMS` | the checksums of everything above |
