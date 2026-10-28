# B20_R157's first attempt (killed; not used)

- **What ran:** the preregistered script (`bdf0c57`, sha256 `49b171f9…1904`), from the clean worktree
  `/home/claude/f4-wt`, alone on CPU 0. It started on 28 Oct 2026 at 01:08 UTC.
- **How it ended:** the memory cgroup killed it at about 02:10 UTC (out of memory, 6.1 GB). That was about two
  minutes into the first joint arm (FRONTIER), before the arm's first state save.
- **What is here:** `rows.jsonl`, the 168 single-search runs (NRPA, GBFS and CEM on each of the 56 bounds). It is
  kept as evidence of the attempt.
- **What was read:** only each row's arm and problem keys, to find where the attempt stopped. No value was read.
- **Why it ran out of memory:** a defect in `conjecture/attack.py`. A star S_k counted as k vertices, but it is built
  with k + 1. So programs with nested products of stars passed the 64-vertex cap and built graphs of thousands of
  vertices.
- **What follows:** the study was amended before any result was looked at (see the script's amendment). Every arm,
  the single searches included, runs again from the amendment commit. These rows are not used in any analysis.
