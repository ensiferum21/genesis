# B20_R185 record (SR-2c): the transformations Genesis derived from its own repairs reached random mutants that neither its lifted transformations nor the builder's rules reached (SPACE_INVENTED; P2 INVENTOR_IMPROVED, 7-0, p_Holm 0.047; P1 and P3 NO_DIFFERENCE_SHOWN; DEV)

**Run by:** the builder, on DEV, on the state-management testbed (15 components). It tests §6 of
`docs/OMEGA_RULE_INVENTION.md`: Genesis growing its own repair space, and the way it grows it (step 6), on defects
nobody chose. It licenses claims about this testbed only.

**Preregistration.** Preregistered at `4f399e8` (31 Oct 2026), its digest pinned at `b69d431`. The script is
`scripts/b20r185_space_invention.py`, SHA-256 `efab4a990a50f4bf7307098019f73874750aa86dae94f270415fb87a5e60b8d6`,
unchanged. The fifth catalogue `src/genesis/repairkernel/defects5.py` (24 random mutants, SHA-256
`59c4fc31a2500a4976a007f8f7fd66f548404f379a2600eba395f7eb910e3baa`) was drawn by fixed rules and sealed at `652f36d`,
before any of SR-2c's research code existed, and is unchanged. It ran from the clean worktree `/home/claude/r185-wt` at
`4f399e8`.

**This run.** Alone on CPU 0, 31 Oct 2026, 15:02:37-15:52:26 SGT (49 min 49 s; one slice; `wall_s` 2,987 s).
- **CPU 0 idle time (disclosed):** 15 s before it (the checkpoint attempt's shard 2 failed at 15:02:22); 1 s after it
  (the checkpoint B20_R184's shard 1 started at 15:52:27).
- During the run CPU 1 ran the regression tests of the pickle repair (below) and a pre-flight of the integration suite.

**Disclosed.**
- The builder wrote the substitution language (swap, rename, map, shift, any), the edits (after, before, replace,
  transplant), the lifting rule and the four derivation operators, after looking at what the hand-written defects'
  reference repairs lift to (development data, `tests_genesis/test_repair_analogy.py`). Which transformations exist,
  which are admitted, and which derived ones are tried first are Genesis's: lifted from its own verified repairs,
  derived from its own admitted ones, admitted only by the kernel's verifier on other families.
- The fifth catalogue was drawn by the builder's code with rules fixed in advance; the builder saw the bag component's
  operator output while testing it, and the 24 entries' identifiers, components and operators, not their text, before
  the code; this record's per-defect table is the first look at what they are.
- During the run the builder looked only at the number of rows written.
- Defect B20R184-PICKLE (found during the run by the checkpoint; repaired at `804f479`) applies to the code this ran
  on: the obstacle loop exchanged data by pickle (restricted on the research plane's side). It changes no result; the
  record tests rebuild and verify every promoted repair on the repaired format.
- Two rehearsals on development defects (`evidence/space_invention_b20r185_rehearsal/`).

**Evidence and checks.**
- `evidence/space_invention_b20r185/`: `result.json`, `rows.jsonl` (592 episodes), `episodes.jsonl`,
  `isolation.json`, the frozen libraries `genesis_g1/` and `genesis_g2/`, the test vaults `test_vault_g1/` and
  `test_vault_g2/`, `run.log`.
- The record tests are `RecordB20R185` in `tests_genesis/test_space_invention_study.py`, drafted with the script,
  dry-run on the rehearsal, appended unchanged. They check the digests; recompute the verdict, both generations'
  summaries, the per-arm table, the three questions with Holm's adjustment and the invented reach from the rows, the
  isolation report and the frozen libraries; check that every admitted transformation was admitted by a verified
  repair of a family it (and its parents) did not come from, in a probe row naming it, and that generation 1's
  admissions are kept in generation 2; that the test vaults differ in their transformations only; verify every
  promoted source again; and check the 30 controls. They pass (14 tests with the design tests, 491 s, on CPU 1,
  on the repaired wire format).

## Result

**SPACE_INVENTED**, by the preregistered rule. Isolation (measured, every catalogue covered) and the 30 controls held;
no promotion outside a component; no probe proposed a false repair.

**Generation 1 (no human step).** Version 3 left 21 of the 57 hand-written defects unsolved (4 false repairs, caught);
the dream repaired 11 of them. From the verified repairs Genesis lifted 16 transformations; probes on other families
admitted **11**: four operator partners (`in`/`not in`, `+`/`-`, `>`/`<`, `min`/`max`), a flag (`True`/`False`), a
constant shift, two method partners transplanted from a sibling method (`add`/`discard` both ways), and three attribute
renamings (after, before, and with two names exchanged).

**Generation 2.** Version 3 with generation 1's transformations repaired 2 of the 10 defects still unsolved (G3 and X2,
both by a transformation); nothing new was lifted. The inventor derived **55** candidates from the 11 admitted ones
(inverse, transfer, composition, generalisation) and probes admitted **7**: three transfers, three generalisations,
one inverse; no composition. The deriver's beliefs: transfer [4, 1], generalisation [4, 1], inverse [2, 1],
composition [1, 1].

**The test (24 random mutants x 3 jobs = 72 obstacles, 300 evaluations each).**

| Arm | Repaired | By a transformation | False repairs (caught) | CPU s |
|---|---|---|---|---|
| loop_v3 (the builder's rules) | 27 | 0 | 3 | 426 |
| analogy, generation 1 | 27 | 0 | 3 | 412 |
| analogy, generation 2 | **34** | 6 | 3 | 360 |
| dream_online (the builder's grammar) | 34 | 0 | 3 | 283 |
| enum | 27 | 0 | 3 | 168 |

The three questions (sign tests on the discordant obstacles, Holm over the three):
- **P1, generation 1 against version 3: NO_DIFFERENCE_SHOWN** (1-1, p 1). Genesis's lifted transformations repaired
  no mutant version 3 did not.
- **P2, generation 2 against generation 1: INVENTOR_IMPROVED** (7-0, p 0.016, p_Holm 0.047). Six of the seven are two
  mutants in all three jobs, each repaired by a transformation the inventor *derived*, not lifted from any repair:
  - Q12 (the ledger, `self.balances[acct] += amount` made `-=` in `_apply`): `g2-generalise:replace:any-op`, the
    generalisation of the `in`/`not in` partner lifted from Genesis's repair of M2 to any operator of the same family,
    which put `+=` back;
  - Q22 (the bag, `self.size -= k` deleted from `remove`): `g2-transfer:transplant:map-op-Add-Sub`, the transfer of
    the `+`-for-`-` replacement lifted from its repair of R1 to a transplant: the sibling method `add`'s
    `self.size += k`, with `+=` made `-=`, inserted in `remove` (two lines above where it was).
  The seventh (Q04 in the job of seed 12) was repaired by version 3's own transplant in generation 2's arm and not in
  generation 1's: a different search path, not a transformation.
- **P3, generation 2 against the builder's grammar: NO_DIFFERENCE_SHOWN** (0-0): they repaired the same 34
  obstacles; the grammar reaches Q12 and Q22 with its own productions (the flip of an augmented assignment, a counter
  decrement).
- Secondary: generation 2 against version 3, 7-0 (p 0.016); against enum, 12-5 (p 0.14).
- **The invented reach**: Q12 and Q22, in all three jobs: repaired by a transformation Genesis invented and by
  nothing in version 3.
- False repairs: every arm proposed the same deletion (`delete state:18`) on Q02 (the window, a statement deleted) in
  every job, and the verifier rejected all fifteen; nothing was promoted. Eleven mutants (Q01, Q02, Q06, Q10, Q11,
  Q14, Q16, Q17, Q19, Q21, Q23) were beyond every arm, among them all four attribute mutants.

## What this licenses, and what it does not

- **Demonstrated (testbed only):** with no human step, Genesis lifted repair transformations from its own verified
  repairs, admitted them only on other families' verified repairs, then derived new ones from them by inverse,
  transfer and generalisation, without any new repair, and admitted those the same way; on random mutants nobody
  chose, the derived generation repaired two mutants (in all three jobs each) that its lifted generation and the
  builder's rules did not reach: the preregistered P2 (7-0, p_Holm 0.047). It is the first preregistered positive
  result for step 6 of the vision, the inventor improving how it invents.
- **The limits of that:** the effect rests on two mutants (the three jobs of one mutant are not independent), and the
  seventh discordant obstacle was not a transformation's: without it P2 is 6-0, p 0.031, p_Holm 0.094. The verdict is
  the preregistered rule's, and it is marginal. The derivation operators, the substitution language and the edits are
  the builder's; Genesis chose which transformations to keep.
- **Not shown:** that Genesis's space beats the builder's grammar (it equalled it: the same 34); that its lifted
  transformations alone add anything (P1); a composition ever being admitted; anything on the eleven mutants every arm
  missed, which include every wrong-attribute mutant.
