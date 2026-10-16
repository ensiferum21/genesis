# B20_R32 evidence: certification with generated rows, prospective on fresh hosts (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no
evaluator.
- **Script:** `scripts/b20r32_generated_certification.py`. It was committed before running in
  `d695705`, and its SHA-256 was sent to the user beforehand.
- **Components:**
  - `src/genesis/verification/lp_dual_rows.py`: an exact checker and a registry built only
    from CHECKED pattern statements;
  - `src/genesis/discovery/generated_certify.py`: the route.
- **Log:** `run.log`, 374 s.

## Design (fixed before running)

**Hosts.** 90 fresh DEV hosts, 30 per `e1b` setting, seed 20263201. They exclude 1,838 exposure
identities, including B20_R30, B20_R31 and B20_R31's development-look hosts.

**Seed witness.** Both routes start from the evaluator's own seed witness: the better of the
8-round DSL and 1 CPU s of LP greedy.

**The two routes.**
- **a**: the evaluator's joint certification, `obstruction.certify`, at 600 s.
- **b**: the same procedure, with every copy of B20_R31's Lean-checked K5 and W5 bounds added as
  LP rows. The exact checker checks b's certificate before b uses it.

The two run back to back, in alternating order.

**Verdict.** CERTIFICATION_UTILITY iff all of the following hold. Otherwise
NO_CERTIFICATION_UTILITY.
- b is sound;
- b certifies at least as many hosts as a;
- McNemar p < 0.05 on hosts whose upper bound is an exact LP dual (no UNSAT proof);
- the 90% interval of the per-host wall saving (a − b) lies above 0.

## Result (`summary.json`, `rows.jsonl`, `hosts.json`, `certificates/`)

| | a (evaluator) | b (generated rows) |
|---|---|---|
| Certified at 600 s | 90/90 | 90/90 |
| Upper bound from an exact LP dual | 87 | 89 |
| Hosts needing an UNSAT proof | 3 | 1 |
| Total wall time | 191.9 s | 86.9 s |
| Median wall time per host | 0.011 s | 0.077 s |

| Check | Result |
|---|---|
| Sound | yes: every b certificate VALID, no value disagreements |
| Coverage | equal |
| McNemar | 2 discordant hosts (b LP-certifies, a does not) against 0, one-sided p = 0.25: **fails** |
| Wall saving a − b | mean +1.17 s per host, 90% interval [−0.10, +3.22]: **fails** |

By setting, the mean saving was:
- erdos n26: +3.77 s;
- erdos n30: −0.00 s;
- planted_cluster: −0.26 s (median 2,161 rows to separate).

**Verdict: NO_CERTIFICATION_UTILITY.**

**The three hosts that needed SAT under a** (all erdos n26):

| Host | a | b |
|---|---|---|
| `…-0005` | SAT/DRAT, 20.8 s | LP, 0.08 s |
| `…-0008` | SAT/DRAT, 93.1 s | LP, 0.05 s |
| `…-0007` | SAT/DRAT, 38.7 s | SAT/DRAT, 37.8 s (the rows did not close the gap) |

The two LP certificates b produced there are kept in `certificates/`. `tests_genesis` re-checks
them.

**Cost of b.** On the 87 hosts both routes certify by LP, b costs 0.11 s more per host on
average (at most 0.95 s): the price of enumerating copies.

## Why the effect did not reach significance

The rows work where they are needed: 2 of 3 SAT hosts here, and 10 of 18 in B20_R30's
diagnostic. But this fresh sample had only 3 hosts whose triangle-LP floor exceeds the optimum,
against 18 in B20_R30's. By setting:

| Setting | B20_R30 | B20_R32 |
|---|---|---|
| planted_cluster | 10/30 | 0/30 |
| erdos n26 | 4/30 | 3/30 |
| erdos n30 | 4/30 | 0/30 |

B20_R31's 48 EVAL hosts are in between: at most 4 hosts have a floor above the best value found.
The difference between B20_R30 and B20_R32 on planted_cluster is large: Fisher one-sided
p ≈ 0.0004. The edge and triangle counts, and the within- and between-cluster edges, are close.
No mechanism was found.

## Post-hoc cross-check (`post_hoc_milp_crosscheck.json`; not preregistered)

**Why.** A defect in the evaluator's SAT route could certify too low an optimum, and that would
show up as spurious LP gaps. So, after the run, every SAT/DRAT-certified optimum was re-solved:
B20_R30's 18 hosts and B20_R32's 3. The solver was the exact integer program in HiGHS
(`scipy.optimize.milp`, scipy pinned), with the domain checker on its solution
(`scripts/b20r32_milp_crosscheck.py`, committed before it ran).

**Result.** All 21 agree, with no refutation. HiGHS reported optimality on each within 0.72 s
wall. The evaluator had needed up to 338 s for some of them.

**What it shows.** The evaluator's optima stand. The sample difference is not an evaluator defect.

**A further observation, for the reviewer of E1 and E1b.** An off-the-shelf exact MIP solver
finds the optimum of these `e1b` hosts in well under a second. E1 and E1b compare their
candidates with time-matched fixed DSL programs, not with such a solver. Whether "beyond strong
baselines" (GV3) is met therefore needs a measurement. A MIP arm at the candidate's budget is
B20_R33. HiGHS's optimality claims carry no proof object. As a certifier it would need a
checkable certificate, and DRAT or an exact LP dual is what the evaluator already uses.

The 90 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r32.json`).
