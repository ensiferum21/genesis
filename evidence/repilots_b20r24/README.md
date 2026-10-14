# E1 and E1b re-pilots on the e1-hard-v2 family, and the first rehearsals (B20_R24, DEV)

**Script.** `scripts/b20r24_repilots.py`, committed as `bf7c4c8` before the calibration produced any result. Its SHA-256 (`6f0de220…f343`) was sent to the user in the conversation before the run.

**Family.** Study calibration `e1-v2` / `e1b` (rule `e1-hard-v2`, `evidence/dev_calibration_e1_hard_v2_b20r24/`). It selected three triangle-free settings:
- planted_cluster n30 p_in 0.6 p_out 0.2;
- erdos n26 p0.35;
- erdos n30 p0.3.

No C4 setting was selected, so E1b on C4 is **NOT_RUN**.

**Pilots.** 30 fresh DEV hosts per study, 10 per setting. They are screened against 1,244 exposure identities: every host named in the evidence, the E1 hosts, and both calibrations' hosts.
- Every arm ran through `candidates.run(isolation='runc')`.
- The reference was `obstruction.certify`, 120 s per host.
- The analysis was the B19 DRAFT plan, as a dry run.
- Power used the centred model with at least 10 per stratum.

## Pilot results

| | E1: represent-and-repair `cross_2`, 0.5 s, vs time-matched 0.5 s | E1b: `construct-pipeline-v1` `lp_greedy`, 2.0 s, vs time-matched 2.0 s |
|---|---|---|
| Certified hosts | 30 / 30 | 30 / 30 |
| Comparator (strongest by total) | `low_cycle_tm` | `multistart_tm` |
| Mean difference per host | **+2.57** (planted +4.0, n26 p0.35 +2.3, n30 p0.3 +1.4) | **+2.63** (planted +2.6, n26 p0.35 +2.3, n30 p0.3 +3.0) |
| Wins / ties / losses | 26 / 3 / 1 | 29 / 1 / 0 |
| CPU ratio, candidate / comparator | 1.00 | 1.02 |
| Candidate at the certified optimum | 12 / 30 (comparator 1) | 25 / 30 (comparator 0) |
| DRAFT plan dry run | SUPPORTED, estimate 2.57 [2.10, 3.03] | SUPPORTED, estimate 2.63 [2.27, 3.00] |
| Centred power | CHOSEN: 10 per stratum, 30 in total (power 0.88) | CHOSEN: 10 per stratum, 30 in total (power 0.97) |
| False-positive rate at zero effect | 0.006 | 0.018 |
| **Verdict** | **READY_FOR_REVIEW** | **READY_FOR_REVIEW** |

Diagnostic for E1b: the candidate minus `cross_2` at 2.0 s is +0.47 per host (15 / 11 / 4).

**E1 is now powerable.** Under `e1-hard-v1` it was UNDERPOWERED (B20R12-OPEN-1), because the selected settings left the time-matched baselines within an edge of the optimum. The `e1-hard-v2` headroom bound removes that problem by design, without reading the candidate.

## First rehearsals: INVALID (kept)

As preregistered, each READY study went through a same-operator rehearsal with fixture keys:
1. a frozen DEV campaign;
2. the custodian's SELECT step on 30 private hosts from the study calibration;
3. the selection recorded;
4. a builder-frozen REHEARSAL copy of the DRAFT;
5. the v4 request for the power-chosen 30 hosts;
6. register, evaluate and judge.

| | E1 | E1b |
|---|---|---|
| SELECT totals → comparator | exchange 2585, low_cycle 2670, multistart 2624 → `low_cycle_tm` | exchange 2616, low_cycle 2650, multistart 2664 → `multistart_tm` |
| Evaluation | **INVALID**: 4 of 30 tasks unsupported (W/L/T on the rest 22/0/4) | **INVALID**: 2 of 30 unsupported (26/0/2) |
| Judge | agrees (INVALID; 52 witnesses re-checked) | agrees (INVALID; 56 re-checked) |

The SELECT step chose the same comparator as the pilot in both studies.

The plan allows at most 5% unsupported tasks, so INVALID is the plan working as preregistered. **Why the hosts were unsupported** (`diagnosis_unsupported.log`, `scripts/b20r24_diagnose_unsupported.py`):
- The custodian's reference was the graph adapter's SAT-only path. It stopped at the first SAT call that returned UNKNOWN within its 60 s per-call limit, after 62–70 s on each host, although its message said "within 600s". Its upper bound never left the host edge count.
- The joint certification that the calibration and the pilots used (`obstruction.certify`: exact LP dual, then SAT/DRAT) closes 5 of the 6 hosts within 120 s:
  - 3 by the exact LP dual, in 4–10 s;
  - 2 by SAT/DRAT, in 158–233 s, with the last call overrunning while drat-trim checked.
- It leaves one host at bounds 100..101.

This is an evaluator defect (**B20R24-OPEN-1**, repaired in this batch). It is not a reason to change the plan. The repair: v4 evaluations now use the joint reference (`domains.GraphHostAdapter.reference(joint=True)`, `custodian.reference_options`), and keep the certificate bundle v2 in the evaluation evidence. The rehearsals are then repeated on new hosts as a separate preregistered step: `scripts/b20r24_rehearsal_rerun.py`, `evidence/rehearsal_rerun_b20r24/`.

A design point for the reviewer remains. The calibration admits settings where up to 10% of hosts fail certification within 60 s. The plan tolerates 5% unsupported tasks at the evaluator's 600 s. These two limits are consistent only if the longer budget certifies the rest. Neither limit is changed here.

## Files

- `rows.jsonl`: per host, each arm's value, status, cgroup CPU and meter, and the certification.
- `pilot_hosts.json`
- `pilot_rows_<study>.json`, `power_analysis_centred_<study>.json`
- `decision_record_DRAFT_<study>.json`: the DRAFTs naming the `e1-hard-v2` study calibrations.
- `campaign_export_<study>.zip`: the frozen rehearsal campaigns.
- `rehearsal_<study>.json`, `rehearsal_receipt_<study>.json`: payload, judge, resource account, and the SELECT and CONFIRM hosts.
- `diagnosis_unsupported.log`
- `summary.json`, `console.log`, `run.log`

Keys and custodian stores were deleted after the rehearsals. Nothing here licenses a claim.
