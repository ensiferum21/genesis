# B20_R180 record (SR-1a2): the repaired loop no longer loses to unfocused search, and does not beat it; five defects in larger components were beyond every arm (MILESTONE_DEMONSTRATED; NO_DIFFERENCE_SHOWN against every arm; REUSE_NOT_SHOWN; DEV)

**Run by:** the builder, on DEV, on the state-management testbed extended with three larger components
(`docs/OMEGA_SELF_REPAIR.md` §7). It licenses claims about this testbed only.

**Preregistration.** Preregistered at `9305178` (31 Oct 2026); its digest pinned at `c3e9cf6`. The script is
`scripts/b20r180_repair_bench_2.py`, SHA-256 `bfe117a72569dc14df2093af60f53c96574a2c9ad40af70f0547b012601e3097`,
unchanged. The second sealed catalogue `src/genesis/repairkernel/defects2.py` has SHA-256
`6a7d091064fec91bda2dca40011b5c1598f07218604f0c5ddeb8a68c89049c85`, unchanged. It ran from the clean clone
`/home/claude/r180-run` at `9305178`.

**This run.** On CPU 1 (disclosed in the preregistration; CPU 0 ran PT-2), on 31 Oct 2026 from 08:46:15 to 09:55:53
SGT: 1 h 10 min, 315 episodes. Nothing else ran on CPU 1 while it ran. Counts and evaluations are deterministic; CPU
seconds are not.

**Disclosed.**
- While it ran, the builder looked at its interim rows (09:14 to 09:30) and read three of its episodes (P2's and P1's
  loop arms, T4's), and wrote three new operators aimed at the classes no arm had reached (T3, T4, P1; see "What
  next"). None of it touched the run (a separate clone, its code frozen) or its analysis.
- The 12 held-out defects were written by the builder of the loop; the jobs and the verifier (not the loop) were run
  on them before the run, to check that each interrupts every job and that the verifier tells the correct source from
  the defective one.

**Evidence and checks.**
- `evidence/repair_bench_2_b20r180/`: `result.json`, `rows.jsonl` (315 episodes), `episodes.jsonl` (the research and
  kernel records and every changed component's final source), `isolation.json`, the three vaults, `run.log`.
- The record tests are `RecordB20R180` in `tests_genesis/test_repair_bench_2_study.py`, drafted before the run,
  dry-run on the rehearsal, appended unchanged. They pass (10 tests with the design tests, 54 s): the digests; the
  verdicts and tables recomputed; every promoted component source verified again (version 2: the resource check and
  rollback) on a rebuilt job interrupted at the same operation; the 18 controls.

## Result

**MILESTONE_DEMONSTRATED.** Isolation (measured) and the 18 controls held; no promotion outside a component. The loop
(version 2) repaired 12 of the 36 held-out obstacles end to end (T1, T2, P3 and P4, each in all three jobs): verified
with the resource check, promoted, resumed, retained. P3 (a heap that sifts up instead of down after a pop) was
repaired by the loop alone, in all three jobs.

**The comparison: no difference shown against any arm.** Repaired, of 36, at 300 candidate evaluations each:

| Arm | Repaired | False repairs (caught) | CPU s (all parties) | Repaired per CPU s |
|---|---|---|---|---|
| loop (version 2) | 12 | 3 | 87 | 0.14 |
| loop_v1 (B20_R178's, frozen) | 10 | 2 | 488 | 0.02 |
| nolocal | 9 | 2 | 91 | 0.10 |
| random | 11 | 2 | 3,101 | 0.004 |
| enum | 8 | 1 | 67 | 0.12 |
| retrieval (the development vault) | 15 | 0 | 73 | 0.21 |

Sign tests on the discordant obstacles: loop_v1 7-5 (p 0.77), nolocal 4-1 (p 0.38), random 4-3 (p 1.0), enum 6-2
(p 0.29), retrieval 3-6 (p 0.51): NO_DIFFERENCE_SHOWN throughout. Against B20_R178 (where every unfocused searcher beat
the loop), the repaired loop no longer loses; on these larger components it is ahead of every unfocused searcher by a
few obstacles, not significantly. Retrieval, which tries only the operator kinds that repaired development defects,
repaired the most and proposed no false repair.

**Reuse: REUSE_NOT_SHOWN.** With the vault grown by the seed-1 repairs, retrieval repaired 11 of the 24 seed-2/3 jobs
against 10 with the development vault (2-1). Where both found a passing candidate, the grown vault found it after 19.5
evaluations on average against 97.6 (8 jobs): the retained hunk of the same defect was tried first.

**What no arm reached.** Five of the twelve defects were repaired by no arm in any job (T3, T4, P1, D3, D4), and D2 only
by loop_v1 (twice):
- T3 (a deadline stored as the bare term, without the clock), T4 (the expiry pass no longer called), P1 (a swap that
  updates the position of one side only), D3 and D4 (an undo that forgets the history, a history index off by one,
  both corrupting saved state): none of the operators produces the missing statement or term, and none has a sibling to
  transplant it from. The resume rollback was therefore never exercised (rolled back: 0 in every arm).
- D1 (a cached total not invalidated) drew three false repairs from the loop, all caught by the verifier.

## What this licenses, and what it does not

- **Demonstrated (testbed only):** the milestone again, now with the resource check in the verifier; the version-2
  loop does not lose to unfocused search on larger components.
- **Not shown:** that diagnosis-led search beats unfocused search; reuse beyond the verbatim recurrence; repair of a
  defect that needs a statement the component does not contain elsewhere.
- **What next (B20_R181, being prepared):** operators for that class, each a structural principle (symmetry
  completion, vestigial calls, dimensional offsets), written after reading this run's interim rows and episodes,
  tested on twelve new held-out defects in three new components; candidates ordered by the posterior first; common
  diagnosis trials across the diagnosing arms.
