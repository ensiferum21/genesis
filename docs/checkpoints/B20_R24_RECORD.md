# B20_R24 record: the e1-hard-v2 family; E1 and E1b ready for review; the GV3 path rehearsed end to end

Builder-run batch, carrying out the user's decision of 14 Oct 2026. Nothing here is independently reviewed, and nothing licenses a claim.

## The decision

For the E1b host family (B20R23-OPEN-1), the user chose: "New rule e1-hard-v2: a versioned rule that adds a candidate-independent headroom bound and certification limit; a calibration picks settings for both E1 and E1b, then both are re-piloted on fresh hosts."

## What changed in the code

- **`calibration.SELECTION_RULE_E1_HARD_V2`** (`e1-hard-v2`). It keeps every `e1-hard-v1` limit and never reads a candidate. It adds three things:
  - it measures the fixed baselines the way the studies run them: `dsl-time-matched-v1` with 2.0 CPU s of restarts in the OCI sandbox (`calibration.measure_time_matched`);
  - a certification limit: `obstruction.certify`, seeded with the best baseline witness, with 60 s per host;
  - a headroom bound: mean (optimum − best time-matched baseline) ≥ 1.0 edge, the plan's design effect.

  The rule is registered. `summarize` and `record_problems` take the rule into account, and older records and summaries are unchanged.
- **The evaluator's reference (B20R24-OPEN-1, found and repaired in this batch).** `domains.GraphHostAdapter.reference(joint=True)` gives the joint LP/SAT certification: exact LP dual first, then SAT/DRAT on the remaining gap with the whole budget. It is seeded with the better of an 8-round DSL solution and 1 s of LP-ordered greedy, and keeps the certificate bundle v2 in the evaluation evidence. `custodian.reference_options` asks for it in v4 evaluations. The default SAT-only path is kept for older callers and request versions, and its message now names why it stopped.
- **Tests.**
  - `tests_genesis/test_calibration_rules.py::RuleV2` (3 tests): the v1 limits are kept; the bound equals the design effect; the measurement spec; selection follows from the rows; tampering is detected; older summaries are unchanged; a real time-matched measurement certifies its hosts; CONFIRM material is refused.
  - `tests_genesis/test_domain_adapters.py`: the joint reference certifies a host with more than 100 edges, its bundle replays VALID, the exact-search range is unchanged, and the custodian's options apply only to v4 graph requests.

## Steps and results

Every step's script was committed before it ran. Because GitHub was disconnected, each script's SHA-256 was also sent to the user in the conversation beforehand.

| Step | Script, commit | Result |
|---|---|---|
| Calibration under `e1-hard-v2` | `b20r24_e1_hard_v2_calibration.py`, `bf7c4c8` | **Triangle-free: 3 of 20 settings selected**: planted_cluster n30 p_in 0.6 p_out 0.2, erdos n26 p0.35, erdos n30 p0.3. **C4: NO_ELIGIBLE_SETTING.** All four of E1's v1 settings, and E1b's C2 (n40 p0.2), are near the time-matched ceiling. Studies `e1-v2` and `e1b` were adopted; study `e1` is unchanged. |
| Re-pilots, 30 fresh hosts each | `b20r24_repilots.py`, `bf7c4c8` | **E1 READY_FOR_REVIEW**: +2.57 per host, 26 / 3 / 1, ratio 1.00, power 0.88 at 30 hosts. **E1b READY_FOR_REVIEW**: +2.63, 29 / 1 / 0, ratio 1.02, power 0.97 at 30. E1b on C4: NOT_RUN. |
| First rehearsals (same script) | — | Both **INVALID**: 4/30 and 2/30 CONFIRM hosts unsupported, against the plan's 5%. The judge agrees. The custodian's SELECT chose the pilots' comparators. Results kept. |
| Diagnosis | `b20r24_diagnose_unsupported.py` | The SAT-only reference stopped after 62–70 s on each host. The joint certification closes 5 of 6 within 120 s: 3 by the LP dual in 4–10 s, 2 by SAT/DRAT. |
| Repair, then rehearsals re-run on new hosts | `b20r24_rehearsal_rerun.py`, `72bd294` | **E1 SUPPORTED**: SELECT → `multistart_tm`; 30/30 certified; 29 / 0 / 1; estimate 3.00 [2.53, 3.47]; cost 1.003. **E1b SUPPORTED**: SELECT → `multistart_tm`; 29/30 certified; 29 / 0 / 0; estimate 3.55 [3.03, 4.05]; cost 1.019. `judge.recompute` agrees on both. |
| Packages | `b20r24_packages.py` | `handoff/e1` v3 and `handoff/e1b` v2. Each has the descriptors (E1b also its interventions), a fresh frozen campaign export, the DRAFT (a frozen copy has no structural problems), the pilot, the power analysis, both rehearsals, and 1,544 exposure hosts. |

Evidence: `evidence/dev_calibration_e1_hard_v2_b20r24/`, `evidence/repilots_b20r24/` and `evidence/rehearsal_rerun_b20r24/`, each with a README.

## What this means

- **Both GV3 studies are now ready for review.** The path runs end to end on the decided design: a candidate-independent calibration, a pilot, a power analysis, the custodian's SELECT, a v4 request bound to a frozen DRAFT, sandboxed evaluation, and the judge's recomputation. Run by the builder, it gives SUPPORTED.
- **E1 itself is now powerable.** That answers B20R12-OPEN-1 on the user's decision.
- **The first rehearsals found a real evaluator defect.** The plan's unsupported limit caught it, and the defect was repaired rather than worked around.
- **What GV3 still needs:**
  - a reviewer to sign off `e1-hard-v2` and the DRAFTs;
  - a statistician (B19-OPEN-4);
  - an independent custodian on its own machine, with a real CONFIRM panel.

  E1b's causal follow-ups were piloted on the B20_R23 settings and need a re-pilot on the `e1b` family.
- **New design point, B20R24-OPEN-2.** The calibration admits up to 10% of hosts uncertified within 60 s, while the plan allows 5% unsupported tasks at 600 s. A reviewer should align these before a real run.

## Still open

B20R24-OPEN-2; reviewer and statistician sign-off; an independent custodian; the E1b causal re-pilot; GV4 (component invention).
