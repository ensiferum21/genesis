# B20_R68 record: E1d's candidate matches a standard max-cut heuristic, and trails it at n60 (E1D_MATCHES_DOMAIN_HEURISTIC; DEV)

- **Run by:** the builder. DEV only; no claim, and no package, rule or comparator changes.
- **Setup commit:** `980794c` (recorded first as `bc5ee6d`; re-authored with an identical tree), script SHA-256
  `5d0a8800…5b97`, sent to Daniel before the run. Run alone, pinned to CPU 0.
- **Evidence:** `evidence/e1d_domain_heuristic_b20r68/`.

## Problem

The B20_R65 review found that E1's frozen candidate is one-flip max-cut local search plus a greedy triangle-free
completion, and that E1d's baselines include no max-cut heuristic. B20_R67 added one (`maxcut-tabu-v1`). Is the
candidate beyond it?

## Design

Part A: 30 fresh hosts on E1d's three calibrated settings. Part B: 20 fresh n60 hosts. Arms in runc under E1's
profile: the candidate (0.5 s), tabu at 0.5 s (primary) and 2 s, the package's HiGHS at 2 s. Primary: candidate −
tabu_0.5s, bootstrap 90% interval, MUE 0.5; CPU delivery checked first.

## Result: **E1D_MATCHES_DOMAIN_HEURISTIC** (Part A); Part B **HEURISTIC_AHEAD**

| | Part A | Part B (n60) |
|---|---|---|
| candidate − tabu_0.5s | +0.03 [0.00, 0.10], 1/29/0 | −1.15 [−1.65, −0.70], 1/6/13 |
| tabu_0.5s − HiGHS 2 s | +8.60 | +207.95 |
| optimum hits, candidate / tabu_0.5s | 29 / 28 of 30 | 3 / 7 of 13 |

CPU delivery holds (0.67 s median for both primary arms). Both parts came out as the builder expected.

## Consequence

- **E1d's advantage is the max-cut reduction, not something beyond the field's methods.** A textbook tabu search
  matches the candidate on the calibrated settings and beats E1d's comparator by the same margin; on n60 hosts it
  beats the candidate. Against HiGHS the result is a potential speedup in the sense of Rønnow et al. (2014); against
  the best-known class of methods there is none.
- **The GV4 fallback draft (Part A) and the review brief are corrected** to say so, with tested citations. The
  "useful solver" reading of E1d now has to be worded as "the system rediscovered the max-cut reduction and a
  max-cut local search", and the strong-baseline decision (review brief item 1) should include domain heuristics.
- **B20R41-OPEN-1** is updated. No package changes: E1d stays a DRAFT, and whether `maxcut-tabu-v1` joins its
  baseline set is the reviewer's decision.
- **For the system:** its invention search found a classical method and its repair engine stops at local optima.
  The physics-inspired plan that starts with B20_R69 takes this as its starting point.

## Tests

`tests_genesis/test_e1d_domain_heuristic.py`: Design (5); Record (3): the analysis and verdicts recompute from the
rows; the arms are the recorded descriptors, all in runc, never above a certified optimum; the hosts are fresh and
in the e1/e1b exposure addenda.
