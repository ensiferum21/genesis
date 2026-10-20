#!/usr/bin/env python3
"""B20_R94: build `tfxw-v1`'s binary from the in-repository source (engineering).

    python3 scripts/b20r94_build_tfxw.py            build and install /usr/local/genesis-sota/bin/tfxw, print its SHA-256
    python3 scripts/b20r94_build_tfxw.py --check    build to a temporary file and compare with the pinned SHA-256

gcc 13.3 (Ubuntu 13.3.0-6ubuntu2~24.04.1), `-O3 -std=gnu11 -static`; the build is deterministic (two builds give the
same bytes), so the pin in `candidate_kinds/tfxw.py` can be re-derived from the source at any time.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/genesis/candidate_kinds/native/tfxw.c'
DEST = Path('/usr/local/genesis-sota/bin/tfxw')
FLAGS = ['-O3', '-std=gnu11', '-Wall', '-Wextra', '-static']


def build(out):
    subprocess.run(['gcc', *FLAGS, '-o', str(out), str(SOURCE), '-lm'], check=True)
    return hashlib.sha256(Path(out).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as d:
        digest = build(Path(d) / 'tfxw')
        if a.check:
            sys.path.insert(0, str(ROOT / 'src'))
            from genesis.candidate_kinds import tfxw as T
            print(digest, 'pinned' if digest == T.BINARY_SHA256 else f'DIFFERS from the pin {T.BINARY_SHA256}')
            return 0 if digest == T.BINARY_SHA256 else 1
        DEST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(d) / 'tfxw', DEST)
        DEST.chmod(0o755)
    print({'binary': str(DEST), 'sha256': digest,
           'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           'gcc': subprocess.run(['gcc', '--version'], capture_output=True, text=True).stdout.splitlines()[0]})
    return 0


if __name__ == '__main__':
    sys.exit(main())
