# B20_R36 record: generated K5 rows as a construction component in the dense regime (relaxation family, attempt 2)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim.
- **Commits:**
  - `9cfe851` (setup): the script, committed before the run. Its SHA-256 was sent to the user
    beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/dense_construction_b20r36/`.

## Why

Attempt 1 (B20_R31) found +0.19 over the plain LP greedy on the `e1b` family, where the triangle
LP is nearly tight. B20_R35 found two settings where it is loose and the K5 rows tighten it.
Attempt 2 asks whether that tighter LP also constructs better. The setting choice was declared in
the preregistration.

## Result

The arms ran on 32 EVAL hosts at 2.0 CPU s each, on one pinned core.

| new − … | Mean per host | Passes |
|---|---|---|
| plain LP greedy | +3.94 [+2.41, +5.41] | yes |
| matched | +3.31 | yes |
| conventional | +11.0 | yes |
| exact MIP, secondary | +4.31 (BEYOND_MIP) | yes |
| menu `cross_2` | **−2.97** [−4.03, −1.94] | **no** |

**Verdict: NO_UTILITY_AFTER_COST.** The generated rows give a large gain over the LP component
they strengthen, even after cost. But a builder-written 2-colouring decoder is better on these
near-bipartite optima.

## What it means

- **GV4.** Five attempts in four families now have Lean-checked components, and none has
  construction utility under the B20_R17 rule:
  - relational ×2;
  - quotient;
  - decomposition;
  - relaxation ×2.

  This attempt is the closest yet. It beats every comparator except the menu, and that by wide
  margins. The menu itself came from the B18 representation grammar.
- **GV3 (B20R33-OPEN-1), exploratory.** In the dense planted regime, `cross_2`, the representation
  of E1's frozen candidate, is at the certified optimum on 10/10 certified hosts. HiGHS at 2 s is
  13.9 below it there. So a regime exists where a candidate could be "beyond strong baselines".
  It is not yet certifiable enough to calibrate: 23/32 here and 27/40 in B20_R35, at 60 s. Raising
  that is B20_R37: generated rows on 7 vertices, a faster copy enumeration, and a preregistered
  coverage test.

## Tests

`tests_genesis/test_dense_construction.py` (4 tests) checks:
- the component is the CHECKED K5 bound;
- the comparisons and verdict follow from the rows;
- no arm exceeds a certified optimum;
- the hosts are fresh and in the addenda.

## Open

- **B20R36-OPEN-1 (new):** relaxation family, attempt 2.
- **B20R9-OPEN-1:** updated.
- **B20R33-OPEN-1:** updated with the dense-regime observation.
