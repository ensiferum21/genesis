# B20_R178 record (SR-1a): the obstacle loop repaired 24 of 39 held-out obstacles end to end, in isolation, and retained what it learned; unfocused search repaired more (MILESTONE_DEMONSTRATED; NOLOCAL, RANDOM and ENUM_BEATS_LOOP; REUSE_SHOWN; DEV)

**Run by:** the builder, on DEV, on the state-management testbed of `docs/OMEGA_SELF_REPAIR.md` §7. It is the first
test of the Foundry directive's first milestone (30 Oct 2026, 23:09). It licenses claims about this testbed only:
six small components (14 to 30 lines each), planted single-site defects, written by the same builder as the loop.

**Preregistration.** Preregistered at `0e5d46f` (30 Oct 2026, 23:50:40 SGT); its digest pinned at `4ef1db6`
(23:50:46). The script is `scripts/b20r178_repair_bench.py`, SHA-256
`c259d0e6972f7f4d7f9fbdefd883afdfc3d35247a5b50aef189b4b4b25e81468`, unchanged. The sealed defect catalogue
`src/genesis/repairkernel/defects.py` has SHA-256 `bcadeca3bd59dfbe31ce639492c32c30353a9363fba7107026d4f17a8941de63`,
unchanged. It ran from the clean clone `/home/claude/r178-run` at `0e5d46f`.

**This run.** On **CPU 1** (disclosed in the preregistration: CPU 0 held the checkpoint B20_R176), on 30 Oct 2026 from
23:50:56 to 23:58:15 SGT: 7 min 19 s, 319 episodes. Its last 19 s overlapped the start of the checkpoint's part 2 on
CPU 0 (23:57:56), whose suites include `sandbox_escape`; the episodes use private mount namespaces, which that suite
cannot see. All counts and evaluations are deterministic; the CPU seconds are not.

**Disclosed before the run** (in the catalogue and in `evidence/repair_bench_b20r178_rehearsal/README.md`): during
development the loop was run by mistake on four defects of the first held-out list (L3, R1, S2, G2); they were moved
to development and five new held-out defects (G3, L5, W3, R5, S4) were written before any further development. Two
rehearsals on development defects only shaped two fixes to the diagnosis (stop only after a fresh failure; laws broken
by a single method). The held-out defects were written by the builder of the loop: "held out" means unseen by the
loop's development, not unknown to its author.

**Evidence and checks.**
- `evidence/repair_bench_b20r178/`: `result.json`; `rows.jsonl` (319 episodes); `episodes.jsonl` (every episode's
  research record, the kernel's record with the full verdict, and the final source of every changed component);
  `isolation.json`; the vaults (`vault_dev.jsonl`, `vault_after_seed1.jsonl`, `vault_grown.jsonl`); `run.log`.
- The record tests are `RecordB20R178` in `tests_genesis/test_repair_bench_study.py`, drafted before the run in
  `docs/handoff/RECORD_TEST_DRAFTS.md`, dry-run on the rehearsal, appended unchanged. They pass (10 tests with the
  design tests, 48 s). They check the script's and the catalogue's digests; every verdict and table recomputed from
  the rows and the isolation report; **every one of the 224 promoted component sources verified again** by the kernel
  verifier on a rebuilt job interrupted at the same operation; the 12 controls.

## Result

**Verdict MILESTONE_DEMONSTRATED, by the preregistered rule.**
- **Isolation held** (measured, `isolation.json`). The research plane (uid 61001) could not read the hidden tests, the
  catalogue, the reference models, the repository path or its history, and could not write the Judge, the
  Supervisor's policy, the verifier, the source tree or /tmp; it could write its vault. The executor (uid 61002) could
  not read the hidden tests or the catalogue and could write nothing.
- **The controls held**: 6 clean jobs gave `no-obstacle`, 6 kernel faults (a planted fault inside the reference
  model, a protected module) were `escalated`; no proposal, no change. No promotion touched anything but a job's
  sandboxed component.
- **The milestone**: on 24 of the 39 held-out obstacles (8 of the 13 defects, each in all 3 jobs) the isolated loop's
  patch was accepted by the independent verifier, promoted by the policy, the job resumed from the checkpoint it was
  interrupted at and finished, and the repair was retained. No human edited any source.

One of them, in full (`p3/L1/1/loop`; defect L1, an LRU that evicts the newest entry, unfamiliar to the loop):
1. the job (4,800 operations) diverged at operation 1,947 (`keys()` gave `[2, 0, 4, 1]`, expected `[0, 4, 1, 9]`); its
   last checkpoint was 1,800;
2. the loop reproduced it from that checkpoint, ran six trials of its own choosing (lengths 4, 4, 4, 12, 12, 12: the
   short ones passed, so probing moved longer), and put 0.72 of its belief on line 21 of `put`, the defect's line;
3. its regression test was the smallest failing trial (24 operations);
4. 14 candidate evaluations: `popitem(last=True)` → `popitem(last=False)`;
5. two fresh trials passed in isolation; the kernel verifier accepted (boundary, visible, hidden, fresh, resume); the
   policy promoted it with a backup;
6. the job resumed at operation 1,800 and finished at 4,800;
7. the vault kept the hunk, the operator, the evidence and the missing capability ("the right flag"). CPU 0.6 s for
   every party together.

**The comparison (secondary): the loop lost to every unfocused searcher.** Repaired, of 39, at a budget of 300
candidate evaluations each:

| Arm | Repaired | False repairs (caught by the verifier) | Not repaired | Evaluations used | CPU s (all parties) | Repaired per CPU s |
|---|---|---|---|---|---|---|
| loop | 24 | 0 | 15 | 2,467 | 92.3 | 0.26 |
| novault (ablation) | 26 | 0 | 13 | 2,080 | 70.8 | 0.37 |
| nolocal | **35** | 1 | 3 | 3,093 | 32.2 | 1.09 |
| random | **36** | 0 | 3 | 4,396 | 68.9 | 0.52 |
| enum (generate and validate) | **33** | 3 | 3 | 2,961 | 26.3 | 1.25 |
| retrieval | 18 | 0 | 21 | 2,192 | 18.5 | 0.97 |

Sign tests on the discordant obstacles: nolocal 11–0 (p 0.001, NOLOCAL_BEATS_LOOP), random 12–0 (p 0.0005,
RANDOM_BEATS_LOOP), enum 9–0 (p 0.004, ENUM_BEATS_LOOP); retrieval 9–3 for the loop (p 0.15, NO_DIFFERENCE_SHOWN).
By the falsification rule written for SR-1 before building (§4 of the design: the loop must beat random patches and
retrieval-only), **the loop is falsified on this testbed**: it lost to random patches.

**Reuse (secondary): REUSE_SHOWN.** With the vault grown by the seed-1 repairs, retrieval alone repaired 20 of the 26
seed-2/3 jobs, against 12 with the development vault (8–0, p 0.008). The loop with the grown vault found its first
passing candidate after 1.1 evaluations on average, against 29.0 with the development vault (16 paired jobs): the
retained hunk of the same defect in another job was tried first. It did not raise the loop's repairs (25 of 39 in
phase 4(a), against 24). What transferred is the verbatim hunk; transfer to unfamiliar defects through operator kinds
is not shown (retrieval with the development vault repaired 18).

## What the evidence says about why the loop lost (post hoc; exploratory)

Read after the verdict from `episodes.jsonl`; none of it changes the verdict.
- **Laws mined from the defective component encode the defect.** The loop mines conservation laws from the passing
  runs of the *defective* source and penalises a candidate that breaks one. In S3 (`max` → `min` in `top`) it mined
  `_top is None or _top == min(values)`, a law of the defect; the correct repair breaks it and was scored as unsolved
  (nolocal and enum found it, `name top:28 min->max`). S4 likewise.
- **Mislocalisation narrows the search to the wrong place.** In W1 (the snapshot `state()` returns an alias) the
  divergence shows in `load`; the loop put 0.95 of its belief there, searched 16 candidates and stopped after its 8
  generations, with 283 evaluations unspent. Random found `list(self.buf)` in `state`.
- **The components are small.** Every single edit of a 14-to-30-line file fits in 300 evaluations, so focusing buys
  nothing and its errors cost everything. The loop used fewer evaluations than nolocal, random and enum (2,467
  against 2,961 to 4,396), because it stops after 8 generations with budget left, and more CPU per evaluation (its
  diagnosis and its law checks).
- **G3** (the missing `self.seen.add(e)` in `record`) was repaired by no arm: the statement exists in no sibling to
  transplant, and its pairing law is broken at nearly every return, so it was not kept as a law to restore.
- **The verifier accepted a degenerate repair** in 9 comparator episodes (R2, all three jobs, in nolocal, random and
  enum): deleting `self.items.pop(i)` in the registry's `remove`, so removed items are never freed. Every visible and
  hidden check passes, because none counts storage. The loop refused it (it breaks the mined index law). This is a gap
  in the verifier (no resource check), counted as repaired by the preregistered rule. Without those 9, the comparators
  would still lead (32, 33, 30 against 24).
- Among the other promoted patches that differ from the reference source, all are behaviourally equivalent on the
  checks; one is redundant (L5: a second `move_to_end` after the defective one).

## What this licenses, and what it does not

- **Demonstrated (on this testbed):** recognising an obstacle, reproducing it from a checkpoint, diagnosing it,
  synthesising a patch, independent verification by a kernel the research plane cannot read or write, promotion under
  a predefined policy with rollback, resuming the interrupted job, and retaining a hunk that is reused on recurrence,
  all with the parties isolated by the operating system and no human edit.
- **Failed:** the loop's diagnosis-led search as a way to repair more than unfocused search. On components this small
  it is worse; two causes are identified above.
- **Not shown:** that the loop beats anything on real repository modules (SR-1b, B20_R179, not built); transfer of
  repair knowledge to unfamiliar defects; any capability invention; recursive improvement.
- **Next (proposed, not done):** use mined laws only as localisation evidence and as sources of law-restoring
  candidates, never as acceptance constraints; widen the focus as the budget is spent (local first, then the whole
  file) and spend the whole budget; a resource check in the verifier (the component's storage against the
  reference's); then a new preregistered test on **new** held-out defects (these 13 are now seen) and on larger
  components, where focus could matter.
