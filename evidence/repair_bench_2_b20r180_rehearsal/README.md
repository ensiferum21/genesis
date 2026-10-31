# B20_R180 (SR-1a2): the rehearsal, on six development defects only

The dry run of `scripts/b20r180_repair_bench_2.py --rehearse` from a copy of the working tree (31 Oct 2026, container
clock about 00:20 to 00:24 SGT): every phase, with six development defects of the first catalogue (M1, L2, S1, W2, R1,
G1) standing in for the held-out ones; the loop was never run on a held-out defect. Development data: its vault is
circular (it holds repairs of the same defects), so its comparison and reuse numbers are not evidence. It completed
every phase (MILESTONE_DEMONSTRATED on the stand-ins; isolation and the 18 controls held; no promotion outside a
component). The development check before it (loop version 2 against version 1 on the 21 defects of the first
catalogue, job seed 1, isolated, empty vault): 17 against 15 repaired.
