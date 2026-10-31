# B20_R189 record (WP-4 repaired): the verifier killed 414 of 437 mutants; no gap was found, but 23 survivors include behaviour it never checks (DEV)

**Run by:** the builder, on DEV. This measures the circle's verifier (blueprint WP-4, weakness C1). It repeats B20_R188
with that study's measurement defect repaired (B20R188-BOUNDARY): each mutant is offered with one added comment line,
so the verifier's other checks decide.

**Preregistration.** Preregistered at `ea06ce8` (31 Oct 2026); its digest is pinned in
`tests_genesis/test_verifier_adequacy_replica_study.py`. The script is `scripts/b20r189_verifier_adequacy.py`,
unchanged. It ran from a clean worktree, alone on CPU 0, 31 Oct 2026, 23:02:00-23:06:59 SGT.
- **CPU 0 idle time (disclosed):** 8 min 12 s before it (B20_R188 ended at 22:53:48; the defect was diagnosed and this
  repeat prepared); idle after it while this was recorded, with nothing preregistered to follow.

**Evidence and checks.** `evidence/verifier_adequacy_b20r189/` holds `result.json`, `rows.jsonl` (437 mutants) and
`run.log`. The record test `RecordB20R189` was drafted from B20_R188's with the names changed and dry-run on the
rehearsal.
- **As drafted, it failed twice, and was amended at recording (disclosed).** It keyed rows by a mutant's description,
  and 7 descriptions repeat (for example, two occurrences of `self.holder` on one line of the lease give the same
  description), so the key is not unique (defect B20R189-KEY).
- The amended test matches rows to mutants by position. The run did not resume, and wrote one row per mutant in
  enumeration order, which the test checks. It then examines every survivor again, to the same class: all 23
  reproduce. With the summary recomputed, it passes (8 tests with the design tests, 201 s, on CPU 1).
- The script's resume key has the same flaw. It was not used (one slice); a resumed run could have skipped the 7
  repeated mutants.


## Result

All 437 single-place mutants of the fifteen components were offered to the verifier on a job of seed 51.

| | Mutants |
|---|---|
| Killed (the verifier rejected it) | **414** |
| of which the job itself was not interrupted, and the verifier's own checks caught it | 8 (4 by the hidden tests alone, 3 by the fresh workloads and the resource check, 1 by all three) |
| Gap (accepted, and it diverged from the reference model in 20 workloads of 5,000 operations) | **0** |
| Possibly equivalent (accepted, and it never diverged) | **23** |

The mutation score, killed / (killed + gaps), is 1.0. By operator, all arithmetic, call and deletion mutants were
killed. The survivors were 9 constants, 6 comparisons, 4 attributes and 4 argument swaps. By component they were 7 in
the heap, 6 in the bag, 4 in stock, 3 in the TTL cache, and 1 each in lease, ledger and registry.

**What "possibly equivalent" hides.** The differential test compares exactly what the job's workloads compare, so a
survivor is either truly equivalent or a change to behaviour that no workload, visible test or hidden test checks.
Some of the 23 look equivalent:
- the heap's `self._swap(i, p)` with its arguments exchanged;
- `<` made `<=` where priorities are distinct.

**At least two are not:** the TTL cache's `counts()` returning hits where it should return misses, and the reverse.
No workload observes `counts()` (the cache's workloads observe its snapshot), and no hidden test checks it. That is a
real blind spot of the circle, in a method no job depends on. The bag's default `k=1` made 0 or 2 is another kind:
behaviour the workloads never exercise, because they always pass `k`.

## What this licenses, and what it does not

- **Measured (testbed only):** on every single-place mutant of the fifteen components, the verifier found no
  behavioural difference that the reference comparison can see and that it passed. Its strength on the behaviour the
  workloads exercise is complete at this mutant order.
- **Not shown:**
  - that the verifier checks every method: the TTL cache's `counts()` is unchecked;
  - its strength on two-point or semantic mutants;
  - which of the 23 survivors are truly equivalent (that needs a proof or a check of every method).
- **Next (blueprint C1, by Daniel's decision):**
  - add checks of the unobserved methods (`counts()` and the default arguments), each passing every correct source;
  - measure again on two-point mutants.
