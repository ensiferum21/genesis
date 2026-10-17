# B20_R64 evidence: E1d's advantage over HiGHS grows with host size (DEV pilot): **ADVANTAGE_GROWS**

Builder-run on DEV, outside every calibrated setting. It licenses nothing.
- **Script:** `scripts/b20r64_e1d_scaling.py`. It was committed before any run in `6feb780`, with its design, rule
  and expectation. SHA-256 `0a576290…8775`.
- **Development looks:** none.

## Run 1 is invalid; this is the re-run

Run 1 (`run1_contended/`) ran beside a release matrix whose unpinned Lean processes shared its core. The two arms
were affected differently:
- **HiGHS** has a wall-clock time limit, and received 0.55–0.86 of its CPU budget;
- **the candidate's** budget is CPU time, so contention could not shorten it.

`RERUN_NOTE.md` records two decisions, both committed before the re-run (`3bceee2`): run 1 is invalid, and the
validity criterion.

**The criterion.** For every HiGHS arm and every n, the median CPU/budget ratio must be at least 0.9, counting only
hosts where HiGHS ran to its limit. The re-run used the unchanged script on the same hosts, alone on the machine
(1,474 s), and it meets the criterion:

| Arm | n40 | n50 | n60 |
|---|---|---|---|
| HiGHS 2 s | 1.118 | 1.113 | 1.117 |
| HiGHS 8 s | 1.018 (1 host) | 1.021 | 1.021 |
| HiGHS 32 s | (none ran to its limit) | 0.998 (1 host) | 0.997 |

## Design (fixed before running)

**Hosts.** planted_cluster with p_in 0.8 and p_out 0.06, 10 fresh hosts at each size:

| n | Edges |
|---|---|
| 40 | 177–194 |
| 50 | 277–312 |
| 60 | 409–440 |

The n50 and n60 hosts are drawn by a DEV-only copy of the adapter's generator, because the registered family space
stops at n40. They are above the custody path's 200-edge certificate bound.

**Arms.** E1's frozen candidate (0.5 CPU s), and HiGHS at 2, 8 and 32 s (4×, 16×, 64×).

**Rule.** B20_R63's per-budget rule and crossover, applied at each n.
- **ADVANTAGE_GROWS:** the n60 crossover is later than the n40 crossover.

## Result: **ADVANTAGE_GROWS**

| n | 2 s (4×) | 8 s (16×) | 32 s (64×) | Crossover |
|---|---|---|---|---|
| 40 | +15.2 [13.6, 16.6] ADVANTAGE | +0.1 [0.0, 0.3] no material difference | 0.0 | **8 s (16×)**, as in B20_R63 |
| 50 | +141.9 [139.1, 144.9] ADVANTAGE | +25.4 [24.3, 26.5] ADVANTAGE | −0.3 [−0.7, 0.1] UNRESOLVED | **32 s (64×)** |
| 60 | +208.8 [205.0, 212.8] ADVANTAGE | +47.5 [40.6, 55.8] ADVANTAGE | **+17.6 [8.1, 28.8] ADVANTAGE, 10/0/0** | **none within 64×** |

At 2 s on the larger hosts HiGHS has barely started (about 50 of about 190 edges at n50). The 4× contrasts there
measure that, not a race.

**How close the candidate gets.** The reference's proven upper bound is the yardstick:

| n | Certified hosts | Candidate below the bound | HiGHS at 32 s below the bound |
|---|---|---|---|
| 40 | 9 of 10 | at most 1 | at most 1 |
| 50 | 9 of 10 | at most 2 | at most 2 |
| 60 | 5 of 10 (120 s) | at most 1 on 9 of 10 hosts, 4 on one | 18.7 on average, up to 69 |

**The two runs agree on the candidate.** It is CPU-budgeted, and it scored the same in run 1 and the re-run on 29
of 30 hosts. Contention had exaggerated run 1's n60 contrast at 32 s (+39), but not its direction.

## Reading

**The crossover moves out with host size.** At 40 vertices an exact MILP catches the 0.5 s candidate at 16× its
budget. At 50 it needs 64×. At 60 it is still 17.6 edges behind at 64×, while the candidate stays within about one
edge of a proven upper bound. The builder's stated expectation (ADVANTAGE_GROWS) held. The mechanism is visible in
HiGHS's CPU use: at n60 it ran to its limit on every host at every budget.

**What it would take to claim this.** The hosts are outside E1d's calibrated settings, outside the registered
family space, and above the custody path's 200-edge certificate bound. Claiming the larger-host advantage would
need three things from a reviewer:
- a family-space extension;
- the bound lifted for the exact LP-dual route, whose check does not depend on size (statistician's brief,
  finding 5);
- a reference that certifies at n60. It certified 5 of 10 in 120 s; the other 5 were within 1 of their bounds.

Until then this is a DEV pointer: the robust form of E1d's claim lies on larger dense hosts.

## Tests

`tests_genesis/test_e1d_scaling.py`.
- **Design (5).**
- **Record (3):**
  - the verdict recomputes from the rows;
  - the validity criterion holds for the re-run and fails for run 1;
  - the hosts are the same in both runs and are in the e1/e1b exposure addenda.
