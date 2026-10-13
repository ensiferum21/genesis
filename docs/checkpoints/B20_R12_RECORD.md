# B20_R12 record: E1 under the user's decisions, redone on the canonical line

- **Branch:** `continuation-b20-rx` (the canonical B20_R11 line plus the ported recovery work; see `B20_RX1_RECORD.md`).
- **Run by:** the builder, on DEV, with fixture keys for the rehearsal. Nothing here is independently reviewed, and nothing licenses a claim.
- **History:** the first B20_R12 run was lost with its workspace. Its code was recovered from the session transcript and re-applied here. The lost run's result (+0.60 per task, INFEASIBLE, a refused registration) is recorded in the archived `NEXT_ACTIONS_after_lost_B20_R12.md`, but its evidence was not recoverable.

## Decisions (the user, 13 Oct 2026), fixed before any run

| Decision | Implementation |
|---|---|
| Cost: time-matched baselines | Candidate kind `dsl-time-matched-v1` restarts a fixed DSL program with fresh seeds until its CPU budget is spent. The plan's cost rule (max ratio 3.0) is unchanged. |
| Comparator: strongest fixed baseline on the custodian's SELECT panel | `custodian.select_comparator`: a private SELECT panel from the adopted calibration, screened against the custodian's exposure registry and every reserved host; the baselines run in the sandbox; the hosts are reserved for good; the selection is signed. `cli.record_comparator_selection` writes it into the campaign (write-once). `register` refuses any other baseline, and any selection the custodian did not make. |
| Power: centred-headroom model, n ≥ 10 per stratum | `power.required_sample(..., headroom='centred')` |
| Host family: a separate, versioned E1 rule | `calibration.SELECTION_RULE_E1_HARD` (`e1-hard-v1`): fixed-baseline ceiling rate in [0, 0.25], target 0. The certification, headroom and evaluator-speed limits are unchanged, and the rule never reads a candidate. `record_problems` accepts only registered rules. `calibration.load(..., study='e1')` reads a study adoption whose record must use the rule it names. The domain rule and adoption are unchanged. |

## Commits

| Commit | What |
|---|---|
| `7b598c0` | Code: time-matched kind, SELECT comparator, versioned rule, study adoption; tests (`test_calibration_rules.py`, `ComparatorSelection`) |
| `02de690` | Setup: `scripts/b20r12_e1_calibration.py` and `scripts/b20r12_e1_redo.py`, with rules and verdicts in their docstrings, committed and pushed before either ran |
| `0d7caaf` | Calibration result and adoption under `studies.e1` |
| `56c3c10` | Redo result and `handoff/e1` v2 |

## Results

**Calibration** (`evidence/dev_calibration_e1_b20r12/`):
- 17 triangle-free settings: every setting measured before, round 2 plus RX4. 8 fresh DEV hosts each.
- 4 settings selected: planted_cluster n20 (fixed-baseline ceiling 0.00), erdos n18 p0.5 (0.00), erdos n22 p0.35 (0.125) and erdos n26 p0.3 (0.25).
- Every larger setting failed the unchanged certification limit within 30 s.

**Redo** (`evidence/e1_redo_b20r12/`):
- 30 fresh DEV hosts; 711 named host identities were excluded.
- Against `multistart_tm`: +0.967 edges per host, wins / ties / losses 19 / 9 / 2, CPU ratio 0.997. The cost rule now holds.
- The DRAFT dry run is SUPPORTED, but the centred power model is INFEASIBLE. On planted_cluster and erdos n22 p0.35 the candidate is at, or within one edge of, the optimum, so a 1.0 design effect cannot be carried.
- **Preregistered verdict: UNDERPOWERED.**
- The custodian SELECT rehearsal (30 private hosts) picks `multistart_tm`. The amended DRAFT fails the decision-record check because no panel size was chosen, so the rehearsal stopped there.

## New open item

**B20R12-OPEN-1.** The decided E1 design cannot be powered on the family that `e1-hard-v1` selects. Choosing between the options below is a reviewer's design decision. None may be taken to obtain a stronger label:
- a power model with per-stratum design effects fixed from the design;
- a rule version (`e1-hard-v2`) that also bounds a candidate-independent headroom;
- retiring E1 at this design.

The options are set out in `handoff/e1/README.md`.

## Tests

- `tests_genesis/test_calibration_rules.py` (4): the domain rule and adoption are unchanged; the E1 rule is candidate-independent; registered rules validate and tampered ones do not; study adoption works.
- `tests_genesis/test_candidate_custody.py::ComparatorSelection` (2): time-matched baselines spend their budget; the custodian selects and registration enforces the selection.
