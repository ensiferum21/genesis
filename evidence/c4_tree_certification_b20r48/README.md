# B20_R48 evidence: certified branch and bound over the transferred C4 rows (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no evaluator.
- **Script:** `scripts/b20r48_c4_tree_certification.py`. It was committed before running in `08b7e41`,
  together with:
  - the exact tree checker (`verification/lp_dual_tree_c4.py`);
  - the producer (`discovery/generated_bnb_c4.py`).
  Their SHA-256s were sent to the user beforehand.
- **Code identity:** the summary records `09006a1a…`, which is that of the setup commit.
- **Registry:** B20_R46's package `7a081e4a…`, 34 CHECKED patterns.
- **Log:** `run.log`, 2,023 s, in one go.
- **Files:**
  - `hosts.json`: the 40 hosts and the exposure scan at generation;
  - `rows.jsonl`;
  - `certificates/`: the 12 tree certificates of hosts certified by the tree route only, gzip, 2.6 MB in
    all;
  - `summary.json`.

## Result (preregistered)

40 fresh hosts in B20_R47's settings, 60 s per route, both from the evaluator's seed witness:

| | a: evaluator (4-cycle LP, then SAT/DRAT) | c: tree route (generated rows, branch and bound) |
|---|---|---|
| **Certified** | **26/40** | **38/40** |
| … erdos n30 p0.2 | 19/20 | 20/20 |
| … erdos n36 p0.17 | 7/20 (35%) | 18/20 (90%) |
| Certified by one route only | 0 | **12** |
| Median wall time (c includes its exact check) | 46.9 s | **2.1 s** |
| Total wall time | 1,533 s | 419 s |

| Test | Result | Passes |
|---|---|---|
| Soundness | every certificate VALID with the claimed bound; witnesses C4-free with the reported values; no value disagrees | yes |
| Coverage c ≥ a | 38 ≥ 26 | yes |
| McNemar (one-sided) | 12 vs 0 discordant, **p = 0.00024** | yes |
| Wall saving a − c | **+27.8 s per host**, 90% interval [+20.7, +35.6] | yes |

**Verdict: CERTIFICATION_UTILITY.**

**Secondary (preregistered, descriptive).**
- **Calibration limit.** Under the tree route, both settings meet e1-hard-v2's certification limit
  (at least 90% within 60 s). Under the evaluator only n30 does. erdos n36 p0.17 is at 35%, and in
  B20_R24, erdos n30 p0.2 failed at 6/8.
- **How hosts were certified.** 31 of the tree route's certifications needed branching, with 3 to 2,753
  nodes; the median over all 38 certified hosts was 35. The other 7 came from the root LP alone.
- **Cost of the certificates.** The exact check took at most 1.7 s. The largest certificate is 9.3 MB
  (raw JSON).

**Notes.**
- **Hosts left open by the tree route.** Two hosts stayed open under it (83..85 and 80..84), and
  under the evaluator too (82..91 and 81..90). On the second, the evaluator's SAT step found a better
  witness (81). The tree route has no SAT step.
- **Time overruns.** Three hosts overran 60 s under the evaluator (80–114 s). As in B20_R47, its DRAT
  check is not counted in the solver's budget. No tree-route host overran: the longest took 53 s,
  check included.

## What it means

The rows the system invented in the triangle-free domain, transferred to C4 by B20_R46 and checked in
Lean, now give the C4 evaluator a certification utility. With branching and exact leaf certificates,
they certify 38 of 40 fresh hosts against 26, about 20 times faster at the median. That makes C4
settings calibratable that were not.

**Not yet shown:** that the invented rows are responsible. The route also adds branching, a
builder-written method. B20_R48's development look found that branching over 4-cycle rows alone
certified none of B20_R47's 18 open hosts. **B20_R49 tests this prospectively** as a registered
ablation.

## Tests

`tests_genesis/test_lp_dual_tree_c4.py` (6):
- the route certifies the exact optimum on fixed small hosts and the Petersen graph, and against
  brute force;
- branching is used and checked;
- every tampering is rejected;
- infeasible leaves are accepted only when overfilled.

`tests_genesis/test_c4_tree_certification.py` (6):
- the preregistered constants, the soundness rule and the tally;
- the verdict recomputes from the rows;
- the 12 kept certificates re-check VALID with their bound and digest;
- the hosts are fresh and in the exposure addenda.
