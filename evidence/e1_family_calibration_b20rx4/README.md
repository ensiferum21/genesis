# B20_RX4: DEV calibration of a harder host family for E1

- **Decision:** the user chose "harder host family" for E1 on 13 Oct 2026.
- **Script:** `scripts/b20rx4_e1_family_calibration.py`, committed as `7b8a57e` before running.
- **Scope:** DEV only, builder-run. Its 144 hosts are now exposed (`hosts.json`).
- **Grid:** triangle-free erdos, n ∈ {26, 30, 34, 38} × p ∈ {.25, .30, .35}, 12 hosts per cell. All 145 E1 hosts the builder has named are excluded.
- **Arms:** E1's candidate (cross_2 represent-and-repair, 0.5 CPU s) against the three time-matched baselines (0.5 CPU s each). Each host's optimum is certified with LP dual + SAT/DRAT in 30 s.

| Cell | Comparator (strongest baseline) | Mean effect | SD | W/T/L | Certified | Candidate below optimum | Eligible |
|---|---|---|---|---|---|---|---|
| n26 p.25 | multistart_tm | −0.08 | 0.29 | 0/11/1 | 12 | 5 | no |
| n26 p.30 | low_cycle_tm | 0.42 | 1.51 | 6/3/3 | 12 | 6 | no |
| n26 p.35 | low_cycle_tm | 0.92 | 1.44 | 7/4/1 | 12 | 10 | no (effect < 1.0) |
| n30 p.25 | low_cycle_tm | 0.17 | 1.34 | 4/3/5 | 12 | 6 | no |
| n30 p.30 | low_cycle_tm | 1.25 | 2.53 | 6/3/3 | 10 | 8 | yes |
| **n30 p.35** | **low_cycle_tm** | **4.92** | **2.81** | **12/0/0** | **10** | **6** | **yes: chosen** |
| n34 p.25 | low_cycle_tm | −0.83 | 1.40 | 2/2/8 | 12 | 12 | no |
| n34 p.30 | low_cycle_tm | 1.42 | 1.83 | 8/2/2 | 5 | 5 | no (too few certified) |
| n34 p.35 | low_cycle_tm | 7.33 | 1.92 | 12/0/0 | 5 | 3 | no (too few certified) |
| n38 p.25 | low_cycle_tm | 1.50 | 2.47 | 6/4/2 | 11 | 9 | yes |
| n38 p.30 | low_cycle_tm | 3.08 | 2.28 | 11/0/1 | 3 | 3 | no |
| n38 p.35 | low_cycle_tm | 10.17 | 3.10 | 12/0/0 | 2 | 1 | no |

## Choice

**n30, p0.35.** Of the eligible cells, the smallest n, then the largest effect/SD.

On this DEV sample the candidate beats the strongest time-matched baseline on every host, by 4.9 edges on average. It is still below the certified optimum on 6 of the 10 certified hosts, so this is not a family where every method sits at the ceiling.

## Reading

- **The candidate's advantage grows with host density.** On E1's current family (n22 p.35) it was +0.6, under the lost B20_R12 run's design.
- **The comparator changes.** On this family the strongest time-matched baseline is low_cycle_tm, not multistart_tm. The custodian's SELECT step decides it on its own panel.

## Next, in the B20_R12 redo

This needs the canonical B20_R11 code:
1. Adopt n30 p0.35 as E1's family through a new DEV calibration record.
2. Run a fresh pilot on new hosts.
3. Run the power analysis under the model the statistician signs off.
4. Run the custodian SELECT step.
5. Regenerate `handoff/e1`.

Nothing from this calibration licenses a claim.
