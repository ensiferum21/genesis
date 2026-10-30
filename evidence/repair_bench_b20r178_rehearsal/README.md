# B20_R178 (SR-1a): the rehearsal, on development defects only

The dry run of `scripts/b20r178_repair_bench.py --rehearse`: every phase, with the 8 development defects standing in
for the held-out ones. It never ran the loop on a held-out defect. It is development data: the circular vault (the
development vault holds repairs of the same defects) makes its reuse and comparison numbers meaningless as evidence.

**Two rehearsals, both disclosed.**
1. 30 Oct 2026, about 23:39 to 23:44 SGT, from a copy of the working tree: `result_first_rehearsal.json`
   (MILESTONE_DEMONSTRATED; the loop repaired 22 of 24 development obstacles, 'nolocal' 16, 'random' 17, 'enum' 18,
   'retrieval' 16; no false repair by the loop, 3 to 5 caught by the verifier in the comparators). Two development
   episodes in its phase 1 (L2 and G2) were not repaired. Reading them showed two faults of the diagnosis, fixed before
   the second rehearsal:
   - the obstacle model stopped after a few short trials that all passed, never having seen a fresh failure, with its
     belief concentrated on whatever lines short trials never reach. Now it stops only when a fresh trial has failed,
     and a length where trials keep passing is "quiet", so probing moves to longer trials (`obstacle.py`); the trial
     cost and the per-length key were also confused (a trial of length n was recorded as 2n, so the per-length
     statistics were never used);
   - a defect that corrupts state silently in runs that still pass removed the very law it breaks (G2's
     `set(events) == set(seen)`). Laws broken by a single method only are now kept (`probe.py`).
   Also added then: the vault's hunks (retrieval of a retained repair verbatim), every party's CPU time.
2. About 23:47 to 23:52 SGT, with those fixes: `result.json`, `rows.jsonl`, `isolation.json`, the vaults and
   `episodes.jsonl.gz`. It ran before the analysis was moved into `analyse()` and before the final sources were kept
   in the episode log; `analyse()` at the preregistration commit reproduces this `result.json` exactly.

The development check of 23:44 (the loop alone, isolated, development defects x job seeds 1 to 3) repaired 21 of 24
before the law fix and 23 of 24 after it.
