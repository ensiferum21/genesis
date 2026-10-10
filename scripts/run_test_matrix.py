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


def run_suite(name, directory, timeout):
    start = time.monotonic()
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONHASHSEED='0')
    proc = subprocess.run([sys.executable, '-W', 'ignore', '-m', 'unittest', 'discover',
                           '-s', directory, '-t', '.'], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)
    tail = proc.stderr.strip().splitlines()[-6:]
    text = proc.stderr
    ran = re.search(r'Ran (\d+) tests?', text)
    skipped = re.search(r'skipped=(\d+)', text)
    failures = re.search(r'failures=(\d+)', text)
    errors = re.search(r'errors=(\d+)', text)
    return {
        'suite': name, 'directory': directory, 'returncode': proc.returncode,
        'ran': int(ran.group(1)) if ran else 0,
        'skipped': int(skipped.group(1)) if skipped else 0,
        'failures': int(failures.group(1)) if failures else 0,
        'errors': int(errors.group(1)) if errors else 0,
        'ok': proc.returncode == 0 and bool(ran),
        'seconds': round(time.monotonic() - start, 2),
        'tail': tail,
        'log': text,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', default=None)
    parser.add_argument('--quick', action='store_true', help='skip the legacy regression suite')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args(argv)
    suites = dict(SUITES)
    for name, spec in OPTIONAL.items():
        if (ROOT / spec[0]).is_dir():
            suites[name] = spec
    if args.quick:
        suites.pop('legacy_regression', None)
    results = []
    for name, (directory, consequence) in suites.items():
        result = run_suite(name, directory, args.timeout)
        result['release_consequence'] = consequence
        if consequence == 'failure blocks release' and result['skipped']:
            # A skipped containment test is not a pass: the property was not demonstrated.
            result['ok'] = False
            result['tail'] = result['tail'] + ['skips are release-blocking for this suite']
        results.append(result)
        status = 'OK' if result['ok'] else 'FAIL'
        print(f"{name:20s} {status:4s} ran={result['ran']} skipped={result['skipped']} "
              f"failures={result['failures']} errors={result['errors']} {result['seconds']}s", flush=True)
        if not result['ok']:
            print('\n'.join(result['log'].strip().splitlines()[-40:]), file=sys.stderr)
    summary = {
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
