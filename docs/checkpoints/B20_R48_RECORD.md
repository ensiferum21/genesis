# B20_R48 record: certified branch and bound over the transferred C4 rows (CERTIFICATION_UTILITY)

- **Run by:** the builder, on DEV. Nothing here licenses a claim, and no evaluator was changed.
- **Commits:**
  - `08b7e41` (setup): the exact checker `verification/lp_dual_tree_c4.py`, the producer
    `discovery/generated_bnb_c4.py`, the script and the tests. All were committed before the run, and
    the SHA-256s were sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/c4_tree_certification_b20r48/`.

## Why

In B20_R47, the transferred C4 rows closed 80% of the evaluator's LP gap, but added no coverage. Its
disclosed diagnostics showed the remaining gap is global, and that branching over the same rows with
exact leaf certificates closes most of it.

## The certificate

A binary tree. Each node fixes one host edge out or in. Each leaf has either:
- a rationalised LP dual over the rows, with each right side reduced by the leaf's fixed-in edges;
- or a row its fixed-in edges overfill.

The checker uses exact arithmetic and no solver. The soundness argument is in the checker's
docstring: every C4-free set reaches exactly one leaf, and that leaf's bound holds for it.

## Result

40 fresh hosts at 60 s:

| Item | Evaluator | Tree route |
|---|---|---|
| Certified | 26/40 | **38/40** |
| … erdos n36 p0.17 | 7/20 | **18/20** |
| Certified by one route only | 0 | **12** |
| Median wall time | 46.9 s | **2.1 s** |

- **McNemar:** p = 0.00024.
- **Wall saving:** +27.8 s per host [20.7, 35.6].
- **Soundness:** every certificate VALID; no value disagrees.
- **Verdict: CERTIFICATION_UTILITY.**
- **Calibration limit:** both settings meet e1-hard-v2's limit under the tree route; only n30 does
  under the evaluator.

## What it means

This is the first prospective certification utility in the transferred domain. Whether the invented
rows are responsible, rather than the branching, is B20_R49, a registered ablation. In its
development look, branching without the rows certified 0 of 18 hard hosts, against 15 with them.

## Tests

- `tests_genesis/test_lp_dual_tree_c4.py` (6).
- `tests_genesis/test_c4_tree_certification.py` (6).

## Open

B20R48-OPEN-1 (new) concerns adopting the tree checker as a certification route for c4_host_v2:
- in the evaluator's reference, or in a DRAFT C4 rule like E1d's `e1-hard-v3-draft`;
- that would be a trust-path change for a reviewer;
- it would make C4 settings calibratable, so E1b's C4 arm, UNSETTLED_REFERENCE in B20_R23, could be
  re-piloted.
