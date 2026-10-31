# B20_R181 (SR-1a3): the rehearsal, on six development defects only

The dry run of `scripts/b20r181_repair_bench_3.py --rehearse` from a copy of the working tree (31 Oct 2026, about 10:08
to 10:13 SGT): every phase, with six development defects (T3, T4, M1, S1, W2, G1; T3 and T4 the development defects
two of the invented operators came from) standing in for the held-out ones. The loop was never run on a held-out
defect. Development data: its vault is built from the same six defects, so its comparison and reuse numbers are not
evidence (every loop repair in it was a retrieved hunk). It completed every phase: MILESTONE_DEMONSTRATED on the
stand-ins; isolation and the 24 controls held; no promotion outside a component.

A first rehearsal (about 10:00) was stopped before it finished, when version 3 was changed (the conservation
tie-breaks, added after version 3 chose a cache-disabling and then a bound-deleting patch on M1 in a unit test; the
verifier had rejected both). Development check before this rehearsal (all 33 development defects, job seed 1,
isolated, empty vault, common trial keys): version 3 repaired 25, version 2 22.
