# B20_R54 record: research beyond the pool does not reach Wolfram's ceiling (design pilot)

- **Built and run by:** the builder. DEV only; a design diagnostic with no claim.
- **Setup commit:** `5eaf4e9` (script SHA-256 `fa4a21a0…c0ff1`).
- **Evidence:** `evidence/wolfram_ceiling_b20r54/`.
- **Disclosed:** a first B20_R54 design was drafted and set aside unrun (see the script docstring). It compared
  GAP with curated, random and complement libraries.

## Problem

B20_R53: on Wolfram's axiom at the hard settings, which pool lemmas are kept moves at most 1 of 15 targets. The
limit is the ceiling: 3–8 targets that no pool library proves. A research procedure can then help only by reaching
beyond the pool.

## Implementation

`scripts/b20r54_wolfram_ceiling.py` runs on fresh seeds 5401–5404 with two pools per seed:
- POOL5, built as in B20_R53;
- POOL6, the true equations of up to 6 nodes (233).

The evaluation targets are screened against every pool and development item for declared relations.

**Libraries:**
- EMPTY;
- EXHAUST5 and EXHAUST6;
- ORACLE5 and ORACLE6;
- GAP5 and GAP6, the transferred keep rule;
- REPEAT, to measure noise.

**Verdict** on ORACLE6 − ORACLE5, fixed in the script.

## Result: **NO_CEILING_HEADROOM**

- **Ceiling headroom.** ORACLE6 − ORACLE5 is 0, 0, 0, 0, and the noise is 0.
- **The larger pool.** EXHAUST6 − EXHAUST5 is −1, 0, 0, 0. EXHAUST6 proved 174–183 lemmas in 523–615 CPU-s; none
  proves a new target.
- **The keep rule.**
  - GAP6, with 1–5 lemmas, equals EXHAUST6.
  - GAP5 differs from EXHAUST5 by −1, 0, 0, +1.
  - On one seed, GAP5 beats ORACLE5 (13 vs 12) through lemma interference.

## Tests

`tests_genesis/test_wolfram_ceiling.py` has 7 tests: 4 design and 3 record.

## Consequence

- **The equational domain at these scales.** Across B20_R53 and R54, no library-building research changes
  Wolfram's successor by more than 1 of 15. None of the eight equational systems tried shows research headroom,
  at 1 s attempts or (Wolfram) at the hard settings.
- **For GV4 and GV6.** The equational target supplies neither GV4 headroom nor a GV6 transfer test.
- **What follows.** The GV6 target question moves to the other candidates. B20_R55 transfers the row-invention
  procedure to sum-free sets of integers, a different theorem family, with the structural caveat stated.

## Open

- **B20R9-OPEN-1.** Updated: the equational domain is closed for GV4 at these scales.
- **B20R46-OPEN-1.** Updated: the equational target has no headroom.
