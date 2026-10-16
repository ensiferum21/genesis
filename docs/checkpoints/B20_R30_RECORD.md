# B20_R30 record: certification at the calibration's 60 s and the evaluator's 600 s (B20R24-OPEN-2)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No limit was changed.
- **Commits:**
  - `ece1999`: setup. The script was committed before the run, and its SHA-256 was sent to the
    user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/certification_budget_b20r30/`. Its README has the full table.

## Why

This is NEXT_ACTIONS decision item 2. `e1-hard-v2` admits a setting when at least 90% of its
calibration hosts are certified within 60 s. The analysis plan tolerates at most 5% unsupported
CONFIRM tasks under the evaluator's reference at 600 s. B20_R24 left the alignment of the two
limits to a reviewer. This step measures both limits on the same 90 fresh hosts from the decided
`e1b` family, 30 per setting.

## Result

**Pooled:**

| Measure | Result |
|---|---|
| Certified at 60 s (calibration) | 86/90 (95.6%) |
| Certified at 600 s (evaluator) | 90/90 |
| Unsupported at 600 s | 0, one-sided 95% upper bound 3.27% |
| Value disagreements | none |
| Verdict | **LIMITS_CONSISTENT** |

**By setting:**

| Setting | At 60 s | At 600 s |
|---|---|---|
| planted_cluster | 28/30 | 30/30 |
| erdos n26 | 30/30 | 30/30 |
| erdos n30 | 28/30 | 30/30 |

**Further observations:**
- **Hosts certified only at 600 s.** The four that the calibration missed took the evaluator
  118–338 s, all by SAT with a DRAT proof.
- **Methods.** Of the 90 hosts, 72 were certified by the LP dual and 18 needed SAT.
- **The 60 s limit is soft in the calibration's implementation.** On one host the calibration's
  certify call overran to 104.8 s and certified; the calibration counts that host as certified.
  Counted strictly, the pooled figure is 85/90 (94.4%), still above the calibration's 90%.

## What it settles, and what it does not

On the decided `e1b` family the two limits agree. A CONFIRM panel from these settings should
meet the plan's unsupported limit.

The limits are still different quantities. The reviewer's choice in B20R24-OPEN-2 stays open,
with this evidence attached. The choices are:
- keep both;
- align the calibration with the evaluator's budget;
- fix a CONFIRM-side certification budget in the plan.

The 90 hosts are exposed. They are listed in the handoff exposure addenda written in B20_R31.

## Open

B20R24-OPEN-2 stays open as a reviewer decision, now with data. The calibration's soft 60 s
limit is a further point for the same reviewer. B20_R30 found nothing new to repair.
