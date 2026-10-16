#!/usr/bin/env python3
"""B20_R49: is the tree route's certification utility due to the transferred, invented rows? A registered
ablation on fresh C4 hosts (GV6 path: attribution of transfer utility; DEV).

    taskset -c 0 python3 scripts/b20r49_c4_rows_ablation.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R48's tree route certifies C4 hosts the evaluator cannot. It combines two things:
  * branching, which is a builder-written method;
  * the rows the system generated and Lean-checked in the new domain (B20_R46).
A transfer claim is about the second only. If branching over the evaluator's own 4-cycle rows does as
well, the invented rows contribute nothing, and the utility belongs to the builder's method.

**Arms.** The same producer and checker, the same budget, from the same seed witness. Back to back, in
alternating order:
  * **c:** the tree route with B20_R46's registry (34 CHECKED patterns), exactly as in B20_R48;
  * **c0:** the registered ablation, the same route with an empty registry, so 4-cycle rows only. Its
    certificates name the empty registry's digest and are checked against it.
Both use B20_R47's limits and 60 s, and both are checked by `verification.lp_dual_tree_c4`, with the
check counted in wall time.

**Hosts.** 20 fresh DEV hosts in each of B20_R47's two C4 settings, seeds 20264901 and 20264911. They
exclude every identity b20r24_repilots.exposure excludes (B20_R47's and B20_R48's hosts included). They
are saved with the exposure scan before running.

**Verdict.**
  * **ROWS_RESPONSIBLE** iff all three hold:
    - both arms are sound (every certificate VALID with the claimed bound, every witness C4-free with
      the reported value, values agree when both certify);
    - c certifies at least as many hosts as c0;
    - McNemar one-sided p < 0.05 on the discordant hosts.
  * DEFECT_FOUND on a soundness failure.
  * NO_ROWS_EFFECT otherwise.
**Secondary (descriptive):** the wall saving c0 − c with its bootstrap 90% interval, node counts, and
each setting's certification rate.

**Development look (disclosed).** This used B20_R47's 18 open hosts: DEV material from an earlier study, none
of them among these hosts. At 60 s from the seed witness:
  * c0 certified **none of the 18**. Its searches reached 6,162–10,655 nodes and left gaps of 5–22 edges.
  * c certified **15 of the 18** in 3–45 s with 63–1,313 nodes (B20_R48's development look).
  * Every certificate of either arm checked VALID.
The expected verdict is ROWS_RESPONSIBLE.

A DEV measurement. It licenses no claim and changes no evaluator. The certificates of hosts certified by c
only are kept, gzip-compressed.
"""
import gzip
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.verification import lp_dual_tree_c4 as VT  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r47_c4_certification as R47  # noqa: E402
import b20r48_c4_tree_certification as R48  # noqa: E402

SEEDS = (20264901, 20264911)
BOOT_SEED = 20264999


def empty_registry(reg):
    return dict(reg, patterns={})


def certified(side):
    return side['lower'] == side['upper']


def sound_side(side):
    return (side['check']['verdict'] == 'VALID' and side['check']['bound'] == side['upper']
            and side['witness_valid'] and side['witness_value'] == side['lower'])


def sound_row(r):
    ok = sound_side(r['c']) and sound_side(r['c0'])
    if certified(r['c']) and certified(r['c0']) and r['c']['upper'] != r['c0']['upper']:
        ok = False
    return ok


def run(out, tasks, reg, empty, log):
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    with path.open('a') as fh:
        for i, t in enumerate(tasks):
            if t.task_id in done:
                continue
            w = R32.seed_witness(t)
            if i % 2 == 0:
                c, cert = R48.route_c(t, w, reg); c0, _ = R48.route_c(t, w, empty)
            else:
                c0, _ = R48.route_c(t, w, empty); c, cert = R48.route_c(t, w, reg)
            raw = json.dumps(cert, sort_keys=True).encode() if cert is not None else b''
            c['certificate_sha256'] = digest(cert) if cert is not None else None
            if cert is not None and certified(c) and not certified(c0):
                (certs / f'{t.task_id}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
            r = {'task_id': t.task_id, 'stratum': t.family, 'n': t.n, 'edges': len(t.edges),
                 'order': 'c,c0' if i % 2 == 0 else 'c0,c', 'witness': len(w), 'c': c, 'c0': c0}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{i:02d} {t.task_id}: c {c["lower"]}..{c["upper"]} {c["method"]} {c["wall_s"]:.1f}s ({c["nodes"]} nodes); '
                f'c0 {c0["lower"]}..{c0["upper"]} {c0["method"]} {c0["wall_s"]:.1f}s ({c0["nodes"]} nodes)')


def tally(rows):
    cc = [certified(r['c']) for r in rows]
    c0 = [certified(r['c0']) for r in rows]
    n = len(rows)
    return {'hosts': n, 'certified_c': sum(cc), 'certified_c0': sum(c0),
            'certified_c_not_c0': sum(a and not b for a, b in zip(cc, c0)),
            'certified_c0_not_c': sum(b and not a for a, b in zip(cc, c0)),
            'rate_c': round(sum(cc) / n, 4) if n else None, 'rate_c0': round(sum(c0) / n, 4) if n else None,
            'wall_total_s': {'c': round(sum(r['c']['wall_s'] for r in rows), 2),
                             'c0': round(sum(r['c0']['wall_s'] for r in rows), 2)},
            'nodes_total': {'c': sum(r['c']['nodes'] for r in rows), 'c0': sum(r['c0']['nodes'] for r in rows)}}


def analyse(out, tasks, scan, reg, empty):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    unsound = [r['task_id'] for r in rows if not sound_row(r)]
    pooled = tally(rows)
    p = R32.mcnemar_one_sided(pooled['certified_c_not_c0'], pooled['certified_c0_not_c'])
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['c0']['wall_s'] - r['c']['wall_s'])
    real = R32.BOOT_SEED
    R32.BOOT_SEED = BOOT_SEED
    try:
        est, ci = R32.boot_mean(by)
    finally:
        R32.BOOT_SEED = real
    passes = {'sound': not unsound, 'coverage': pooled['certified_c'] >= pooled['certified_c0'], 'mcnemar': p < 0.05}
    verdict = ('DEFECT_FOUND' if unsound else 'ROWS_RESPONSIBLE' if all(passes.values()) else 'NO_ROWS_EFFECT')
    summary = {'schema': 'genesis-b20r49-c4-rows-ablation-v1', 'seeds': list(SEEDS),
               'settings': [{'family': f, 'params': q} for f, q in R48.SETTINGS], 'budget_s': R48.SECONDS,
               'route': R48.ROUTE,
               'registry': {'package_sha256': reg['package_sha256'], 'patterns': len(reg['patterns']), 'sha256': digest(reg)},
               'ablation_registry_sha256': digest(empty), 'checker_identity': VT.checker_identity(),
               'pooled': pooled, 'by_setting': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)},
               'mcnemar_p_one_sided': round(p, 8), 'wall_saving_c0_minus_c': {'mean': est, 'interval_90': ci},
               'unsound_rows': unsound, 'passes': passes, 'verdict': verdict, 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV measurement; licenses nothing; route and checker not wired into the evaluator'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    reg = R47.registry()
    empty = empty_registry(reg)
    log(f'registry: {len(reg["patterns"])} C4 patterns from {reg["package_sha256"][:16]}; ablation: empty registry '
        f'{digest(empty)[:16]}')
    real = R48.SEEDS
    R48.SEEDS = SEEDS
    try:
        tasks, scan = R48.hosts(out, log)
    finally:
        R48.SEEDS = real
    run(out, tasks, reg, empty, log)
    s = analyse(out, tasks, scan, reg, empty)
    log(f'verdict {s["verdict"]}: certified c {s["pooled"]["certified_c"]} c0 {s["pooled"]["certified_c0"]}; McNemar p '
        f'{s["mcnemar_p_one_sided"]}; wall saving c0 - c {s["wall_saving_c0_minus_c"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
