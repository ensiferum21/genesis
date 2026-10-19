#!/usr/bin/env python3
"""B20_R74: build and install the pinned state-of-the-art tools outside the locked environment.

    python3 scripts/b20r74_sota_tools.py [--check]

MQLib (Dunning et al. 2018) is fetched from GitHub at the commit `candidate_kinds/mqlib.py` pins, compiled from
outside its source tree with the fixed command, installed at that kind's BINARY and checked against its SHA-256.
The build runs in a fresh temporary directory; the downloaded code is compiled, never executed during the build.
With --check it only verifies what is installed.

OR-Tools CP-SAT and PySAT come from PyPI, which this workspace could not reach on 19 Oct 2026 (the egress proxy
refused pypi.org with 403); `candidate_kinds/cpsat.py` stays unregistered until their wheels are supplied.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.candidate_kinds import mqlib as MQ  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_mqlib():
    with tempfile.TemporaryDirectory(prefix='mqlib-') as d:
        src = Path(d) / 'MQLib'
        subprocess.run(['git', 'clone', '-q', MQ.SOURCE['repository'], str(src)], check=True)
        subprocess.run(['git', '-C', str(src), 'checkout', '-q', MQ.SOURCE['commit']], check=True)
        out = Path(d) / 'MQLib.bin'
        # relative paths and a prefix map, so that no build-directory path ends up in the binary (reproducible)
        cpps = sorted(str(p.relative_to(d)) for p in (src / 'src').rglob('*.cpp'))
        subprocess.run(['g++', '-IMQLib/include', '-std=c++11', '-O2', '-w', f'-ffile-prefix-map={d}=.',
                        '-o', str(out), *cpps, '-lm'], check=True, cwd=d)
        Path(MQ.BINARY).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, MQ.BINARY)
        Path(MQ.BINARY).chmod(0o555)
    return sha(MQ.BINARY)


def main(argv=None):
    argv = argv or sys.argv[1:]
    got = sha(MQ.BINARY) if Path(MQ.BINARY).is_file() else None
    if '--check' not in argv and got != MQ.BINARY_SHA256:
        got = build_mqlib()
    ok = got == MQ.BINARY_SHA256
    print(f'MQLib {MQ.BINARY}: {got} {"OK" if ok else "!= pinned " + MQ.BINARY_SHA256}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
