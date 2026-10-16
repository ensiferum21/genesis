#!/usr/bin/env python3
"""B20_R35: certification with generated rows where the evaluator's certification fails (DEV;
s15.3 / W13; GV4 and GV3 paths).

    b20r35_dense_certification.py OUT_DIR            run (resumable) and analyse
    b20r35_dense_certification.py OUT_DIR --summary  analyse existing rows only

**Why.** B20_R32 measured B20_R31's Lean-checked generated rows as a certification component on
the `e1b` family. The route was sound but had NO_CERTIFICATION_UTILITY there, because hosts the
evaluator could not certify by its LP were rare. B20R32-OPEN-1 proposed a study enriched for such
hosts, with the enrichment fixed in advance. B20_R34 then found two settings where the
evaluator's 60 s certification mostly fails:
  * planted_cluster n40 p_in 0.8 p_out 0.06: 0/8 certified;
  * erdos n30 p0.42: 2/8 certified.
This step enriches by setting, choosing those two. Everything below is fixed before running.

**Hosts.** 20 fresh DEV hosts per setting, generator seeds 20263501 and 20263511. They exclude every
identity b20r24_repilots.exposure excludes: every graph host named under evidence/ and handoff/
(B20_R34's run and regenerated listings included), the regenerated E1 hosts, and the calibration
hosts. On resume the script reloads its own `hosts.json` instead of regenerating
(B20R34-OPEN-1).

**Per host.** Both routes start from the evaluator's own seed witness: the better of an 8-round DSL
solution and 1.0 CPU s of LP greedy.
  a  obstruction.certify(task, witness, seconds=60): the evaluator's joint certification at the
     calibration's limit;
  b  generated_certify.certify_with_rows(task, witness, registry, seconds=60,
     separation_seconds=10, max_rows=50000). The registry is B20_R31's Lean-CHECKED K5 and W5
     bounds. Copies are enumerated smallest pattern first, and enumeration stops at 10 s wall or
     50,000 copies per pattern; any subset of copies gives valid rows. The exact checker
     (verification.lp_dual_rows) checks b's LP certificate before b uses it.
  The routes run back to back, a first on even-numbered hosts and b first on odd ones. Each
  route's certified value, upper-bound method and wall time are recorded.

**Endpoints.**
  coverage  hosts certified (lower == upper) within 60 s by a and by b. The discordant pairs
            n_ba (b certifies, a does not) and n_ab get an exact one-sided McNemar test:
            p = P(Bin(n_ba + n_ab, 1/2) ≥ n_ba);
  time      per-host d = wall_a − wall_b, mean stratified by setting, bootstrap of 4000 resamples
            (seed 20263599), 90% interval.

**Soundness.** Every b LP certificate is VALID under the exact checker, and on hosts both routes
certify, the values agree. A disagreement makes the verdict DEFECT_FOUND.

**Verdict (fixed here).** CERTIFICATION_UTILITY iff all of these hold; otherwise
NO_CERTIFICATION_UTILITY:
  * sound;
  * b certifies at least as many hosts as a;
  * McNemar p < 0.05;
  * the 90% interval of mean d is above 0.

**Development looks before preregistration.** On three B20_R34 hosts of the dense planted
setting, which are excluded here, the builder computed three things:
  * the LP with K5 rows only, which met the certified optimum's floor on all three in under 0.9
    CPU s, against triangle-LP gaps of 8;
  * the LP with all W5 copies only, which gave no improvement and took 25–44 s for 160–260
    thousand copies;
  * HiGHS's exact MILP, which needed about 9.5 s to prove each optimum.
This look motivated the separation limits above. The builder then ran route b once, with these
limits, on the first of those hosts. It certified 122 in 16.0 s: the LP step took 6.5 s over 51,500
rows, and SAT raised the witness from 110 to 122. The design was not changed after either look.

A DEV measurement of a certification component. It licenses no claim, changes no evaluator, and
persists no certificate to custody. The certificates of discordant hosts are kept for re-checking.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.verification import lp_dual_rows as V  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402

TF = RD.TF
SETTINGS = [('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 30, 'p': 0.42})]
PER, SEEDS = 20, (20263501, 20263511)
SECONDS, SEPARATION_S, MAX_ROWS = 60, 10, 50000
BOOT_SEED = 20263599


def hosts(out, log):
    path = out / 'hosts.json'
    excluded, scan, _ = R24.exposure(log)
    if path.exists():                                    # resume: never regenerate (B20R34-OPEN-1)
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
        log(f'resume: {len(tasks)} hosts reloaded from hosts.json')
        return tasks, scan
    seen, tasks = set(excluded), []
    for seed, (family, params) in zip(SEEDS, SETTINGS):
        ts, seen, _ = ADAPTERS[TF].generate(seed, PER, 'DEV', family, params, excluded=seen)
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


def route_b(task, w, registry):
    rec = GC.certify_with_rows(task, w, registry, seconds=SECONDS, separation_seconds=SEPARATION_S, max_rows=MAX_ROWS)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'wall_s': rec['wall_s'],
            'lp_step': rec['steps'][0], 'certificate': rec['certificate']}


def certified(side):
    return side['lower'] == side['upper']


def run(out, tasks, registry, log):
    path = out / 'rows.jsonl'
    done = set()
    if path.exists():
        done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()}
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    t0 = time.monotonic()
    with path.open('a') as fh:
        for i, t in enumerate(tasks):
            if t.task_id in done:
                continue
            w = R32.seed_witness(t)
            if i % 2 == 0:
                a = route_a(t, w); b = route_b(t, w, registry)
            else:
                b = route_b(t, w, registry); a = route_a(t, w)
            cert = b.pop('certificate')
            b['certificate_sha256'] = cert and digest(cert)
            if cert is not None and certified(b) and not certified(a):
                (certs / f'{t.task_id}.json').write_text(json.dumps(cert, sort_keys=True))
            r = {'task_id': t.task_id, 'stratum': t.family, 'n': t.n, 'edges': len(t.edges),
                 'order': 'ab' if i % 2 == 0 else 'ba', 'witness': len(w), 'a': a, 'b': b}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: a {a["lower"]}..{a["upper"]} {a["method"]} {a["wall_s"]:.1f}s; '
                f'b {b["lower"]}..{b["upper"]} {b["method"]} {b["wall_s"]:.1f}s [{time.monotonic() - t0:.0f}s]')


def tally(rows):
    import statistics
    ca = [certified(r['a']) for r in rows]
    cb = [certified(r['b']) for r in rows]
    n = len(rows)
    return {'hosts': n, 'certified_a': sum(ca), 'certified_b': sum(cb),
            'certified_b_not_a': sum(b and not a for a, b in zip(ca, cb)),
            'certified_a_not_b': sum(a and not b for a, b in zip(ca, cb)),
            'lp_upper_b': sum(r['b']['method'] == 'LP_DUAL_GENERATED_EXACT' and certified(r['b']) for r in rows),
            'lp_upper_a': sum(r['a']['method'] == 'LP_DUAL_EXACT' and certified(r['a']) for r in rows),
            'wall_total_s': {'a': round(sum(r['a']['wall_s'] for r in rows), 2),
                             'b': round(sum(r['b']['wall_s'] for r in rows), 2)},
            'wall_median_s': {'a': round(statistics.median(r['a']['wall_s'] for r in rows), 3),
                              'b': round(statistics.median(r['b']['wall_s'] for r in rows), 3)} if n else None,
            'b_lp_rows_median': statistics.median(r['b']['lp_step']['rows'] for r in rows) if n else None,
            'b_lp_step_wall_s_max': max(r['b']['lp_step']['wall_s'] for r in rows) if n else None}


def analyse(out, tasks, scan, registry):
    import statistics
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
    summary = {'schema': 'genesis-b20r35-dense-certification-v1', 'seeds': list(SEEDS),
               'settings': [{'family': f, 'params': q} for f, q in SETTINGS], 'budget_s': SECONDS,
               'separation': {'seconds': SEPARATION_S, 'max_rows_per_pattern': MAX_ROWS, 'order': 'smallest first'},
               'registry': {'sha256': digest(registry), 'package_sha256': registry['package_sha256']},
               'checker_identity': V.checker_identity(), 'pooled': pooled,
               'by_stratum': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)},
               'mcnemar_p_one_sided': round(p, 8),
               'wall_saving_a_minus_b': {'mean': round(est, 3), 'interval_90': [round(ci[0], 3), round(ci[1], 3)],
                                         'by_stratum': {s: round(statistics.fmean(d), 3) for s, d in sorted(by.items())}},
               'value_disagreements': disagreements, 'invalid_b_certificates': invalid, 'passes': passes,
               'verdict': verdict, 'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV measurement of a certification component; licenses no claim; no evaluator change'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    registry = GC.load_registry()
    tasks, scan = hosts(out, log)
    if '--summary' not in argv:
        run(out, tasks, registry, log)
    s = analyse(out, tasks, scan, registry)
    log(f'verdict {s["verdict"]}: {s["pooled"]}; McNemar p {s["mcnemar_p_one_sided"]}; '
        f'saving {s["wall_saving_a_minus_b"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
