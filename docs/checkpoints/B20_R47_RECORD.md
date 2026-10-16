# B20_R47 record: certification coverage on C4 hosts with the transferred C4 rows (NO_CERTIFICATION_UTILITY)

- **Run by:** the builder, on DEV. Nothing here licenses a claim, and no evaluator was changed.
- **Commits:**
  - `73ecc52` (setup): the exact checker `verification/lp_dual_rows_c4.py`, the route
    `discovery/generated_certify_c4.py`, the script and the tests. All were committed before the run,
    and the SHA-256s were sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/c4_certification_b20r47/`.

## Why

B20_R46 transferred the row-invention procedure to C4-free subgraphs. This step tests prospectively
whether the transferred rows help where the evaluator is weakest: certifying C4 optima. No C4
setting could be calibrated under e1-hard-v2, because the evaluator certified too few hosts in time.

## Result

40 fresh hosts in two settings, erdos n30 p0.2 and n36 p0.17, 60 s per route:

| Item | Evaluator | C4 rows route |
|---|---|---|
| Certified | 22/40 | 22/40 |
| Certified by the LP bound alone | 0 | 10 |
| Mean LP bound | 74.98 | 71.43 |

- **Discordant hosts:** none (McNemar p = 1.0).
- **Wall saving:** +2.24 s per host [0.23, 4.74], in the rows route's favour.
- **Soundness:** every LP certificate VALID.
- **Verdict: NO_CERTIFICATION_UTILITY.**
- **Secondary:** the rows close 80% of the LP gap on hosts with a known optimum.

The run was interrupted once, at the builder's 30-minute background limit after 25 hosts. It resumed
from the saved hosts and rows, and the interrupted host was re-run.

## Diagnostics after the run (disclosed)

These were run on the 18 open hosts:
- **Witness.** HiGHS's MILP over the same rows (a float diagnostic) shows the seed witness optimal or
  one edge short. The gap is in the bound.
- **Local rows.** Failure-driven rows on up to 8 vertices move the LP by at most 0.4. The gap is
  global.
- **Branch and bound.** A prototype with exact LP-dual leaf certificates certified 10 of the 13 open
  hosts recorded by then, at 60 s. That is B20_R48.

## What it means

The transferred rows are much stronger and somewhat faster, but they add no certification coverage
on their own. This is near-domain evidence (roadmap E5: C4-free and triangle-free are near domains).
GV6 still needs a structurally different formal domain.

## Tests

- `tests_genesis/test_lp_dual_rows_c4.py` (7).
- `tests_genesis/test_c4_certification.py` (5).

## Open

- B20R47-OPEN-1 (new): whether to adopt the C4 rows checker in the evaluator's C4 path. It would be a
  trust-path change. Its benefit is speed only, unless B20_R48's branching changes the picture.
- B20R46-OPEN-1 is updated: this is near-domain evidence.
