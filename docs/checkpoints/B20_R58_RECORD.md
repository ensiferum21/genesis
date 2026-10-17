# B20_R58 record: no pattern-selection headroom in sum-free certification (GV4 design pilot)

- **Built and run by:** the builder. DEV only; no claim.
- **Setup commit:** `641ff38` (script SHA-256 `26535533…2cb4eb`).
- **Evidence:** `evidence/sf_pattern_selection_b20r58/`.

## Problem

Does choosing a subset of B20_R55's 17 patterns beat both none and all on sum-free certification? That would be a
research decision with headroom, which GV4 needs.

## Result: **NO_HEADROOM**

- **Certified at 30 s, of 16 evaluation hosts:**
  - ALL: 13;
  - NONE: 10;
  - TOP-1: 9;
  - TOP-2: 10;
  - TOP-4: 10;
  - TOP-8: 11.
- **Headroom.** H = −2, and the deployable choice is also −2.
- **Why.** Patterns alone move the root bound 0.1–0.6; together they move it 7. Their value is joint.

## Tests

`tests_genesis/test_sf_pattern_selection.py` (3 design, 2 record).

## Consequence

B20R9-OPEN-1 is updated. Every probed setting lacks research-decision headroom. The builder recommends the
roadmap's GV4 fallback (a useful solver, not a better improver) for the reviewer's decision.
