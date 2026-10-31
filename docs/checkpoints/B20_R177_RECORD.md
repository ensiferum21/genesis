# B20_R177 record (PT-2, the proving test with the gate judged bound by bound): Genesis refuted a bound the predecessor missed three times, with its starting representation; four of the five parts failed (NOT_PROVED_OUT; valid; DEV)

**Run by:** the builder, on DEV. PT-2 is the second attempt at Daniel's proving test (27 Oct 2026, 20:22), its design
the builder's choice after PT-1 ("Do the best", 30 Oct 2026, 20:06). It licenses nothing.

**Preregistration.** Preregistered at `a7303de` (30 Oct 2026); amended twice after two attempts crashed on defects
(B20R177-LIBRARY at `25eadb7`, B20R177-SEEN at `75b5bac`; `docs/BLOCKING_DEFECTS.md`; only the tracebacks were read,
the attempts' files kept unused in `evidence/proving_test_2_b20r177_attempt1/` and `_attempt2/`). The script is
`scripts/b20r177_proving_test_2.py`, SHA-256 `9cc8b4534bce265056e5100762233fc52461aaa991a14e1943b3f6340338ee91`,
unchanged since the second amendment. The third attempt ran from the clean worktree `/home/claude/pt2c-wt` at
`75b5bac`.

**This run.** Alone on CPU 0, in four slices, 31 Oct 2026: 00:11:36-02:05:56 (paused), 08:42:20-10:38:47 (paused),
10:38:53 to a container restart about 10:45 (nothing saved after 10:38:47; the slice's work after that was lost and
redone), and 10:49:12-11:48:22 (done). About 5 h 51 min of computing.
- **CPU 0 idle time (disclosed):** 8 s before it (after the checkpoint B20_R176); **6 h 36 min 24 s** between the
  first and second slices (02:05:56-08:42:20: this session stalled, and the safety-net trigger that fired at 01:30
  reached it only at 08:42); 6 s between the second and third; about 4 min around the container restart; and 4 min
  32 s after the end (B20_R182 started at 11:52:54).

**Evidence and checks.**
- `code_identity` `a8c32e8745ed1f15cd07ce2aa9afddf14c6520b10ea7b7c8f0d29e9d3a9060b4`, recomputed at recording from a
  temporary worktree of `75b5bac`: it matches.
- The evidence is in `evidence/proving_test_2_b20r177/`: `stages.json` (every stage's record with every claimed
  artifact), the engines' saved states, `summary.json`, `run.log` (the slice log).
- The record tests are `RecordB20R177` in `tests_genesis/test_proving_test_2_study.py`, drafted with the script on 30
  Oct 2026, dry-run through the registered path on the design tests' invented families, appended unchanged. They
  check the script's digest; every certificate of every stage again by the kernel (A and C: the rational Rayleigh
  certificate and the second exact check; B: both invariant implementations); A' recomputed from the predecessor's
  runs and the discovery inside it; the families posed again from the sealed seed and the data seeds; the parts, the
  statistics, validity and the verdict recomputed from the saved stages. They pass (2 tests, 968 s), and the whole
  file passes (19 tests, 1,063 s), on CPU 1.

## Result

**Verdict NOT_PROVED_OUT, by the preregistered rule; valid** (budgets spent, pins held, no audit hit). Parts: the gate
held, part 2 passed; parts 1, 3, 4 and 5 failed.
- **The gate held, bound by bound.** The predecessor P0 ran three times on family A (the five Laplacian bounds held out
  of F4 and F5). Its runs certified bounds 21 and 40; 18 and 40; and 21, 24 and 40. **A' = {30}**: bound 30 is the only
  one no predecessor run refuted.
- **Part 2 passed: Genesis refuted bound 30** (and 40). G certified a counterexample to bound 30 at evaluation 249,021
  of 500,000, the kernel's Rayleigh certificate and exact check confirming it: a bound the predecessor missed three
  times at the same budget.
- **Part 1 failed.** The discovery was made in the starting representation Γ, by the `imagine` operator under the
  allocator's best-first search, not by a representation Genesis learned (a library) or derived. What beat the
  predecessor was G's search over Γ, not a new representation.
- **Part 3 failed**: no procedure (named library macros or derived operations) was extracted from the discovery, so the
  replay had nothing to replay.
- **Part 4 failed** (family B, the Graffiti statements): the improved inventor certified 5 statements, the
  predecessor 6 (2 only by the improved, 3 only by the predecessor; McNemar p 0.81).
- **Part 5 failed** (family C, Genesis's own conjectures): both arms certified the same 18 (none by one arm only).

**What this licenses, and what it does not.** On DEV, at these budgets: Genesis's frontier found a counterexample to
one held-out Laplacian bound (30) that the predecessor did not find in three tries. It does not show that Genesis
discovered a representation, extracted a procedure, transferred it, or improved its inventor; the preregistered
expectation (NOT_PROVED_OUT, high confidence) held.
