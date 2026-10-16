# B20_R43 evidence: the E1d DRAFT package, and a same-operator rehearsal through the v5 path (DEV)

Builder-run, with fixture keys. Nothing here is independently reviewed, and nothing licenses a claim. The
DRAFT rule `e1-hard-v3-draft` was adopted **only in a throwaway copy** of the code, for the rehearsal.
The repository's `configs/dev_calibration.json` is unchanged.
- **Script:** `scripts/b20r43_e1d_package.py`. It was committed before the run in `ab11467`, and its
  SHA-256 (`c11e8692…2272`) was sent to the user beforehand.
- **Log:** `run.log`. 5,524 s in one go, pinned to one core.
- **Development look:** a smoke run of the rehearsal path. Its 9 hosts and its finding are disclosed
  in `development_look_hosts.json`. The finding: a single exposure file of every named host exceeded
  the screener's node limit. It was fixed before the run.

## What was done (fixed before running)

1. **Calibration record.** `calibration_triangle_free_host_v1_e1_hard_v3_draft.json`, SHA-256
   `a4673c74…1154`.
   - It holds B20_R41's Part A rows, copied rather than re-measured, as a
     `genesis-dev-calibration-v1` record under the registered DRAFT rule.
   - `record_problems` is [], and it selects what B20_R41 selected.
   - B20_R41's evidence is unchanged.
2. **Rehearsal** in `git archive` of the setup commit (code identity `b246226f…`, equal to the
   repository's):
   - a fresh frozen campaign with E1's frozen candidate;
   - the custodian's SELECT on 30 private hosts among five baselines;
   - the DRAFT decision record and a REHEARSAL-labelled frozen copy;
   - a **v5** request for 240 hosts (B20_R41's power choice), with the reference route
     `generated-rows-v1`;
   - a CONFIRM pool drawn from the calibration, excluding every named host and the SELECT hosts;
   - register, evaluate, verify, the log check, and `judge.recompute`.
3. **Package** written to `handoff/e1d/`.

## Result (`rehearsal_summary.json`, `rehearsal_receipt.json`, `decision_record_DRAFT.json`, `summary.json`)

| Step | Result |
|---|---|
| SELECT (30 private hosts) | comparator **`milp_highs_4x`**: HiGHS at 2.0 s, four times the candidate's budget. Totals: 3,123, against 3,053 for the best DSL program. |
| Reservation and screening | 240 CONFIRM hosts, none overlapping the exposure registry |
| Reference | 237 of 240 certified by the LP over generated rows. Median 17.5 s, max 33.5 s. 3 unsupported (1.25%; the plan allows 5%). |
| Rows | 474 of 474 expected, with no execution failures |
| Wins / losses / ties | **198 / 0 / 39** |
| Estimate | **+9.80 per host** [9.30, 10.35], p = 5 × 10⁻⁵ |
| By stratum | +10.83 (n38, 0.8, 0.07), +4.59 (n40, 0.7, 0.06), +14.00 (n40, 0.8, 0.06) |
| Sensitivity | leave-one-stratum-out estimates 9.29 / 12.41 / 7.71; stratum-level sign-flip p 0.125 |
| Cost ratio | 0.338 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | **agrees**: 474 witnesses re-checked, no fairness problems, and the resource account matches |

## What it means

- **The opt-in v5 path works end to end on this family.** It covers:
  - selection of an exact-MIP comparator by the custodian;
  - registry-v2 arms in runc;
  - the generated-rows reference, with its certificates in the evaluation's custody;
  - the judge's recomputation.
- **The outcome agrees with B20_R41's re-pilot.** The re-pilot gave +10.6 [9.1, 12.1]; the
  rehearsal gave +9.80 [9.30, 10.35].

## Limits

- **One operator played every role,** with fixture keys, and the builder froze the record.
- **The adoption was simulated** in a copy. A real run needs reviewer adoption (B20R41-OPEN-1).
- **The stratum-level sign-flip has p 0.125.** With 3 strata, 0.125 is the smallest p that test can
  give, so it is reported, not used to decide.
- **The reference itself is an exact method of about 20 s** (see the package README).
- **Exposure.** The 279 hosts (30 SELECT, 240 CONFIRM, 9 development) are in
  `handoff/e1*/exposure_hosts_addendum_b20r43.json` and in `handoff/e1d/exposure_hosts_all_part_*.json`.
