# E1b readiness pilot (B20_R23, DEV)

**Script:** `scripts/b20r23_e1b_readiness.py`. Its rules are in the docstring. It was committed as `8d47cf8` before it ran. The GitHub push failed (no credentials in the session), so the script's SHA-256 (`82936b95…1bb72`) was sent to the user in the conversation before the run, as an external anchor.

**Question.** Is an LP-guided construction candidate a second, powerable better-solver claim ("E1b")? E1 is UNDERPOWERED at its decided design (B20R12-OPEN-1).

**Design.** E1's decided design:
- time-matched conventional baselines;
- the strongest baseline by total as the comparator;
- the centred power model with n ≥ 10 per stratum;
- the B19 DRAFT plan as a dry run.

**Arms.** Every arm ran in the OCI sandbox through `candidates.run(isolation='runc')`, under one profile (4 CPU s, 2048 MiB, 20 s wall, 1000 queries) and the cgroup meter.

| Arm | Descriptor |
|---|---|
| candidate | `construct-pipeline-v1` `{init lp_greedy, frac 1.0, finish none, cpu_seconds 2.0}` |
| baselines | three fixed DSL programs as `dsl-time-matched-v1`, 2.0 CPU s of restarts each |
| diagnostic (triangle-free only) | `represent-and-repair-v1` `cross_2` with 2.0 CPU s (E1's candidate at this budget) |

**Hosts.** 12 fresh DEV hosts for each of C1 (triangle-free erdos n30 p0.3), C2 (triangle-free erdos n40 p0.2) and C3 (C4 erdos n30 p0.2). They are screened against 1,018 exposure identities: every host named in 800 evidence and handoff files, plus the regenerated E1 exposure set. The two empty files that were skipped are listed in `summary.json`.

**Reference optimum.** `obstruction.certify` with 120 s per host, seeded with the best arm witness. Certified 12/12 on C1, 12/12 on C2 and 9/12 on C3. The C3 threshold is 9, so C3 is at the edge. The three uncertified C3 hosts are reported and not scored. One certification overran its 120 s by 27 s while its last SAT/DRAT call finished; the proof is valid regardless.

## Result

| | triangle_free_host_v1 (C1 + C2) | c4_host_v2 (C3) |
|---|---|---|
| Comparator (strongest by total) | `low_cycle_tm` | `low_cycle_tm` |
| Scored hosts | 24 | 9 |
| Mean difference, candidate − comparator | **+1.79** (C1 +2.42, C2 +1.17) | **+1.00** |
| Wins / ties / losses | 18 / 6 / 0 | 4 / 5 / 0 |
| Hosts where the candidate reaches the certified optimum | 22 / 24 (comparator 5) | 3 / 9 (comparator 2) |
| Mean gap to the optimum, candidate / comparator | 0.08 / 1.88 | 0.78 / 1.78 |
| CPU ratio, candidate / comparator (cgroup) | 1.02 | 0.99 |
| DRAFT plan dry run | SUPPORTED, estimate 1.79 [1.29, 2.29] | NOT_SUPPORTED at n = 9 (p 0.0625; Holm fails), estimate 1.00 [0.22, 1.78] |
| Centred power | CHOSEN: 12 per stratum, 24 in total (power 0.88) | CHOSEN: 20 (power 0.92) |
| False-positive rate at zero effect | 0.011 | 0.006 |
| **Verdict** | **READY_FOR_REVIEW** | **READY_FOR_REVIEW** |

Diagnostic, triangle-free only: the candidate minus E1's `cross_2` candidate at the same 2.0 s budget is +1.375 (21 / 3 / 0).

## What this means

- E1b is the first candidate on this line whose E1-design pilot is powerable. The power model chooses a size on both domains.
- It is a DEV readiness diagnostic. It licenses no claim.
- The candidate is a builder-written method (`discovery/construct.py`, B20_RX3). A supported E1b would be a scoped better-solver statement against fixed DSL baselines. It would not be evidence of research ability (GV4).
- The host family is builder-chosen (B20_R14 settings with room to the optimum). The `e1-hard-v1` rule applies to E1 only, by the user's decision of 13 Oct 2026. So the custodian's SELECT step has no study calibration to draw from until a family rule for E1b is decided.
- On C4 the certification rate (9/12 at 120 s) is at the threshold. The pilot excludes the three hardest hosts from scoring. A study on C3 should either keep a certification limit in its family rule or accept that the reference is only a power input.

## Files

- `rows.jsonl`: one row per host, with every arm's value, status, cgroup CPU and meter, and the certification result.
- `hosts.json`: the 36 hosts and their generator records.
- `pilot_rows_<domain>.json`: the scored rows in analysis form.
- `power_analysis_centred_<domain>.json`
- `summary.json`
- `console.log`, `run.log`
