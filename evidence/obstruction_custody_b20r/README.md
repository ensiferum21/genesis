# B20_R1: custody-complete re-run of the B19 joint certification (DEV)

Produced by `python3 scripts/b20r_obstruction_custody.py evidence/obstruction_custody_b20r`
after Repair D (finding B20-REVIEW-04). It is a new execution on the B19 task specification
(HARD settings, seed 20261021, represent-and-repair witnesses, 60 s per task). Only the joint
arm was run. The B19 record (`evidence/discovery_b19/obstruction/evaluation.json`) is
unchanged history and still lacks its witnesses and certificates.

- `bundles/<sha256>.json`: one certificate bundle v2 per task, written before the summary.
- `objects/<sha256>`: the lower witnesses and exact rational LP dual certificates.
- `evaluation.json`: per-task results, the B19 recorded values for comparison, and the
  checker-only replay outcome from a separate process (scipy blocked, SAT solver refused).

Outcome: 12 of 12 OPTIMALITY_CHECKED via LP_DUAL_EXACT, all 12 replaying as recorded.
B19 recorded 11 of 12; task `dev-erdos-b73f6828-20261021-0000` closed this time (100..100,
B19 99..100) because the time-based witness search found a better witness. That is a
difference between two executions, not a correction of B19.

Replay any bundle with the producers disabled:

    python3 -m genesis.verification.certificates evidence/obstruction_custody_b20r/bundles/<sha>.json \
        --objects evidence/obstruction_custody_b20r/objects

DEV only; builder-run; no independent replay yet.
