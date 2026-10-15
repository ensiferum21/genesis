# B20_R28 record: E1b causal re-pilot on the e1b family; exposure addenda for the E1/E1b packages

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim.
- **Commits:** `df20d32` (setup: script, committed before the run; SHA-256 sent to the user
  beforehand) and the result commit that follows it.
- **Evidence:** `evidence/e1b_causal_repilot_b20r28/` (see its README).

## Why

This is NEXT_ACTIONS item 2. B20_R23 piloted E1b's registered causal follow-ups (ablation
`random_greedy`, placebo `lp_shuffled_greedy`) on builder-chosen settings. B20_R24 then moved E1b
to the `e1b` family under `e1-hard-v2`. The handoff README said the follow-ups had to be
re-piloted there before any ablation or placebo request.

## Result

**Hosts and runs.** 30 fresh hosts from the `e1b` calibration. All arms ran in the runc sandbox,
with 0 failed runs. 28 hosts were certified (gate passed).

| Contrast | Mean per host | W / T / L | CPU ratio | Verdict |
|---|---|---|---|---|
| candidate − ablation | +1.25 | 24 / 3 / 1 | 1.03 | READY_FOR_REVIEW (power: 10 per stratum) |
| candidate − placebo | +2.61 | 27 / 1 / 0 | 1.00 | READY_FOR_REVIEW (power: 10 per stratum) |

The placebo is 1.36 per host below the ablation. On DEV, the LP signal is E1b's active
ingredient. This replicates the B20_R23 pilot on the decided family.

## Exposure addenda

B20_R26–R28 named 126 new DEV hosts, all triangle-free. Some are in the e1-v2 setting
(erdos n30 p0.3), and all of B20_R28's are in the e1b settings. The E1 v3 and E1b v2 packages are
frozen DRAFTs, so their files were not edited.

`scripts/b20r28_exposure_addendum.py` writes `handoff/e1/exposure_hosts_addendum_b20r28.json` and
`handoff/e1b/exposure_hosts_addendum_b20r28.json`: every host named under evidence/ and handoff/
that the package's `exposure_hosts_all.json` lacks. Both READMEs now tell a custodian to list both
files. The E1b README also records this re-pilot.

## Open

The E1b causal follow-ups are ready for review on the decided family. They need what E1b needs:
- reviewer sign-off;
- a statistician (B19-OPEN-4);
- an independent custodian.

After that, signed ablation and placebo evaluations follow, once E1b is SUPPORTED.
