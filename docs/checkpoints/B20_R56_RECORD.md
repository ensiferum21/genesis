# B20_R56 record: the transferred sum-free rows do not give certification utility (NO_CERTIFICATION_UTILITY)

- **Built and run by:** the builder. DEV only; no claim.
- **Setup commit:** `b7c9d1c` (script SHA-256 `e5a43d1d…5b0d65`).
- **Evidence:** `evidence/sf_tree_certification_b20r56/`.

## Problem

B20_R55 transferred the row-invention procedure to sum-free sets of integers. Do the rows help certify optima?
In C4 they did (B20_R48/R49).

## Implementation

- **`verification/lp_dual_tree_sf.py`.** The exact tree-certificate checker. Its rows:
  - Schur triples, rhs 2;
  - doubles, rhs 1;
  - Freiman-type copies of CHECKED patterns from an intact package with the trusted `SFDefs`.

  Its soundness argument is in the docstring.
- **`discovery/generated_bnb_sf.py`.** The producer:
  - root separation over pattern copies (the C4 route's design);
  - depth-first branch and bound with exact dual pruning;
  - a descriptive HiGHS MILP.
- **The study.** 40 fresh random-subset hosts, (300, 0.6) and (360, 0.6), with a shared 10 s HiGHS witness and
  60 s per route. Route a is the Schur rows only: both the conventional route and the registered ablation.
- **The verdict rule.** B20_R35's.

The docstring disclosed the development looks and the expectation: a utility verdict was unlikely.

## Result: **NO_CERTIFICATION_UTILITY**

- **Coverage.** a certified 26 and c 28; 0 vs 2 hosts were certified by one route only (McNemar p 0.25).
- **Time.** Wall saving a − c is −1.61 s per host, 90% interval [−4.14, +1.37].
- **Soundness.** Every certificate is VALID.
- **Relaxation.** The rows lower the root bound by 5–10 (median 7) and cut median nodes from 278 to 85. Separation
  adds 3,924–10,429 rows, which slows node LPs: on easy hosts c is slower (median 18.8 vs 8.5 s).
- **Hard hosts (after the fact).** Where route a needs more than 30 s or fails, c does better on 6 of 8.

## Tests

- `tests_genesis/test_lp_dual_tree_sf.py` (3).
- `tests_genesis/test_sf_tree_certification.py` (3 design, 3 record).

## Consequence

GV6, second target:
- **The procedure transfers.** B20_R55: 20/20 obligations Lean-checked.
- **The rows strengthen the relaxation**, as in C4.
- **No preregistered utility on these settings.** Unlike C4.

Transfer utility is therefore domain-dependent. The after-the-fact concentration on hard hosts motivates one
preregistered follow-up, enriched by hardness for the conventional route (B20_R57). If that is also negative,
the sum-free target is settled as procedural transfer without utility.

## Open

B20R46-OPEN-1 is updated: the second target has no certification utility on these settings. The reviewer's GV6
decision now has one positive near-domain chain (C4) and one negative result in a different theorem family.
