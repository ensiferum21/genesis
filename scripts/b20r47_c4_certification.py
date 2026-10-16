#!/usr/bin/env python3
"""B20_R47: does the transferred row-invention procedure help in the C4 domain? Certification coverage on
C4 hosts with generated, Lean-checked C4 rows (GV6 path: transfer; DEV).

    taskset -c 0 python3 scripts/b20r47_c4_certification.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R46 transferred the triangle-free row generator to C4-free subgraphs: 34 patterns on up to 6
vertices, each bound Lean-checked. The C4 domain is where the evaluator's certification is weakest:
  * in the e1-hard-v2 calibration, the one C4 setting with headroom (erdos n30 p0.2) certified only 75%
    of its hosts and was too slow (median 24 s);
  * so no C4 setting could be calibrated, and B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.
This step tests prospectively whether the transferred rows give the C4 evaluator a certification
utility, as B20_R35 showed for the triangle-free rows. Everything below is fixed before running.

**This commit also adds the C4 checker and route:**
  * `verification/lp_dual_rows_c4.py` is the exact checker. Its registry admits a pattern only from a
    CHECKED statement of an intact package with the trusted GTDefs, G4Defs and P4Defs.
  * `discovery/generated_certify_c4.py` is the route: LP over 4-cycle rows plus pattern copies, then
    rounding of its own LP, then SAT/DRAT.
Neither is wired into the evaluator.

**Hosts.** 20 fresh DEV hosts per C4 setting, seeds 20264701 and 20264711. They exclude every identity
b20r24_repilots.exposure excludes, and are saved before running and reloaded on resume.
  * **erdos n30 p0.2.** This is the e1b C3 setting, the only C4 setting with headroom in the e1-hard-v2
    calibration, where the evaluator certified 6/8.
  * **erdos n36 p0.17.** A larger host at about the same average degree.

**Routes.** Both start from the evaluator's seed witness, each gets 60 s, and they run back to back in
alternating order.
  * **a:** the evaluator's joint LP/SAT certification (`obstruction.certify`).
  * **b:** the C4 route with B20_R46's registry (package `7a081e4a…`, 34 CHECKED patterns). It uses
    B20_R37's limits (15 s of separation, 50,000 copies per pattern, 80,000 in all, densest pattern
    first) and 1 CPU s of LP rounding.
  The exact checker checks every LP certificate first.

**Verdict.** CERTIFICATION_UTILITY iff all four hold (B20_R35's rule):
  * b is sound: every LP certificate is VALID, and no value disagrees when both certify;
  * b certifies at least as many hosts as a;
  * McNemar one-sided p < 0.05 on the hosts certified by one route only;
  * the bootstrap 90% interval of the per-host wall saving a − b is above 0.
A soundness failure gives DEFECT_FOUND; anything else gives NO_CERTIFICATION_UTILITY.

**Secondary (descriptive, fixed now; decides nothing).** The LP gap closed by the rows, on hosts whose
optimum either route certifies: the mean of (LP bound a − LP bound b) / (LP bound a − optimum) over hosts
with LP bound a above the optimum, and the number of hosts where the rows' LP bound alone meets the
optimum. This separates "the transferred rows are stronger" from "they make certification cheaper".

**Development looks (disclosed).** On 6 non-study hosts (seeds 777001 and 777002, 3 hosts each of the two
settings), both routes at these budgets:
  * the rows lowered the LP bound by 1 to 3;
  * the same hosts were certified by both routes (4 of 6), all by SAT/DRAT;
  * route b was no faster: its SAT step is the evaluator's, and the bound it must prove is the same.
Profiling showed that copy enumeration spent about 2 s on K_{2,4}, whose generated labels start with its
independent side. The route therefore relabels each pattern for the search only (`search_order`); the
copies found are identical (checked on the same hosts), and enumeration takes about 0.5 s.
A smoke run of this script on 2 more non-study hosts (seeds 999001 and 999011, one per setting, 10 s per
route, a synthetic registry of the same 34 patterns) went the other way on one host: there route b's LP
bound alone met its rounded witness (76, in 3.4 s), while route a stopped at 76..78.
On this evidence the verdict could go either way, with NO_CERTIFICATION_UTILITY the likelier. The study is
the prospective test the transfer needs, and the secondary diagnostic measures the rows' strength.

A DEV measurement. It licenses no claim, changes no evaluator, and persists nothing to custody.
Certificates of hosts certified by b alone are kept for re-checking.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_certify_c4 as GC4  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.formal_research.triangle_theory import DEFS_SOURCE  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.verification import lp_dual_rows_c4 as V4  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

C4 = RD.C4
SETTINGS = [('erdos', {'n': 30, 'p': 0.2}), ('erdos', {'n': 36, 'p': 0.17})]
PER, SEEDS = 20, (20264701, 20264711)
SECONDS = 60
ROUTE = {'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000, 'order': 'dense-first',
         'lp_rounding_seconds': 1.0}
BOOT_SEED = 20264799
PACKAGE = ROOT / 'evidence' / 'c4_generator_b20r46' / 'package.json'


def registry():
    pkg = json.loads(PACKAGE.read_text())
    problems = TP.integrity_problems(pkg)
    if problems:
        raise RuntimeError(f'package integrity: {problems}')
    return V4.registry_from_package(pkg, defs_source=DEFS_SOURCE, c4_source=RP.C4_SOURCE)


def hosts(out, log):
    path = out / 'hosts.json'
    excluded, scan, _ = R24.exposure(log)
    if path.exists():
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
        log(f'resume: {len(tasks)} hosts reloaded from hosts.json')
        return tasks, scan
    seen, tasks = set(excluded), []
    for seed, (family, params) in zip(SEEDS, SETTINGS):
        ts, seen, _ = ADAPTERS[C4].generate(seed, PER, 'DEV', family, params, excluded=seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'seeds': list(SEEDS), 'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks, scan


def route_a(task, w):
    rec = O.certify(task, w, seconds=SECONDS)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['upper_evidence']['method'],
            'wall_s': rec['wall_s'], 'lp_step': rec['steps'][0]}


def route_b(task, w, reg):
    rec = GC4.certify_with_rows(task, w, reg, seconds=SECONDS, **ROUTE)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'wall_s': rec['wall_s'],
            'lp_step': rec['steps'][0], 'certificate': rec['certificate']}


def certified(side):
    return side['lower'] == side['upper']


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
                a = route_a(t, w); b = route_b(t, w, reg)
            else:
                b = route_b(t, w, reg); a = route_a(t, w)
            cert = b.pop('certificate')
            b['certificate_sha256'] = cert and digest(cert)
            if cert is not None and certified(b) and not certified(a):
                (certs / f'{t.task_id}.json').write_text(json.dumps(cert, sort_keys=True))
            r = {'task_id': t.task_id, 'stratum': t.family, 'n': t.n, 'edges': len(t.edges),
                 'order': 'ab' if i % 2 == 0 else 'ba', 'witness': len(w), 'a': a, 'b': b}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{i:02d} {t.task_id}: a {a["lower"]}..{a["upper"]} {a["method"]} {a["wall_s"]:.1f}s; '
                f'b {b["lower"]}..{b["upper"]} {b["method"]} {b["wall_s"]:.1f}s')


def gap_closure(rows):
    """The secondary diagnostic: LP gap closed by the rows on hosts with a certified optimum."""
    known = []
    for r in rows:
        opt = r['a']['upper'] if certified(r['a']) else r['b']['upper'] if certified(r['b']) else None
        if opt is not None:
            known.append((r['a']['lp_step']['bound'], r['b']['lp_step']['bound'], opt))
    gapped = [(la, lb, o) for la, lb, o in known if la is not None and lb is not None and la > o]
    return {'hosts_with_optimum': len(known), 'hosts_with_lp_gap': len(gapped),
            'mean_fraction_closed': round(statistics.fmean((la - lb) / (la - o) for la, lb, o in gapped), 4) if gapped else None,
            'rows_lp_meets_optimum': sum(lb == o for _, lb, o in known),
            'cycle_lp_meets_optimum': sum(la == o for la, _, o in known)}


def tally(rows):
    ca = [certified(r['a']) for r in rows]
    cb = [certified(r['b']) for r in rows]
    n = len(rows)
    return {'hosts': n, 'certified_a': sum(ca), 'certified_b': sum(cb),
            'certified_b_not_a': sum(b and not a for a, b in zip(ca, cb)),
            'certified_a_not_b': sum(a and not b for a, b in zip(ca, cb)),
            'lp_upper_b': sum(r['b']['method'] == 'LP_DUAL_GENERATED_C4_EXACT' and certified(r['b']) for r in rows),
            'lp_upper_a': sum(r['a']['method'] == 'LP_DUAL_EXACT' and certified(r['a']) for r in rows),
            'upper_bound_mean': {'a': round(statistics.fmean(r['a']['upper'] for r in rows), 3),
                                 'b': round(statistics.fmean(r['b']['upper'] for r in rows), 3)} if n else None,
            'wall_total_s': {'a': round(sum(r['a']['wall_s'] for r in rows), 2),
                             'b': round(sum(r['b']['wall_s'] for r in rows), 2)},
            'wall_median_s': {'a': round(statistics.median(r['a']['wall_s'] for r in rows), 3),
                              'b': round(statistics.median(r['b']['wall_s'] for r in rows), 3)} if n else None,
            'lp_bound_mean': {side: round(statistics.fmean(bs), 3) if bs else None for side in ('a', 'b')
                              for bs in [[r[side]['lp_step']['bound'] for r in rows
                                          if r[side]['lp_step']['bound'] is not None]]},
            'gap_closure': gap_closure(rows)}


def analyse(out, tasks, scan, reg):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    disagreements = [r['task_id'] for r in rows if certified(r['a']) and certified(r['b'])
                     and r['a']['upper'] != r['b']['upper']]
    invalid = [r['task_id'] for r in rows if r['b']['lp_step']['verdict'] != 'VALID']
    pooled = tally(rows)
    p = R32.mcnemar_one_sided(pooled['certified_b_not_a'], pooled['certified_a_not_b'])
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['a']['wall_s'] - r['b']['wall_s'])
    real = R32.BOOT_SEED
    R32.BOOT_SEED = BOOT_SEED
    try:
        est, ci = R32.boot_mean(by)
    finally:
        R32.BOOT_SEED = real
    sound = not disagreements and not invalid
    passes = {'sound': sound, 'coverage': pooled['certified_b'] >= pooled['certified_a'], 'mcnemar': p < 0.05,
              'time': ci[0] > 0}
    verdict = ('DEFECT_FOUND' if not sound else 'CERTIFICATION_UTILITY' if all(passes.values())
               else 'NO_CERTIFICATION_UTILITY')
    summary = {'schema': 'genesis-b20r47-c4-certification-v1', 'seeds': list(SEEDS),
               'settings': [{'family': f, 'params': q} for f, q in SETTINGS], 'budget_s': SECONDS, 'route_b': ROUTE,
               'registry': {'package_sha256': reg['package_sha256'], 'patterns': len(reg['patterns']),
                            'sha256': digest(reg)},
               'checker_identity': V4.checker_identity(), 'pooled': pooled,
               'by_setting': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted({r['stratum'] for r in rows})},
               'mcnemar_p_one_sided': round(p, 8), 'wall_saving_a_minus_b': {'mean': est, 'interval_90': ci},
               'disagreements': disagreements, 'invalid_certificates': invalid, 'passes': passes, 'verdict': verdict,
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
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
    reg = registry()
    log(f'registry: {len(reg["patterns"])} C4 patterns from {reg["package_sha256"][:16]}')
    tasks, scan = hosts(out, log)
    run(out, tasks, reg, log)
    s = analyse(out, tasks, scan, reg)
    log(f'verdict {s["verdict"]}: certified a {s["pooled"]["certified_a"]} b {s["pooled"]["certified_b"]}; McNemar p '
        f'{s["mcnemar_p_one_sided"]}; wall saving {s["wall_saving_a_minus_b"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
