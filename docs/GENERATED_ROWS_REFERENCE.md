# A generated-rows reference: built and wired opt-in, not adopted (B20_R39, B20_R42; DRAFT for a reviewer)

**Status.** DEV engineering by the builder. Adoption is a reviewed trust-path change
(B20R35-OPEN-1, B20R33-OPEN-1, B20R41-OPEN-1).
- **B20_R39** built the custody and the reference.
- **B20_R42** wired them into the custodian, but only for evaluation requests v5 that name the
  route explicitly, under rules this code knows. Requests v3 and v4, receipts, the adopted rules
  and the frozen packages behave exactly as before. No study adopts the route.
- **B20_R41** calibrated a dense family under the DRAFT rule `e1-hard-v3-draft` with this
  reference, and found E1 READY_FOR_REVIEW against an exact MIP at four times its budget.

## Why it exists

The evidence comes in three steps:
1. **The decided `e1b` family is easy for an exact solver.** There, an exact MIP solver proves
   every optimum within 0.36 CPU s. E1 is dominated by it, and E1b is within 0.2 edges (B20_R33).
2. **No harder setting is certifiable today.** Inside the 200-edge certification bound, wherever
   the evaluator certifies, the MIP is optimal (B20_R34).
3. **The dense planted regime is the candidate.** There, the MIP at 2 s fails, and E1's
   representation was optimal on every certified host (B20_R36, exploratory; tested in B20_R38).

That regime is certifiable at about 90% within 60 s only with the generated rows: 19/20 with v2
and 17/20 with v1 in B20_R37, against 1/20 for the evaluator alone (B20_R35). So the GV3 question,
"beyond strong baselines", can only be put to a custodian there if the evaluator can certify with
those rows.

## What is built

**`verification/lp_dual_rows.py` (B20_R32).** The exact checker for certificates over generated
rows. Its registry admits a pattern only from a CHECKED statement of an intact theory package that
uses the trusted definitions. Its identity is `lp_dual_rows.checker_identity()`.

**`verification/certificates_rows.py` (B20_R39).** Custody under its own schema,
`genesis-certificate-bundle-rows-v1`. The bundle holds four objects: the lower witness, the
certificate, the theory package, and the registry derived from the package. Replay is
checker-only:
- it checks the problem hash and the witness;
- it checks the package's integrity, re-derives the registry and compares it with the stored one;
- it re-checks the certificate exactly and compares the bound;
- it refuses revoked checker or package identities;
- optionally, it replays the Lean package in the pinned workspace.

`certificates.CHECKED_METHODS_V2` is unchanged, and the evaluator's replay does not accept this
schema.

**`discovery/generated_certify.reference` (B20_R39).** The evaluator's joint reference with the
generated rows: the same seed witness, LP over the rows, and SAT/DRAT on the remaining gap. A
certified result is taken into custody:
- LP_DUAL_GENERATED_EXACT in a rows bundle;
- SAT_DRAT in an ordinary v2 bundle.

`reference_record` (B20_R42) returns the bundle and its objects unwritten, so that the custodian
can persist them into its evidence store. B20_R41 adds `lp_rounding_seconds`, off by default: it
rounds the route's own LP solution, which is integral on most dense planted hosts.

**The wiring (B20_R42, opt-in).**
- **Request v5** (`kernel.receipts.REQUEST_V5`) is a v4 request plus a closed `reference` field.
  The field holds the route `generated-rows-v1`, the theory package by digest, and every route
  limit.
- **The custodian checks the route before registration** (`custodian.reference_problems`). The
  package must be one of `generated_certify.KNOWN_PACKAGES` and must pass its integrity checks.
  Its rows are derived only from CHECKED statements.
- **The reference.** `reference_options` asks the domain adapter for exactly that route. Only the
  triangle-free adapter offers it, and a C4 request is refused.
- **Custody.** The bundle goes into the evaluation's evidence store.
- **Binding.** The receipt stays scientific receipt v4. It binds the whole request, route
  included, by hash.

## What a reviewer would have to decide and do to adopt it

Steps 3 and 4 are built (B20_R42), and step 5 has a DRAFT measurement (B20_R41). Each still needs
the reviewer's decision.

1. **The package.** Accept the theory package, generator v1 (`evidence/relaxation_invention_b20r31/package.json`)
   or v2 (`evidence/generator_v2_b20r37/package.json`), and put it in custody. Its statements are
   checked in the pinned Lean workspace. A custodian replays it with `theory_package.replay`.
2. **The checker.** Review `lp_dual_rows.check_certificate` and `registry_from_package`, about
   200 lines, and record their identities. Revoking either identity blocks every bundle that rests
   on it.
3. **The reference method.** Version the evaluator reference, for example
   `joint-generated-rows-v1` beside the present joint LP/SAT reference. Name it in the analysis
   plan and in the evaluation request, so that neither side can switch methods silently.
4. **Custody.** Accept `certificates_rows` bundles in the custodian's evidence path, under the
   same object store and replay discipline as v2.
5. **Calibration.** Write a versioned family rule, for example an `e1-hard-v3` that names the
   generated-rows reference and its budget. Calibrate the dense regime under it, on DEV, with the
   certification limit measured by that reference.
6. **Strong baselines.** Decide whether the exact MIP is a comparator in the analysis plan
   (B20R33-OPEN-1). B20_R38 measures the frozen candidates against it in this regime.

## What it does not change

- **No existing package, rule or reference changes.**
- **Frozen descriptors are unaffected.** The E1/E1b descriptors do not include these files.
- **The certification is no more trusted than its parts.** It rests on the Lean statements, the
  exact checker and the witness checker. The LP producer and the MILP that generates ex(F) are
  untrusted. Their outputs are re-checked, and Lean proves each bound.

## The C4 counterpart: a tree route over transferred rows (B20_R46–R51; DRAFT for a reviewer)

The same discipline now exists for c4_host_v2. It is built and wired opt-in, and it is not adopted.

| Part | Module | Batch |
|---|---|---|
| Rows | 34 C4 patterns from the transferred procedure, all Lean-CHECKED (`evidence/c4_generator_b20r46/package.json`) | B20_R46 |
| Row checker | `verification/lp_dual_rows_c4.py`: registry from CHECKED statements only, with the trusted GTDefs, the c4_host_v2 G4Defs and a 0/1 `P4.adj` | B20_R47 |
| Tree checker | `verification/lp_dual_tree_c4.py`: branch-and-bound certificates. Each node fixes an edge out or in, and each leaf has an exact LP dual or an overfilled row. The soundness argument is in its docstring | B20_R48 |
| Producer | `discovery/generated_bnb_c4.py`: depth-first branch and bound, with no SAT step. It is untrusted, and every certificate is checked | B20_R48 |
| Custody | `verification/certificates_tree_c4.py`: schema `genesis-certificate-bundle-tree-c4-v1`. Checker-only replay with registry re-derivation, revocation of checker or package, and optional Lean replay of the package | B20_R51 |
| Wiring | v5 route `generated-rows-tree-c4-v1`, over a known C4 package (`generated_certify_c4.KNOWN_PACKAGES`) with the fast enumerator; the C4 adapter offers it, and the triangle-free adapter refuses it (`ROWS_ROUTES`) | B20_R51 |
| Rule | DRAFT `e1-hard-v2-c4tree-draft` (e1-hard-v2 with this reference), known to `calibration.DRAFT_RULES_BY_NAME`, adopted by no study | B20_R50, R51 |

**Evidence (DEV, preregistered).**
- **Coverage.** The tree route certifies 38 vs 26 of 40 fresh C4 hosts against the evaluator,
  p = 0.00024 (B20_R48).
- **Attribution.** A registered ablation gives the utility to the transferred rows: 36 vs 24 of
  40 (B20_R49).
- **Calibration.** Under the DRAFT rule, two C4 settings calibrate, and E1b's C4 arm is
  READY_FOR_REVIEW in readiness and both causal contrasts (B20_R50).

**Limits.**
- **Small dense hosts.** The route is slow there: K8 is not certified in 30 s, because tens of
  thousands of pattern copies make every node LP large (B20_R51 test).
- **Calibrated settings.** The calibrated settings are sparse erdos hosts. On those, an exact C4 MIP
  is optimal within 2 s (B20_R50; B20R33-OPEN-1 on C4).

**A reviewer's decisions** follow the six steps above, with this package, these checkers, this
custody, and B20R48-OPEN-1 and B20R50-OPEN-1. B20R46-OPEN-1 adds whether near-domain transfer
counts toward GV6.
