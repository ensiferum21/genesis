#!/bin/bash
# One slice of a preregistered study, alone on CPU 0, from a clean worktree of its preregistration commit.
# Usage: run_slice.sh WORKTREE SCRIPT OUTPUT LOG     (exit code: the study's; 3 = paused at the end of a slice)
wt=$1; script=$2; out=$3; slog=$4
log=/home/claude/chain.log
export PYTHONPYCACHEPREFIX=/home/claude/.pyc-run GENESIS_TOOLCHAIN=/home/claude/toolchain
cd "$wt" || exit 1
tag=$(basename "$script" .py)
echo "RUNTREE $tag $(git rev-parse HEAD) $(date -Is)" >> $log
echo "START $tag $(date -Is)" >> $log
taskset -c 0 python3 "$script" "$out" >> "$slog" 2>&1
rc=$?
echo "END $tag rc=$rc $(date -Is)" >> $log
exit $rc
