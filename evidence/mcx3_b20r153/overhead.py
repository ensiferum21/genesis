#!/usr/bin/env python3
"""B20_R153 (engineering, disclosed): what mcx3's tree interpreter costs, and the identity at study scale.

    taskset -c 1 python3 evidence/mcx3_b20r153/overhead.py evidence/mcx3_b20r153/overhead.json

Builds mcx2's and mcx3's sources with the counting clock (`b20r153_build_mcx3.build_test`), so that both make the
same moves for the same number of clock readings; runs them alternately on 800-vertex graphs (random with mean
degree 6, and a 28 x 28 toroidal grid, weights +-1) and on mcx2 programs; records the child CPU time of each run and
whether output and trace agree. The CPU ratio mcx3 / mcx2 is the interpreter's cost on the same work."""
import json
from pathlib import Path
import random
import resource
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r153_build_mcx3 as B  # noqa: E402

PROGRAMS = ('B100 X I S2000 C', 'B5 X I D', 'b3 L X I S50 M P3 C')
TICKS_MS = 300                                       # 300,000 clock readings per run


def graphs():
    rng = random.Random(153)
    n = 800
    E = set()
    while len(E) < 3 * n:
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            E.add((min(u, v), max(u, v)))
    rnd = [(u, v, rng.choice((-1, 1))) for u, v in sorted(E)]
    k = 28
    tor = []
    for i in range(k):
        for j in range(k):
            a = i * k + j
            for b in (i * k + (j + 1) % k, ((i + 1) % k) * k + j):
                tor.append((min(a, b), max(a, b), rng.choice((-1, 1))))
    return {'random800': (n, rnd), 'torus784': (k * k, tor)}


def run(binary, n, E, seed, prog):
    text = f'{n} {len(E)} {seed} {TICKS_MS}\n' + ''.join(f'{u} {v} {w}\n' for u, v, w in E)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    r = subprocess.run([str(binary), '-prog', prog], input=text, capture_output=True, text=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return (r.returncode, r.stdout, r.stderr), cpu


def main(out):
    d = Path(tempfile.mkdtemp())
    b2, b3 = B.build_test(B.MCX2_SOURCE, d / 'mcx2t'), B.build_test(B.SOURCE, d / 'mcx3t')
    rows = []
    for name, (n, E) in graphs().items():
        for prog in PROGRAMS:
            for rep in range(5):
                order = (b2, b3) if rep % 2 == 0 else (b3, b2)
                res = {}
                for b in order:
                    res[b.name] = run(b, n, E, 10 + rep, prog)
                (o2, c2), (o3, c3) = res['mcx2t'], res['mcx3t']
                rows.append({'graph': name, 'prog': prog, 'seed': 10 + rep, 'identical': o2 == o3,
                             'cut': int(o2[1].split()[1]), 'trace': o2[2].split()[1:], 'cpu_mcx2': c2, 'cpu_mcx3': c3})
                print(rows[-1]['graph'], prog, rep, rows[-1]['identical'], round(c3 / c2, 4), flush=True)
    ratios = [r['cpu_mcx3'] / r['cpu_mcx2'] for r in rows]
    summary = {'runs': len(rows), 'identical': sum(r['identical'] for r in rows),
               'cpu_ratio_median': statistics.median(ratios), 'cpu_ratio_min': min(ratios), 'cpu_ratio_max': max(ratios),
               'by_program': {p: statistics.median(r['cpu_mcx3'] / r['cpu_mcx2'] for r in rows if r['prog'] == p)
                              for p in PROGRAMS},
               'ticks_ms': TICKS_MS, 'sources': {'mcx2': B.MCX2_SOURCE.name, 'mcx3': B.SOURCE.name}}
    Path(out).write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
