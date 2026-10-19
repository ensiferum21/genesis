# B20_R68 evidence: E1d's candidate against a standard max-cut heuristic: **E1D_MATCHES_DOMAIN_HEURISTIC** (Part A), **HEURISTIC_AHEAD** at n60 (Part B)

Builder-run on DEV. It licenses nothing, and no package, rule or comparator changes.
- **Script:** `scripts/b20r68_e1d_domain_heuristic.py`, committed with its design, rule and expectation before any
  run (setup commit `980794c`, first recorded as `bc5ee6d` before a re-authoring with an identical tree; script
  SHA-256 `5d0a8800…5b97`, sent to Daniel before the run).
- **Run:** alone on the machine, pinned to CPU 0, 2,102 s. `code_identity` `f0ce6ac7…0911`.
- **Development looks:** none (`maxcut-tabu-v1` had run only on its unit-test hosts).

## Question

The B20_R65 review found that E1's frozen candidate (`represent-and-repair-v1`, `cross_2` decoder) is one-flip
max-cut local search from random two-colourings plus a greedy triangle-free completion, and that none of E1d's five
baselines is a max-cut heuristic. Is the candidate beyond a standard method of its own field?

## Design (fixed before running)

- **Part A:** 30 fresh hosts on the three planted settings of E1d's calibration record (10 each, 154–199 edges).
- **Part B:** 20 fresh n60 planted (0.8, 0.06) hosts (411–447 edges), beyond the family space and the 200-edge
  bound. Both parts exclude all 3,037 hosts named in the evidence (B20_R66's included).
- **Arms, in runc, E1's profile:** the candidate (0.5 s); `maxcut-tabu-v1` at 0.5 s (primary) and at 2 s; the E1d
  package's HiGHS at 2 s (`milp_highs_4x`, checked by id).
- **Primary:** candidate − tabu_0.5s per host; Part A stratified bootstrap 90% interval, Part B plain bootstrap
  (4,000 resamples, seed 20266899); MUE 0.5; CPU delivery checked first.

## Result

**Validity.** Every run succeeded; the median cgroup CPU of the candidate and of tabu_0.5s is 0.67 s in both parts
(0.5 s of search plus start-up), so the budget was delivered.

| | Part A (calibrated, n38–40) | Part B (n60) |
|---|---|---|
| candidate − tabu_0.5s | **+0.03 [0.00, 0.10]**, 1 / 29 / 0 | **−1.15 [−1.65, −0.70]**, 1 / 6 / 13 |
| verdict | **NO_MATERIAL_DIFFERENCE** | **HEURISTIC_AHEAD** |
| candidate − tabu_2s | +0.03 [0.00, 0.10] | −1.25 [−1.75, −0.75], 1 / 5 / 14 |
| tabu_0.5s − HiGHS 2 s | +8.60 [7.20, 9.93], 25 / 5 / 0 | +207.95 [205.75, 210.30], 20 / 0 / 0 |
| candidate − HiGHS 2 s | +8.63 [7.23, 10.00] | +206.80 [204.75, 209.00] |
| certified hosts | 30 of 30 | 13 of 20 |
| optimum hits (cand / tabu 0.5 s / tabu 2 s / HiGHS) | 29 / 28 / 28 / 5 | 3 / 7 / 8 / 0 |
| mean gap to the proven upper bound (cand / tabu 0.5 s) | 0.03 / 0.07 | 1.95 / 0.80 |

**Overall verdict (from Part A): E1D_MATCHES_DOMAIN_HEURISTIC.** Both parts came out as the builder expected.

## Reading

**On E1d's calibrated settings, a textbook max-cut heuristic does everything the candidate does.** Tabu search at
the same 0.5 s budget ties it on 29 of 30 hosts and beats E1d's comparator, HiGHS at 2 s, by the same margin
(+8.60 against the candidate's +8.63). So E1d's advantage over HiGHS is the advantage of the max-cut reduction plus
local search over a generic MILP at a short budget. In the terms of Rønnow et al. (2014), it is a *potential*
speedup, against one chosen baseline; against the best-known class of methods for the problem there is no
advantage.

**On larger hosts the standard heuristic is ahead** (later labelled FRAGILE by the B20_R73 multiverse analysis: it holds
only with the mean and MUE ≤ 0.5; the direction, 13 of 20 hosts against 1, is not in doubt). At n60 tabu search is better on 13 hosts and worse on 1, by
1.15 edges per host, and it reaches the optimum on 7 of 13 certified hosts against the candidate's 3. Four times
more time for tabu changes little (−1.25), so the gap is in the search, not the budget: one-flip descent stops at
local optima that tabu search's moves escape.

**HiGHS at 2 s on n60 hosts is not a meaningful comparator.** It returns about 58 edges on hosts where the optimum
is about 265: its incumbent after 2 s is still poor. This is why B20_R64's n60 gaps at short HiGHS budgets were so
large; at 32 s and 60 s HiGHS is close (B20_R66).

**What this means for E1d.** The discovery the system made is real but classical: its representation search
rediscovered that a cut of the host is a large triangle-free subgraph, and turned that into a max-cut local search.
A claim of "useful discovery beyond strong baselines" (GV3) cannot rest on beating HiGHS when a standard max-cut
heuristic matches the candidate on the calibrated settings and beats it on larger hosts. The GV4 fallback draft and
the review brief now say so. Whether the reviewer's strong-baseline set must include domain heuristics (review brief
item 1) is still the reviewer's decision; this study is the evidence for it.

**A side effect for certification.** Seeded with tabu search's better witnesses, the generated-rows reference
certified 13 of 20 n60 hosts (B20_R66: 10 of 20, seeded by the candidate and HiGHS), with a median of 43 s.

## Tests

`tests_genesis/test_e1d_domain_heuristic.py`.
- **Design (5):** fresh seeds; the arms; the rule; the analysis on synthetic rows (including the delivery and
  failure verdicts); the study is pinned.
- **Record (3):** both parts' analyses and the verdicts recompute from `rows.jsonl`; the arms are the recorded
  descriptors, all in runc, never above a certified optimum; the 50 hosts are distinct, match the rows and are in
  the e1/e1b exposure addenda (`exposure_hosts_addendum_b20r68.json`).
