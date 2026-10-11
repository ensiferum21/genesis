#!/bin/bash
# Reproducible build of the pinned source-built tools (roadmap W04, R-04).
#
#   toolchain/build_reproducible.sh OUT_DIR [SOURCE_MIRROR]
#
# Clones each tool at its pinned commit into OUT_DIR/<tool> (from SOURCE_MIRROR/<tool>
# if given, else from GitHub) and builds it so that the bytes do not depend on where
# or when the build ran:
#   * -ffile-prefix-map maps the build directory to /genesis-src/<tool>;
#   * SOURCE_DATE_EPOCH is the pinned commit's own timestamp; LC_ALL=C, TZ=UTC;
#   * CaDiCaL is built with -DNBUILD so `uname -n`/kernel strings are not embedded.
# The same compiler and C library then give the same binaries (checked by
# toolchain/check_pins.py against the "reproducible" hashes in PINS.json). Different
# compilers can still give different bytes: that is why PINS records the builder
# toolchain and why toolchain/known_answers.py checks behaviour, not just bytes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(realpath -m "$1")"
MIRROR="${2:-}"
if [ -n "$MIRROR" ] && [ "$(realpath -m "$MIRROR")" = "$OUT" ]; then
  echo "source mirror and output directory must differ (the output clones are replaced)" >&2; exit 2
fi
mkdir -p "$OUT"
export LC_ALL=C TZ=UTC
pin() { python3 -c "import json;print(json.load(open('$HERE/PINS.json'))['$1']['$2'])"; }
clone() { # name url
  local name="$1" url="$2" commit
  commit="$(pin "$name" commit)"
  [ -n "$MIRROR" ] && url="$MIRROR/$name"
  rm -rf "$OUT/$name"
  git clone -q --no-hardlinks "$url" "$OUT/$name"
  git -C "$OUT/$name" -c advice.detachedHead=false checkout -q "$commit"
  [ "$(git -C "$OUT/$name" rev-parse HEAD)" = "$commit" ] || { echo "commit mismatch for $name" >&2; exit 1; }
  SOURCE_DATE_EPOCH="$(git -C "$OUT/$name" log -1 --format=%ct)"
  export SOURCE_DATE_EPOCH
  MAP="-ffile-prefix-map=$OUT/$name=/genesis-src/$name"
}
clone zstd https://github.com/facebook/zstd.git
make -C "$OUT/zstd" -j2 zstd MOREFLAGS="$MAP" >/dev/null
clone cadical https://github.com/arminbiere/cadical.git
(cd "$OUT/cadical" && ./configure CXXFLAGS="-DNBUILD $MAP" >/dev/null && make -j2 >/dev/null)
clone drat-trim https://github.com/marijnheule/drat-trim.git
make -C "$OUT/drat-trim" CFLAGS="-O2 $MAP" >/dev/null 2>&1 || make -C "$OUT/drat-trim" >/dev/null
clone eprover https://github.com/eprover/eprover.git
(cd "$OUT/eprover" && ./configure >/dev/null && make -j2 OPTFLAGS="-O03 -fno-common -fomit-frame-pointer $MAP" >/dev/null)
python3 - "$OUT" "$HERE/PINS.json" <<'EOF'
import hashlib, json, sys
from pathlib import Path
out, pins = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
for name in ('zstd', 'cadical', 'drat-trim', 'eprover'):
    print(name, hashlib.sha256((out / pins[name]['binary']).read_bytes()).hexdigest())
EOF
