# B20_R39 record: custody for certificates over generated rows, and a generated-rows reference (built, not wired)

- **Run by:** the builder. This is engineering only: there is no study and no new evidence
  directory. Nothing is wired into the evaluator or the custodian.
- **Commit:** the B20_R39 commit.
- **Design note for a reviewer:** `docs/GENERATED_ROWS_REFERENCE.md`.

## Why

B20_R35 and B20_R37 showed that certification with generated rows makes the dense planted regime
certifiable at about 90% within 60 s, where the evaluator alone certifies about 5%. B20_R36 and
B20_R38 concern whether a frozen candidate is beyond an exact MIP solver there. For a custodian to
use that regime, the generated-rows route needs the same custody as every other upper bound.

## What was built

**`verification/certificates_rows.py`.**
- **Schema:** `genesis-certificate-bundle-rows-v1`, with method LP_DUAL_GENERATED_EXACT.
- **Objects:** the witness, the exact certificate, the Lean theory package, and the registry
  derived from it.
- **`build`** refuses three things:
  - a certificate that does not check;
  - a package that fails integrity;
  - a lower bound above the upper.
- **`replay`** is checker-only:
  - it checks the problem hash and the witness;
  - it checks package integrity and re-derives the registry, compared with the stored one;
  - it re-checks the certificate exactly and compares the bound;
  - it refuses revoked checker or package identities;
  - optionally, it replays the Lean package.
- **Independence:** `certificates.CHECKED_METHODS_V2` is unchanged, and the evaluator's replay
  does not accept this schema.

**`discovery/generated_certify.reference`.** The evaluator's joint reference with the generated
rows: the same seed witness, LP over the rows, then SAT/DRAT on the remaining gap. Its results go
into custody: a rows bundle for LP_DUAL_GENERATED_EXACT, an ordinary v2 bundle for SAT_DRAT.
`certify_with_rows` now also returns the final witness and the SAT objects. Its bounds and
decisions are unchanged.

**`docs/GENERATED_ROWS_REFERENCE.md`.** What a reviewer would have to decide to adopt the route:
- the package in custody;
- checker identities;
- a versioned reference method named in the plan and the request;
- custodian acceptance of the schema;
- a versioned family rule and calibration;
- the strong-baseline comparator.

## Tests

`tests_genesis/test_certificates_rows.py` (6) checks:
- a bundle replays checker-only;
- each alteration is rejected: certificate, package, registry, bound, lower value, a missing
  object;
- revoked checker and package identities are refused;
- `build` refuses bad inputs;
- the evaluator's replay does not accept the schema;
- the reference takes its result into custody, and the custody replays.

## Open

B20R35-OPEN-1 now has the engineering it would need. Adoption remains a reviewer's decision.
