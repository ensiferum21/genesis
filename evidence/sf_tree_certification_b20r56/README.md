# B20_R56: certified branch and bound over the transferred sum-free rows (GV6 second target; DEV)

- **Script:** `scripts/b20r56_sf_tree_certification.py`, preregistered in commit `b7c9d1c`.
  SHA-256 `e5a43d1d…5b0d65`.
- **Modules:** `verification/lp_dual_tree_sf.py` (the exact checker) and `discovery/generated_bnb_sf.py` (the
  producer).
- **Run:** the builder, pinned to one core, 3,142 s.
- **Code identity:** `46d76297…eb08d8`.
- **Status:** a DEV measurement. It licenses nothing, and neither module is wired into anything.

## Question

B20_R55 transferred the row-invention procedure to sum-free sets of integers: 17 Lean-checked patterns. In C4,
the same rows inside certified branch and bound gave CERTIFICATION_UTILITY (B20_R48), attributed to the rows
(B20_R49). Do they help certify maximum sum-free subsets?

Route a is the same tree over the Schur rows only. It is both the conventional route and the registered ablation.

## Result: **NO_CERTIFICATION_UTILITY**

The setup:
- 40 fresh hosts: random subsets of {1..N} with density p, 20 each at (300, 0.6) and (360, 0.6), 159–236 elements;
- a 10 s HiGHS witness for each host, shared by both routes;
- 60 s per route, with the exact check counted in each route's time.

| | a: Schur rows only | c: with the transferred rows |
|---|---|---|
| Certified | 26 | 28 |
| Certified by one route only | 0 | 2 |
| Median wall time | 30.7 s | 28.7 s |
| Total wall time | 1,341 s | 1,406 s |
| Median nodes | 278 | 85 |
| Root bound | — | 5–10 below a's on every host (median 7) |

The rule's four tests:

| Test | Result | Passes |
|---|---|---|
| Soundness | Every certificate of both routes VALID, every witness sum-free, values agree | yes |
| Coverage | c ≥ a | yes |
| McNemar (one-sided) | p = 0.25 | **no** |
| Wall saving a − c | −1.61 s per host, 90% interval [−4.14, +1.37] | **no** |

## Where the rows help (descriptive, after the fact)

- **Easy hosts.** On the 20 hosts both routes certify and route a finishes within 30 s, c is slower: median
  18.8 s against 8.5 s. Separation adds 3,924–10,429 rows, and each node's LP gets heavier.
- **Hard hosts.** On the 8 hosts where route a needs more than 30 s, or fails, c does better on 6:
  - it certifies 2 hosts route a cannot: 37.4 s and 16.9 s, against a's gaps of 30 and 49;
  - it is faster on 4 of the other 6 (for example 50.5 → 24.1 s and 39.9 → 29.8 s).
- **Hosts neither certifies (12).** c's remaining gap is smaller: median 19 against 24.5.
- **Witnesses.** The 10 s witnesses are often weak. HiGHS proved optimality on only 5 hosts, and one witness had
  3 elements. Both routes start from the same witness.

**Interpretation.** In sum-free, the transferred rows strengthen the relaxation as they did in C4 (root bound
5–10 lower, 3× fewer nodes). On these settings, though, their cost outweighs that on most hosts, and the
preregistered utility test fails. Any benefit is concentrated where the conventional route struggles. This
after-the-fact pattern motivates one preregistered follow-up on hosts that are hard for the conventional route:
B20_R57, the B20_R32 → R35 pattern of enrichment. It is not evidence by itself.

## Files

- `hosts.json`: the 40 hosts.
- `rows.jsonl`: per host, the witness and both routes' bounds, times, nodes, root bounds, separation, check
  verdicts and certificate digests.
- `summary.json`: the verdict, tallies by setting, and the registry and checker identities.
- `certificates/`: gzip-compressed certificates of the 2 hosts certified by one route only.
- `run.log`: the log.

## Tests

`tests_genesis/test_sf_tree_certification.py` (6) and `tests_genesis/test_lp_dual_tree_sf.py` (3).

The design tests check:
- the constants;
- the hosts;
- the ablation is the empty registry;
- the verdict rule.

The record tests check:
- the hosts are the script's;
- the verdict recomputes;
- the witnesses are sum-free;
- the kept certificates re-check VALID.

The checker tests check:
- the registry is derived from the package only, and other definitions are refused;
- the optimum is certified on small hosts by both routes;
- alterations are refused;
- copies match brute force;
- separation keeps the Schur rows.
