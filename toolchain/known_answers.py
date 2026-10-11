#!/usr/bin/env python3
"""Behavioural known-answer checks for the pinned tools (roadmap W04, R-04).

Byte-identical binaries need the same compiler; behaviour must agree everywhere.
Each case runs one tool on a tiny input with a known verdict. A pin revision
(toolchain/revise_pins.py) requires every case to pass for the new binaries.

  known_answers.py [TOOLCHAIN_ROOT] [--json OUT]
Exit status 0 only if every case passes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
UNSAT = 'p cnf 2 4\n1 2 0\n-1 2 0\n1 -2 0\n-1 -2 0\n'
SAT = 'p cnf 3 2\n1 2 0\n-1 3 0\n'
BOGUS_PROOF = '0\n'          # claims the empty clause at once: not a RUP step for SAT
THEOREM = 'fof(a, axiom, p).\nfof(b, axiom, (p => q)).\nfof(c, conjecture, q).\n'
NON_THEOREM = 'fof(a, axiom, p).\nfof(c, conjecture, q).\n'
LEAN_TRUE = 'theorem genesis_ka : 2 + 2 = 4 := rfl\n'
LEAN_FALSE = 'theorem genesis_ka : 2 + 2 = 5 := rfl\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, timeout=120, **kw):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env={'PATH': '/usr/bin:/bin'}, **kw)
    return p.returncode, p.stdout + p.stderr


def cases(root, pins, d):
    b = {k: root / v['binary'] for k, v in pins.items() if isinstance(v, dict) and 'binary' in v}
    (d / 'unsat.cnf').write_text(UNSAT); (d / 'sat.cnf').write_text(SAT); (d / 'bogus.drat').write_text(BOGUS_PROOF)
    code, _ = run([str(b['cadical']), '-q', '--no-binary', str(d / 'unsat.cnf'), str(d / 'unsat.drat')])
    yield 'cadical: UNSAT formula exits 20', code == 20
    code, out = run([str(b['cadical']), '-q', str(d / 'sat.cnf')])
    yield 'cadical: SAT formula exits 10 with a model', code == 10 and 'v ' in out
    code, out = run([str(b['drat-trim']), str(d / 'unsat.cnf'), str(d / 'unsat.drat')])
    yield 'drat-trim: verifies the CaDiCaL refutation', any(l.strip() == 's VERIFIED' for l in out.splitlines())
    code, out = run([str(b['drat-trim']), str(d / 'sat.cnf'), str(d / 'bogus.drat')])
    yield 'drat-trim: rejects a bogus refutation of a SAT formula', \
        any(l.strip() == 's NOT VERIFIED' for l in out.splitlines())
    (d / 't.p').write_text(THEOREM); (d / 'n.p').write_text(NON_THEOREM)
    code, out = run([str(b['eprover']), '--auto', '--cpu-limit=10', '-s', str(d / 't.p')])
    yield 'eprover: proves a theorem', 'SZS status Theorem' in out
    code, out = run([str(b['eprover']), '--auto', '--cpu-limit=10', '-s', str(d / 'n.p')])
    yield 'eprover: finds a non-theorem counter-satisfiable', 'SZS status CounterSatisfiable' in out
    payload = bytes(range(256)) * 64
    (d / 'blob').write_bytes(payload)
    run([str(b['zstd']), '-q', '-19', '-f', str(d / 'blob'), '-o', str(d / 'blob.zst')])
    run([str(b['zstd']), '-q', '-d', '-f', str(d / 'blob.zst'), '-o', str(d / 'blob.out')])
    yield 'zstd: round trip is lossless', (d / 'blob.out').exists() and (d / 'blob.out').read_bytes() == payload
    if 'lean' in b and b['lean'].exists():
        code, out = run([str(b['lean']), '--version'])
        yield 'lean: reports the pinned version', pins['lean']['version'] in out
        (d / 'T.lean').write_text(LEAN_TRUE); (d / 'F.lean').write_text(LEAN_FALSE)
        yield 'lean: accepts a true kernel-checked statement', run([str(b['lean']), str(d / 'T.lean')])[0] == 0
        yield 'lean: rejects a false statement', run([str(b['lean']), str(d / 'F.lean')])[0] != 0


def known_answers(root, pins=None):
    root = Path(root)
    pins = pins or json.loads((HERE / 'PINS.json').read_text())
    with tempfile.TemporaryDirectory(prefix='genesis-ka-') as d:
        results = []
        for name, ok in cases(root, pins, Path(d)):
            results.append({'case': name, 'pass': bool(ok)})
    binaries = {k: sha(root / v['binary']) for k, v in pins.items()
                if isinstance(v, dict) and 'binary' in v and (root / v['binary']).is_file()}
    return {'schema': 'genesis-known-answers-v1', 'ok': all(r['pass'] for r in results) and len(results) >= 7,
            'cases': results, 'binaries': binaries}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('root', nargs='?', default=str(HERE.parents[1] / 'toolchain'))
    ap.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    result = known_answers(a.root)
    text = json.dumps(result, indent=1, sort_keys=True)
    if a.json:
        a.json.write_text(text + '\n')
    print(text)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
