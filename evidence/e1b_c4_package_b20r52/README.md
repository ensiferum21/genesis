# B20_R52 evidence: the E1b-C4 DRAFT package and a same-operator rehearsal through the v5 C4 tree route (DEV)

Builder-run, with fixture keys. Nothing is adopted or registered with any custodian, and nothing is
licensed.
- **Script:** `scripts/b20r52_e1b_c4_package.py`, committed before running in `75d91fa`. Its SHA-256 was
  sent to the user beforehand.
- **Code identity:** the rehearsal records `b767fdfb…`, the setup commit's.
- **Log:** `run.log`, 676 s, in one go.
- **Files:**
  - the calibration record (`calibration_c4_host_v2_e1_hard_v2_c4tree_draft.json`);
  - `rehearsal_summary.json` and `rehearsal_receipt.json`;
  - `decision_record_DRAFT.json`;
  - `development_look_hosts.json` (the disclosed smoke run's 9 hosts);
  - `summary.json`.
- **Package:** `handoff/e1b_c4/`.

## Result

| Step | Result |
|---|---|
| Calibration record | B20_R50's Part A rows under the registered DRAFT rule; `record_problems` = []; selects erdos n40 p0.15 and n30 p0.2, as B20_R50 did (record `77d81192…`) |
| SELECT (30 private hosts, custodian) | totals: exchange 2,408, low_cycle 2,572, multistart 2,457 → **low_cycle_tm** |
| Request | v5, reference `generated-rows-tree-c4-v1` (B20_R46 package, 600 s), 20 CONFIRM hosts (B20_R50's power choice) |
| Reference | **20/20 certified**: 16 by trees, 4 at the root; 2.6–68.9 s (median 4.2 s); none unsupported |
| Outcome | **SUPPORTED**: +1.15 per host [0.70, 1.65], W/L/T 12/1/7, cost ratio 0.92, p = 0.00073 |
| Judge | agrees; 40 witnesses re-checked; no registration-log problems |
| Package | 2,957 exposure hosts in 6 files; the frozen decision record has no problems |

## Reading

- **What SUPPORTED with the judge agreeing means.** Only that the opt-in C4 custody path works end to
  end: v5 request, tree reference, custody bundles, custodian SELECT, judge. One operator plays every
  role, and the builder froze the record.
- **Scope.** The claim it rehearses is scoped to the DSL baselines. On these settings an exact C4 MIP
  is optimal within 2 s and dominates E1b (B20_R50; B20R33-OPEN-1).
- **The 600 s budget.** The disclosed smoke run at 120 s was INVALID: one dense host's reference
  needed 221 s. At 600 s every host certified here, the slowest in 69 s.

## Tests

`tests_genesis/test_e1b_c4_package.py` (7):
- the record is B20_R50's under the registered draft and checks clean, and no study adopts it;
- the arms and the reference route;
- the DRAFT decision record freezes clean;
- the record on disk equals the derived record;
- the rehearsal went through v5 with the C4 tree route (SELECT, rows, judge, log, reference methods);
- the package files match the index, with exposure files of at most 500 hosts;
- every rehearsal and development-look host is in the package exposure and in the addenda.
