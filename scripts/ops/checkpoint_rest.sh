#!/bin/bash
# A checkpoint's other release suites alone on CPU 0, then the checkpoint from the six shard reports and this one.
# Usage: checkpoint_rest.sh CLONE NAME SUFFIX PARENT_ZIP PARENT_REF     (e.g. ... B20_R184 _R184 .../B20_R176.zip 2e7fd2f)
clone=$1; name=$2; suffix=$3; parent=$4; pref=$5
out=${CKPT_OUT:-/home/claude/checkpoints}; log=${CHAIN_LOG:-/home/claude/chain.log}
cd "$clone" || exit 1
export GENESIS_TOOLCHAIN=${GENESIS_TOOLCHAIN:-/home/claude/toolchain} PYTHONPYCACHEPREFIX=/home/claude/.pyc-ckpt
export GENESIS_ORTOOLS_WHEEL=${GENESIS_ORTOOLS_WHEEL:-/home/claude/inbox/wheels/ortools-9.15.6755-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl}
echo "START checkpoint_${name}_rest $(git rev-parse HEAD) $(date -Is)" >> $log
taskset -c 0 python3 scripts/run_test_matrix.py --profile release --suites legacy_regression,sandbox_escape,certificates,formal \
  --timeout 7000 --report $out/${name}_matrix_rest.json > $out/${name}_rest.log 2>&1
rc=$?
echo "END checkpoint_${name}_rest rc=$rc $(date -Is)" >> $log
[ $rc -eq 0 ] || exit $rc
echo "START checkpoint_${name}_make $(date -Is)" >> $log
taskset -c 0 python3 scripts/make_checkpoint.py --batch 20 --suffix $suffix --parent $parent --parent-ref $pref \
  --reports $out/${name}_matrix_integration_{1,2,3,4,5,6}.json $out/${name}_matrix_rest.json > $out/${name}_make.log 2>&1
rc=$?
echo "END checkpoint_${name}_make rc=$rc $(date -Is)" >> $log
exit $rc
