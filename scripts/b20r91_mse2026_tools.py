#!/usr/bin/env python3
"""B20_R91: build the MaxSAT Evaluation 2026 anytime entrants from the submitted sources (engineering).

    python3 scripts/b20r91_mse2026_tools.py ARCHIVE_DIR --gmp LIBGMP_DEV.deb LIBGMPXX.deb [--only NAME ...] [--dest DIR]
    python3 scripts/b20r91_mse2026_tools.py --check            report what is installed and its SHA-256

**Why.** B20_R90's opponents were the strongest solvers available then (2024 podium, DeepDist, Aperture via
hermax). The 2026 Evaluation's ranking (its slides and `results.zip`, Zenodo record 21358014) puts these first in the
unweighted anytime track: PASMaxSAT-c (1st at 60 s and 1707 s), Aperture-KBG (1st at 300 s), SGAT-NuWLS-c,
Aperture-GBG, NuWLS-c-2026-UB, then Aperture-IBI, DeepDist-c and NuWLS-c-2026. Daniel downloaded the submitted solver
archives (this workspace's proxy refuses Zenodo) and attached them; each is checked here against the SHA-256 recorded
below, which was taken after checking the archive's MD5 against the one Zenodo publishes.

**What is built.** Each archive holds the submitted source (`code/`), the authors' binaries and run scripts (`bin/`)
and often compiled objects and a bundled GMP. Every shipped binary, object, library and GMP header is deleted before
building; the run scripts are read (not run) for the configuration the Evaluation used, which
`candidate_kinds/maxsat2026.py` reproduces. Each solver is then built with its own Makefile's statically linked
release target (`make rs`), against the GMP from the Ubuntu packages Daniel supplied (as B20_R87), in a fixed build
directory. **One build fix, disclosed:** the open-wbo-based sources use std::function without including
`<functional>`, which the compilers of the Evaluation pulled in indirectly and gcc 13 does not; their build passes
`-include functional` to the compiler (no source change; no search code touched). Aperture does not need it. SGAT-NuWLS-c reads a learned weight file (text,
`nuwls_sgat_weights.artifact`), installed read-only with the binary and pinned.

**Not built.** Loandra 2026: it needs Rust crates from crates.io, which this workspace cannot reach; the archive's
prebuilt Rust library is not used (it ranked 10th–12th). px-tt-open-wbo-inc: absent from the 2026 ranking
(disqualified); SPB-NIM-c: entered the weighted track only. Aperture 2026 and NuWLS-c-2026-UB arrived later the same
day and are built too.

**Aperture 2026** (configurations GBG, KBG and IBI from its run scripts; one binary) carries B20_R87's input patch for
pipes (disclosed; its reader is unchanged since hermax's copy in those lines), and its IPAMIR wrapper (the incremental
C API, which the command-line solver does not use) is left out of the build because it does not compile under gcc 13. Its bundled SAT solvers' configure
scripts embed the build date, so a rebuild differs in those bytes only (as B20_R87's Aperture).
"""
import argparse
import contextlib
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = Path('/usr/local/genesis-sota/bin')
SHARE = Path('/usr/local/genesis-sota/share')
BUILD_ROOT = Path('/tmp/genesis-sota-build-2026')
GMP_PREFIX_DEBS = ROOT / 'scripts' / 'b20r87_maxsat_tools.py'
# archive file name -> (SHA-256, Zenodo's MD5)
ARCHIVES = {
    'solver-PASMaxSAT-c.zip': ('a277e3cd74128be6ef055ac69a1f2ae38b426cd2c6d8a52d701d92775eda7c2e',
                               'b21a7b7ac4b784e4e6ddae9b3dcf7a79'),
    'solver-SGAT-NuWLS-c.zip': ('d3f807fa6a199cf8411dd806b9a719c0f5bb0552ce9afbd4d450f4196359e1dd',
                                '627bbeb08b3ef31013eaa0ee73785fd9'),
    'solver-NuWLS-c-2026.zip': ('6e609171019d45bc28dfca2593669bf1061cb4dd112fe538764c741dda09ee4e',
                                '96c6ea79ada060e790fb41ef7c3048cb'),
    'solver-DeepDist-c.zip': ('889bc6cbd82b80f027a749fdc5272465db3db63d5b43c993ee4b5b2f06edbb0a',
                              '0d798799a4376b8da143b4115e90893d'),
    'solver-Aperture.zip': ('96c5cb794387db15be42e0276c0c5b10636e5eb4a753bd2f0df9b924d110f9c6',
                            'bda194071fa7c70fd73eb670a60e593c'),
    'solver-NuWLS-c-2026-UB.zip': ('8b0643863234de587a677d8ad0e2271e63312960d18155a63755c8c4cc4b834e',
                                   '6d58ed416740dd94fb3eb76b9a57467a'),
}
# Aperture reads its input by seeking to the end, which fails on the pipe the sandboxed run must use (B20_R87's
# patch for hermax's copy; the 2026 source has the same three lines): input reading only, no search code
APERTURE_PIPE_PATCH = ('src/cli/CNFReader.cc',
                       '    file_.seekg(0, ios::end);\n    file_size_ = file_.tellg();\n    file_.seekg(0, ios::beg);\n',
                       '    file_.seekg(0, ios::end);\n    std::streamoff end = file_.tellg();\n'
                       '    if (end < 0) {  // not seekable (a pipe): read from the start, size unknown\n'
                       '      file_.clear();\n      file_size_ = 0;\n    } else {\n'
                       '      file_size_ = end;\n      file_.seekg(0, ios::beg);\n    }\n')
# installed name -> (archive, top directory, binary the build writes (relative to the top), data files kept from bin/,
#                    patches (file under code/, from, to), source directories under code/ left out of the build)
BUILDS = {
    'PASMaxSAT-c': ('solver-PASMaxSAT-c.zip', 'PASMaxSAT-c', 'bin/PASMaxSAT-c_static', (), (), ()),
    'SGAT-NuWLS-c': ('solver-SGAT-NuWLS-c.zip', 'SGAT-NuWLS-c', 'bin/NuWLS-c_static',
                     ('nuwls_sgat_weights.artifact',), (), ()),
    'NuWLS-c-2026': ('solver-NuWLS-c-2026.zip', 'NuWLS-c-2026', 'bin/NuWLS-c_static', (), (), ()),
    'DeepDist-c': ('solver-DeepDist-c.zip', 'DeepDist-c', 'bin/DeepDist-c_static', (), (), ()),
    # its IPAMIR wrapper (the incremental C API, not used by the command-line solver: nothing outside src/ipamir
    # refers to it) does not compile under gcc 13 (requires-clauses redeclared), so it is left out of the build
    'Aperture-2026': ('solver-Aperture.zip', 'Aperture', 'code/build/aperture_static', (), (APERTURE_PIPE_PATCH,),
                      ('src/ipamir',)),
    'NuWLS-c-2026-UB': ('solver-NuWLS-c-2026-UB.zip', 'NuWLS-c-2026-UB', 'bin/NuWLS-c_static', (), (), ()),
}
# Aperture includes <functional> itself, and its bundled CaDiCaL compiles C files with $(CXX), which the forced C++
# header would break; it is built without the fix
NO_FUNCTIONAL_FIX = ('Aperture-2026',)
SHIPPED = ('.o', '.or', '.od', '.op', '.a', '.so', '.rlib', '.rmeta')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


@contextlib.contextmanager
def build_root():
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    BUILD_ROOT.mkdir(parents=True)
    try:
        yield BUILD_ROOT
    finally:
        shutil.rmtree(BUILD_ROOT, ignore_errors=True)


def gmp_prefix(debs, d):
    """GMP headers and static libraries from B20_R87's checked Ubuntu packages (its function and checks)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('b20r87', GMP_PREFIX_DEBS)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.gmp_prefix(debs, d)


def unpack(archive, d):
    """Extract a checked archive (no member may leave the target directory)."""
    target = Path(d).resolve()
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            out = (target / info.filename).resolve()
            if target not in out.parents and out != target:
                raise SystemExit(f'{archive}: member {info.filename} escapes the build directory')
        z.extractall(target)
        for info in z.infolist():                       # zipfile drops Unix modes (configure scripts need +x)
            mode = (info.external_attr >> 16) & 0o777
            if mode and not info.is_dir():
                (target / info.filename).chmod(mode)


def strip_shipped(top, keep):
    """Delete every shipped binary, object, library and bundled GMP header; return the kept data files' paths."""
    kept = {}
    bindir = top / 'bin'
    for name in keep:
        src = bindir / name
        if not src.is_file():
            raise SystemExit(f'{top.name}: expected data file bin/{name}')
        kept[name] = src.read_bytes()
    shutil.rmtree(bindir, ignore_errors=True)
    bindir.mkdir()
    removed = 0
    for p in list(top.rglob('*')):
        if p.is_file() and (p.suffix in SHIPPED or p.name in ('gmp.h', 'gmpxx.h', '.DS_Store')
                            or p.name.startswith('.nfs') or '.so.' in p.name):
            p.unlink()
            removed += 1
    return kept, removed


def build(archive_dir, debs, names=None):
    out = []
    with build_root() as d:
        prefix = gmp_prefix(debs, d)
        env_gmp = dict(CPATH=f'{prefix}/usr/include:{prefix}/usr/include/x86_64-linux-gnu',
                       LIBRARY_PATH=f'{prefix}/usr/lib/x86_64-linux-gnu')
        for name, (archive, topname, product, keep, patches, drop) in BUILDS.items():
            if names and name not in names:
                continue
            a = Path(archive_dir) / archive
            want_sha, want_md5 = ARCHIVES[archive]
            if sha256(a) != want_sha or md5(a) != want_md5:
                raise SystemExit(f'{a}: not the checked archive')
            work = d / name
            work.mkdir()
            unpack(a, work)
            top = work / topname
            kept, removed = strip_shipped(top, keep)
            code = top / 'code'
            for sub in drop:
                shutil.rmtree(code / sub)
            for f, frm, to in patches:
                text = (code / f).read_text()
                if text.count(frm) != 1:
                    raise SystemExit(f'{name}: {f} does not have the expected text; refusing to patch')
                (code / f).write_text(text.replace(frm, to))
            log = d / f'{name}.make.log'
            make_vars = () if name in NO_FUNCTIONAL_FIX else ('CXX=g++ -include functional',)
            with open(log, 'w') as fh:
                r = subprocess.run(['make', 'rs', f'-j{os.cpu_count() or 1}', *make_vars],
                                   cwd=code, env=dict(os.environ, PWD=str(code), **env_gmp),
                                   stdout=fh, stderr=subprocess.STDOUT)
            if r.returncode:
                kept_log = Path(tempfile.gettempdir()) / f'b20r91-{name}.make.log'
                shutil.copy2(log, kept_log)
                errors = [l for l in log.read_text().splitlines() if 'error' in l.lower() and 'Werror' not in l][:20]
                raise SystemExit(f'{name}: make rs failed (exit {r.returncode}); log kept at {kept_log}:\n'
                                 + '\n'.join(errors) + '\n' + log.read_text()[-1500:])
            binary = top / product
            if not binary.is_file():
                raise SystemExit(f'{name}: the build did not produce {product}')
            DEST.mkdir(parents=True, exist_ok=True)
            shutil.copy2(binary, DEST / name)
            (DEST / name).chmod(0o755)
            data = {}
            for fname, blob in kept.items():
                (SHARE / name).mkdir(parents=True, exist_ok=True)
                p = SHARE / name / fname
                p.write_bytes(blob)
                p.chmod(0o444)
                data[str(p)] = sha256(p)
            out.append({'solver': name, 'archive': archive, 'archive_sha256': want_sha, 'shipped_files_deleted': removed,
                        'patched': [f for f, _, _ in patches], 'left_out': list(drop),
                        'make_variables': list(make_vars),
                        'binary': str(DEST / name), 'sha256': sha256(DEST / name), 'data': data,
                        'embeds_build_path': str(d).encode() in (DEST / name).read_bytes()})
    return out


def main(argv=None):
    global DEST, SHARE
    ap = argparse.ArgumentParser()
    ap.add_argument('archive_dir', nargs='?')
    ap.add_argument('--gmp', nargs=2, metavar='DEB', help='the libgmp-dev and libgmpxx4ldbl packages (B20_R87)')
    ap.add_argument('--only', nargs='+', choices=sorted(BUILDS))
    ap.add_argument('--dest', help='install into this directory instead (a rebuild check)')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    if a.dest:
        DEST = Path(a.dest)
        SHARE = Path(a.dest) / 'share'
    if a.archive_dir:
        if not a.gmp:
            ap.error('--gmp is required to build')
        for r in build(a.archive_dir, a.gmp, a.only):
            print(r)
    if a.check or not a.archive_dir:
        for name in BUILDS:
            p = DEST / name
            print(name, sha256(p) if p.exists() else 'missing')
    return 0


if __name__ == '__main__':
    sys.exit(main())
