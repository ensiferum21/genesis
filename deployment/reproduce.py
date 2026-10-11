#!/usr/bin/env python3
"""Clean-room reproduction of a Genesis checkpoint on a second machine (R-04).

  reproduce.py --checkpoint GENESIS_COMPLETION_CHECKPOINT_Bnn.zip --expected-sha256 HEX \\
               --work NEW_DIR [--toolchain DIR | --build-toolchain] --report report.json

Steps, each recorded in the report; the first failing step stops the run:
  1  checkpoint bytes match the SHA-256 given out of band;
  2  safe extraction; every member matches CHECKPOINT_MANIFEST.json, nothing extra;
  3  the git bundle contains the recorded commit, whose tree equals the extracted tree;
  4  toolchain: use --toolchain, or build it from source (--build-toolchain, needs GitHub);
  5  host check against deployment/SUPPORTED_PLATFORM.json (`genesis platform check`);
  6  the release test matrix (all suites; the sandbox suites need root);
  7  deterministic reference computations equal deployment/EXPECTED_RESULTS.json.
Verdict: REPRODUCED only if every step passed. The report is evidence about one
host; it does not sign anything. The second machine's operator attests to it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import time
import zipfile

SCHEMA = 'genesis-reproduction-report-v1'
ADDED = {'genesis/source-history.bundle', 'genesis/CHECKPOINT_RECORD.json', 'genesis/CHECKPOINT_MANIFEST.json'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class Step(Exception):
    pass


def safe_extract(zip_path, dest):
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise Step('duplicate members')
        for info in z.infolist():
            n = info.filename
            kind = stat.S_IFMT(info.external_attr >> 16)
            if n.startswith('/') or '\\' in n or any(p in ('', '.', '..') for p in n.rstrip('/').split('/')) \
                    or (kind and kind not in (stat.S_IFREG, stat.S_IFDIR)) or not n.startswith('genesis/'):
                raise Step(f'unsafe member {n!r}')
        manifest = json.loads(z.read('genesis/CHECKPOINT_MANIFEST.json'))
        files = {n for n in names if not n.endswith('/')} - {'genesis/CHECKPOINT_MANIFEST.json'}
        if files != set(manifest):
            raise Step(f'members differ from the manifest: {sorted(files ^ set(manifest))[:5]}')
        for n in sorted(files):
            data = z.read(n)
            if sha256(data) != manifest[n]['sha256'] or len(data) != manifest[n]['bytes']:
                raise Step(f'member hash differs from the manifest: {n}')
            target = dest / n
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            # Readable by the unprivileged test worker (UID 65534); scripts executable.
            target.chmod(0o755 if n.endswith('.sh') or '/scripts/' in n else 0o644)
        for d in sorted({p for n in files for p in (dest / n).parents if dest in p.parents or p == dest}):
            d.chmod(0o755)
    return len(files)


def check_history(tree, record):
    repo = tree.parent / 'history'
    subprocess.run(['git', 'clone', '-q', str(tree / 'source-history.bundle'), str(repo)], check=True,
                   capture_output=True)
    head_tree = subprocess.run(['git', '-C', str(repo), 'rev-parse', f"{record['commit']}^{{tree}}"],
                               capture_output=True, text=True, check=True).stdout.strip()
    if head_tree != record['tree']:
        raise Step('the bundle commit does not have the recorded tree')
    listed = subprocess.run(['git', '-C', str(repo), 'ls-tree', '-r', '-z', record['commit']], capture_output=True,
                            check=True).stdout.split(b'\0')
    committed = {e.split(b'\t', 1)[1].decode() for e in listed if e}
    extracted = {str(p.relative_to(tree)) for p in tree.rglob('*') if p.is_file()} - \
        {a.split('/', 1)[1] for a in ADDED}
    if extracted != committed:
        raise Step(f'extracted tree differs from the commit: {sorted(extracted ^ committed)[:5]}')
    for entry in filter(None, listed):
        meta, path = entry.split(b'\t', 1)
        blob = meta.split()[2].decode()
        data = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', blob], capture_output=True,
                              check=True).stdout
        if (tree / path.decode()).read_bytes() != data:
            raise Step(f'extracted file differs from the committed tree: {path.decode()}')
    return {'commit': record['commit'], 'tree': head_tree, 'files': len([e for e in listed if e])}


def run(argv, *, env, cwd, log, timeout=7200):
    start = time.monotonic()
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    log.write_text(p.stdout + '\n--- stderr ---\n' + p.stderr)
    return p.returncode, p.stdout, round(time.monotonic() - start, 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    ap.add_argument('--work', type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--toolchain', type=Path)
    g.add_argument('--build-toolchain', action='store_true')
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--label', default='second machine', help='how the operator describes this host')
    a = ap.parse_args(argv)
    if a.work.exists():
        raise SystemExit('work directory must not exist (clean room)')
    blocked = [str(p) for p in a.work.resolve().parents if not p.stat().st_mode & 0o001]
    if blocked:
        raise SystemExit(f'the unprivileged test worker cannot traverse {blocked}; choose a work directory '
                         'whose ancestors are world-searchable (e.g. under /tmp or /srv)')
    a.work.mkdir(parents=True)
    a.work.chmod(0o755)
    logs = a.work / 'logs'; logs.mkdir()
    report = {'schema': SCHEMA, 'label': a.label, 'checkpoint': a.checkpoint.name, 'steps': [],
              'host': {'platform': platform.platform(), 'python': platform.python_version(),
                       'uid_is_root': os.geteuid() == 0}, 'operator_attestation': None}

    def step(name, fn):
        start = time.monotonic()
        try:
            detail = fn()
            report['steps'].append({'step': name, 'ok': True, 'detail': detail,
                                    'seconds': round(time.monotonic() - start, 1)})
            return detail
        except (Step, subprocess.CalledProcessError, OSError, ValueError, KeyError) as exc:
            report['steps'].append({'step': name, 'ok': False, 'detail': f'{type(exc).__name__}: {exc}',
                                    'seconds': round(time.monotonic() - start, 1)})
            raise Step(name)

    tree = a.work / 'genesis'
    try:
        def s1():
            actual = sha256(a.checkpoint.read_bytes())
            if actual != a.expected_sha256.lower():
                raise Step(f'checkpoint sha256 {actual} != expected')
            return actual
        report['checkpoint_sha256'] = step('1 checkpoint hash', s1)
        step('2 extraction and manifest', lambda: {'files': safe_extract(a.checkpoint, a.work)})
        record = json.loads((tree / 'CHECKPOINT_RECORD.json').read_text())
        report['commit'] = record['commit']
        step('3 source history', lambda: check_history(tree, record))
        toolchain = a.work / 'toolchain' if a.build_toolchain else a.toolchain.resolve()
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin', 'PYTHONPATH': str(tree / 'src'),
               'GENESIS_TOOLCHAIN': str(toolchain), 'PYTHONHASHSEED': '0', 'LC_ALL': 'C.UTF-8',
               'HOME': str(a.work)}
        for key in ('HTTPS_PROXY', 'https_proxy', 'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'GIT_SSL_CAINFO'):
            if key in os.environ:
                env[key] = os.environ[key]      # network only for --build-toolchain

        def s4():
            if a.build_toolchain:
                code, out, secs = run(['bash', str(tree / 'toolchain/install_tools.sh')], env=env, cwd=tree,
                                      log=logs / 'toolchain_build.log')
                if code:
                    raise Step('toolchain build failed; see logs/toolchain_build.log')
            code, out, secs = run([sys.executable, str(tree / 'toolchain/check_pins.py'), str(toolchain)], env=env,
                                  cwd=tree, log=logs / 'check_pins.log')
            if code:
                raise Step('pinned binaries or pin history do not match; see logs/check_pins.log')
            return {'toolchain': str(toolchain), 'built_here': a.build_toolchain, 'pins': out.strip().splitlines()}
        step('4 toolchain', s4)

        def s5():
            code, out, secs = run([sys.executable, '-m', 'genesis', 'platform', 'check', '--store-root', str(a.work)],
                                  env=env, cwd=tree, log=logs / 'platform.log')
            result = json.loads(out)
            report['platform'] = result
            if result['verdict'] != 'SUPPORTED':
                raise Step(f"host {result['verdict']}: failed {result['failed']}, unverified {result['unverified']}")
            return {'verdict': result['verdict']}
        step('5 supported host', s5)

        def s6():
            matrix = a.work / 'matrix.json'
            code, out, secs = run([sys.executable, str(tree / 'scripts/run_test_matrix.py'), '--profile', 'release',
                                   '--report', str(matrix)], env=env, cwd=tree, log=logs / 'matrix.log')
            summary = json.loads(matrix.read_text())
            report['matrix'] = {k: summary[k] for k in ('total_ran', 'total_skipped', 'all_ok')} | {
                'suites': {s['suite']: {k: s[k] for k in ('ran', 'skipped', 'failures', 'errors', 'ok')}
                           for s in summary['suites']}}
            if code or not summary['all_ok']:
                raise Step('release matrix failed; see logs/matrix.log')
            return report['matrix']
        step('6 release test matrix', s6)

        def s7():
            code, out, secs = run([sys.executable, str(tree / 'deployment/reference_run.py'), str(a.work / 'reference')],
                                  env=env, cwd=tree, log=logs / 'reference.log')
            result = json.loads(out.strip().splitlines()[-1])
            if not result['match']:
                raise Step(f"reference results differ: {result['differences']}")
            return {'match': True, 'sections': sorted(result['results'])}
        step('7 reference results', s7)
        report['verdict'] = 'REPRODUCED'
    except Step:
        report['verdict'] = 'NOT_REPRODUCED'
    report['note'] = ('Evidence about one host, produced by this script. R-04 acceptance needs a run on a second, '
                      'independently operated machine and that operator\'s attestation.')
    a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'report': str(a.report)}))
    return 0 if report['verdict'] == 'REPRODUCED' else 1


if __name__ == '__main__':
    sys.exit(main())
