#!/usr/bin/env python3
"""Run the Genesis test suites and write a machine-readable report.

Each suite runs in a fresh interpreter with PYTHONPATH=src so one suite cannot
leak state into another. Exit status is non-zero if any suite fails or errors.
Skips are reported separately; a skip never counts as a pass of the property
it would have tested.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

# name -> (directory, release consequence from spec §38)
SUITES = {
    'integration': ('tests_genesis', 'must pass'),
    'legacy_regression': ('tests', 'must pass'),
}
OPTIONAL = {
    'kernel': ('tests_kernel', 'must pass'),
    'sandbox_escape': ('tests_sandbox', 'failure blocks release'),
    'certificates': ('tests_certificates', 'failure blocks release'),
    'formal': ('tests_formal', 'failure blocks release'),
}


PYCACHE = None


def run_suite(name, directory, timeout):
    start = time.monotonic()
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONHASHSEED='0')
    # Site-packages bytecode is never trusted: each suite compiles from verified source into a
    # private cache (B15-REV-01; see genesis.deployment.bytecode_problems).
    env['PYTHONPYCACHEPREFIX'] = PYCACHE
    proc = subprocess.run([sys.executable, '-W', 'ignore', '-m', 'unittest', 'discover', '-v',
                           '-s', directory, '-t', '.'], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)
    tail = proc.stderr.strip().splitlines()[-6:]
    text = proc.stderr
    ran = re.search(r'Ran (\d+) tests?', text)
    skipped = re.search(r'skipped=(\d+)', text)
    failures = re.search(r'failures=(\d+)', text)
    errors = re.search(r'errors=(\d+)', text)
    skips = [{'test': m.group(1), 'reason': m.group(2)}
             for m in re.finditer(r'^(\S+) \([^)]*\) \.\.\. skipped [\'"](.*)[\'"]$', text, re.M)]
    return {
        'suite': name, 'directory': directory, 'returncode': proc.returncode, 'skips': skips,
        'ran': int(ran.group(1)) if ran else 0,
        'skipped': int(skipped.group(1)) if skipped else 0,
        'failures': int(failures.group(1)) if failures else 0,
        'errors': int(errors.group(1)) if errors else 0,
        'ok': proc.returncode == 0 and bool(ran),
        'seconds': round(time.monotonic() - start, 2),
        'tail': tail,
        'log': text,
    }


def git_state():
    """(HEAD commit, whether the working tree is clean), or (None, False) outside git: a report says what it tested."""
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True,
                               check=True).stdout.strip()
        return commit, not dirty
    except (OSError, subprocess.CalledProcessError):
        return None, False


def release_suites():
    """The suite names of the release profile in this tree."""
    return sorted(set(SUITES) | {k for k, v in OPTIONAL.items() if (ROOT / v[0]).is_dir()})


def merge(reports, commit):
    """One release report from several partial ones (`--suites` runs): each must have tested `commit` on a clean
    tree, together they must cover the release profile's suites exactly once, and the merged report is all_ok only
    if every suite is. Raises ValueError otherwise."""
    suites = []
    for r in reports:
        if r.get('commit') != commit or not r.get('clean'):
            raise ValueError(f"a report of {r.get('commit')} (clean={r.get('clean')}) for {commit}")
        if r.get('profile') != 'release':
            raise ValueError('only release-profile reports are merged')
        suites += r['suites']
    names = [x['suite'] for x in suites]
    if sorted(names) != release_suites():
        raise ValueError(f'the reports cover {sorted(names)}, not {release_suites()}')
    return {'profile': 'release', 'python': reports[0]['python'], 'commit': commit, 'clean': True,
            'selected': sorted(names), 'merged_from': len(reports), 'suites': suites,
            'total_ran': sum(x['ran'] for x in suites), 'total_skipped': sum(x['skipped'] for x in suites),
            'all_ok': all(x['ok'] for x in suites)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', default=None)
    parser.add_argument('--quick', action='store_true', help='skip the legacy regression suite')
    parser.add_argument('--profile', choices=['commit', 'nightly', 'release'], default='release',
                        help='spec §38 cadence: commit = integration; nightly adds legacy, certificates, formal; '
                             'release adds the sandbox escape suite (all suites)')
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--suites', default=None,
                        help='comma-separated suite names: run only these of the profile (so that a long matrix can be '
                             'split across jobs and merged by make_checkpoint.py --reports)')
    args = parser.parse_args(argv)
    commit, clean = git_state()
    global PYCACHE
    import tempfile
    PYCACHE = tempfile.mkdtemp(prefix='genesis-pycache-')      # created 0700 by mkdtemp
    suites = dict(SUITES)
    for name, spec in OPTIONAL.items():
        if (ROOT / spec[0]).is_dir():
            suites[name] = spec
    keep = {'commit': {'integration'},
            'nightly': {'integration', 'legacy_regression', 'certificates', 'formal'},
            'release': set(suites)}[args.profile]
    suites = {k: v for k, v in suites.items() if k in keep}
    if args.quick:
        suites.pop('legacy_regression', None)
    if args.suites:
        want = [x.strip() for x in args.suites.split(',') if x.strip()]
        unknown = [x for x in want if x not in suites]
        if unknown:
            raise SystemExit(f'not in the {args.profile} profile: {unknown}')
        suites = {k: v for k, v in suites.items() if k in want}
    results = []
    for name, (directory, consequence) in suites.items():
        result = run_suite(name, directory, args.timeout)
        result['release_consequence'] = consequence
        if consequence == 'failure blocks release' and result['skipped']:
            # A skipped containment test is not a pass: the property was not demonstrated.
            result['ok'] = False
            result['tail'] = result['tail'] + ['skips are release-blocking for this suite']
        # Elsewhere a skip is blocking unless it is declared non-mandatory (with a reason) in
        # docs/NONMANDATORY_SKIPS.json; an undeclared skip never counts as a pass.
        allowed = json.loads((ROOT / 'docs' / 'NONMANDATORY_SKIPS.json').read_text())['skips']
        undeclared = [s for s in result['skips'] if not any(re.search(a['pattern'], s['test'] + ' ' + s['reason'])
                                                            for a in allowed)]
        result['undeclared_skips'] = undeclared
        if undeclared or len(result['skips']) != result['skipped']:
            result['ok'] = False
            result['tail'] = result['tail'] + [f'undeclared or unparsed skips: {undeclared[:3]}']
        results.append(result)
        status = 'OK' if result['ok'] else 'FAIL'
        print(f"{name:20s} {status:4s} ran={result['ran']} skipped={result['skipped']} "
              f"failures={result['failures']} errors={result['errors']} {result['seconds']}s", flush=True)
        if not result['ok']:
            print('\n'.join(result['log'].strip().splitlines()[-40:]), file=sys.stderr)
    summary = {
        'profile': args.profile,
        'commit': commit, 'clean': clean,
        'selected': sorted(suites),
        'python': sys.version.split()[0],
        'suites': [{k: v for k, v in r.items() if k != 'log'} for r in results],
        'total_ran': sum(r['ran'] for r in results),
        'total_skipped': sum(r['skipped'] for r in results),
        'all_ok': all(r['ok'] for r in results),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if summary['all_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
