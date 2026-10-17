# B20_R66 evidence: E1d at n60 replicates and leads HiGHS through 120× (DEV): **REPLICATED_ADVANTAGE_THROUGH_120X**

Builder-run on DEV, outside every calibrated setting. It licenses nothing.
- **Script:** `scripts/b20r66_e1d_n60.py`. It was committed before the run in `f2731ba`, with its design, rule,
  validity criterion and expectation. SHA-256 `9618ae76…aaa`.
- **Log:** `run.log`, 3,472 s, alone on the machine.
- **Development looks:** none.

## Design (fixed before running)

**Hosts.** 20 fresh planted_cluster n60 hosts (0.8, 0.06), with 415–465 edges. They are drawn by B20_R64's DEV-only
generator, because they are beyond the registered family space and the 200-edge certificate bound. They exclude
3,017 exposure identities, which covers all of B20_R64's hosts.

**Arms.** All arms ran in runc:
- the 0.5 s candidate;
- HiGHS at 32 s (64×);
- HiGHS at 60 s (120×), the ceiling of `milp-highs-v1`.

**Rule.** B20_R63's per-budget rule.
- **Valid** iff HiGHS received at least 0.9 of its CPU budget where it ran to its limit.
- **REPLICATED** iff ADVANTAGE at 32 s.

## Result: **REPLICATED_ADVANTAGE_THROUGH_120X**

**Validity.** HiGHS received 0.9945 of its budget at 32 s (20 hosts) and 0.991 at 60 s (19 hosts). No run failed.

| HiGHS budget | Candidate − HiGHS, 90% interval | W/T/L | Verdict |
|---|---|---|---|
| 32 s (64×) | **+18.75** [12.85, 24.80] | 19/1/0 | ADVANTAGE: replicates B20_R64's +17.6 [8.1, 28.8] |
| 60 s (120×) | **+2.20** [1.60, 2.80] | 17/3/0 | ADVANTAGE, narrowly |

**Gap to the reference's proven upper bound.** The reference certified 10 of 20 hosts in 120 s; its upper bound is
the yardstick for all 20.

| Arm | Mean gap | Max gap |
|---|---|---|
| Candidate | 1.65 | 3 (at the bound on 4) |
| HiGHS at 60 s | 3.85 | 9 |
| HiGHS at 32 s | 20.4 | 48 |

HiGHS at 60 s never scored below HiGHS at 32 s.

## Reading

- **The n60 lead replicates.** On fresh hosts it matches B20_R64: about +18 edges at 64× HiGHS budget.
- **It survives 120×, but only just.** At 60 s HiGHS is about two edges behind the 0.5 s candidate. So at n60 the
  crossover lies just beyond 120× the candidate's budget, against 16× at n40 (B20_R63) and 64× at n50 (B20_R64).
- **The builder's expectation held:** an advantage through 120×, with a smaller lead.

**What it means for E1d's claim.** The candidate's edge is speed, and it widens with host size: at n60 it reaches,
in 0.5 s, values that HiGHS needs more than a minute to match. A claim at that size needs two reviewer decisions:
- extending the family space beyond n40;
- lifting the 200-edge certificate bound for the exact LP-dual route.

The reference certified only half of these hosts in 120 s, so a rule there would also need a longer reference
budget or a different certificate route.

## Tests

`tests_genesis/test_e1d_n60.py`.
- **Design (4).**
- **Record (3):** the verdict and validity recompute from the rows; no arm exceeds a proven upper bound; the hosts
  are fresh against B20_R64 and in the e1/e1b exposure addenda.
