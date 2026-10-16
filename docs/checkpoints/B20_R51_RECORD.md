# B20_R51 record: the C4 tree route wired as an opt-in v5 reference with custody (built for review; not adopted)

- **Built by:** the builder. This is engineering only: no study, no claim, and no adopted rule.
- **Commit:** the B20_R51 commit.
- **Docs:** `docs/GENERATED_ROWS_REFERENCE.md`, new section "The C4 counterpart".

## Why

B20_R48–R50 showed three things on DEV:
- the C4 tree route has certification utility (38 vs 26 of 40);
- the utility is attributable to the transferred rows (36 vs 24 of 40);
- under a DRAFT rule it makes E1b's C4 arm scorable (READY_FOR_REVIEW).

A reviewer can adopt it only if its results have custody and the evaluator can be asked for it
explicitly. This batch builds both, in the B20_R39/R42 pattern.

## What changed

**New: `verification/certificates_tree_c4.py`.** A custody bundle for tree certificates, schema
`genesis-certificate-bundle-tree-c4-v1`. Replay is checker-only:
- the witness is re-checked;
- the package's integrity and identity are checked;
- the registry is re-derived from the package, with the trusted GTDefs and G4Defs, and compared with
  the stored one;
- the tree is re-checked exactly;
- revoked checker or package identities are refused;
- with `replay_package=True`, the Lean package is replayed too.

The evaluator's replay and the generated-rows replay refuse this schema.

**Other modules:**

| Module | Change |
|---|---|
| `discovery/generated_certify_c4.py` | `KNOWN_PACKAGES`, a closed list (today B20_R46's package), and `known_package(sha256)` |
| `discovery/generated_bnb_c4.py` | `reference_record`: the tree route from the evaluator's seed (DSL rounds=8 or 1 s of LP greedy), with custody, returning (record, bundle, objects) |
| `custodian.py` | route `generated-rows-tree-c4-v1` in `REFERENCE_ROUTES`. `reference_problems` checks the C4 package (and refuses a triangle-free one) and requires the fast enumerator. `reference_options` asks the adapter for the route only if the adapter lists it in `ROWS_ROUTES` |
| `domains.py` | `ROWS_ROUTES`: the triangle-free adapter offers `generated-rows-v1`, and the C4 adapter offers `generated-rows-tree-c4-v1` (`ROWS_REFERENCE` is now True for C4). An adapter refuses any other route as Unsupported. The C4 reference persists its bundle in the evidence store |
| `calibration.py` | `SELECTION_RULE_E1_HARD_V2_C4TREE_DRAFT`, identical by test to B20_R50's rule, is listed in `DRAFT_RULES_BY_NAME` so that records using it can be checked. It is not in `RULES`, and no study adopts it |

**Unchanged:**
- v3 and v4 requests and their references;
- the triangle-free route and its behaviour (the existing v5 tests pass unchanged);
- receipts, adopted rules, frozen descriptor ids and packages.

## Tests

`tests_genesis/test_wiring_tree_c4.py` (9). It checks:
- that custody replays OPTIMALITY_CHECKED on a 30-edge host, and that altered certificate and
  registry objects, a misstated lower bound, revoked checker and package, and missing objects are
  all refused;
- that the other custody paths refuse this schema;
- that the route is closed, its package must be a known C4 package, and it needs the fast
  enumerator;
- that each adapter offers only its own route;
- that the C4 adapter computes the reference with custody;
- that an uncertified host (K8 at 5 s) is Unsupported, and small hosts keep exact search;
- that the draft rule is known but adopted by no study.

`tests_genesis/test_e1b_c4_readiness.py`: one design assertion is updated deliberately. The draft is
now listed as a DRAFT; the test still checks that no study adopts it.

The full `tests_genesis` suite passes.

## Limits

The route is slow on small dense hosts: K8 is not certified in 30 s. The DEV evidence so far is on
sparse erdos settings, where an exact C4 MIP is optimal within 2 s (B20_R50).

## Open

B20R48-OPEN-1 and B20R50-OPEN-1 are updated: custody and opt-in wiring now exist for the reviewer's
adoption decision.
