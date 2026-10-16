# B20_R30 evidence: certification at the calibration's budget and the evaluator's (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no limit.
- **Script:** `scripts/b20r30_certification_budget.py`. It was committed before running in
  `ece1999`, and its SHA-256 was sent to the user beforehand.
- **Log:** `run.log`, 2,616 s.

## Why

B20R24-OPEN-2 is a design point for a reviewer. Two limits bear on it:

| Limit | Source | Budget | Threshold |
|---|---|---|---|
| Calibration | `e1-hard-v2` admits a setting | 60 s, `obstruction.certify` seeded with the best time-matched baseline | at least 90% of its calibration hosts certified |
| Evaluator | the analysis plan | 600 s, the evaluator's reference `GraphHostAdapter.reference(joint=True)` | at most 5% unsupported CONFIRM tasks |

The calibration measured 8 hosts per setting. This step measures both limits on the same 90 fresh
hosts.

## Design (fixed before running)

**Hosts.** 90 fresh DEV hosts, drawn round-robin from the adopted `e1b` calibration's three
selected settings, seed 20263001. They exclude 1,670 exposure identities:
- every graph host named under evidence/ and handoff/;
- the regenerated E1 hosts;
- the calibration hosts.

**Per host:**
- the calibration's own measurement (`calibration.measure_time_matched` under `e1-hard-v2`);
- the evaluator's reference at 600 s, with its wall time recorded.

Where both certify, their values must agree.

**Verdict rule.** u is the pooled evaluator unsupported rate, and U is the one-sided 95%
Clopper–Pearson upper bound of u.

| Verdict | Condition |
|---|---|
| LIMITS_CONSISTENT | U ≤ 0.05 |
| LIMITS_INCONCLUSIVE | u ≤ 0.05 but U > 0.05 |
| LIMITS_INCONSISTENT | u > 0.05 |

## Result (`summary.json`, `rows.jsonl`, `hosts.json`)

| Setting | Certified at 60 s (calibration) | Certified at 600 s (evaluator) | Only at 600 s | Evaluator wall: median / p90 / max |
|---|---|---|---|---|
| planted_cluster n30 p_in 0.6 p_out 0.2 | 28/30 | 30/30 | 2 | 1.4 / 23.7 / 334.2 s |
| erdos n26 p0.35 | 30/30 | 30/30 | 0 | 1.0 / 6.5 / 27.5 s |
| erdos n30 p0.3 | 28/30 | 30/30 | 2 | 1.0 / 22.0 / 338.3 s |
| **pooled** | **86/90 (95.6%)** | **90/90** | 4 | 1.0 / 11.4 / 338.3 s |

- **Verdict: LIMITS_CONSISTENT.** No host is unsupported at 600 s (u = 0), and U = 0.0327.
- **No value disagreements.** Where both certify, the calibration and the evaluator agree on
  every host.
- **How the evaluator certified:**
  - LP dual (`JOINT_LP_DUAL_EXACT`): 72 hosts;
  - SAT with a DRAT proof (`JOINT_SAT_DRAT`): 18 hosts (10, 4 and 4 by setting).
- **The four hosts certified only at 600 s** stopped at 59–60 s in the calibration. The
  evaluator took 118–338 s on them, all by SAT/DRAT. A fifth host took more than 60 s at the
  evaluator (103.0 s); it is the one below.
- **The 60 s limit is soft in the calibration.** On one host (`…20263001-0004`) the calibration's
  certify ran for 104.8 s and certified, and the calibration counts that as certified, as it
  would in calibration. Counted strictly within 60 s, the pooled fraction is 85/90 (94.4%), still
  above 90%.

## What it means

On the decided `e1b` family the two limits agree. Every setting passes the calibration's 90%
limit at 60 s, and the evaluator at 600 s leaves nothing unsupported. Even the strict 95% upper
bound is under the plan's 5%. A real CONFIRM panel drawn from these settings should therefore
meet the plan's unsupported limit, on this evidence.

The limits remain different quantities, and nothing guarantees that agreement on another
family. That is still the reviewer's decision (B20R24-OPEN-2). Possible options:
- keep both;
- measure the calibration at the evaluator's budget;
- fix a CONFIRM-side certification budget in the plan.

This step gives the reviewer the data. It does not choose among the options.

The 90 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r31.json`, written in B20_R31).
