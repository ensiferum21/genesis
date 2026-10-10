#!/bin/bash
# Rebuild the pinned external checkers/solvers used by Genesis verification.
# Installs into ${GENESIS_TOOLCHAIN:-$HOME/toolchain}. Sources come from GitHub
# (git clone at a pinned commit; Lean from its GitHub release tarball). Every
# binary's SHA-256 is compared with PINS.json after building; a mismatch is
# reported (compiler differences can change bytes) and recorded, not ignored.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
T="${GENESIS_TOOLCHAIN:-$HOME/toolchain}"
mkdir -p "$T" && cd "$T"
pin() { python3 -c "import json,sys;print(json.load(open('$HERE/PINS.json'))['$1']['$2'])"; }
clone() { # name url commit
  [ -d "$1/.git" ] || git clone -q "$2" "$1"
  git -C "$1" fetch -q --depth 1 origin "$3" 2>/dev/null || true
  git -C "$1" checkout -q "$3"
}
clone zstd https://github.com/facebook/zstd.git "$(pin zstd commit)" && make -C zstd -j2 zstd >/dev/null
clone cadical https://github.com/arminbiere/cadical.git "$(pin cadical commit)"
(cd cadical && ./configure >/dev/null && make -j2 >/dev/null)
clone drat-trim https://github.com/marijnheule/drat-trim.git "$(pin drat-trim commit)" && make -C drat-trim >/dev/null
clone eprover https://github.com/eprover/eprover.git "$(pin eprover commit)"
(cd eprover && ./configure >/dev/null && make -j2 >/dev/null)
LV="$(pin lean version)"
if [ ! -x "lean-$LV-linux/bin/lean" ]; then
  curl -sSL -o "lean-$LV-linux.tar.zst" "https://github.com/leanprover/lean4/releases/download/v$LV/lean-$LV-linux.tar.zst"
  echo "$(pin lean tarball_sha256)  lean-$LV-linux.tar.zst" | sha256sum -c -
  ./zstd/programs/zstd -dc "lean-$LV-linux.tar.zst" | tar -xf -
  rm -f "lean-$LV-linux.tar.zst"
fi
python3 "$HERE/check_pins.py" "$T"
