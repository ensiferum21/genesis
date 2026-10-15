# B20_R28 evidence: E1b causal re-pilot on the e1b family (DEV)

Builder-run. Nothing here is independently reviewed, and it licenses no claim.
- **Script:** `scripts/b20r28_e1b_causal_repilot.py`, committed before running in `df20d32`; its
  SHA-256 was sent to the user beforehand.
- **Log:** `run.log`, 741 s.

## Design (fixed before running)

**Hosts.** 30 fresh DEV hosts, drawn round-robin from the adopted `e1b` calibration's three
selected settings (rule `e1-hard-v2`), seed 20262951. They exclude 1,640 exposure identities:
every graph host named under evidence/ and handoff/ (B20_R26/R27 included), the regenerated E1
hosts, and the calibration hosts.

**Arms.** All ran through `candidates.run(isolation='runc')` with the E1b profile:
- candidate: construct-pipeline-v1 `lp_greedy`, 2.0 CPU s;
- the registered ablation: `random_greedy`;
- the registered placebo: `lp_shuffled_greedy`.

Both interventions were checked with `intervention_problems` before any run. There were 0 failed
runs.

**Reference.** The joint LP/SAT `obstruction.certify`, 120 s per host. Certified: 10/10, 8/10 and
10/10 by stratum, which passes the 75% gate.

**Analysis.** The B19 DRAFT plan core, with a dry run, and the centred power model (`sims` 1000).

## Result (`summary.json`, `pilot_rows_*.json`, `power_analysis_centred_*.json`)

| Contrast | Mean per host | By stratum | W / T / L | CPU ratio | Dry run | Power (chosen) | Verdict |
|---|---|---|---|---|---|---|---|
| candidate − ablation | **+1.25** | +1.00 / +1.38 / +1.40 | 24 / 3 / 1 | 1.03 | SUPPORTED, 1.26 [1.02, 1.48] | 10 per stratum, 30 total | **READY_FOR_REVIEW** |
| candidate − placebo | **+2.61** | +2.50 / +2.13 / +3.10 | 27 / 1 / 0 | 1.00 | SUPPORTED, 2.58 [2.23, 2.95] | 10 per stratum, 30 total | **READY_FOR_REVIEW** |

**The placebo is worse than the ablation**, by 1.36 per host. Permuted LP values mislead the
greedy order more than a random order does.

**Optimum hits** (28 scored hosts):
- candidate: 18;
- ablation: 1;
- placebo: 1.

## What it means

On the `e1b` family, the E1b candidate's advantage depends on the LP signal. Removing the
signal (ablation) or scrambling it (placebo) takes away 1.25–2.61 edges per host, at the same
cost. This replicates, on the decided family, the B20_R23 pilot on builder-chosen settings
(ablation +1.42, placebo +2.53).

A causal level (ABLATION_SUPPORTED, PLACEBO_CONTROLLED) still needs signed ablation and placebo
evaluations by a custodian, after the E1b claim itself is SUPPORTED. The descriptors are in
`handoff/e1b/interventions.json`.

The 30 hosts are in `hosts.json`, and they are listed in the handoff exposure addenda
(`handoff/e1*/exposure_hosts_addendum_b20r28.json`).
