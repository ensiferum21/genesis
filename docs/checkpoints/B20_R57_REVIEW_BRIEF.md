# Review brief: the continuation line from B20_R21 to B20_R57

This brief is for an independent reviewer, statistician or custodian. It says what to decide and what to check on
the `continuation-b20-rx` branch since `B20_R20_REVIEW_BRIEF.md`.
- **Who ran what.** The builder ran everything on one host, on DEV material, with fixture keys.
- **Not reviewed or promoted.** Nothing here has been independently reviewed, run on sealed panels, or promoted to a
  scientific claim.
- **Why decisions come first.** Builder-side work is near exhaustion. Most of what remains toward the grand vision
  needs the decisions in section 1.

## Reproduce

```
git clone https://github.com/ensiferum21/genesis genesis-work && cd genesis-work && git checkout continuation-b20-rx
GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json     # as root (runc)
```

Checkpoints:
- **Archives.** The archive is the `archive` branch. Each checkpoint was restore-verified, and its driver rehearsal
  was REPRODUCED on the build host. That host is not a second machine.
- **Studies.** Each DEV study is one script, committed with its verdict rule before it ran. Each has an evidence
  README and a record in `docs/checkpoints/`.

## 1. Decisions, in order of leverage

| # | Decision | Why it matters | Evidence |
|---|---|---|---|
| 1 | **Scope of "strong baselines" (B20R33-OPEN-1).** An exact MIP (HiGHS) solves the certifiable triangle-free and C4 settings within seconds, so E1 is dominated there and E1b ties or is dominated. Either accept claims scoped to time-matched DSL baselines, or require beating an exact solver. | Decides whether E1/E1b can ever pass GV3 as specified | `evidence/strong_baseline_audit_b20r33/`, `evidence/e1b_c4_readiness_b20r50/` |
| 2 | **E1d (B20R41-OPEN-1, B20R44-OPEN-1).** E1's frozen candidate beats HiGHS at four times its budget on three dense planted settings: +10.6 per host on the re-pilot, and +9.80 in the same-operator rehearsal (SUPPORTED). The registered ablation of its discovered representation costs +7.07 per host, with a clean null control. Adopting it needs the DRAFT rule `e1-hard-v3-draft`, the generated-rows reference (item 3), the v5 and registry-v2 wiring (B20R40-OPEN-1), and the `cross_2 → ordered_2` intervention. | The only GV3 path found that is beyond an exact solver | `handoff/e1d/`, `evidence/e1d_*` |
| 3 | **Generated-rows certification as a trust-path change (B20R35-OPEN-1, B20R48-OPEN-1).** Should the evaluator accept certificates whose rows are Lean-checked theorems of a generated theory package? The checkers are exact (`verification/lp_dual_rows*.py`, `lp_dual_tree_*.py`), custody exists (`certificates_rows.py`, `certificates_tree_c4.py`), and the wiring is opt-in through v5. | Makes the dense regime (E1d) and the C4 settings certifiable | `docs/GENERATED_ROWS_REFERENCE.md` |
| 4 | **Does certification utility count as "helps"?** This is asked for GV4 (B20R35-OPEN-1) and for GV6. Every positive invention result is in certification: B20_R35 (27 vs 7 of 40) and B20_R48 (38 vs 26 of 40, attributed to the rows by B20_R49). No invented component has construction utility after cost (six attempts). | Without it, GV4 and GV6 have no positive evidence | `handoff/gv4/README.md`, `handoff/gv6/README.md` |
| 5 | **GV6 target (B20R46-OPEN-1).** Results by target:<br>• **C4:** a positive near-domain chain (B20_R46–R52).<br>• **Equational:** no research headroom (B20_R53, R54).<br>• **Sum-free sets** (a different theorem family): the procedure transfers, 20/20 Lean-CHECKED (B20_R55). There is no certification utility on an unenriched sample (B20_R56), and there is CERTIFICATION_UTILITY on hosts hard for the conventional route (B20_R57: 22 vs 14, p 0.0039), but it did **not replicate** (B20_R59: 23 vs 21, p 0.25); the certified-bound advantage did replicate.<br>The builder's view is that sum-free and codes share the source's abstract structure, a hypergraph-free packing. | Decides whether any existing evidence can count toward GV6 | `handoff/gv6/README.md` |
| 6 | **GV4 domain and fallback (B20R9-OPEN-1).** No probed domain has research-policy headroom:<br>• graph construction: selection and proposal;<br>• nine equational settings, including Wolfram at hard settings: selection, keeping and larger conjecture spaces;<br>• larger C4 rows;<br>• sum-free pattern selection (B20_R58).<br>The roadmap's fallback is "a useful solver, not a better improver". The reviewer should say whether to pursue a new domain or accept the fallback. | GV4 is the main risk to the grand vision | `evidence/headroom_pilot_b20r3/`, `evidence/wolfram_*_b20r53/54/`, `handoff/gv4/README.md` |
| 7 | **E1, E1b, E1b-C4 sign-off.** The rule `e1-hard-v2`, the cost and comparator decisions, and the statistician's sign-off of the centred power model (B19-OPEN-4). For C4: the DRAFT rule `e1-hard-v2-c4tree-draft` and the tree reference (B20R50-OPEN-1). All are READY_FOR_REVIEW, and their rehearsals are SUPPORTED. | GV3 within scope (item 1) | `handoff/e1/`, `handoff/e1b/`, `handoff/e1b_c4/` |
| 8 | **Certification limits (B20R24-OPEN-2).** Align the calibration limit (≥ 90% certified within 60 s) with the plan's limit (≤ 5% unsupported at 600 s). Measured LIMITS_CONSISTENT on `e1b` (B20_R30). | Needed before any real run | `evidence/certification_budget_b20r30/` |
| 9 | **People.** An independent custodian on its own machine, a statistician, and a second operator for GV7. | Every scientific gate | `docs/OPERATIONS.md` |

## 2. Trusted-path changes to read (engineering)

| Area | What to read | Tests |
|---|---|---|
| New trusted Lean definitions | `P4Defs` (`invention/cuts_c4.py`, B20_R46) and **`SFDefs`** (`invention/cuts_sf.py`, B20_R55: `SF.SumFree`, `SF.ind`). These are domain contracts; a wrong definition would make every pattern theorem about something else. | `tests_formal/test_c4_generator.py`, `tests_formal/test_sf_generator.py` |
| Exact certificate checkers | `verification/lp_dual_rows.py`, `lp_dual_rows_c4.py`, `lp_dual_tree_c4.py`, `lp_dual_tree_sf.py`. Each docstring holds a soundness argument; registries come only from CHECKED statements of intact packages. | `tests_genesis/test_lp_dual_*`, `test_wiring_*` |
| Custody of generated-row certificates | `verification/certificates_rows.py`, `certificates_tree_c4.py`. Checker-only replay with registry re-derivation and revocation. | `tests_genesis/test_wiring_v5.py`, `test_wiring_tree_c4.py` |
| Evaluation request v5 and registry v2 | `custodian.py` (closed reference routes, `reference_problems`), `domains.py` (`ROWS_ROUTES`), `candidate_registry.py`, `candidates_v2.py`, `candidate_kinds/`. These are opt-in; v3 and v4 requests are unchanged. | `tests_genesis/test_wiring_v5.py`, `test_candidates_v2.py` |
| Registered interventions | `kernel/replay_contracts.INTERVENTIONS` (B20_R44: `cross_2 → ordered_2`, a Lean-checked strictly weaker decoder). | `tests_genesis/test_e1d_ablation.py` |
| DRAFT calibration rules | `calibration.DRAFT_RULES_BY_NAME` (`e1-hard-v3-draft`, `e1-hard-v2-c4tree-draft`). These are known for record checks, and no study adopts them. | `tests_genesis/test_wiring_tree_c4.py`, `test_e1d_*` |

Questions:
1. Do the exact checkers' soundness arguments hold? In particular, check:
   - effective right sides under fixed-in elements;
   - infeasible leaves;
   - pattern copies (graph embeddings for C4; maps preserving the additive relations for sum-free).
2. Do `P4Defs` and `SFDefs` say what the domain contracts mean (`G4.C4Free`; sum-free with a = b allowed)?
3. Is a generated theory package an acceptable source of evaluator rows, given revocation by package and checker
   identity?

## 3. Results since B20_R20, by gate (DEV, builder-run, preregistered)

**Positive:**

| Result | Batches |
|---|---|
| E1d beyond an exact MIP at 4× budget, with a causal control | B20_R41–R45 |
| Generated-row certification utility on triangle-free hosts | B20_R35 |
| The C4 transfer chain: an invented, Lean-checked component whose certification utility is attributed to it in a new graph domain | B20_R46–R49 |
| E1b scorable on C4, READY_FOR_REVIEW against DSL baselines | B20_R50, R52 |
| Sum-free transfer: stronger certified bounds, replicated (the coverage effect of B20_R57 did not replicate in B20_R59) | B20_R55, R57, R59 |

**Negative or limiting:**

| Result | Batches |
|---|---|
| No construction utility after cost for six invented components | B20_R17, R19, R26, R27, R31, R36 |
| MIP dominance on the certifiable settings | B20_R33, R34, R50 |
| No coverage gain from 7-vertex rows | B20_R37 |
| No equational research headroom | B20_R53, R54 |
| No sum-free certification utility on an unenriched sample (positive when enriched, B20_R57) | B20_R56 |
| No pattern-selection headroom (all patterns beat every subset) | B20_R58 |

**False discovery.** The attempt family has six construction and seven certification attempts. Under
Benjamini–Yekutieli at q = 0.1, B20_R35 (p 9.5e-7) and B20_R48 (p 0.00024) survive whatever the other p-values
are, and B20_R57 (p 0.0039) survives over the current 13, though its internal replication (B20_R59) failed on coverage.

## 4. Known limits

- One host. The rehearsals are clean-room on the build host only.
- DEV material only. No custodian-held panels, and fixture keys.
- Wall-time budgets on a shared two-core machine. Studies were pinned to one core; concurrent runs are disclosed
  where they happened.
- GitHub is not linked to the builder's session. The line is mirrored locally and delivered as checkpoint zips and
  git bundles.
