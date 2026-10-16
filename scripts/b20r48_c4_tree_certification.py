#!/usr/bin/env python3
"""B20_R48: certified branch and bound over the transferred C4 rows. Certification coverage on fresh C4 hosts
(GV6 path: transfer utility; DEV).

    taskset -c 0 python3 scripts/b20r48_c4_tree_certification.py OUT_DIR      run (resumable) and analyse

**Why.** In B20_R47, B20_R46's Lean-checked C4 rows closed 80% of the evaluator's LP gap, but certified no
host the evaluator could not (22 vs 22 of 40). The post-run diagnostics, disclosed in its evidence README,
located the obstacle:
  * the open gap is in the upper bound, not the witness;
  * the gap is global: violated rows on up to 8 vertices barely move the LP;
  * branching over the same rows, with an exact LP-dual certificate at every leaf, certified 10 of 13
    open hosts at 60 s in a prototype.
This step builds that route with an exact checker, and tests it prospectively on fresh hosts.

**This commit adds:**
  * `verification/lp_dual_tree_c4.py`, the exact checker for tree certificates. Each internal node fixes
    one host edge out or in. Each leaf has either a rationalised LP dual over B20_R47's rows, with each
    row's right side reduced by its fixed-in edges, or a row its fixed-in edges overfill. Its docstring
    has the soundness argument. Rows and registry are B20_R47's: 4-cycles of the host, and copies of
    CHECKED patterns of an intact package with the trusted definitions.
  * `discovery/generated_bnb_c4.py`, the producer. It runs depth-first search on the most fractional
    free edge, fixed-in child first, closes a node when its exact dual bound is at most the incumbent,
    and takes integral LP solutions as incumbents. When it runs out of time it falls back to the root's
    rows certificate. It has no SAT step.
Neither is wired into the evaluator.

**Hosts.** 20 fresh DEV hosts in each of B20_R47's settings (erdos n30 p0.2 and erdos n36 p0.17), seeds
20264801 and 20264811. They exclude every identity b20r24_repilots.exposure excludes, which now includes
B20_R47's hosts. They are saved with the exposure scan before running, and reloaded on resume.

**Routes.** Both start from the evaluator's seed witness, each gets 60 s, and they run back to back in
alternating order.
  * **a:** the evaluator (`obstruction.certify`: 4-cycle LP, then SAT/DRAT). Its wall time includes the
    DRAT check.
  * **c:** the tree route with B20_R46's registry and B20_R47's limits (15 s of separation, 50,000 copies
    per pattern, 80,000 in all, densest first; 1 CPU s of LP rounding). Every certificate it produces is
    checked by the exact checker, and its wall time includes that check.

**Verdict.** CERTIFICATION_UTILITY iff all four hold (B20_R35's rule):
  * c is sound: every certificate is VALID with the claimed bound, every reported witness is C4-free
    with the reported value, and no value disagrees when both routes certify;
  * c certifies at least as many hosts as a;
  * McNemar one-sided p < 0.05 on the hosts certified by one route only;
  * the bootstrap 90% interval of the per-host wall saving a − c is above 0.
A soundness failure gives DEFECT_FOUND; anything else gives NO_CERTIFICATION_UTILITY.

**Secondary (descriptive, fixed now; decides nothing):**
  * each setting's certification rate under c, against the e1-hard-v2 calibration limit (at least 90% within
    60 s);
  * tree sizes, and the exact check's time and certificate sizes.

**Development looks (disclosed).** None of these hosts is among this study's hosts.
  * **B20_R47's 18 open hosts** (DEV material from the previous study). The prototype certified 10 of the 13
    recorded when it ran. This commit's route, from the seed witness at 60 s, certified **15 of 18**:
    - 3 to 45 s and 63 to 1,313 nodes;
    - every certificate checked VALID, in under 1 s;
    - certificates of up to 4.3 MB, or 341 KiB gzip-compressed.
    Their values agree with the HiGHS MILP optima of the diagnostic probe, where it ran.
  * **25 small random hosts** (n 8–16) for correctness: 24 certified at the exact optimum (HiGHS, re-checked),
    and every certificate checked VALID. The other timed out at 30 s on a small dense host, where the rows
    number in the tens of thousands. Such hosts are not in this study.
  * **A smoke run of this script** on 2 more hosts (seeds 999101 and 999111, 10 s per route). The tree route
    certified both in under 2 s; the evaluator certified neither.
On this evidence the expected verdict is CERTIFICATION_UTILITY. The study is the prospective test.

A DEV measurement. It licenses no claim, changes no evaluator, and persists nothing to custody. The
certificates of hosts certified by c only are kept, gzip-compressed, for re-checking.
"""
import gzip
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_bnb_c4 as GB  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.verification import lp_dual_tree_c4 as VT  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r47_c4_certification as R47  # noqa: E402

C4 = RD.C4
SETTINGS = R47.SETTINGS
PER, SEEDS = 20, (20264801, 20264811)
SECONDS = 60
ROUTE = dict(R47.ROUTE)
BOOT_SEED = 20264899
CALIBRATION_LIMIT = 0.9


def hosts(out, log):
    path = out / 'hosts.json'
    if path.exists():
        saved = json.loads(path.read_text())
        log(f'resume: {len(saved["tasks"])} hosts and the exposure scan reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in saved['tasks']], saved['exposure_scan']
    excluded, scan, _ = R24.exposure(log)
    seen, tasks = set(excluded), []
    for seed, (family, params) in zip(SEEDS, SETTINGS):
        ts, seen, _ = ADAPTERS[C4].generate(seed, PER, 'DEV', family, params, excluded=seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'seeds': list(SEEDS), 'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
                    'exposure_scan': scan, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks, scan


def route_a(task, w):
    rec = O.certify(task, w, seconds=SECONDS)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['upper_evidence']['method'],
            'wall_s': rec['wall_s'], 'lp_bound': rec['steps'][0].get('bound')}


def route_c(task, w, reg):
    rec = GB.certify_with_tree(task, w, reg, seconds=SECONDS, **ROUTE)
    t0 = time.monotonic()
    v = (VT.check_certificate(task, rec['certificate'], reg) if rec['certificate'] is not None
         else {'verdict': 'NONE', 'bound': None, 'reason': None, 'leaves': None})
    check_s = time.monotonic() - t0
    try:
        wit = check_witness(task, [tuple(e) for e in rec['witness']])
        wit = {'value': wit['value'], 'valid': len(wit['selected']) == len(rec['witness'])}
    except ValueError:
        wit = {'value': None, 'valid': False}
    root = next(s for s in rec['steps'] if s['step'] == 'root-lp')
    side = {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'search_wall_s': rec['wall_s'],
            'check_s': round(check_s, 3), 'wall_s': round(rec['wall_s'] + check_s, 3), 'nodes': rec['nodes'],
            'leaves': rec['leaves'], 'root_bound': root['bound'], 'check': {k: v[k] for k in ('verdict', 'bound', 'reason', 'leaves')},
            'witness_value': wit['value'], 'witness_valid': wit['valid']}
    return side, rec['certificate']


def certified(side):
    return side['lower'] == side['upper']


def sound_row(r):
    c = r['c']
    ok = c['check']['verdict'] == 'VALID' and c['check']['bound'] == c['upper']
    ok = ok and c['witness_valid'] and c['witness_value'] == c['lower']
    if certified(r['a']) and certified(c) and r['a']['upper'] != c['upper']:
        ok = False
    return ok


def run(out, tasks, reg, log):
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
                a = route_a(t, w); c, cert = route_c(t, w, reg)
            else:
                c, cert = route_c(t, w, reg); a = route_a(t, w)
            raw = json.dumps(cert, sort_keys=True).encode() if cert is not None else b''
            c['certificate_sha256'] = digest(cert) if cert is not None else None
            c['certificate_bytes'] = len(raw)
            if cert is not None and certified(c) and not certified(a):
                (certs / f'{t.task_id}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
            r = {'task_id': t.task_id, 'stratum': t.family, 'n': t.n, 'edges': len(t.edges),
                 'order': 'ac' if i % 2 == 0 else 'ca', 'witness': len(w), 'a': a, 'c': c}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{i:02d} {t.task_id}: a {a["lower"]}..{a["upper"]} {a["method"]} {a["wall_s"]:.1f}s; '
                f'c {c["lower"]}..{c["upper"]} {c["method"]} {c["wall_s"]:.1f}s ({c["nodes"]} nodes, check '
                f'{c["check"]["verdict"]} {c["check_s"]:.1f}s)')


def tally(rows):
    ca = [certified(r['a']) for r in rows]
    cc = [certified(r['c']) for r in rows]
    n = len(rows)
    med = lambda xs: round(statistics.median(xs), 3) if xs else None
    return {'hosts': n, 'certified_a': sum(ca), 'certified_c': sum(cc),
            'certified_c_not_a': sum(c and not a for a, c in zip(ca, cc)),
            'certified_a_not_c': sum(a and not c for a, c in zip(ca, cc)),
            'rate_c': round(sum(cc) / n, 4) if n else None, 'rate_a': round(sum(ca) / n, 4) if n else None,
            'by_method_c': {m: sum(1 for r in rows if r['c']['method'] == m and certified(r['c']))
                            for m in sorted({r['c']['method'] for r in rows})},
            'wall_total_s': {'a': round(sum(r['a']['wall_s'] for r in rows), 2),
                             'c': round(sum(r['c']['wall_s'] for r in rows), 2)},
            'wall_median_s': {'a': med([r['a']['wall_s'] for r in rows]), 'c': med([r['c']['wall_s'] for r in rows])},
            'nodes_median_certified_c': med([r['c']['nodes'] for r in rows if certified(r['c'])]),
            'check_s_max': max((r['c']['check_s'] for r in rows), default=None),
            'certificate_bytes_max': max((r['c']['certificate_bytes'] for r in rows), default=None)}


def analyse(out, tasks, scan, reg):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    unsound = [r['task_id'] for r in rows if not sound_row(r)]
    pooled = tally(rows)
    p = R32.mcnemar_one_sided(pooled['certified_c_not_a'], pooled['certified_a_not_c'])
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['a']['wall_s'] - r['c']['wall_s'])
    real = R32.BOOT_SEED
    R32.BOOT_SEED = BOOT_SEED
    try:
        est, ci = R32.boot_mean(by)
    finally:
        R32.BOOT_SEED = real
    sound = not unsound
    passes = {'sound': sound, 'coverage': pooled['certified_c'] >= pooled['certified_a'], 'mcnemar': p < 0.05,
              'time': ci[0] > 0}
    verdict = ('DEFECT_FOUND' if not sound else 'CERTIFICATION_UTILITY' if all(passes.values())
               else 'NO_CERTIFICATION_UTILITY')
    by_setting = {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)}
    summary = {'schema': 'genesis-b20r48-c4-tree-certification-v1', 'seeds': list(SEEDS),
               'settings': [{'family': f, 'params': q} for f, q in SETTINGS], 'budget_s': SECONDS, 'route_c': ROUTE,
               'registry': {'package_sha256': reg['package_sha256'], 'patterns': len(reg['patterns']), 'sha256': digest(reg)},
               'checker_identity': VT.checker_identity(), 'pooled': pooled, 'by_setting': by_setting,
               'calibration_limit_met_by_c': {s: t['rate_c'] >= CALIBRATION_LIMIT for s, t in by_setting.items()},
               'calibration_limit_met_by_a': {s: t['rate_a'] >= CALIBRATION_LIMIT for s, t in by_setting.items()},
               'mcnemar_p_one_sided': round(p, 8), 'wall_saving_a_minus_c': {'mean': est, 'interval_90': ci},
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
    from genesis.verification.tools import tool
    log('SAT tools: ' + ', '.join(tool(n)['identity'] for n in ('cadical', 'drat-trim')))
    reg = R47.registry()
    log(f'registry: {len(reg["patterns"])} C4 patterns from {reg["package_sha256"][:16]}')
    tasks, scan = hosts(out, log)
    run(out, tasks, reg, log)
    s = analyse(out, tasks, scan, reg)
    log(f'verdict {s["verdict"]}: certified a {s["pooled"]["certified_a"]} c {s["pooled"]["certified_c"]}; McNemar p '
        f'{s["mcnemar_p_one_sided"]}; wall saving {s["wall_saving_a_minus_c"]}; calibration limit met by c '
        f'{s["calibration_limit_met_by_c"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
