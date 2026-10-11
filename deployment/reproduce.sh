#!/bin/bash
# Second-machine reproduction of a Genesis checkpoint (R-04). Run as root on the
# second machine (the sandbox suites and the launcher need it). Example:
#
#   deployment/reproduce.sh GENESIS_COMPLETION_CHECKPOINT_B15.zip <sha256 from the sender> \
#       /srv/genesis-repro --build-toolchain
#
# The script itself can be taken from the checkpoint or from the repository; it
# verifies the checkpoint before running anything from inside it.
set -euo pipefail
[ $# -ge 3 ] || { echo "usage: $0 CHECKPOINT.zip SHA256 WORK_DIR (--build-toolchain | --toolchain DIR)" >&2; exit 2; }
CKPT="$1"; SHA="$2"; WORK="$3"; shift 3
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 -I "$HERE/reproduce.py" --checkpoint "$CKPT" --expected-sha256 "$SHA" --work "$WORK" \
     --report "$WORK.report.json" "$@"
