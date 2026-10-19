# Genesis handover (continuation line, as of B20_R57)

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
| Canonical branch | `continuation-b20-rx` (GitHub `ensiferum21/genesis`; GitHub has not been linked to the builder's session since B20_R24, so the line is delivered as zips and bundles) |
| Side branch, not canonical | `side-b21-equational` (`710d26d`; equational generations W21/E4, primitives, fault routes) |
| Archive of checkpoints | the `archive` branch (zips, rehearsal reports, `SHA256SUMS`, README with one row per checkpoint) |
| Latest checkpoint | see the table in `NEXT_ACTIONS.md` ("Checkpoints"); each one is restore-verified, and its driver rehearsal on the build host is REPRODUCED (not a second machine) |
| Batch records | `docs/checkpoints/B20_R<n>_RECORD.md`; the batch table is in `BATCHES.md`; machine-readable state is in `batch_state.json` (`continuation_b20_r1`) |
| Open items | `docs/BLOCKING_DEFECTS.md` (append-only rows per update); the requirements ledger is `docs/REQUIREMENTS_LEDGER.md` (regenerate with `scripts/build_ledger.py`) |
| Decisions needed | `docs/checkpoints/B20_R57_REVIEW_BRIEF.md` (nine decisions, ordered by leverage) and `NEXT_ACTIONS.md` |
| Roadmap | the reviewer roadmap "Genesis: what remains to reach the grand vision" (gates GV0–GV8, work packages W01–W27, experiments E1–E7) |

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
   zip> --parent-ref <commit>` from a clean worktree. It refuses a dirty tree and runs the release matrix. Then:
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
| GV3 (useful discovery beyond strong baselines) | Builder side done for E1, E1b, E1b-C4 and E1d. **E1d** beats HiGHS at 4× budget (+9.80 per host, SUPPORTED rehearsal; ablation +7.07, null clean); the advantage ends between 8× and 16× (B20_R63: HiGHS ties from 32×, proving every optimum in about 6 CPU s) on the calibrated hosts, and grows with host size (B20_R64, DEV: at n60 it holds at 64×, +17.6; replicated by B20_R66 on 20 fresh hosts, +16.65 at 64× and +2.00 at 120×). **But B20_R68:** a standard max-cut tabu search at the same budget ties it on the calibrated settings and beats it at n60, so E1d's advantage is over a generic MILP, not over the field's methods. E1, E1b and E1b-C4 are READY_FOR_REVIEW against DSL baselines but MIP-dominated (B20R33-OPEN-1) | `handoff/e1`, `e1b`, `e1b_c4`, `e1d` |
| GV4 (better improver) | **UNESTABLISHED; the main risk.** No probed domain has research-policy headroom: graph construction (selection, proposal), the equational systems (nine settings, including Wolfram at hard settings: selection, keeping, larger conjecture spaces), larger C4 rows, sum-free pattern selection (B20_R58). The builder recommends the roadmap's fallback. Six invented components have no construction utility after cost. Two certification utilities survive false-discovery control (B20_R35, B20_R48) | `handoff/gv4/README.md` (DRAFT) |
| GV5 (compounding generations) | Not started (depends on GV4) | — |
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

## 6. Next steps, in order

1. **Checkpoint B20_R73** (at `5f3dd5e`) covers B20_R66–R73: release matrix 1,515 OK, restore-verified (6,151 entries), archived; the build-host rehearsal (`deployment/reproduce.sh`) was not run for it. **Checkpoint B20_R65** (at `821b743`) covers B20_R59–R65: release matrix 1,455 OK, restore-verified (6,093 entries), build-host rehearsal REPRODUCED, archived. B20_R58 (at `02415a8`) is recorded likewise. The next checkpoint follows B20_R66. Build checkpoints and run timing-sensitive studies on a quiet machine, one at a time (a checkpoint matrix failed when the tree was edited during it, and B20_R64's first run was CPU-starved). Keep the session's disk allowance in mind: delete old `/tmp/genesis-repro-*` trees after each rehearsal (B20_R59 and one B20_R58 rehearsal were interrupted by disk exhaustion).
2. **Get the decisions in the review brief.** Most remaining work depends on them. In particular:
   - item 1, the strong-baseline scope;
   - item 3, generated-rows certification as a trust path;
   - item 4, whether certification utility counts;
   - item 5, the GV6 target;
   - item 6, the GV4 domain or the fallback.
3. **After decisions:**
   - freeze the adopted DRAFT rules and packages;
   - have an independent custodian run SELECT, register and evaluate for E1d (and E1/E1b/E1b-C4 within scope);
   - with a statistician, sign off the power models (`docs/STATISTICIAN_BRIEF.md`; fix its findings 1–3 at the freeze).
4. **GV4:** if a new domain is chosen, run a headroom pilot first (the B20_R3/R53 pattern) before any study.
   Otherwise the fallback claim is drafted (`handoff/gv4/FALLBACK_CLAIM_DRAFT.md`, B20_R60) for the reviewer to accept,
   narrow or reject.
5. **GV7:** give `handoff/replication/` and a checkpoint to a second operator.

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
