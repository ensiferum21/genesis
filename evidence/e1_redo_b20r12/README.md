# B20_R12 (redo on the canonical line): E1 under the decided design — UNDERPOWERED

- **Script:** `scripts/b20r12_e1_redo.py`, committed as `02de690` before it ran. Its rules and verdicts are in the docstring.
- **Calibration:** the E1 study calibration `c7893f5b…92c6` (rule `e1-hard-v1`), in `evidence/dev_calibration_e1_b20r12/`.
- **Run:** 13 Oct 2026, 263 s, with nothing else running.
- **Status:** builder-run DEV pilot plus a same-operator rehearsal with fixture keys. It licenses nothing.

## Pilot (30 fresh DEV hosts, seed 20261921)

Excluded from the draw: 711 host identities. They are every earlier E1 host, every triangle-free host in the B20_R13–RX5 evidence, and the calibration's own hosts.

The arms all ran through `candidates.run(isolation='runc')` under one profile (2 CPU s, 1000 queries, 2048 MiB, 10 s wall). Every host had a certified optimum (0 unsupported).

| Arm | Total edges (30 hosts) | Hosts at the optimum |
|---|---|---|
| candidate (cross_2, 0.5 s) | 1738 | 20 |
| multistart_tm | 1709 | 7 |
| low_cycle_tm | 1694 | 6 |
| exchange_tm | 1686 | 2 |
| low_cycle (plain, diagnostic) | 1682 | 3 |
| multistart (plain) | 1613 | 0 |
| exchange (plain) | 1522 | 0 |

Against `multistart_tm`, the pilot comparator:
- mean difference +0.967 per host; wins / ties / losses 19 / 9 / 2;
- CPU ratio 0.997.

By stratum:

| Stratum | Mean difference | Hosts | Candidate below the optimum | Hosts with centred headroom |
|---|---|---|---|---|
| erdos n18 p0.5 (`a1b8a28d`) | +2.00 | 8 | 0 of 8 | 8 of 8 |
| erdos n26 p0.3 (`4b389647`) | +0.86 | 7 | 4 of 7 | 4 of 7 |
| erdos n22 p0.35 (`80a647eb`) | +0.57 | 7 | 5 of 7 | 5 of 7 |
| planted_cluster n20 (`91e61c9b`) | +0.38 | 8 | 1 of 8 | 1 of 8 |

Centred headroom is the optimum minus (candidate − the stratum's mean difference), which is the headroom of the centred candidate the power simulation perturbs (`power._pilot`). On n18 p0.5 the candidate is already optimal on every host, but its centred copy is not.

- **DRAFT plan dry run (DEV):** SUPPORTED. Estimate 0.95, interval [0.69, 1.21].
- **Centred power model:** INFEASIBLE. A design effect of 1.0 per host cannot be carried by two strata, so no panel size reaches 0.8:
  - planted_cluster: 1 of 8 hosts has centred headroom, of 1 edge;
  - erdos n22 p0.35: 5 of 7 hosts have 1 edge each, so at most 0.71 per host.

**Verdict: UNDERPOWERED** (mean ≥ MUE, cost ratio within bound, no size chosen).

## Rehearsal

- The custodian SELECT comparator ran on 30 private hosts, drawn from the E1 study calibration and screened against the 711 named hosts. Totals: exchange_tm 1538, low_cycle_tm 1535, multistart_tm 1582. Selected: `multistart_tm`.
- The amended DRAFT fails the decision-record check: "the power analysis found no sample size reaching the power target". So register, evaluate and judge were not run, as the script's rule says.

## Files

| File | What |
|---|---|
| `pilot_rows.json` | The scored rows (DEV) |
| `pilot_summary.json` | Totals, strata, cost, dry run and verdict |
| `power_analysis_centred.json` | The full power table |
| `rehearsal_summary.json` | The signed SELECT payload and the stopping reason |
| `readiness.json` | The summary and the code identity |
| `run.log` | The console log, with a networkx deprecation warning removed |

The package is in `handoff/e1/` (v2), and its README sets out the decisions a reviewer could make.
