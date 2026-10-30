# B20_R158's first attempt (crashed; not used)

- **What ran:** the preregistered script, amended once before it ran (`ff9eada`, sha256 `6b9652d3…7b14`). It ran from
  the clean worktree `/home/claude/f5b-wt`, alone on CPU 0, on 30 Oct 2026 from 10:44:29 to 10:50:30 SGT.
- **How it ended:** exit 1, after six minutes, in generation 1's FULL arm. The traceback is in `run.log`.
  - `abstraction.TemplateRep.mutate` raised `OverflowError: Python int too large to convert to C long`, after numpy
    warnings of an invalid cast.
  - The cause: an annealer whose current genome is invalid accepts any other invalid candidate (`cs >= s` with both
    -inf). So the walk on a template's slot values was unconstrained. Its multiplicative steps (x0.5, x1.5, x2)
    drift upward, about +0.135 per step in log terms, until int64 overflowed.
- **What is here:**
  - `gen1/conjectures.json`: generation 1's posed conjectures;
  - `gen1/state_FULL.json` and `gen1/state_FULL.templates.json`: the FULL arm's last saved state;
  - `run.log`: the slice log.
- **What was read:** only `run.log`'s traceback and warnings, and these files' names and sizes. No conjecture, state
  or result was read.
- **What follows:** the defect is repaired (slot values kept within [lo, max_n]). The study is amended a second time
  before any of its results was looked at, and runs again in full from the amendment commit, in a fresh output
  directory. These files are not used.
