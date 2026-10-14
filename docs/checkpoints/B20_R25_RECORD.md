# B20_R25 record: E1b's causal follow-ups on its family, and the causal ladder rehearsed end to end

Builder-run batch. Nothing here is independently reviewed, and nothing licenses a claim.

## What was done

`scripts/b20r25_e1b_causal.py` (rules in the docstring, committed before it ran; evidence in `evidence/e1b_causal_b20r25/`).

**Part A, the DEV re-pilot.** E1b's registered ablation and placebo were measured on 30 fresh hosts of the `e1b` family, all certified:

| Contrast | Mean per host | Wins / ties / losses | Power | Verdict |
|---|---|---|---|---|
| Candidate − ablation (`random_greedy`) | +1.80 | 27 / 3 / 0 | 0.996 at 30 hosts | **READY_FOR_REVIEW** |
| Candidate − placebo (`lp_shuffled_greedy`) | +3.70 | 28 / 2 / 0 | 0.865 at 36 hosts | **READY_FOR_REVIEW** |

**Part B, a same-operator rehearsal with fixture keys.** All steps ran in one frozen campaign:
1. The custodian's SELECT chose `multistart_tm`.
2. The main sealed evaluation was **SUPPORTED**: 30 / 0 / 0, estimate 3.03 [2.67, 3.43], cost 1.02.
3. The ablation follow-up was **SUPPORTED**: 28 / 0 / 2, 1.97 [1.70, 2.23].
4. The placebo follow-up was **SUPPORTED**: 35 / 0 / 1, 3.19 [2.78, 3.64].
5. `judge.recompute` agreed on all three.
6. The evidence kernel, under a FIXTURE registry, recorded every anchor and receipt and bound one claim to the three requests. It promoted the claim to **utility CONFIRMED_SAME_DOMAIN** and then **causality ABLATION_SUPPORTED → PLACEBO_CONTROLLED**.

This is the first end-to-end run of the causal ladder on a real study. Fixture grants never reach a release path, because release, preflight and bundle verification build their own trust-root kernel.

## Incidents (all recorded in the evidence README)

| Incident | Cause | Handling |
|---|---|---|
| The pre-registration anchor was late | The SHA-256 reached the user about 30 s after the first run started, with 3 of 30 hosts logged | The commit preceded the run; disclosed |
| First run stopped at SELECT | The custodian's exposure screen refuses a JSON source with more than 1,000,000 values. The script's list was not deduplicated: 2,741 entries for 1,574 hosts | Split into sources of 400 hosts (`1132f16`); rules unchanged |
| Second run stopped after SELECT | The builder added helper scripts to the source tree during the run, and the campaign's frozen-environment guard refused to continue | Scripts moved out until the run finished; the aborted SELECT hosts are kept and excluded later |
| `pilot_hosts.json` overwritten on resume | The run's own output sat inside the exposure walk, and task ids are index-based. Rows were matched by id and never re-run | `scripts/b20r25_restore_pilot_hosts.py` regenerated the scored hosts from the first run's exclusion set; 30 / 30 match their rows (task id, stratum, certified optimum) |
| A wrong statement to the user | The builder first said the packages' exposure lists would be refused. They are accepted (1,544 hosts, about 587,000 values) | Corrected to the user. The split of the package lists is recorded as preventive, not a repair |

## Other changes

- **`handoff/e1` and `handoff/e1b`.** Both exposure lists are refreshed to 1,760 hosts and split into `exposure_hosts_part_NN.json` files of at most 400, plus an `exposure_sources.json` manifest fragment (`scripts/b20r25_package_exposure.py`). The single file would still have been accepted; the limit is reached at about 2,600 hosts.
- **`handoff/e1b`** also gains the follow-up DRAFTs and power analyses, and its README now records the causal results.
- **`docs/OPERATIONS.md`, two new rules:**
  - do not change the source tree while a run is going;
  - keep a resumable run's own output out of the exposure walk.

## Still open

- GV3 sign-off: a reviewer for `e1-hard-v2` and the DRAFTs; a statistician (B19-OPEN-4); an independent custodian.
- B20R24-OPEN-2.
- Replication (INTERNAL_INDEPENDENT, EXTERNAL_REPRODUCTION), which needs a second operator.
- GV4 (component invention).
