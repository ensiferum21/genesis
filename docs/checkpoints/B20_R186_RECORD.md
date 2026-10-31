# B20_R186 record (SR-2c'): on a fresh draw of 36 random mutants, the inventor's derived transformations again reached what its lifted ones did not, decisively (SPACE_INVENTED; P2 INVENTOR_IMPROVED, 12-0, p_Holm 0.0015; replicated; DEV)

**Run by:** the builder, on DEV, on the same testbed. It is the replication of B20_R185 (SR-2c) with fresh seeds on a
fresh draw of random mutants; its question is whether B20_R185's narrow P2 (step 6 of
`docs/OMEGA_RULE_INVENTION.md`: the inventor improving how it invents) holds. It licenses claims about this testbed
only.

**Preregistration.** Preregistered at `56b414a` (31 Oct 2026), its digest pinned at `15d6888`. The script is
`scripts/b20r186_space_invention_replica.py`, SHA-256 `3fa647254aadd6317a6f35d08672b71a2253101e467550d89c469a42aeba6097`,
unchanged. The sixth catalogue `src/genesis/repairkernel/defects6.py` (36 mutants drawn by the fifth's rules with seed
20261186, excluding every earlier catalogue's defects; SHA-256
`a4cb0c9976022378c70ce6b4ecf0cab8f1203a7b8c67af4893a6bae20feeca5e`) was sealed at `a2c1fa0` before the
preregistration and is unchanged. It ran from the clean worktree `/home/claude/r186-wt` at `56b414a`.

**This run.** On CPU 0, 31 Oct 2026, 16:40:47-18:19:29 SGT (1 h 38 min 42 s; one slice; `wall_s` 5,922 s).
- **Not alone on CPU 0 for its first 17 min 16 s (a protocol deviation, disclosed).** The command that was to start it
  when the checkpoint's integration shard 2 ended waited for a line in `chain.log` that the checkpoint's failed first
  attempt had already written (`END checkpoint_B20_R184_integration_2/6 rc=1`, 15:02:22), so it started at once, while
  shard 2 of the rebuilt checkpoint was still running (16:26:05-16:58:03). Both ran on CPU 0 until 16:58:03. The study's
  outcomes do not depend on time (budgets are counted in evaluations; no episode came near its 1,500 s timeout: the
  longest took 129 s, and none was killed); its CPU times are inflated for that period. The checkpoint shard passed.
- **CPU 0 idle time:** none before it (it overlapped); 0 s after it (shard 3 started at 18:19:29).
- During the run CPU 1 ran a pre-flight of the integration suite's shards.

**Disclosed.**
- Preregistered after B20_R185's result was read. The sixth catalogue was drawn after it too, by rules fixed in
  advance; the script printed counts only, and the builder saw the operator and component counts, not the entries.
- The code is B20_R185's but for the wire format (the repair of B20R184-PICKLE) and the catalogue's lookup; the
  cycle and the test are textually B20_R185's (checked by the design tests).
- During the run the builder looked only at the number of rows written.

**Evidence and checks.**
- `evidence/space_invention_b20r186/`: `result.json`, `rows.jsonl` (772 episodes), `episodes.jsonl`,
  `isolation.json`, `genesis_g1/`, `genesis_g2/`, `test_vault_g1/`, `test_vault_g2/`, `run.log`.
- The record tests are `RecordB20R186` in `tests_genesis/test_space_invention_replica_study.py`, drafted with the
  script, dry-run on the rehearsal (`evidence/space_invention_b20r186_rehearsal/`), appended unchanged. They check the
  digests and the seeds; recompute the verdict, the generations, the tables, the questions with Holm's adjustment,
  the invented reach and the replication table; check every admitted transformation's admission and that generation
  1's are kept; that the test vaults differ in their transformations only; verify every promoted source again; and
  check the 30 controls. They pass (11 tests with the design tests, 278 s, on CPU 1).

## Result

**SPACE_INVENTED; replicated** (every verdict B20_R185's). Isolation (every catalogue covered) and the 30 controls
held; no promotion outside a component; no probe proposed a false repair.

**The invention cycle (no human step).** As in B20_R185 with other jobs: version 3 left 21 of 57 unsolved, the dream
repaired 11; 16 transformations were lifted and 11 admitted (the same eleven). The inventor derived 55 candidates and
admitted **8** (B20_R185's seven and one more: `g2-transfer:replace:rename-attr`, the transfer of the attribute
renaming lifted from Genesis's own dream of E3 to an in-place edit, admitted by its repair of K4). The deriver's
beliefs: transfer [5, 1], generalisation [4, 1], inverse [2, 1], composition [1, 1].

**The test (36 mutants x 3 jobs = 108 obstacles, 300 evaluations each).**

| Arm | Repaired | By a transformation | False repairs (caught) |
|---|---|---|---|
| loop_v3 (the builder's rules) | 53 | 0 | 1 |
| analogy, generation 1 | 56 | 3 | 2 |
| analogy, generation 2 | **68** | 21 | 2 |
| dream_online (the builder's grammar) | 59 | 0 | 2 |
| enum | 26 | 0 | 6 |

- **P1, generation 1 against version 3: NO_DIFFERENCE_SHOWN** (3-0, p 0.25): V33 (the log's `add` made `discard`) in
  all three jobs, by the transformation lifted from Genesis's dream of N1 (a method partner transplanted from a
  sibling method). Replicates B20_R185's NO_DIFFERENCE_SHOWN.
- **P2, generation 2 against generation 1: INVENTOR_IMPROVED** (12-0, p 0.00049, p_Holm 0.0015). All twelve are four
  mutants in all three jobs, every one repaired by a transformation the inventor derived:
  - V02 (the graph's `self.edges += 1` made `-=`) and V34 (the lease's `self.granted += 1` made `-=`):
    `g2-generalise:replace:any-op`, as for B20_R185's Q12;
  - V15 and V18 (the ledger using `self.balances` where it should use `self.by_acct`, in `history` and in `open`):
    `g2-transfer:replace:rename-attr`, the derived transfer admitted in this run. Wrong-attribute mutants were beyond
    every arm in B20_R185.
  Replicates B20_R185's INVENTOR_IMPROVED, now without a doubtful obstacle and on four mutants instead of two.
- **P3, generation 2 against the builder's grammar: NO_DIFFERENCE_SHOWN** (12-3, p 0.035, p_Holm 0.070): Genesis's
  space repaired V15, V18, V33 and V31 (the calendar's `self.mine` for `self.slot`, which version 3 also repairs and
  the grammar's larger space lost) in all three jobs, the grammar V17 (the memo's deleted `self._seen[key] = v`). The
  direction favours Genesis's space; Holm's adjustment leaves it unshown. Replicates B20_R185's verdict.
- Secondary: generation 2 against version 3, 15-0 (p 6 x 10^-5); against enum, 42-0.
- **The invented reach**: V02, V15, V18, V33 and V34, in all three jobs: 15 obstacles repaired by a transformation
  Genesis invented and by nothing in version 3.
- False repairs: on V01 (the heap, a constant in `_down`), several arms proposed calling `_up` after `_down` or `pop`,
  and enum deleted a statement of V27's `remove`; the verifier rejected all thirteen and nothing was promoted. Eleven
  mutants were beyond every arm.

## What this licenses, and what it does not

- **Demonstrated and replicated (testbed only):** with no human step, Genesis invents repair transformations from its
  own verified repairs, admits them only on other families' verified repairs, and derives new ones from those it has
  admitted (transfer to another edit, generalisation to a family of partners, inverse), admitted the same way; on two
  independent draws of random mutants nobody chose, the derived generation repaired mutants its lifted generation did
  not (B20_R185 7-0, p_Holm 0.047; B20_R186 12-0, p_Holm 0.0015), among them wrong-attribute mutants nothing had
  reached. It equalled or (not significantly) exceeded the builder's grammar. This is step 6 of the vision shown on
  this testbed: the way Genesis invents its repairs improved, and the improvement made it more capable on problems it
  had not seen.
- **Not shown:** that generation 1's lifted transformations alone beat the builder's rules (P1, twice not
  significant); that Genesis's space beats the builder's grammar (P3, twice not after Holm); a composition ever being
  admitted; a third generation; anything beyond this testbed's fifteen small components. The substitution language,
  the edits and the derivation operators are the builder's; the transformations, their admission and their order are
  Genesis's.
