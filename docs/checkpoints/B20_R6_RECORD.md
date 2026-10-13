# B20_R6 record: search for an equational family with selection headroom (B20R3-OPEN-1)

- **Parent:** checkpoint B20_R5 (commit `0989a4f`).
- **Run by:** the builder, on DEV material only. Nothing in this record is independently reviewed.

## Problem

B20_R3 found no room for a better lemma-selection policy on six equational systems.
A better-improver claim needs a family where selection can matter.

## Implementation

Commit `d68da75` was made before the run. It contains:

- **The `ba_robbins` system** in `learning/equational.py`.
  - Axioms: commutativity, associativity and Robbins' equation.
  - Every Robbins algebra is Boolean (McCune 1997), so the two-element algebra decides truth exactly.
  - `tests_formal/test_learning.py::test_axioms_hold_in_their_variety` covers the new system.
- **`scripts/b20r6_family_search.py`.** It reuses the B20_R3 round-1 method unchanged.
  - Variants: Robbins and Boolean rings, each at two target sizes.
  - Verdict rule, fixed in the script: SELECTION_HEADROOM, HEADROOM_OVER_CAP or NO_HEADROOM.

## Evidence

All results are in `evidence/family_search_b20r6/`. All four variants came out NO_HEADROOM.

**Robbins' basis sits at the floor.**
- E proves 13 of 155 pool equations at 1 s.
- No target proof uses any of those lemmas.
- EXHAUST equals EMPTY in every range.

**Boolean rings sit near the ceiling, and lemmas interfere.**
- On 8–10 nodes the results were:
  - FIXED@CAP (34 lemmas): 11/12.
  - EXHAUST (132 lemmas): 8/12, the same as EMPTY.
  - ORACLE, built from the exhaust proofs: 8/12.
- In both larger ranges, one target that EMPTY proves is lost by EXHAUST.

## Limitations

- Two families, one prover, 12 targets per range, DEV only.
- The ORACLE built from exhaust proofs is not an upper bound once lemmas interfere.

## Consequence

B20R3-OPEN-1 stays open: eight systems show no room for choosing *which lemmas to prove*.

The interference finding is now replicated across two families (B20R3-OPEN-2). It points the next design at a different action space: library curation and premise selection (handoff s19.2). Measuring that needs a reference that searches library subsets.

Better-improver stays UNESTABLISHED.
