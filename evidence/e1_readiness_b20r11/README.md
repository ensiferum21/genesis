# B20_R11: E1 readiness through the custodian's own runner (GV3 path)

- **Script:** `scripts/b20r11_e1_readiness.py`, committed as `96fdf26` before running.
- **Status:** DEV material, run by the builder. No sealed task. No claim.
- **Package:** `handoff/e1/`.

## Part A: DEV pilot under the custodian runner

**Setup.** 30 fresh DEV hosts from the adopted triangle-free calibration (seed 20261113), excluding the B19 pilot hosts. Each arm ran through `candidates.run(isolation='runc')`: the same OCI sandbox, one resource profile (2 CPU s, 1000 queries, 2048 MiB) and cgroup CPU for every arm.

| | Candidate (cross_2) | low_cycle | multistart | exchange |
|---|---|---|---|---|
| Total edges | 1,769 | 1,729 | 1,663 | 1,580 |
| Optimum reached (of 30) | 20 | 3 | – | – |
| CPU (s, total) | 21.35 | 6.31 | 6.57 | 6.26 |

**Against the strongest baseline (low_cycle).**
- Mean difference: **+1.333 edges per task**.
- Wins / ties / losses: 24 / 5 / 1.
- B19 measured +1.27 under different metering, so the effect replicates on the custodian's path.

**Under the B19 DRAFT plan (dry run).**
- Estimate: 1.33, interval [1.0, 1.7], p = 5e-5.
- The cost check fails: the CPU ratio is **3.38**, above the plan's `max_ratio` of 3.0. Decision: **NOT_SUPPORTED**.
- Verdict under the rule fixed in the script: **COST_RULE_FAILS**.

## Part B: package and same-operator rehearsal

**Package.**
- A real triangle-free campaign was frozen (15 s), with the candidate descriptor frozen in it.
- The campaign's own strongest conventional baseline, measured on its tiny DEV panels, is `multistart`.
- The v4 request was built with a builder-frozen copy of the DRAFT. That copy is labelled REHEARSAL; it is not a reviewed decision.

**Rehearsal** (fixture keys, builder as custodian, 25 fresh CONFIRM-split hosts, which are listed in the package so a real custodian excludes them):
- register → evaluate → signed v4 receipt → registration log → judge recomputation;
- outcome NOT_SUPPORTED: wins / losses / ties 24 / 0 / 1, estimate +3.04 per task against multistart, cost ratio 3.43 > 3.0;
- the judge agrees and re-checked all 50 witnesses; arm fairness had no problems.

This shows the package executes end to end. It is not independent, not a CONFIRM result, and licenses nothing.

## Findings for review

1. **The E1 effect holds under equal sandbox metering.** On 30 fresh DEV hosts the candidate beats low_cycle by +1.33 per task, and it reaches the certified optimum on 20 of 30 hosts against 3 for low_cycle.
2. **The preregistered cost rule fails (B20R11-OPEN-1).** Every arm pays about 0.21 s of interpreter start-up in the sandbox; the candidate adds its 0.5 s search, and the DSL baselines finish almost immediately. With `max_ratio = 3.0` the DRAFT design cannot return SUPPORTED. A reviewer must fix the design before any sealed panel exists, for example with time-matched baselines. Raising the threshold after seeing this result would be relaxing a criterion to obtain a label.
3. **The comparator rules disagree (B20R11-OPEN-2).** The DRAFT names the strongest baseline on a custodian SELECT panel. The custodian's v4 check requires the campaign's own strongest baseline, and the campaign's tiny panel picked multistart where the pilot picks low_cycle.

## Files

- `pilot_rows.json`, `pilot_summary.json`: Part A.
- `rehearsal_summary.json`, `rehearsal_receipt.json`, `rehearsal_registration_log.json`: Part B. The receipt and log are signed by fixture keys.
- `readiness.json`: both parts, with the code identity.
- `run.log`: the run log.
