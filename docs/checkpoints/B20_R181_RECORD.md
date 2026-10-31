# B20_R181 record (SR-1a3): one invented operator reached a defect nothing else reached, in every job; the loop beat random patches but not its predecessor (MILESTONE_DEMONSTRATED; LOOP_BEATS_RANDOM; NO_DIFFERENCE_SHOWN against loop_v2, nolocal, enum; REUSE_NOT_SHOWN; DEV)

**Run by:** the builder, on DEV, on the state-management testbed with three new components (a lease table with a
clock, an undirected graph, a two-way map; `docs/OMEGA_SELF_REPAIR.md` §7). It licenses claims about this testbed
only. It is the first test of the Foundry directive's item 4 (capability invention, against a strong predecessor at
matched compute).

**Preregistration.** Preregistered at `0e0ecc7` (31 Oct 2026); its digest pinned at `7d9c712`. The script is
`scripts/b20r181_repair_bench_3.py`, SHA-256 `b0417fc5e7e7a9748a143eaa76cb6515fd9506a1831fe2446ae0c3b78cbb6dbb`,
unchanged. The third sealed catalogue `src/genesis/repairkernel/defects3.py` has SHA-256
`ce4506573532f2b5d314a4fb96b4edd66decfd64254532ed1862afcd95e40254`, unchanged. It ran from the clean clone
`/home/claude/r181-run` at `0e0ecc7`.

**This run.** On CPU 1 (disclosed in the preregistration; CPU 0 ran PT-2), on 31 Oct 2026 from 10:15:32 SGT; **a
container restart (about 10:45) stopped it** after 266 of its 321 episodes, in phase 4(a). The rows already written
and the growing vault were consistent (11 repairs retained, 11 entries added); the episode in progress had retained
nothing. It was resumed by the same command at 10:49:28 (the script skips recorded rows) and finished at 10:54:07.
`result.json`'s `wall_s` covers the resumed part only. Nothing else ran on CPU 1.

**Disclosed.**
- The three operators were written after reading B20_R180's interim rows and three of its episodes; the third
  catalogue was written after the operators, by their author, with four defects in their classes. One of those four
  (E1, a renewal that stores the bare term) turned out to have a homologue (the same statement in `acquire`), so a
  transplant repairs it and it does not test the offset operator.
- During the run the builder looked at its interim rows once (10:39), which changed nothing.

**Evidence and checks.**
- `evidence/repair_bench_3_b20r181/`: `result.json`, `rows.jsonl` (321 episodes), `episodes.jsonl`,
  `isolation.json`, the three vaults, `run.log` (both parts).
- The record tests are `RecordB20R181` in `tests_genesis/test_repair_bench_3_study.py`, drafted before the run,
  dry-run on the rehearsal, appended unchanged. They pass (10 tests with the design tests, 86 s): the digests; the
  verdicts and tables recomputed (the invention reach and the operator counts included); every promoted component
  source verified again on a rebuilt job; the 24 controls.

## Result

**MILESTONE_DEMONSTRATED.** Isolation (measured) and the 24 controls held; no promotion outside a component; **no arm
proposed a false repair**. The loop (version 3) repaired 12 of the 36 held-out obstacles end to end (E1, E2, E4 and N3,
each in all three jobs).

**The comparison.** Repaired, of 36, at 300 candidate evaluations each:

| Arm | Repaired | In the operators' classes (12) | Elsewhere (24) | CPU s (all parties) |
|---|---|---|---|---|
| loop (version 3) | 12 | 6 | 6 | 523 |
| loop_v2 (B20_R180's, frozen) | 9 | 3 | 6 | 519 |
| nolocal | 9 | 3 | 6 | 151 |
| random | 6 | 1 | 5 | 284 |
| enum | 9 | 3 | 6 | 36 |

Sign tests on the discordant obstacles: random 6-0 (p 0.031, **LOOP_BEATS_RANDOM**); loop_v2, nolocal and enum 3-0
each (p 0.25, NO_DIFFERENCE_SHOWN). The three obstacles that separate the loop from everything else are E2's, all
three jobs: **the vestigial-call operator** restored the lost `self._sweep()` at the end of `advance`. No other arm
reached E2 in any job. Elsewhere (the 24 other obstacles) every arm but random repaired the same 6: the inventions cost
no reach.

**What the operators did not reach.**
- **Symmetry completion missed both of its defects** (N1, N2: the graph's link and unlink update one side only). The
  operator looks for two arguments that index the same container; the defect had removed the only place where the
  second argument did, so the symmetry was no longer visible. A broader rule (the mirror of a statement that names
  both arguments asymmetrically, `self.adj[u].add(v)` to `self.adj[v].add(u)`) would have reached them; it was not
  preregistered and was not run.
- E3 (a release that forgets the lease's end), N4 (`-=` turned into `+=`: no operator flips an augmented assignment)
  and K1-K4 (the two-way map's missing or wrong updates) were beyond every arm.

**Reuse: REUSE_NOT_SHOWN** (8 of 24 seed-2/3 jobs with the grown vault, 6 with the development vault; 2-0). Where both
found a passing candidate, the grown vault found it after 2.0 evaluations against 44.1.

## What this licenses, and what it does not

- **Demonstrated (testbed only):** an operator invented from a structural principle (a private method nothing calls)
  repaired, in a component and at a site it was not developed on, a defect no earlier operator and no searcher could
  reach, in all three jobs, verified independently; the inventions cost no reach elsewhere; no false repair in any arm.
- **Not claimed:** that Genesis invented these operators. The builder wrote them, from three structural principles,
  after reading where B20_R180's arms failed; what is tested is whether such operators reach held-out defects. Genesis
  inventing operators of its own is not built.
- **Not shown:** that the loop beats its predecessor overall (3-0 is not significant over 36 obstacles); that
  symmetry completion or dimensional offsets work beyond the defects they came from (neither was tested by a defect it
  could reach); transfer of repair knowledge to unfamiliar defects.
- **Next (proposed, not done):** the broader mirror rule; an operator that flips augmented assignments; operators for
  missing paired dictionary updates (E3, K1, K2); then a new held-out catalogue, with each invention-class defect
  checked in advance for an unintended homologue.
