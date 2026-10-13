# B20_R11 record: E1 readiness through the custodian's own runner (GV3 path)

- **Parent:** B20_R10 (commit `c49f974`).
- **Run by:** the builder, on DEV material. A rehearsal used fixture keys.
- **Review status:** nothing here has been independently reviewed.

## Problem

E1 is the only candidate with positive DEV evidence of usefulness: B19's represent-and-repair solver, using the `cross_2` cut representation on triangle-free hosts, gained +1.27 edges per task.

It could not go to a custodian, for two reasons:

- The custodian's evaluator ran DSL programs only (B19-OPEN-3). B20_R5 repaired this.
- The candidate's CPU had been measured in-process, while the baselines' CPU was measured in the DSL worker.

## Implementation

`scripts/b20r11_e1_readiness.py`, committed as `96fdf26` before running. Its rules were fixed in that commit.

**Part A: DEV pilot on the custodian's runner.**

- 30 fresh DEV hosts. The B19 pilot hosts were excluded.
- Every arm ran through `candidates.run(isolation='runc')` with one resource profile.
- Results were scored with the B19 DRAFT plan as a dry run.
- The readiness verdict rule was fixed in the script.

**Part B: the E1 handoff package.** In `handoff/e1/`:

- a real frozen triangle-free campaign export, with the candidate descriptor frozen in it;
- the DRAFT decision record, unchanged;
- the B19 pilot and power analyses;
- every builder-generated host, so a custodian can exclude them;
- exact steps for the reviewer, the research operator, an independent custodian and the judge.

Part B also ran a same-operator rehearsal with fixture keys. It used a builder-frozen copy of the DRAFT, labelled REHEARSAL, and went through register → evaluate → signed v4 receipt → registration log → judge on 25 fresh hosts.

## Evidence (`evidence/e1_readiness_b20r11/`)

**The effect replicates under equal sandbox metering.**

- Against `low_cycle`: +1.333 edges per task, 24 wins / 5 ties / 1 loss.
- Certified optimum reached on 20 of 30 hosts, against 3 for `low_cycle`.

**The preregistered cost rule fails.**

- Candidate/baseline CPU ratio is 3.38, against the plan's `max_ratio` of 3.0.
- The DRAFT dry run therefore returns NOT_SUPPORTED. The script's verdict is `COST_RULE_FAILS`.
- Cause: every arm pays about 0.21 s of interpreter start-up. The candidate adds its 0.5 s search; the DSL baselines finish almost immediately.

**The rehearsal executes end to end.**

- Outcome NOT_SUPPORTED: 24 wins / 0 losses / 1 tie, estimate +3.04 against `multistart`, cost ratio 3.43.
- The judge agrees, with 50 witnesses re-checked. Arm fairness is clean.
- Same operator, so it licenses nothing.

**The comparator rules disagree.**

- The DRAFT names the strongest baseline on a custodian SELECT panel.
- The custodian's v4 check uses the campaign's own strongest baseline. For this export that is `multistart`, where the pilot picks `low_cycle`.

## Consequence

GV3 now has a concrete, executable package. Three decisions block a valid sealed E1 run, and each must be made on design grounds before any panel exists:

1. **The power model** (B19-OPEN-4).
2. **The cost rule** (B20R11-OPEN-1). For example, time-matched baselines. Raising `max_ratio` after seeing this result would be relaxing a criterion to obtain a label.
3. **The comparator rule** (B20R11-OPEN-2).

An independent custodian, a reviewer and fresh panels are also needed.

## Claim ceiling

DEV pilot and rehearsal only. No sealed task. No promoted claim.
