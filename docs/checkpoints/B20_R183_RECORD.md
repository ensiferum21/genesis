# B20_R183 record (SR-2b): with fresh seeds Genesis invented and admitted the same rule; its library again added nothing; the grammar's lead over it did not replicate, and the learned grammar order did not help (RULES_INVENTED; replicated: no; inventor NO_DIFFERENCE_SHOWN; DEV)

**Run by:** the builder, on DEV, on the same testbed as B20_R182. It asks whether B20_R182's findings hold under other
jobs and searches, and tests step 6 of `docs/OMEGA_RULE_INVENTION.md` (the inventor improving how it invents). It
licenses claims about this testbed only.

**Preregistration.** Preregistered at `229ca10` (31 Oct 2026), its digest pinned at `4e8dde2`. The script is
`scripts/b20r183_rule_invention_replica.py`, SHA-256 `3ca48cda3d542bd090084e4afa3fd28ae603844fb248d3f02b51498709c65728`,
unchanged; the catalogue is B20_R182's fourth (SHA-256 `7143763d…c14e0`), unchanged. It ran from the clean worktree
`/home/claude/r183-wt` at `229ca10`.

**This run.** Alone on CPU 0, 31 Oct 2026, 12:41:16-13:10:41 SGT (29 min 25 s; `wall_s` 1,765 s).
- **CPU 0 idle time (disclosed):** 12 min 3 s before it (from the stopped checkpoint attempt, 12:29:13, while it was
  prepared and rehearsed); **1 h 7 min 2 s after it** (13:10:41-14:17:43): the session was not running when it ended,
  and the next job (the checkpoint B20_R184) started only when the session resumed.
- During the run CPU 1 was used for other work (B20_R182's record tests, the matrix sharding, the isolation repair,
  the fifth catalogue's generation and SR-2c's development and rehearsal).

**Disclosed.**
- Preregistered after B20_R182's result was read; the fourth catalogue's 12 defects had been seen by B20_R182, so this
  is a check of robustness and of step 6, not a test on new defects.
- The builder looked once at the interim rows (12:46), at the counts of the detection phase's outcomes only.
- The isolation probe set is B20_R182's. The defect B20R183-CATALOGUES (found during this run, repaired at `32b412b`)
  applies: the trial executor could read three of the four catalogues; the research plane, which proposes every
  patch, could read none, and the guard refuses every way a candidate could read a file.

**Evidence and checks.**
- `evidence/rule_invention_b20r183/`: `result.json`, `rows.jsonl` (319 episodes), `episodes.jsonl`, `isolation.json`,
  `genesis_library/`, `run.log`.
- The record tests are `RecordB20R183` in `tests_genesis/test_rule_invention_replica_study.py`, drafted with the
  script, dry-run on the rehearsal (`evidence/rule_invention_b20r183_rehearsal/`), appended unchanged. They check the
  digests and the seeds; recompute the verdict, the invention summary, the per-arm table, the comparisons, the step-6
  comparison and the replication table from the rows, the isolation report and the frozen library; check every
  admitted rule's admission; verify every promoted source again; and check the 30 controls. They pass (11 tests
  with the design tests, 283 s, on CPU 1).

## Result

**RULES_INVENTED**, by the preregistered rule; isolation (as probed) and the 30 controls held; no promotion outside a
component.

**The invention cycle (no human step; 769 CPU s).** Version 3 left 19 of the 45 development defects unsolved (4 of
them false repairs, caught by the verifier: R2, W1, T4, D1). The dream repaired 7 (B20_R182's six and T4); 19 rules were
lifted; **the same single rule was admitted**: symmetry completion, lifted from Genesis's own repair of N2 at the level
that abstracts names, attributes and the operation, verified on N1. The inventor's posteriors moved exactly as in
B20_R182.

**The test (36 obstacles, 300 evaluations each).**

| Arm | Repaired | False repairs (caught) | B20_R182 |
|---|---|---|---|
| loop (version 4) | 22 | 0 | 21 |
| loop_v3 | 22 | 0 | 21 |
| dream_online (the grammar, fixed order) | 28 | 1 | 30 |
| dream (the grammar, the inventor's learned order) | 29 | 1 | not run |
| enum | 18 | 0 | 18 |

**Replication** (`replicated`: false):
- the verdict, RULES_INVENTED: replicated (the same rule);
- version 4 against version 3, NO_DIFFERENCE_SHOWN (0-0, the same 22 obstacles; the rule matched no held-out defect):
  replicated;
- **the grammar's lead over version 4 did not replicate**: 11-5 (p 0.21), NO_DIFFERENCE_SHOWN, against B20_R182's
  11-2 (p 0.022). The direction held; the grammar again reached X4, C1, B1 and B3, which version 4 never did, and
  again lost X3, now in all three jobs, and lost X2 (which version 3 reached once) and one C3;
- enum, NO_DIFFERENCE_SHOWN (4-0): replicated.

**Step 6 (the learned grammar order against the fixed one): NO_DIFFERENCE_SHOWN.** 'dream' repaired one obstacle
'dream_online' did not (1-0, p 1); over the 28 both repaired, it found its first passing candidate earlier in 2, later
in 6, at the same evaluation in 20 (p 0.29; mean 51.9 against 53.4 evaluations). The inventor's posteriors over
productions, learned from seven verified dreams, did not make it invent faster.

**False repairs.** Unlike B20_R181's and B20_R182's test phases, two arms proposed a patch the kernel's verifier
rejected: both grammar arms, on C3 in the job of seed 8, called the calendar's `_drop_past()` at the start of
`snapshot` (the builder's vestigial-call operator, at a wrong place); the verifier caught both, and nothing was
promoted.

## What this licenses, and what it does not

- **Replicated (testbed only):** with no human step, Genesis invents and admits the same general rule (symmetry
  completion) from its own repair under other jobs and searches; the rule is not used on these held-out defects, and
  the library adds nothing to version 3.
- **Not replicated:** that searching the builder's grammar directly beats Genesis's library (B20_R182's p 0.022 was
  not significant again; the effect is smaller than it looked, and the grammar's larger space costs obstacles version
  3 reaches).
- **Not shown:** step 6. The inventor's learned order over its productions did not improve how fast it invents.
- **Next (preregistered separately):** SR-2c (B20_R185), in which Genesis grows the repair space itself
  (transformations lifted from its verified repairs and derived from one another) and is tested on random mutants
  nobody chose.
