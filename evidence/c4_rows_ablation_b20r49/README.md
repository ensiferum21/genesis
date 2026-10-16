# B20_R49 evidence: the transferred rows are responsible for the tree route's certification utility (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no evaluator.
- **Script:** `scripts/b20r49_c4_rows_ablation.py`, committed before running in `c6eae14`. Its SHA-256
  was sent to the user beforehand.
- **Code identity:** the summary records `6a1ccaa9…`, the setup commit's.
- **Producer and checker:** B20_R48's, unchanged.
- **Log:** `run.log`, 1,737 s, in one go.
- **Files:**
  - `hosts.json`: the 40 hosts and the exposure scan at generation;
  - `rows.jsonl`;
  - `certificates/`: the 12 tree certificates of hosts certified with the rows only, gzip, 1.8 MB in
    all;
  - `summary.json`.

## Design

There are two arms, run back to back in alternating order. They use the same producer, checker, limits
and 60 s budget, from the same seed witness:
- **c:** the tree route with B20_R46's registry (34 patterns the system generated and Lean-checked);
- **c0:** the registered ablation, the same route with an empty registry, so only the evaluator's own
  4-cycle rows. Its certificates name the empty registry's digest (`f64668f5…`) and are checked
  against it.

## Result (preregistered)

| | c: with the transferred rows | c0: 4-cycle rows only |
|---|---|---|
| **Certified** | **36/40** | **24/40** |
| … erdos n30 p0.2 | 20/20 | 12/20 |
| … erdos n36 p0.17 | 16/20 | 12/20 |
| Certified by one arm only | **12** | 0 |
| Search nodes, all hosts | **13,294** | 186,574 |
| Median nodes, hosts both certify (24) | **12** | 926 |
| Total wall time | 440 s | 1,226 s |

| Test | Result | Passes |
|---|---|---|
| Soundness | every certificate of both arms VALID with its bound; witnesses C4-free; no value disagrees | yes |
| Coverage c ≥ c0 | 36 ≥ 24 | yes |
| McNemar (one-sided) | 12 vs 0, **p = 0.00024** | yes |

**Verdict: ROWS_RESPONSIBLE.** Descriptive: the wall saving c0 − c is **+19.6 s per host**, 90% interval
[14.2, 25.3].

**Notes.**
- **Hosts open under both arms.** Four n36 hosts stayed open under both. The rows narrowed every one of
  their gaps: 3–5 edges with the rows, against 9–15 without.
- **n36 rate.** On this sample the tree route certified 16/20 (80%) at n36, against 18/20 in B20_R48.
  With 20 hosts per setting, the rate is uncertain near the 90% calibration limit.

## What it means

The certification utility of B20_R48 is attributable to the rows the system invented and transferred,
not to branching alone:
- with branching and 4-cycle rows only, the tree route certifies 24 of 40, about what the evaluator
  certified in B20_R48 (26 of 40, on other hosts);
- with the transferred rows, it certifies 36, with 14 times fewer search nodes.

This completes a prospective, preregistered chain on DEV for one invented component in a new
(near) domain:
- **B20_R46.** The procedure transfers, and every bound is Lean-checked.
- **B20_R47.** On its own the component adds no coverage, an honest negative.
- **B20_R48.** With branching it has certification utility.
- **B20_R49.** The utility is caused by the component.

In roadmap terms (E5), C4-free and triangle-free are near domains, so this is near-domain transfer
evidence. GV6 proper still needs a structurally different formal domain (B20R46-OPEN-1).

## Tests

`tests_genesis/test_c4_rows_ablation.py` (6):
- the preregistered constants;
- the ablation is the empty registry and is checked against it (K5: 6);
- the soundness rule and the tally;
- the verdict recomputes from the rows;
- the 12 kept certificates re-check VALID with their bound and digest;
- the hosts are fresh and in the exposure addenda.
