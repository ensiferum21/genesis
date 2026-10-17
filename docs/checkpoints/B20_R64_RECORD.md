# B20_R64 record: E1d's advantage over HiGHS grows with host size (ADVANTAGE_GROWS; DEV pilot)

- **Run by:** the builder. DEV only, outside every calibrated setting; no claim.
- **Setup commit:** `6feb780` (script SHA-256 `0a576290…8775`).
- **Re-run decision:** `3bceee2`.
- **Evidence:** `evidence/e1d_scaling_b20r64/`.

## Problem

B20_R63 showed that E1d's advantage on its calibrated hosts (n38–40) is speed, and that it ends between 8× and 16×
HiGHS budget. Does the crossover move out on larger hosts, or does the 0.5 s candidate degrade first?

## Design

- **Hosts:** planted_cluster (0.8, 0.06) at n = 40, 50 and 60, 10 fresh hosts each. n50 and n60 are drawn by a
  DEV-only copy of the adapter's generator, beyond the registered family space and the 200-edge bound.
- **Arms:** the candidate at 0.5 s, and HiGHS at 2, 8 and 32 s.
- **Rule:** B20_R63's rule per n.
- **Verdict:** ADVANTAGE_GROWS iff the n60 crossover is later than the n40 one.

## Run 1 was invalid

Run 1 ran beside the checkpoint's release matrix, whose unpinned Lean processes shared its core.
- **HiGHS** has a wall-clock time limit, and received only 0.55–0.86 of its CPU budget.
- **The candidate** is CPU-budgeted, so it was unaffected.

The builder declared run 1 invalid and stated a validity criterion before re-running: every HiGHS arm must receive
at least 0.9 of its budget. The unchanged script then re-ran on the same hosts, alone on the machine. The re-run
meets the criterion, at 0.997–1.118.

## Result: **ADVANTAGE_GROWS**

| n | Crossover | At 32 s (64×) |
|---|---|---|
| 40 | 8 s (16×), as in B20_R63 | 0.0 |
| 50 | 32 s (64×) | −0.3, UNRESOLVED |
| 60 | none within 64× | **+17.6 [8.1, 28.8], 10/0/0** |

At n60 the candidate is within one edge of the reference's proven upper bound on 9 of 10 hosts, and four edges on
the other. HiGHS at 32 s is 18.7 below on average.

**Run 1 compared.** It had exaggerated the n60 contrast (+39) but not its direction. The candidate's values agree
across runs on 29 of 30 hosts.

## Consequence

The robust form of E1d's claim lies on larger dense hosts. Claiming it there needs reviewer decisions:
- extend the planted-cluster family space beyond n40;
- lift the 200-edge certificate bound for the exact LP-dual route (statistician's brief, finding 5);
- a reference that certifies at n60 (5 of 10 in 120 s; the rest within 1 of their bounds).

## A lesson for the protocol

A run that compares a wall-clock-limited arm with a CPU-limited one must run alone. Its CPU delivery is now part of
the record.

## Tests

`tests_genesis/test_e1d_scaling.py`.
- **Design (5).**
- **Record (3):** the verdict recomputes; the validity criterion holds for the re-run and fails for run 1; the
  hosts are the same in both runs and are in the addenda.
