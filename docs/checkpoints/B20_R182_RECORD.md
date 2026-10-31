# B20_R182 record (SR-2a): with no human step, Genesis invented a repair rule from its own repair and admitted it on another family's defect; on the held-out defects its library added nothing, and searching the grammar directly beat it (RULES_INVENTED; LOOP_V4 = LOOP_V3; DREAM_ONLINE_BEATS_LOOP_V4; DEV)

**Run by:** the builder, on DEV, on the state-management testbed (15 components; `docs/OMEGA_SELF_REPAIR.md` §7). It
is the first test of Daniel's requirement of 31 Oct 2026, 11:26 (`docs/OMEGA_RULE_INVENTION.md`): Genesis inventing
its own repair rules. It licenses claims about this testbed only.

**Preregistration.** Preregistered at `884713e` (31 Oct 2026); its digest pinned at `63b9ade`. The script is
`scripts/b20r182_rule_invention.py`, SHA-256 `72275f94e3e4f034d367f5bcb49d7baeceb402467ab10b4743480fb6aeff7572`,
unchanged. The fourth sealed catalogue `src/genesis/repairkernel/defects4.py` (SHA-256
`7143763d0847f46e552a1e2d149529ae1e772d8b3f1200d699d4ec4bc40c14e0`) was committed at `b30342e`, before any of the
inventor's code existed, and is unchanged. It ran from the clean worktree `/home/claude/r182-wt` at `884713e`.

**This run.** Alone on CPU 0, 31 Oct 2026, 11:52:54-12:25:47 SGT (32 min 53 s; `result.json`'s `wall_s` 1,972 s).
- **CPU 0 idle time (disclosed):** 4 min 32 s before it (after PT-2 ended at 11:48:22); after it, 2 min 32 s to the
  start of the checkpoint attempt (12:28:19), which was stopped at 12:29:13 because the integration suite has outgrown
  the matrix's 7,000 s timeout and the 2 h job limit; then **12 min 3 s** idle while B20_R183 was prepared and
  rehearsed (it started at 12:41:16).

**Disclosed.**
- The builder wrote the grammar of the dream, the lifting lattice and the admission rule after reading where
  B20_R181's arms failed, and looked at what the grammar reaches on the 45 development defects while writing it (§3 of
  the vision document lists what it reached). The fourth catalogue was written and sealed before that code, by the same
  author, who knew which classes B20_R181 had missed (its record's "Next": augmented-assignment flips, paired
  dictionary updates). Several held-out defects are in classes the grammar has productions for (missing increments,
  a reverse index, a missing deletion, an augmented sign). What the grammar reaches on them is the builder's, not
  Genesis's.
- Two rehearsals on development defects only (`evidence/rule_invention_b20r182_rehearsal/`); the first ran an earlier
  version with a second generation that only re-solved the same jobs from their retained hunks, so that generation was
  removed before preregistration.
- During the run the builder did not look at its rows.

**Evidence and checks.**
- `evidence/rule_invention_b20r182/`: `result.json`, `rows.jsonl` (280 episodes), `episodes.jsonl` (each episode's
  research and kernel records and every promoted source), `isolation.json`, `genesis_library/` (the library and the
  inventor as frozen before the test: `rules.jsonl`, `inventor.json`, `vault.jsonl`), `run.log`.
- The record tests are `RecordB20R182` in `tests_genesis/test_rule_invention_study.py`, drafted with the script,
  dry-run on the rehearsal, appended unchanged. They check the digests; recompute the verdict, the invention summary,
  the per-arm table and the comparisons from the rows, the isolation report and the frozen library; check that every
  admitted rule was admitted by a verified repair of another family, in a probe row that names it; verify every
  promoted component source again on a rebuilt job; and check the 30 controls. They pass (10 tests with the design
  tests, 152 s, on CPU 1).

## Result

**RULES_INVENTED**, by the preregistered rule. Isolation (measured) and the 30 controls held; no promotion outside a
component.

**The invention cycle (no human step; 829 CPU s).**
1. **Detect.** Version 3 (the builder's rules) ran on the 45 development defects (seed-1 jobs) and left **16
   unsolved**. Three of the 16 were *false repairs*: it proposed a patch that passed what the loop could see and the
   kernel's verifier rejected (R2, W1, D1). The others ended with nothing that passed.
2. **Diagnose and invent (the dream).** On each of the 16, a fresh job and 1,000 evaluations over the grammar built
   from the component's own vocabulary. **6 were repaired and verified** (E3, N1, N2, N4, K1, K2; first passing
   candidate at evaluations 227, 167, 59, 112, 70, 19). The dream re-proposed false repairs on R2, W1 and D1, which the
   verifier rejected again; G3, P1, D2-D4, K3 and K4 stayed unsolved.
3. **Lift.** The 6 verified repairs were lifted into **17 candidate rules** across the lattice (concrete, names,
   names+attrs, names+attrs+ops, names+attrs+ops+consts, free).
4. **Verify by transfer.** Every development defect was probed (seed-2 jobs, 120 evaluations) with the candidate rules
   of *other* families only; 18 probes had candidates. **One rule was admitted**: lifted from N2's repair (the graph's
   `unlink`, which forgot `self.adj[v].discard(u)`) at the level that abstracts names, attributes and the operation,
   it says *after `self.A[x].m(y)`, add `self.A[y].m(x)`*: **symmetry completion**. It repaired N1 (the graph's
   `link`, a different defect), verified by the kernel. This is the rule B20_R181's builder-written operator missed on
   both N1 and N2, because the defect had erased the evidence that operator looked for; Genesis's version was invented
   from its own verified repair and is general (any container, any method). No probe proposed a false repair.
5. **Learn.** The inventor's posteriors: the level names+attrs+ops [2, 1] (the others at their prior); grammar
   productions delete [3, 1], container-call [3, 1], flip [2, 1], assign [2, 1].

**The test (12 held-out defects x 3 jobs = 36 obstacles, 300 evaluations each, the library frozen).**

| Arm | Repaired | False repairs | By an invented rule | Mean evaluations to the first passing candidate | CPU s |
|---|---|---|---|---|---|
| loop (version 4: version 3 + Genesis's library) | 21 | 0 | 0 | 32.6 | 438 |
| loop_v3 (the builder's rules) | 21 | 0 | 0 | 32.1 | 478 |
| dream_online (version 3 + the grammar, searched at test time) | **30** | 0 | 0 | 51.8 | 115 |
| enum | 18 | 0 | 0 | 119.7 | 63 |

Sign tests on the discordant obstacles (version 4 against each): loop_v3 0-0 (NO_DIFFERENCE_SHOWN); dream_online 2-11
(p 0.022, **DREAM_ONLINE_BEATS_LOOP_V4**); enum 3-0 (p 0.25, NO_DIFFERENCE_SHOWN). The milestone held on 21 obstacles
(X1, X3, C2, C3, C4, B2, B4, each in all three jobs).
- **The library added nothing.** Versions 4 and 3 repaired the same 21 obstacles. The admitted rule matched nothing
  it could repair: no held-out defect is in the mirror class.
- **The grammar searched directly reached 11 obstacles version 4 did not** (X4 twice by flipping `+=` to `-=`; C1 by
  `self.mine.setdefault(who, set()).add(s)`; B1 by `self.size += k`; B3 by deleting the emptied entry; each in all
  three jobs), at a quarter of the CPU. **It cost reach too**: it missed X3 in two of three jobs (a sign in an
  expression, which version 3's arithmetic mutation finds early), because the larger space pushed that candidate past
  the budget. No arm reached X2.

## What this licenses, and what it does not

- **Demonstrated (testbed only):** with no human step between the first job and the frozen library, Genesis found the
  obstacles its rules could not solve, searched a larger space for repairs the kernel verified, generalised one of its
  own repairs into a rule at a level it chose by measurement, and admitted that rule only when it repaired, verified
  independently, a defect of another family. The rule (symmetry completion) is one the builder had tried to write and
  had written too narrowly.
- **Not shown:** that an invented rule helps on unseen problems (it was used 0 times in the test); that Genesis's
  library makes the loop more capable (4 = 3); step 6, the inventor improving how it invents (its learned posteriors
  were not used by any test arm; B20_R183 tests them).
- **Found against the plan:** at this scale the product that helps is the *space* (the grammar, which the builder
  wrote), not the rules lifted from it. The grammar holds the held-out repairs the rules lacked, and searching it
  online is cheap; a learned rule pays only when the space it compresses is too big to search, which this testbed's
  is not. What the grammar reaches is the builder's capability, not Genesis's.
- **Gaps in the mechanism found by the record:** step 1 is coarser than the vision says. The script sends every
  unsolved obstacle to the dream, false repairs included (the vision says only an exhausted repertoire should go), and
  the loop's record does not tell an exhausted repertoire from a spent budget (version 3 always spends its budget:
  after its candidates it mutates). A candidate rule whose patches fail the visible tests is not counted as a failure:
  the library's posteriors learn only from proposals.
