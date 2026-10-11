#!/bin/bash
# Install the pinned external checkers/solvers used by Genesis verification into
# ${GENESIS_TOOLCHAIN:-$HOME/toolchain}.
#   * zstd, CaDiCaL, drat-trim and E: toolchain/build_reproducible.sh (git clone at the
#     pinned commit, path- and date-independent flags);
#   * Lean: the upstream release tarball, checked against its pinned SHA-256;
#   * the Lean/Mathlib workspace: toolchain/build_formal_workspace.py (FORMAL_WORKSPACE.json).
# Then every binary is compared with PINS.json and the known-answer suite is run.
# A hash mismatch (e.g. another compiler) is reported, never silently accepted: see
# toolchain/revise_pins.py for the only way to change a pin.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
T="${GENESIS_TOOLCHAIN:-$HOME/toolchain}"
mkdir -p "$T"
"$HERE/build_reproducible.sh" "$T" "${GENESIS_SOURCE_MIRROR:-}"
pin() { python3 -c "import json;print(json.load(open('$HERE/PINS.json'))['$1']['$2'])"; }
LV="$(pin lean version)"
cd "$T"
if [ ! -x "lean-$LV-linux/bin/lean" ]; then
  curl -sSL -o "lean-$LV-linux.tar.zst" "https://github.com/leanprover/lean4/releases/download/v$LV/lean-$LV-linux.tar.zst"
  echo "$(pin lean tarball_sha256)  lean-$LV-linux.tar.zst" | sha256sum -c -
  ./zstd/programs/zstd -dc "lean-$LV-linux.tar.zst" | tar -xf -
  rm -f "lean-$LV-linux.tar.zst"
fi
python3 "$HERE/check_pins.py" "$T"
python3 "$HERE/known_answers.py" "$T" >/dev/null && echo "known answers: all pass"
# Lean/Mathlib research workspace (W08): pinned sources, import closure built locally and offline.
if [ ! -f "$T/formal-workspace/WORKSPACE_MANIFEST.json" ]; then
  python3 "$HERE/build_formal_workspace.py" build "$T/formal-workspace"
fi
python3 "$HERE/build_formal_workspace.py" check "$T/formal-workspace"
