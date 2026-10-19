# B20_R66 evidence: E1d at n60 replicates, and leads HiGHS through 120× its budget: **REPLICATED_ADVANTAGE_THROUGH_120X**

Builder-run on DEV, outside every calibrated setting, the registered family space and the 200-edge certificate
bound. It licenses nothing.
- **Script:** `scripts/b20r66_e1d_n60.py`, committed with its design, rule and expectation in `f2731ba` before any
  run. The run used that file unchanged (SHA-256 `9618ae76…9aaa`) at commit `4341806`.
- **Run:** alone on the machine after the B20_R65 release-matrix re-run had finished, pinned to CPU 0
  (`taskset -c 0`), 3,476 s. `code_identity` `f6a8dcf9…137b`.
- **Development looks:** none.

## Question

B20_R64 (a pilot, 10 hosts) found the 0.5 s candidate leading HiGHS at 32 s (64×) by +17.6 [8.1, 28.8] on n60
planted hosts. Does that replicate on fresh hosts, and does it survive HiGHS at 60 s (120×), `milp-highs-v1`'s
ceiling?

## Design (fixed before running)

- **Hosts:** 20 fresh planted_cluster hosts, n60, p_in 0.8, p_out 0.06 (seed 20266601), 415–465 edges, drawn by
  B20_R64's DEV-only generator and excluding all 3,017 hosts named anywhere in the evidence (B20_R64's included).
- **Arms, in runc:** E1's frozen candidate (0.5 CPU s), HiGHS at 32 s (B20_R63/R64's descriptor) and at 60 s.
- **Endpoint per budget:** candidate − HiGHS per host; bootstrap 90% interval (4,000 resamples, seed 20266699);
  ADVANTAGE iff the lower end > 0.5 (B20_R63's rule).
- **Validity:** for each HiGHS arm, the median CPU/budget over hosts where it ran to its limit must be ≥ 0.9.
- **Reference:** B20_R41's generated-rows route at 120 s; descriptive.

## Result

**Validity holds.** HiGHS 32 s: 0.994 (20 hosts at the limit); HiGHS 60 s: 0.990 (18 hosts). Every run of every
arm succeeded, in `OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP`.

| HiGHS budget | candidate − HiGHS | 90% interval | W / T / L | Verdict |
|---|---|---|---|---|
| 32 s (64×) | **+16.65** | [11.0, 22.6] | 19 / 1 / 0 | ADVANTAGE |
| 60 s (120×) | **+2.00** | [1.35, 2.65] | 17 / 2 / 1 | ADVANTAGE |

**Verdict: REPLICATED_ADVANTAGE_THROUGH_120X**, as the builder expected, with a much smaller lead at 60 s.

**Descriptive.**

| Arm | Mean gap to the proven upper bound (max) | Optimum hits on the 10 certified hosts |
|---|---|---|
| candidate (0.5 s) | 1.65 (3) | 4 |
| HiGHS 32 s | 18.3 (46) | 0 |
| HiGHS 60 s | 3.65 (9) | 0 |

- HiGHS at 60 s was never below HiGHS at 32 s on a host.
- The reference certified 10 of 20 hosts (median 92 s wall; every certificate `LP_DUAL_GENERATED_EXACT`); the other
  10 hit its 120 s limit, each with a bound at most 3 above the candidate.
- The candidate's median cgroup CPU was 0.67 s (0.5 s of search plus start-up).

## Reading

**The n60 pilot replicates.** At 64× the lead (+16.65 [11.0, 22.6]) is B20_R64's (+17.6 [8.1, 28.8]) on twice
the hosts, and HiGHS's mean gap to the bound (18.3) is B20_R64's (18.7).

**The lead shrinks fast between 64× and 120×.** HiGHS's gap to the bound falls from 18.3 to 3.65 when its budget
rises from 32 s to 60 s. The candidate is still ahead by 2 edges at 120×, on 17 of 20 hosts, but the trend
points to a crossover not far above 60 s, beyond `milp-highs-v1`'s ceiling. This replicates B20_R63's finding at
n38–40, at a larger scale: the candidate's advantage over an exact MILP is speed, and the budget at which HiGHS
catches up grows with host size (16× at n40, 64× at n50, above 120× at n60).

**The candidate is not optimal at n60.** It reached the optimum on 4 of the 10 certified hosts and is 1.3 below on
average there. At n38–40 it is optimal on 29–30 of 30. So at this size there is room above it, and a stronger
search could close it. Whether a standard max-cut heuristic does so is B20_R68's question.

**What this does not show.** The hosts are outside the calibrated settings, the family space and the 200-edge
bound, so it cannot support a claim (B20_R64's three reviewer decisions still apply). And the comparator is a
generic exact solver; no domain heuristic was run.

## Tests

`tests_genesis/test_e1d_n60.py`.
- **Design (4):** seeds are fresh; the arms; the rule; the delivery measure.
- **Record (3):** the verdict, per-budget results, delivery and descriptive figures recompute from `rows.jsonl`;
  the arms are the recorded descriptors; the hosts are distinct, match the rows and are in the e1/e1b exposure
  addenda (`exposure_hosts_addendum_b20r66.json`).
