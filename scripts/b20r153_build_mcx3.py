#!/usr/bin/env python3
"""B20_R153: build `mcx3-v1`'s binary from the in-repository source (engineering).

    python3 scripts/b20r153_build_mcx3.py            build and install /usr/local/genesis-sota/bin/mcx3, print its SHA-256
    python3 scripts/b20r153_build_mcx3.py --check    build to a temporary file and compare with the pinned SHA-256

The same compiler and flags as mcx2's (`b20r125_build_mcx2.py`: gcc 13.3, `-O3 -std=gnu11 -static`); the build is
deterministic, so the pin in `candidate_kinds/mcx3.py` can be re-derived from the source at any time.

`build_test(source, out, probe)` makes the TEST builds of `test_mcx3_kind` (never installed, never pinned): the
source compiled with `tests_genesis/native/countclock.h`, a counting clock in place of the CPU clock and a trace of
every exp call, and with `probe`, mcx3's MCX3_PROBE reports (where each operator acts; each observable and what it
is made of). The same function builds mcx2's unchanged source the same way, for the identity test.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/genesis/candidate_kinds/native/mcx3.c'
MCX2_SOURCE = ROOT / 'src/genesis/candidate_kinds/native/mcx2.c'
COUNT_CLOCK = ROOT / 'tests_genesis/native/countclock.h'
DEST = Path('/usr/local/genesis-sota/bin/mcx3')
FLAGS = ['-O3', '-std=gnu11', '-Wall', '-Wextra', '-static']


def build(out):
    subprocess.run(['gcc', *FLAGS, '-o', str(out), str(SOURCE), '-lm'], check=True)
    return hashlib.sha256(Path(out).read_bytes()).hexdigest()


def build_test(source, out, probe=False):
    extra = ['-DMCX3_PROBE'] if probe else []
    subprocess.run(['gcc', '-O3', '-std=gnu11', *extra, '-include', str(COUNT_CLOCK), '-o', str(out), str(source),
                    '-lm'], check=True, capture_output=True)
    return Path(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as d:
        digest = build(Path(d) / 'mcx3')
        if a.check:
            sys.path.insert(0, str(ROOT / 'src'))
            from genesis.candidate_kinds import mcx3 as K
            print(digest, 'pinned' if digest == K.BINARY_SHA256 else f'DIFFERS from the pin {K.BINARY_SHA256}')
            return 0 if digest == K.BINARY_SHA256 else 1
        DEST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(d) / 'mcx3', DEST)
        DEST.chmod(0o755)
    print({'binary': str(DEST), 'sha256': digest,
           'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           'gcc': subprocess.run(['gcc', '--version'], capture_output=True, text=True).stdout.splitlines()[0]})
    return 0


if __name__ == '__main__':
    sys.exit(main())
