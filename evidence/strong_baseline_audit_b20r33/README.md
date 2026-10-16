# B20_R33 evidence: strong-baseline audit of E1 and E1b with an exact MIP arm (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no package
or comparator.
- **Script:** `scripts/b20r33_strong_baseline_audit.py`. It was committed before running in
  `b03e429`, and its SHA-256 was sent to the user beforehand.
- **Log:** `run.log`, 1,154 s, the whole study pinned to one core.

## Why

GV3 needs a discovery to help "beyond strong baselines". E1 and E1b compare their frozen
candidates only with time-matched fixed DSL programs. Then B20_R32's post-hoc cross-check found
that HiGHS's exact MILP proves the optimum of the hardest `e1b` hosts in under a second
(B20R32-OPEN-2).

## Design (fixed before running)

**Hosts.** 60 fresh DEV hosts, 20 per `e1b`/`e1-v2` setting, seed 20263301. They exclude 1,928
exposure identities.

**Arms.**
- The frozen packages' own descriptors, unchanged, in runc:
  - E1: the candidate (represent-and-repair `cross_2`) and its three baselines, 0.5 CPU s each;
  - E1b: the candidate (construct-pipeline `lp_greedy`) and its three baselines, 2.0 CPU s each.
- An exact MIP arm at each budget: `scipy.optimize.milp` (HiGHS, scipy pinned) with
  `time_limit` = budget, on the same core. Its CPU is measured with threads included, and a run
  over 1.25× scores 0.

**Reference.** The evaluator's joint LP/SAT certification at 600 s. All 60 hosts were certified:
56 by the LP dual and 4 by SAT/DRAT.

**Verdict.** Per study, from D = MIP − candidate, stratified bootstrap with 90% interval:
- MIP_DOMINATES if the mean D ≥ 0.5 and the interval is above 0;
- MIP_WORSE if the mean D ≤ −0.5 and the interval is below 0;
- otherwise NO_MATERIAL_DIFFERENCE.

## Result (`summary.json`, `rows.jsonl`, `hosts.json`)

**The MIP arm.** It **proved optimality on all 60 hosts** at both budgets, using a median of
0.02 CPU s and at most 0.36 CPU s. No run overran its budget and no run failed. It is at the
certified optimum on 60/60 hosts.

| | E1 (0.5 s) | E1b (2.0 s) |
|---|---|---|
| Candidate at the certified optimum | 27/60 | 49/60 |
| Best of the three baselines at the optimum | 6/60 | 6/60 |
| **MIP − candidate** | **+0.75 [+0.58, +0.92]**, W/T/L 33/27/0 | **+0.20 [+0.12, +0.30]**, W/T/L 11/49/0 |
| Candidate − best baseline | +2.08 [+1.70, +2.45] | +2.27 [+2.02, +2.52] |
| MIP − best baseline | +2.83 [+2.53, +3.13] | +2.47 [+2.20, +2.73] |
| **Verdict** | **MIP_DOMINATES** | **NO_MATERIAL_DIFFERENCE** |

**Candidate distance to the optimum:**

| Distance | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| E1 (hosts) | 27 | 23 | 8 | 2 |
| E1b (hosts) | 49 | 10 | 1 | — |

**By setting, MIP − candidate:**

| Setting | E1 | E1b |
|---|---|---|
| planted_cluster | +0.60 | +0.10 |
| erdos n26 | +0.55 | +0.25 |
| erdos n30 | +1.10 | +0.25 |

## What it means

1. **The candidates' gains over their comparator are real, against those baselines.** Both
   candidates beat the time-matched DSL baselines by about 2 edges per host. That replicates
   B20_R24.
2. **On this family, an off-the-shelf exact solver is a much stronger baseline.** It is always
   optimal, with proof, in under 0.4 CPU s.
   - E1's candidate is dominated: 0.75 edges per host below it, and never above it.
   - E1b's candidate is within 0.2 edges, below the 0.5 minimum useful effect. It is never above
     the MIP either, and cannot be, since the MIP is always optimal.
3. **For GV3, "beyond strong baselines" cannot be met on this family by either candidate.** The
   best possible outcome against a MIP comparator is a tie. A SUPPORTED E1 or E1b result would
   support a better-solver statement against time-matched DSL baselines only. The packages
   already scope it that way. A reviewer should decide whether that scope is worth running.
   - **Alternative 1: add a MIP comparator.** E1 would then fail. E1b could at best tie.
   - **Alternative 2: move to families where an exact solver does not finish within the
     budget, but the evaluator can still certify.** On triangle-free hosts the SAT encoding is
     bounded at 200 edges (`CERTIFICATE_MAX_EDGES`). It is an open question whether such
     settings exist inside that bound.

The 60 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r33.json`).
