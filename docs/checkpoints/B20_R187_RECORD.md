# B20_R187 record (SR-2d): a third generation did not compound, but Genesis's derived space beat the builder's grammar for the first time, and step 6 held a third time (SPACE_INVENTED; P1 NO_DIFFERENCE_SHOWN; P2 INVENTOR_IMPROVED; P3 GENESIS_SPACE_BEATS_BUILDER_GRAMMAR; DEV)

**Run by:** the builder, on DEV, on the same testbed. It asks whether the inventor's improvement compounds (a third
generation of derived transformations, `docs/OMEGA_RULE_INVENTION.md` §6). It licenses claims about this testbed
only.

**Preregistration.** Preregistered at `0e56949` (31 Oct 2026), its digest pinned at `0509da1`. The script is
`scripts/b20r187_third_generation.py`, SHA-256 `e2f3473716639e77da543098ec3a78a2bed4b647b41468e553d67d931b631f7d`,
unchanged. The seventh catalogue `src/genesis/repairkernel/defects7.py` (36 random mutants, seed 20261187; SHA-256
`9836c54d9be1738def9f04089f45857e35c8e852b0666645a264aa66741c9572`) was sealed at `b82c54a` before any of this code and
is unchanged. It ran from the clean worktree `/home/claude/r187-wt` at `0e56949`.

**This run.** Alone on CPU 0, 31 Oct 2026, in two slices:
- slice 1: 20:41:51-22:31:55, paused by the slice rule (exit 3);
- slice 2: 22:31:57-22:37:37, finished.

That is 1 h 55 min 46 s in all; `wall_s` covers slice 2 only.
- **CPU 0 idle time (disclosed):** 0 s before it (the checkpoint B20_R184 ended at 20:41:51); 2 s between the slices;
  after it, idle from 22:37:37 while this record was written, with no study preregistered to follow.
- During the run CPU 1 ran a pre-flight and the restore check of the checkpoint, and `wip/b20r187` snapshots were
  pushed every 15 minutes.

**Disclosed.**
- Preregistered after B20_R186's result was read; the seventh catalogue was drawn after it by fixed rules (counts only
  seen).
- Its preregistration commit carried a failing design test of B20_R185 (the loop's probe tuple), repaired at
  `a56289a`; the study's script and the loop were unchanged by the repair.
- **Defect B20R187-ANCESTRY, found while recording:** `analogy.derive` records a derived transformation's
  `derived_from_families` as its parents' own families. A second-generation parent has none (its family is `None`),
  so third-generation transformations record `''` instead of their ancestral families. The rule "never admitted by a
  family it comes from" was therefore not enforced against grandparents' families in this run. **Checked on the
  evidence: no admission violated it** (each of the eleven third-generation admissions came from a family outside its
  true ancestry). Repaired for future studies (see the commit after this record).
- During the run the builder looked only at the number of rows written.

**Evidence and checks.**
- `evidence/third_generation_b20r187/`: `result.json`, `rows.jsonl` (951 episodes), `episodes.jsonl`,
  `isolation.json`, `genesis_g1/` to `genesis_g3/`, `test_vault_g1/` to `test_vault_g3/`, `run.log`.
- The record tests are `RecordB20R187` in `tests_genesis/test_third_generation_study.py`, drafted with the script,
  dry-run on the rehearsal, appended unchanged. They recompute the verdict, the three generations, the tables, the
  questions and the invented reach; check every admission and that each generation's admissions are kept in the next;
  check that the test vaults differ in their transformations only; verify every promoted source again; and check the
  30 controls. They pass (11 tests with the design tests, 475 s, on CPU 1).

## Result

**SPACE_INVENTED.** Isolation and the 30 controls held; no promotion outside a component.

**The cycle (no human step; 2,365 CPU s).**
- **Generation 1:** 23 of 57 unsolved by version 3; the dream repaired 10; 15 transformations lifted and 11 admitted.
- **Generation 2:** 55 derived and 8 admitted; 4 of the 13 still unsolved defects repaired with generation 1's
  transformations.
- **Generation 3:** 58 derived from the 19 admitted ones, and 11 admitted. **Compositions were admitted for the first
  time** (six, such as `any-op` composed with `rename-attr`), alongside four transfers; a composition derived in
  generation 2 was admitted in generation 3's probes. One third-generation probe proposed a false repair (R2), which
  the verifier caught.
- The deriver's beliefs: transfer [9, 2], composition [8, 1], generalisation [4, 1], inverse [2, 1].

**The test (36 mutants x 3 jobs = 108 obstacles, 300 evaluations each).**

| Arm | Repaired | By a transformation |
|---|---|---|
| loop_v3 (the builder's rules) | 48 | 0 |
| generation 1 | 57 | 9 |
| generation 2 | **77** | 38 |
| generation 3 | 76 | 39 |
| dream_online (the builder's grammar) | 54 | 0 |
| enum | 39 | 0 |

- **P1, generation 3 against generation 2: NO_DIFFERENCE_SHOWN** (3-4). Generation 3 gained Z06 (the ledger's deleted
  `self._apply(acct, amount)`, in all three jobs, by a third-generation transformation) and lost four obstacles of the
  wrong-attribute mutants Z23, Z32 and Z34. Its larger space pushed their candidates past the budget: the same
  trade-off as the grammar's (B20_R182). **The improvement did not compound at this budget.**
- **P2, generation 2 against generation 1: INVENTOR_IMPROVED** (22-2, p_Holm 7 x 10^-5; at the defect level 8-2).
  Step 6 holds for the third time, on a third independent draw.
- **P3, generation 3 against the builder's grammar: GENESIS_SPACE_BEATS_BUILDER_GRAMMAR** (22-0, p_Holm below
  10^-5; at the defect level 10-0). This draw holds 11 wrong-attribute mutants (it is random). The grammar has no
  production for them, and Genesis's derived renamings (transferred and composed from what it lifted from its own
  repairs) repaired six of them in some or all jobs, and Z06 besides. On B20_R185's and R186's draws, with fewer
  such mutants, the same comparison was not significant.
- Secondary: generation 3 against version 3 28-0; against generation 1 23-4 (p 0.0003); against enum 37-0.
- Generation 3's reach by operator: constants 18/18, arithmetic 12/12, comparisons 9/9, calls 3/3, attributes 19/33,
  deletions 15/33. Eight mutants were beyond every arm (Z02, Z11, Z17, Z20, Z21, Z22, Z24, Z36).
- **Invented reach:** 34 obstacles over 12 mutants, repaired by a transformation Genesis invented and by nothing in
  version 3.

## What this licenses, and what it does not

- **Demonstrated (testbed only):**
  - The inventor's derived generation beat its lifted one on three independent random draws (B20_R185, R186, R187).
  - On this draw, Genesis's own space (lifted from its repairs, derived and composed, all admitted by the verifier on
    other families) beat the builder's grammar outright.
  - Compositions can be admitted once there are enough admitted parts to compose.
- **Not shown:** compounding. A third generation added a mutant and lost others at the same budget, net zero. The next
  generation needs either more budget, or a better order over a growing library (the MDL ordering of
  `docs/OMEGA_WEAKNESSES_AND_BLUEPRINT.md` A6 and A7), before more generations can pay.
- **The defect found** (B20R187-ANCESTRY) did not change any admission here, and is repaired for what follows.
