#!/bin/bash
# A checkpoint's integration shards K... of 6, one after another, alone on CPU 0, from a single-branch clone.
# Usage: checkpoint_shards.sh CLONE NAME K [K...]     (NAME e.g. B20_R184; reports go to $CKPT_OUT, default ~/checkpoints)
clone=$1; name=$2; shift 2
out=${CKPT_OUT:-/home/claude/checkpoints}; log=${CHAIN_LOG:-/home/claude/chain.log}
cd "$clone" || exit 1
export GENESIS_TOOLCHAIN=${GENESIS_TOOLCHAIN:-/home/claude/toolchain} PYTHONPYCACHEPREFIX=/home/claude/.pyc-ckpt
export GENESIS_ORTOOLS_WHEEL=${GENESIS_ORTOOLS_WHEEL:-/home/claude/inbox/wheels/ortools-9.15.6755-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl}
for k in "$@"; do
  echo "START checkpoint_${name}_integration_$k/6 $(git rev-parse HEAD) $(date -Is)" >> $log
  taskset -c 0 python3 scripts/run_test_matrix.py --profile release --suites integration --shard $k/6 --timeout 7000 \
    --report $out/${name}_matrix_integration_$k.json > $out/${name}_integration_$k.log 2>&1
  rc=$?
  echo "END checkpoint_${name}_integration_$k/6 rc=$rc $(date -Is)" >> $log
  [ $rc -eq 0 ] || exit $rc
done
