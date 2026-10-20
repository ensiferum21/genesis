#!/usr/bin/env python3
"""B20_R87: build the strongest available MaxSAT solvers as pinned external tools (engineering).

    python3 scripts/b20r87_maxsat_tools.py --deepdist            build DeepDist from its pinned commit
    python3 scripts/b20r87_maxsat_tools.py --solvers LIBGMP_DEV.deb LIBGMPXX.deb   build the competition solvers
    python3 scripts/b20r87_maxsat_tools.py --check               report what is installed and its SHA-256
    ... --dest DIR                                               install elsewhere (a rebuild check)

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

**The competition solvers**, each built with its own Makefile's statically linked release target, `make rs`, in a
fresh copy of its pinned source:
  * from https://github.com/josalhor/hermax (a Python packaging of MaxSAT solvers; the MaxSAT Evaluation's own site,
    which hosts the submitted sources, is refused by this workspace's proxy): SPB-MaxSAT-c-FPS (MSE 2024 anytime
    winner, with SPB-MaxSAT-c-Band) and NuWLS-c-IBR (MSE 2024 podium). hermax's edits to them since their first
    import (its commit b68a6de) only silence output (checked line by line); Aperture (Nadel, Slonimski and
    Strichman, SOFT 2026: an anytime SAT-based optimiser that also runs NuWLS and DeepDist local search; reported to
    beat SPB-MaxSAT-c and TT-Open-WBO-Inc in all four MSE 2024 anytime categories). **One patch, disclosed:**
    Aperture's reader sizes the input by seeking to its end, which fails on the pipe the sandboxed run must use
    (the sandbox may not write files) and leaves the stream failed, so the instance reads as empty; the patch
    clears the failed seek. It changes input reading only;
  * from the author's repository, https://github.com/alexander-nadel-academic/tt-open-wbo-inc (its MSE 2024
    submission; hermax's copy edits search files, so it is not used): TT-Open-WBO-Inc with IntelSAT
    (`starexec_run_i`, the Makefile's default). Its Glucose configuration (`starexec_run_g`) does not compile from
    the pinned source (it uses std::function without <functional>, and a member only the IntelSAT wrapper has,
    StopAfterNewImprovingModel), so only IntelSAT is built. Its shipped GMP libraries and binaries are deleted.
The GMP these link comes from the two Ubuntu packages Daniel supplied (checked by SHA-256, unpacked into a build-only
prefix; nothing is installed on the system).
**Not built: Loandra** (core-boosted linear search). hermax's copy links MaxPRE objects that its standalone
Makefile cannot compile (hermax edited MaxPRE for its own CMake build: `shuffle_with_rand` is defined twice), and
Loandra 2024's own repository needs a Rust toolchain and a Bitbucket submodule this workspace cannot fetch. It was not
on the 2024 unweighted anytime podium; Aperture reports beating that podium's winners.
The Makefiles take the solver root from `$PWD` and write into a `bin` directory the repository does not track, so
the build sets `PWD` and creates it. Some binaries embed source paths (assertion messages), so every build runs in
the same fixed directory, `/tmp/genesis-sota-build` (emptied before and removed after), and a rebuild gives the same
bytes.
"""
import argparse
import contextlib
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

DEST = Path('/usr/local/genesis-sota/bin')
SOURCES = {
    'hermax': {'repo': 'https://github.com/josalhor/hermax', 'commit': '6960f98db37843ebdeef6291273b361e50dc8fed'},
    'tt-open-wbo-inc': {'repo': 'https://github.com/alexander-nadel-academic/tt-open-wbo-inc',
                        'commit': '5881d2de7a1949ae28200d4bc0d1074e5e441ce7'},
}
# installed name -> (source, build directory in it, output directory of `make rs`, binary glob, needs GMP,
#                    extra make variables, shipped files deleted before building, patches (file, from, to))
BUILDS = {
    'SPB-MaxSAT-c-FPS': ('hermax', 'solvers/SPB-MaxSAT-c-FPS/code', '../bin', '*_static', True, (), (), ()),
    'NuWLS-c-IBR': ('hermax', 'solvers/NuWLS-c-IBR/code', '../bin', '*_static', True, (), (), ()),
    # Aperture sizes its input by seeking to the end; on a pipe the seek fails, the stream stays failed and the
    # instance reads as empty. The patch clears the failed seek (input reading only; no search code changes)
    'Aperture': ('hermax', 'solvers/Aperture', 'build', 'aperture_static', False, (), (),
                 (('src/cli/CNFReader.cc',
                   '    file_.seekg(0, ios::end);\n    file_size_ = file_.tellg();\n    file_.seekg(0, ios::beg);\n',
                   '    file_.seekg(0, ios::end);\n    std::streamoff end = file_.tellg();\n'
                   '    if (end < 0) {  // not seekable (a pipe): read from the start, size unknown\n'
                   '      file_.clear();\n      file_size_ = 0;\n    } else {\n'
                   '      file_size_ = end;\n      file_.seekg(0, ios::beg);\n    }\n'),)),
    # the author's repository (the MSE 2024 submission); its shipped GMP libraries and binaries are deleted, never used
    'TT-Open-WBO-Inc-IntelSAT': ('tt-open-wbo-inc', 'code', '.', '*_static', True, (),
                                 ('code/libgmp.a', 'code/libgmpxx.a', 'bin/tt-open-wbo-inc-Glucose4_1_static',
                                  'bin/tt-open-wbo-inc-IntelSATSolver_static'), ()),
}
GMP_DEBS = {'libgmp-dev_6.3.0+dfsg-2ubuntu6_amd64.deb':
            'ffadf91b116cc2647ef213742ac1cbe80f450af14413c146df6e200f8c3c9a1a',
            'libgmpxx4ldbl_6.3.0+dfsg-2ubuntu6_amd64.deb':
            'a50e3c79d72857077ec7602fb2b59dd3fa12ce15ae46c7a9409301311ae212b0'}   # supplied by Daniel, 20 Oct 2026
DEEPDIST = {'repo': 'https://github.com/jmhmaxsat/DeepDist', 'commit': '4d8997802ea042285dc402ef05573ba1f4631ffd'}
PATCH_FROM = '\t//s.print_best_solution();\n'
PATCH_TO = '\ts.print_best_solution();\n'


BUILD_ROOT = Path('/tmp/genesis-sota-build')


@contextlib.contextmanager
def build_root():
    """The fixed build directory (embedded source paths then do not vary between builds)."""
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    BUILD_ROOT.mkdir(parents=True)
    try:
        yield str(BUILD_ROOT)
    finally:
        shutil.rmtree(BUILD_ROOT, ignore_errors=True)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_deepdist():
    with build_root() as d:
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


def build_solvers(debs, names=None):
    out = []
    with build_root() as d:
        clones = {}
        for key in sorted({BUILDS[x][0] for x in BUILDS if not names or x in names}):
            src = Path(d) / 'src' / key
            subprocess.run(['git', 'clone', '-q', '--filter=blob:none', SOURCES[key]['repo'], str(src)], check=True)
            subprocess.run(['git', '-C', str(src), 'checkout', '-q', SOURCES[key]['commit']], check=True)
            clones[key] = src
        prefix = gmp_prefix(debs, d)
        for name, (key, sub, outdir, pattern, gmp, make_vars, remove, patches) in BUILDS.items():
            if names and name not in names:
                continue
            tree = Path(d) / 'build' / name                 # a fresh copy per configuration
            shutil.copytree(clones[key], tree, symlinks=True, ignore=shutil.ignore_patterns('.git'))
            for f in remove:
                (tree / f).unlink()
            code = tree / sub
            digest = tree_digest(code)                      # of the pinned source, before any patch
            for f, frm, to in patches:
                text = (code / f).read_text()
                if text.count(frm) != 1:
                    raise SystemExit(f'{name}: {f} does not have the expected text; refusing to patch')
                (code / f).write_text(text.replace(frm, to))
            extra = {}
            if gmp:
                extra = dict(CPATH=f'{prefix}/usr/include:{prefix}/usr/include/x86_64-linux-gnu',
                             LIBRARY_PATH=f'{prefix}/usr/lib/x86_64-linux-gnu')
            target = (code / outdir).resolve()
            target.mkdir(parents=True, exist_ok=True)
            log = Path(d) / f'{name}.make.log'
            with open(log, 'w') as fh:
                r = subprocess.run(['make', 'rs', f'-j{os.cpu_count() or 1}', *make_vars], cwd=code,
                                   env=dict(os.environ, PWD=str(code), **extra), stdout=fh, stderr=subprocess.STDOUT)
            if r.returncode:
                raise SystemExit(f'{name}: make rs failed (exit {r.returncode}):\n' + log.read_text()[-3000:])
            built = sorted(p for p in target.glob(pattern) if p.is_file())
            if len(built) != 1:
                raise SystemExit(f'{name}: expected one static binary in {target}, found {built}')
            embeds = str(d).encode() in built[0].read_bytes()
            DEST.mkdir(parents=True, exist_ok=True)
            shutil.copy2(built[0], DEST / name)
            (DEST / name).chmod(0o755)
            out.append({'solver': name, 'source': f'{key}/{sub}', 'source_tree_sha256': digest,
                        'make_variables': list(make_vars), 'patched': [f for f, _, _ in patches],
                        'binary': str(DEST / name),
                        'sha256': sha256(DEST / name), 'embeds_build_path': embeds, **SOURCES[key]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--deepdist', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--solvers', nargs='+', metavar='GMP_DEB', help='build the competition solvers with these GMP .debs')
    ap.add_argument('--only', nargs='+', choices=sorted(BUILDS), help='with --solvers: build only these')
    ap.add_argument('--dest', help='install into this directory instead (to check that a rebuild gives the pinned bytes)')
    a = ap.parse_args(argv)
    global DEST
    if a.dest:
        DEST = Path(a.dest)
    if a.deepdist:
        print(build_deepdist())
    if a.solvers:
        for r in build_solvers(a.solvers, a.only):
            print(r)
    if a.check or not (a.deepdist or a.solvers):
        for name in ('DeepDist', *BUILDS):
            p = DEST / name
            print(name, sha256(p) if p.exists() else 'missing')
    return 0


if __name__ == '__main__':
    sys.exit(main())
