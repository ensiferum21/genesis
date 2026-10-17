# B20_R64: run 1 is invalid (HiGHS was starved of CPU); a re-run on a quiet machine, decided before it runs

**What happened.** Run 1 (`run1_contended/`) ran on core 1 while the B20_R63 checkpoint's release matrix ran on
core 0. The matrix's Lean processes are not pinned and spilled onto core 1.
- **HiGHS loses.** HiGHS's time limit is wall-clock (`milp-highs-v1` passes `time_limit` to HiGHS), so under
  contention it gets less CPU than its budget.
- **The candidate does not.** Its search budget is process CPU time (`represent_and_repair`), so contention cannot
  shorten it.

The comparison was therefore biased toward the candidate.

**How it shows in the arms' own cgroup CPU.** The measure is the median ratio of CPU to budget, over hosts where
HiGHS ran to its limit (its value is below the best known).

| Run | Ratio |
|---|---|
| B20_R63 (valid) | 1.01–1.10 |
| B20_R64 run 1 | 0.55–0.86 |

Run 1's verdict (ADVANTAGE_GROWS) is reported in `run1_contended/` and is not the result.

**Validity criterion, stated before the re-run.** The design's premise is that every arm receives its budget. A run
is valid only if, for every HiGHS arm and every n, that median ratio is at least 0.9. Hosts where HiGHS reached the
best known value are left out, because they may have stopped early with a proof.

**The re-run.**
- **Script:** the preregistered script, unchanged, into this directory.
- **Hosts:** the same, reloaded from `hosts.json`.
- **Conditions:** pinned to core 0, with nothing else running on the machine and no edits to the tree.
- **Verdict:** the re-run's verdict is B20_R64's, if it meets the criterion. If it does not, B20_R64 is INVALID.
