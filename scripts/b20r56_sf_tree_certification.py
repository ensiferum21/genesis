#!/usr/bin/env python3
"""B20_R56: certified branch and bound over the transferred sum-free rows. Certification coverage on fresh sum-free
hosts, with the plain Schur-row route as the registered ablation (GV6 second target: utility and attribution; DEV).

    taskset -c 0 python3 scripts/b20r56_sf_tree_certification.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R55 transferred the row-invention procedure to sum-free sets of integers: 17 patterns, all Lean-CHECKED.
In C4, the same rows inside certified branch and bound gave CERTIFICATION_UTILITY (B20_R48, 38 vs 26 of 40), and the
registered ablation attributed it to the rows (B20_R49, 36 vs 24). This study asks the same question in the second
target, in one step: there is no prior sum-free evaluator, so the conventional route *is* the ablation (the same tree
over the Schur rows only).

**This commit adds:**
  * `verification/lp_dual_tree_sf.py`, the exact checker for sum-free tree certificates: hosts are plain records of
    sorted distinct positive integers; rows are Schur triples (rhs 2), doubles a, 2a (rhs 1), and Freiman-type copies
    of CHECKED patterns of an intact package whose `SFDefs` is the trusted contract (rhs ex). Its docstring has the
    soundness argument. Leaves and branching mirror `lp_dual_tree_c4`.
  * `discovery/generated_bnb_sf.py`, the producer: every Schur and double row; root cutting planes over the pattern
    copies (as B20_R47's separation for C4: the most violated copies, up to 400 a round, for up to 30 rounds); then
    depth-first branch and bound on the most fractional element, fixed-in child first, with exact dual pruning. When
    time runs out it falls back to the root dual. A descriptive HiGHS MILP over the Schur rows.
Neither is wired into anything.

**Hosts.** 20 fresh hosts in each of two settings: uniformly random subsets of {1..N} with density p, (N, p) =
(300, 0.6) and (360, 0.6). Host i of a setting uses `random.Random(seed + i)`, with seeds 20265601 and 20265611. They
are saved to hosts.json before running and reloaded on resume. The settings were chosen from a calibration of the
conventional route alone (see below).

**Witness.** HiGHS's MILP over the Schur rows for 10 s (untrusted; its incumbent is re-checked as sum-free), once per
host before either route runs. Both routes start from it.

**Routes.** Each gets 60 s; they run back to back in alternating order; each one's wall time includes the exact check
of its certificate.
  * **a (conventional = ablation):** the tree over the Schur and double rows only (an empty registry).
  * **c (transferred):** the tree over the same rows plus B20_R55's pattern rows, through root separation.

**Verdict.** CERTIFICATION_UTILITY iff all four hold (B20_R35's rule, as B20_R48):
  * soundness: every certificate of either route is VALID with its claimed bound, every reported witness is sum-free
    with the reported value, and no value disagrees when both routes certify;
  * c certifies at least as many hosts as a;
  * McNemar one-sided p < 0.05 on the hosts certified by one route only;
  * the bootstrap 90% interval of the per-host wall saving a − c, stratified by setting, is above 0.
A soundness failure gives DEFECT_FOUND; anything else gives NO_CERTIFICATION_UTILITY.

**Secondary (descriptive, fixed now; decides nothing):** the root bounds of both routes and their difference; the
separation's rounds and rows; nodes; whether HiGHS proved optimality within 10 s; certificate sizes and check times.

**Development looks (disclosed).** On scratch copies, with a registry built from the same statements:
  * Correctness: 5 hosts (N 40-120), both routes certified at HiGHS's optimum and every certificate checked VALID;
    5 more (N 100-300), both routes certified at HiGHS's optimum (not checked).
  * Calibration of route a alone (60 s witnesses), 4 hosts per setting: (200, 0.5) 4/4 certified, (250, 0.5) 4/4,
    (300, 0.5) 4/4, (240, 0.6) 4/4 (one host 42 s), (300, 0.6) 4/4 (one host 40 s), (300, 0.7) 4/4, (360, 0.6) 3/4.
    The builder chose (360, 0.6), the only setting with an uncertified host, and (300, 0.6), one of the two with a
    host above 40 s (the other, (240, 0.6), has smaller hosts).
  * Both routes on 6 of those hosts with 10 s witnesses: without separation (every pattern copy in every node LP)
    c certified 0 and a 2; with the separation used here, c certified 3 (300/0.6 #3 at 57 s, 300/0.7 #0 at 51 s,
    360/0.6 #1 at 35 s) and a 2 (the last two, at 23 s and 21 s). c's root bound was 7-9 below a's on every host.
  * A smoke run of this script on 2 tiny hosts (seeds 999601 and 999611; N 60 and 80; 10 s per route, 2 s
    witnesses): both routes certified both, every certificate VALID.
On this evidence a utility verdict is unlikely: c may certify a few more hosts, but it is slower where both certify,
and the time criterion is part of the rule. The study is the prospective test.

A DEV measurement. It licenses no claim and persists nothing to custody. Certificates of hosts certified by one route
only are kept, gzip-compressed, for re-checking.
"""
import gzip
import json
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import generated_bnb_sf as GB  # noqa: E402
from genesis.verification import lp_dual_tree_sf as VT  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

SETTINGS = ((300, 0.6), (360, 0.6))
PER, SEEDS = 20, (20265601, 20265611)
SECONDS = 60
WITNESS_S = 10
SEPARATION = {'rounds': 30, 'per_round': 400}
BOOT_SEED = 20265699


def setting_name(N, p):
    return f'random_subset_N{N}_p{p}'


def make_hosts():
    tasks = []
    for seed, (N, p) in zip(SEEDS, SETTINGS):
        for i in range(PER):
            rng = random.Random(seed + i)
            A = [x for x in range(1, N + 1) if rng.random() < p]
            tasks.append({'domain': VT.DOMAIN, 'task_id': f'sf_N{N}_p{p}_{seed + i}', 'family': setting_name(N, p),
                          'elements': A})
    return tasks


def hosts(out, log):
    path = out / 'hosts.json'
    if path.exists():
        saved = json.loads(path.read_text())
        log(f'resume: {len(saved["tasks"])} hosts reloaded from hosts.json')
        return saved['tasks']
    tasks = make_hosts()
    if len({tuple(t['elements']) for t in tasks}) != len(tasks):
        raise RuntimeError('two hosts coincide')
    R11.dump(path, {'seeds': list(SEEDS), 'settings': [{'N': N, 'p': p} for N, p in SETTINGS], 'tasks': tasks})
    return tasks


def task_of(t):
    """The checker's record: domain, task id and elements (the family label is not part of it)."""
    return {'domain': t['domain'], 'task_id': t['task_id'], 'elements': t['elements']}


def route(task, w, reg, *, separation):
    rec = GB.certify_with_tree(task, w, reg, seconds=SECONDS, separation=separation)
    t0 = time.monotonic()
    v = (VT.check_certificate(task, rec['certificate'], reg) if rec['certificate'] is not None
         else {'verdict': 'NONE', 'bound': None, 'reason': None, 'leaves': None})
    check_s = time.monotonic() - t0
    try:
        wv = VT.check_witness(task, rec['witness'])
        wit = {'value': wv, 'valid': True}
    except ValueError:
        wit = {'value': None, 'valid': False}
    root = next(s for s in rec['steps'] if s['step'] == 'root-lp')
    sep = next((s for s in rec['steps'] if s['step'] == 'separation'), None)
    side = {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'search_wall_s': rec['wall_s'],
            'check_s': round(check_s, 3), 'wall_s': round(rec['wall_s'] + check_s, 3), 'nodes': rec['nodes'],
            'leaves': rec['leaves'], 'root_bound': root['bound'], 'rows': rec['rows'],
            'separation': sep, 'check': {k: v[k] for k in ('verdict', 'bound', 'reason', 'leaves')},
            'witness_value': wit['value'], 'witness_valid': wit['valid']}
    return side, rec['certificate']


def certified(side):
    return side['lower'] == side['upper']


def sound_row(r):
    ok = True
    for k in ('a', 'c'):
        s = r[k]
        ok = ok and s['check']['verdict'] == 'VALID' and s['check']['bound'] == s['upper']
        ok = ok and s['witness_valid'] and s['witness_value'] == s['lower']
    if certified(r['a']) and certified(r['c']) and r['a']['upper'] != r['c']['upper']:
        ok = False
    return ok


def run(out, tasks, reg, log):
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    abl = GB.empty_registry(reg)
    with path.open('a') as fh:
        for i, t in enumerate(tasks):
            if t['task_id'] in done:
                continue
            task = task_of(t)
            m = GB.mip(task, seconds=WITNESS_S)
            w = m['witness']
            if i % 2 == 0:
                a, ca = route(task, w, abl, separation=None); c, cc = route(task, w, reg, separation=SEPARATION)
            else:
                c, cc = route(task, w, reg, separation=SEPARATION); a, ca = route(task, w, abl, separation=None)
            for side, cert, name in ((a, ca, 'a'), (c, cc, 'c')):
                raw = json.dumps(cert, sort_keys=True).encode() if cert is not None else b''
                side['certificate_sha256'] = digest(cert) if cert is not None else None
                side['certificate_bytes'] = len(raw)
                other = c if name == 'a' else a
                if cert is not None and certified(side) and not certified(other):
                    (certs / f'{t["task_id"]}.{name}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
            r = {'task_id': t['task_id'], 'stratum': t['family'], 'size': len(t['elements']),
                 'order': 'ac' if i % 2 == 0 else 'ca', 'witness': {'value': len(w), 'elements': w,
                                                                    'mip_optimal': m['optimal'], 'mip_wall_s': m['wall_s']},
                 'a': a, 'c': c}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{i:02d} {t["task_id"]} |A|={len(t["elements"])} w {len(w)}: a {a["lower"]}..{a["upper"]} '
                f'{a["wall_s"]:.1f}s ({a["nodes"]} nodes, root {a["root_bound"]}); c {c["lower"]}..{c["upper"]} '
                f'{c["wall_s"]:.1f}s ({c["nodes"]} nodes, root {c["root_bound"]}, {c["rows"]} rows); checks '
                f'{a["check"]["verdict"]}/{c["check"]["verdict"]}')


def tally(rows):
    ca = [certified(r['a']) for r in rows]
    cc = [certified(r['c']) for r in rows]
    n = len(rows)
    med = lambda xs: round(statistics.median(xs), 3) if xs else None
    return {'hosts': n, 'certified_a': sum(ca), 'certified_c': sum(cc),
            'certified_c_not_a': sum(c and not a for a, c in zip(ca, cc)),
            'certified_a_not_c': sum(a and not c for a, c in zip(ca, cc)),
            'rate_a': round(sum(ca) / n, 4) if n else None, 'rate_c': round(sum(cc) / n, 4) if n else None,
            'wall_total_s': {'a': round(sum(r['a']['wall_s'] for r in rows), 2),
                             'c': round(sum(r['c']['wall_s'] for r in rows), 2)},
            'wall_median_s': {'a': med([r['a']['wall_s'] for r in rows]), 'c': med([r['c']['wall_s'] for r in rows])},
            'root_bound_a_minus_c_median': med([r['a']['root_bound'] - r['c']['root_bound'] for r in rows]),
            'nodes_median': {'a': med([r['a']['nodes'] for r in rows]), 'c': med([r['c']['nodes'] for r in rows])},
            'witness_mip_optimal': sum(r['witness']['mip_optimal'] for r in rows),
            'check_s_max': max((max(r['a']['check_s'], r['c']['check_s']) for r in rows), default=None),
            'certificate_bytes_max': max((max(r['a']['certificate_bytes'], r['c']['certificate_bytes']) for r in rows),
                                         default=None)}


def verdict_of(rows):
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
    return {'verdict': verdict, 'passes': passes, 'pooled': pooled, 'mcnemar_p_one_sided': round(p, 8),
            'wall_saving_a_minus_c': {'mean': est, 'interval_90': ci}, 'unsound_rows': unsound,
            'by_setting': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)}}


def analyse(out, tasks, reg):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t['task_id'] for t in tasks}:
        raise RuntimeError('not every host has been run')
    v = verdict_of(rows)
    summary = dict(v, schema='genesis-b20r56-sf-tree-certification-v1', seeds=list(SEEDS),
                   settings=[{'N': N, 'p': p} for N, p in SETTINGS], budget_s=SECONDS, witness_s=WITNESS_S,
                   separation=SEPARATION,
                   registry={'package_sha256': reg['package_sha256'], 'patterns': len(reg['patterns']),
                             'sha256': digest(reg)},
                   checker_identity=VT.checker_identity(), code_identity=code_identity(ROOT)['sha256'],
                   status='DEV measurement; licenses nothing; route and checker not wired into anything')
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
    reg = GB.load_registry()
    log(f'registry: {len(reg["patterns"])} sum-free patterns from {reg["package_sha256"][:16]}')
    tasks = hosts(out, log)
    run(out, tasks, reg, log)
    s = analyse(out, tasks, reg)
    log(f'verdict {s["verdict"]}: certified a {s["pooled"]["certified_a"]} c {s["pooled"]["certified_c"]}; McNemar p '
        f'{s["mcnemar_p_one_sided"]}; wall saving {s["wall_saving_a_minus_c"]}; passes {s["passes"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
