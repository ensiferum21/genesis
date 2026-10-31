# Operations scripts (the builder's, for the CPU 0 protocol)

- `run_slice.sh WORKTREE SCRIPT OUT LOG`: one slice of a preregistered study alone on CPU 0, from a clean worktree of
  its preregistration commit; logs RUNTREE, START and END to `/home/claude/chain.log`; exit 3 = a slice paused.
- `checkpoint_shards.sh CLONE NAME K...` and `checkpoint_rest.sh CLONE NAME SUFFIX PARENT_ZIP PARENT_REF`: a
  checkpoint's release matrix in parts (the integration suite in six shards, `run_test_matrix.py --shard K/6`; each
  background job at most two shards, under the 2 h job limit), then `make_checkpoint.py --reports`. Run them from a
  single-branch clone (`git clone --single-branch --branch continuation-b20-rx`).
- `restore_verify_checkpoint.py ZIP OUT.json` (run with `python3 -I`): a checkpoint's manifest, its bundle's commit and
  tree, and its tracked files against the archive.
- `snapshot_running_study.sh STUDY OUT WORK`: pushes a running study's state to `wip/<study>` so another session can
  resume it.

Watching `chain.log` for a line: match only lines written after the watch starts (a watcher that matched a failed
attempt's old line started B20_R186 early).
