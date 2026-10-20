#!/usr/bin/env python3
"""B20_R87: build the strongest available MaxSAT solvers as pinned external tools (engineering).

    python3 scripts/b20r87_maxsat_tools.py --deepdist            build DeepDist from its pinned commit
    python3 scripts/b20r87_maxsat_tools.py --check               report what is installed and its SHA-256

**Why.** Daniel asked that the system be compared with the best, most tuned solvers there are. The problem here, the
largest triangle-free subgraph, is exactly an unweighted partial MaxSAT problem (one soft unit clause per host
edge, one hard clause per host triangle), the problem class of the MaxSAT Evaluation's anytime track, where solvers
have been tuned against each other every year since 2018. The 2024 unweighted anytime podium was SPB-MaxSAT-c-Band,
NuWLS-c-IBR and TT-Open-WBO-Inc (MaxSAT Evaluation 2024 slides, Berg and Järvisalo). DeepDist (ECAI 2025, "Enhancing
Local Search for MaxSAT with Deep Differentiation Clause Weighting") builds on SPB-MaxSAT's code and reports beating
SPB-MaxSAT and USW-LS.

**DeepDist.** Source: https://github.com/jmhmaxsat/DeepDist at commit 4d8997802ea042285dc402ef05573ba1f4631ffd. The
repository also ships prebuilt binaries; they are not used. Built from source with its own command
(`g++ pms.cpp -O3 -static`), plus `-ffile-prefix-map` so the binary does not depend on the build directory.
**One patch, disclosed:** the SIGTERM handler prints the best assignment (`s.print_best_solution();`, which the
pinned source has commented out). Without it the solver reports only costs ("o" lines), which are never trusted
here; the patch changes no search code. Installed as `/usr/local/genesis-sota/bin/DeepDist` (inside `/usr`, so the
runc sandbox sees it read-only), and pinned by SHA-256 in `candidate_kinds/maxsat.py`.

**The competition hybrids** (SPB-MaxSAT-c-FPS, NuWLS-c-IBR, TT-Open-WBO-Inc, Loandra; sources vendored by
https://github.com/josalhor/hermax) need GMP's development files, which this workspace cannot fetch (the Ubuntu
archive does not resolve); they are added when Daniel supplies the libgmp-dev packages.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

DEST = Path('/usr/local/genesis-sota/bin')
HERMAX = {'repo': 'https://github.com/josalhor/hermax', 'commit': '6960f98db37843ebdeef6291273b361e50dc8fed'}
# solver directory under hermax/solvers -> (installed name, the static binary the Makefile's `rs` target produces)
HERMAX_SOLVERS = {'SPB-MaxSAT-c-FPS': 'SPB-MaxSAT-c-FPS', 'NuWLS-c-IBR': 'NuWLS-c-IBR',
                  'tt-open-wbo-inc': 'TT-Open-WBO-Inc', 'Loandra': 'Loandra'}
GMP_DEBS = {'libgmp-dev_6.3.0+dfsg-2ubuntu6_amd64.deb':
            'ffadf91b116cc2647ef213742ac1cbe80f450af14413c146df6e200f8c3c9a1a',
            'libgmpxx4ldbl_6.3.0+dfsg-2ubuntu6_amd64.deb':
            'a50e3c79d72857077ec7602fb2b59dd3fa12ce15ae46c7a9409301311ae212b0'}   # supplied by Daniel, 20 Oct 2026
DEEPDIST = {'repo': 'https://github.com/jmhmaxsat/DeepDist', 'commit': '4d8997802ea042285dc402ef05573ba1f4631ffd'}
PATCH_FROM = '\t//s.print_best_solution();\n'
PATCH_TO = '\ts.print_best_solution();\n'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_deepdist():
    with tempfile.TemporaryDirectory(prefix='deepdist-') as d:
        src = Path(d) / 'src'
        subprocess.run(['git', 'clone', '-q', DEEPDIST['repo'], str(src)], check=True)
        subprocess.run(['git', '-C', str(src), 'checkout', '-q', DEEPDIST['commit']], check=True)
        main = src / 'pms.cpp'
        text = main.read_text()
        if text.count(PATCH_FROM) != 1:
            raise SystemExit('the pinned source does not have the expected commented-out print; refusing to patch')
        main.write_text(text.replace(PATCH_FROM, PATCH_TO))
        for stale in ('DeepDist', 'runsolver'):
            (src / stale).unlink(missing_ok=True)          # never use the shipped binaries
        subprocess.run(['g++', 'pms.cpp', '-O3', '-static', f'-ffile-prefix-map={src}=.', '-o', 'DeepDist.bin'],
                       cwd=src, check=True)
        DEST.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / 'DeepDist.bin', DEST / 'DeepDist')
        (DEST / 'DeepDist').chmod(0o755)
        return {'binary': str(DEST / 'DeepDist'), 'sha256': sha256(DEST / 'DeepDist'),
                'patched_pms_cpp_sha256': sha256(main), **DEEPDIST}


def tree_digest(root):
    h = hashlib.sha256()
    for f in sorted(Path(root).rglob('*')):
        if f.is_file():
            h.update(str(f.relative_to(root)).encode() + b'\0' + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def gmp_prefix(debs, d):
    """GMP's headers and static libraries, unpacked from the supplied .debs (hash-checked) into a build-only prefix;
    nothing is installed on the system, and the solvers are linked statically."""
    prefix = Path(d) / 'gmp'
    for path in debs:
        got = sha256(path)
        if got not in GMP_DEBS.values():
            raise SystemExit(f'{path}: unexpected SHA-256 {got}')
        subprocess.run(['dpkg-deb', '-x', str(path), str(prefix)], check=True)
    return prefix


def build_hermax(debs, names=None):
    out = []
    with tempfile.TemporaryDirectory(prefix='hermax-') as d:
        src = Path(d) / 'hermax'
        subprocess.run(['git', 'clone', '-q', '--filter=blob:none', HERMAX['repo'], str(src)], check=True)
        subprocess.run(['git', '-C', str(src), 'checkout', '-q', HERMAX['commit']], check=True)
        prefix = gmp_prefix(debs, d)
        env = dict(os.environ, CPATH=f'{prefix}/usr/include:{prefix}/usr/include/x86_64-linux-gnu',
                   LIBRARY_PATH=f'{prefix}/usr/lib/x86_64-linux-gnu')
        for sub, name in HERMAX_SOLVERS.items():
            if names and name not in names:
                continue
            code = src / 'solvers' / sub / 'code'
            digest = tree_digest(code)
            before = {p for p in (code.parent).rglob('*') if p.is_file()}
            subprocess.run(['make', 'rs', '-j1'], cwd=code, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            built = [p for p in code.parent.rglob('*_static') if p.is_file() and p not in before]
            if len(built) != 1:
                raise SystemExit(f'{sub}: expected one static binary, found {built}')
            DEST.mkdir(parents=True, exist_ok=True)
            shutil.copy2(built[0], DEST / name)
            (DEST / name).chmod(0o755)
            out.append({'solver': name, 'source': f'hermax/solvers/{sub}/code', 'source_tree_sha256': digest,
                        'binary': str(DEST / name), 'sha256': sha256(DEST / name), **HERMAX})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--deepdist', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--hermax', nargs='+', metavar='GMP_DEB', help='build the hermax solvers with these GMP .debs')
    a = ap.parse_args(argv)
    if a.deepdist:
        print(build_deepdist())
    if a.hermax:
        for r in build_hermax(a.hermax):
            print(r)
    if a.check or not (a.deepdist or a.hermax):
        for name in ('DeepDist', *HERMAX_SOLVERS.values()):
            p = DEST / name
            print(name, sha256(p) if p.exists() else 'missing')
    return 0


if __name__ == '__main__':
    sys.exit(main())
