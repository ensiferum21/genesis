# Known-answer ladder: c4_host_v2

Preregistration `364d972bab91eb1c24c12c307dc6f7024aa4b71bd146528b700cc10454316a27` · status **PUBLIC_CALIBRATION_COMPLETE** · answer key `847757b66bfa5f9e…` [cited: OEIS A006855]

## Test rungs

| Arm | Matched | Unbroken height | Total shortfall | Max CPU/budget |
|---|---:|---:|---:|---:|
| sat_cadical | 0/20 | — | 225 | 1.227 |

## Per rung

| Split | n | Arm | Best | Reference | Status | Invocations |
|---|---:|---|---:|---|---|---:|
| development | 4 | sat_cadical | 4 | 4 | MATCHES_KNOWN_OPTIMUM | 1 |
| test | 21 | sat_cadical | 48 | 50 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 22 | sat_cadical | 49 | 52 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 23 | sat_cadical | 53 | 56 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 24 | sat_cadical | 55 | 59 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 25 | sat_cadical | 59 | 63 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 26 | sat_cadical | 60 | 67 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 27 | sat_cadical | 64 | 71 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 28 | sat_cadical | 67 | 76 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 29 | sat_cadical | 70 | 80 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 30 | sat_cadical | 74 | 85 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 31 | sat_cadical | 74 | 90 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 32 | sat_cadical | 79 | 92 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 33 | sat_cadical | 82 | 96 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 34 | sat_cadical | 87 | 102 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 35 | sat_cadical | 89 | 106 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 36 | sat_cadical | 93 | 110 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 37 | sat_cadical | 97 | 113 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 38 | sat_cadical | 100 | 117 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 39 | sat_cadical | 102 | 122 | BELOW_KNOWN_OPTIMUM | 1 |
| test | 40 | sat_cadical | 107 | 127 | BELOW_KNOWN_OPTIMUM | 1 |

## Paired test comparisons (exploratory)


## Limitations

- Public calibration: complete hosts and their optima are published; not a sealed evaluation.
- Matched values are known optima only according to the cited source; no optimality certificate is produced here.
- Realized CPU includes interpreter start-up for every invocation; the final invocation may overshoot.
- A frontier candidate is not a discovery until independently re-checked and priority-checked.

Promotion allowed: **no**.
