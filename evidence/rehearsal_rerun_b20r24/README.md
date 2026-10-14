# E1 and E1b rehearsals after the evaluator repair (B20_R24): SUPPORTED, judge agrees

**Script.** `scripts/b20r24_rehearsal_rerun.py`, committed as `72bd294` before it ran. That commit also carries the repair. The script's SHA-256 (`b8cfdb9d…a461d`) was sent to the user in the conversation before the run.

**What this is.** The rehearsal procedure of `scripts/b20r24_repilots.py`, unchanged. It ran after B20R24-OPEN-1 was repaired: v4 evaluations now use the joint LP/SAT reference.
- **Hosts:** new campaign and CONFIRM seeds, and a new custodian SELECT panel. Every host named so far is excluded (1,424 identities), including both earlier rehearsals.
- **Operator:** the same operator, with fixture keys and a builder-frozen REHEARSAL copy of each DRAFT.
- **Status:** **it licenses nothing**, and it is not a CONFIRM result.

## Results

| | E1 (study `e1-v2`) | E1b (study `e1b`, triangle-free) |
|---|---|---|
| Custodian SELECT, 30 private hosts | exchange 2553, low_cycle 2600, multistart 2606 → `multistart_tm` | exchange 2602, low_cycle 2618, multistart 2638 → `multistart_tm` |
| Panel (power-chosen) | 30 CONFIRM hosts: 30 certified, 0 unsupported | 30 CONFIRM hosts: 29 certified, 1 unsupported (3.3%, within the plan's 5%) |
| Wins / losses / ties | 29 / 0 / 1 | 29 / 0 / 0 |
| Estimate (mean of stratum means), 90% interval | **3.00** [2.53, 3.47] | **3.55** [3.03, 4.05] |
| Cost ratio, candidate / baseline (cgroup CPU) | 1.003 | 1.019 |
| Decision checks | all pass (Holm, interval, MUE, cost, no stratum regression) | all pass |
| Leave-one-stratum-out estimates | 2.45 – 3.30 | 3.10 – 4.07 |
| Outcome | **SUPPORTED** | **SUPPORTED** |
| `judge.recompute` | agrees: SUPPORTED, 60 witnesses re-checked, no problems | agrees: SUPPORTED, 58 re-checked |
| Isolation, raw evidence | OCI runc for every arm; complete; 0 execution failures | the same |

Notes on the results:
- **The comparator differs from the pilot.** The custodian's SELECT chose `multistart_tm` for E1, while the pilot's comparator was `low_cycle_tm`. The custodian's private panel governs, as the decided design requires.
- **A sensitivity limit.** With three strata, the stratum-level sign-flip p-value cannot go below 0.125. It is reported, and it is not a decision rule.

## What this shows, and what it does not

**It shows that the GV3 path runs end to end on the decided design**, for both studies:
- a calibration under a rule that does not read the candidate;
- a pilot and a power analysis;
- the custodian's SELECT step;
- a v4 request bound to a frozen DRAFT;
- registration, sandboxed evaluation and the judge's recomputation.

It also shows that the outcome was SUPPORTED when the builder ran it.

**It does not show** independence, reviewed decisions or a real CONFIRM panel:
- the same operator ran every role, with fixture keys;
- the decision records were frozen by the builder;
- the rule `e1-hard-v2`, the power model and both studies' decisions still need a reviewer and a statistician (GV3 needs an independent custodian).

**Custody note.** As preregistered, the custodian stores and keys were deleted after each rehearsal. The per-task reference records, including which hosts were certified by the LP dual and which by SAT/DRAT, are therefore not kept here. The signed receipts bind the deleted stores by their raw-evidence roots.

## Files

- `rehearsal_<study>.json`: the receipt payload, the judge, the resource account and fairness, the DRAFT, and the SELECT and CONFIRM hosts.
- `rehearsal_receipt_<study>.json`
- `decision_record_DRAFT_<study>.json`
- `campaign_export_<study>.zip`
- `summary.json`, `console.log`, `run.log`
