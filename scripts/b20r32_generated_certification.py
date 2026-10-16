#!/usr/bin/env python3
"""B20_R32 (s15.3 / W10, GV4): certification with generated rows, prospective on fresh hosts (DEV).

    b20r32_generated_certification.py OUT_DIR            run (resumable) and analyse
    b20r32_generated_certification.py OUT_DIR --summary  analyse existing rows only

B20_R31 found, on a float diagnostic, that its generated pattern rows bring the LP floor down to
the certified optimum on 10 of the 18 B20_R30 hosts whose upper bound needed SAT. This step builds
the exact route and measures it on fresh hosts. Everything below is fixed before running.

The route (`discovery.generated_certify.certify_with_rows`) is the evaluator's joint
certification (`discovery.obstruction.certify`) with one change: the LP has a row for every copy of
every pattern in the registry of the B20_R31 theory package (K5 ≤ 6, W5 ≤ 7, Lean-CHECKED). The
LP dual is made exact and checked by `verification.lp_dual_rows.check_certificate`. The SAT/DRAT
step is unchanged. Nothing is wired into the evaluator.

Hosts: 90 fresh DEV hosts, drawn round-robin from the adopted `e1b` calibration's three selected
settings (calibration.calibrated_panel), generator seed 20263201. They exclude every identity
b20r24_repilots.exposure excludes: every graph host named under evidence/ and handoff/
(B20_R30 and B20_R31 included, and B20_R31's development-look hosts), the regenerated E1 hosts,
and the calibration hosts.

Per host:
  witness  the evaluator's own seed (domains.GraphHostAdapter._joint_reference): the better of
           an 8-round DSL solution and 1.0 CPU s of LP-ordered greedy (seed 0), computed once
           and given to both routes;
  a        obstruction.certify(task, witness, seconds=600): the evaluator's certification;
  b        generated_certify.certify_with_rows(task, witness, registry, seconds=600).
  The two routes run back to back. a runs first on even-numbered hosts and b first on odd ones.
  Each route's wall time and its upper-bound method are recorded.

Endpoints:
  coverage      hosts certified (lower == upper) by a and by b;
  proof-free    hosts whose certified upper bound is an exact LP dual (a: LP_DUAL_EXACT; b:
                LP_DUAL_GENERATED_EXACT), so that no UNSAT proof is needed. The discordant pairs
                n_ba (b LP, a not) and n_ab (a LP, b not) get an exact one-sided McNemar test,
                p = P(Bin(n_ba + n_ab, 1/2) ≥ n_ba);
  time          per-host d = wall_a − wall_b. Its mean is stratified by setting, with a bootstrap
                of 4000 resamples (seed 20263299) and a 90% interval.

Soundness: every b certificate is checked VALID by the exact checker (an invalid one is not
used), and on hosts both certify, the values must agree. A disagreement makes the verdict
DEFECT_FOUND.

Verdict (fixed here): CERTIFICATION_UTILITY iff sound, b certifies at least as many hosts as a,
McNemar p < 0.05, and the 90% interval of mean d lies above 0. Otherwise
NO_CERTIFICATION_UTILITY.

Development looks before preregistration: the builder ran route b on the K6 host (bound 9) and
on one B20_R30 host (…20263001-0006). That host's witness was 95, and the generated LP bound
was 96 against its optimum of 96. SAT found a 96 witness in 11 s, so b certified in 11.3 s. The
evaluator had needed 334 s on that host, to prove 97 impossible. The builder also ran this
script's code path, both routes at 60 s, on two more B20_R30 hosts (…-0001, …-0002). Both routes
certified both hosts by LP, with b about 0.1 s slower. B20_R30's hosts are excluded here. The
design was not changed after these looks.

A DEV measurement of a certification component. It licenses no claim, changes no evaluator, and
persists no certificate to custody. The certificates for discordant hosts are kept in the
evidence for re-checking.
"""
import json
from math import comb
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import construct as K  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.dsl import solve  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402
from genesis.verification import lp_dual_rows as V  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402

TF = RD.TF
STUDY, HOSTS, SEED = 'e1b', 90, 20263201
SECONDS = 600
BOOT, BOOT_SEED = 4000, 20263299


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    record = CAL.load(TF, ROOT, study=STUDY)
    tasks, _ = CAL.calibrated_panel(record, SEED, HOSTS, 'DEV', excluded=excluded)
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    return tasks, scan, record


def seed_witness(task):
    start = tuple(map(tuple, solve(task, SolverProgram(rounds=8), 100000, 0)['selected']))
    lp = tuple(map(tuple, K.lp_greedy(task, K.Budget(1.0), 0)['witness']))
    return max((start, lp), key=len)


def route_a(task, w):
    rec = O.certify(task, w, seconds=SECONDS)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['upper_evidence']['method'],
            'wall_s': rec['wall_s'], 'lp_step': rec['steps'][0]}


def route_b(task, w, registry):
    rec = GC.certify_with_rows(task, w, registry, seconds=SECONDS)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'wall_s': rec['wall_s'],
            'lp_step': rec['steps'][0], 'certificate': rec['certificate']}


def run(out, tasks, registry, log):
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        done = {json.loads(l)['task_id'] for l in rows_path.read_text().splitlines() if l.strip()}
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    t0 = time.monotonic()
    with rows_path.open('a') as fh:
        for i, t in enumerate(tasks):
            if t.task_id in done:
                continue
            w = seed_witness(t)
            if i % 2 == 0:
                a = route_a(t, w); b = route_b(t, w, registry)
            else:
                b = route_b(t, w, registry); a = route_a(t, w)
            cert = b.pop('certificate')
            b['certificate_sha256'] = cert and digest(cert)
            a_lp, b_lp = a['method'] == 'LP_DUAL_EXACT', b['method'] == 'LP_DUAL_GENERATED_EXACT'
            if cert is not None and b['lower'] == b['upper'] and b_lp and not a_lp:
                (certs / f'{t.task_id}.json').write_text(json.dumps(cert, sort_keys=True))
            r = {'task_id': t.task_id, 'stratum': t.family, 'edges': len(t.edges), 'order': 'ab' if i % 2 == 0 else 'ba',
                 'witness': len(w), 'a': a, 'b': b}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: a {a["lower"]}..{a["upper"]} {a["method"]} {a["wall_s"]:.1f}s; '
                f'b {b["lower"]}..{b["upper"]} {b["method"]} {b["wall_s"]:.1f}s [{time.monotonic() - t0:.0f}s]')


def certified(side):
    return side['lower'] == side['upper']


def boot_mean(by):
    rng = random.Random(BOOT_SEED)
    strata = sorted(by)
    est = statistics.fmean(statistics.fmean(by[s]) for s in strata)
    sims = sorted(statistics.fmean(statistics.fmean(rng.choice(by[s]) for _ in by[s]) for s in strata)
                  for _ in range(BOOT))
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def mcnemar_one_sided(n_ba, n_ab):
    n = n_ba + n_ab
    return sum(comb(n, i) for i in range(n_ba, n + 1)) / 2 ** n if n else 1.0


def tally(rows):
    n = len(rows)
    lp_a = [r['a']['method'] == 'LP_DUAL_EXACT' and certified(r['a']) for r in rows]
    lp_b = [r['b']['method'] == 'LP_DUAL_GENERATED_EXACT' and certified(r['b']) for r in rows]
    wa = [r['a']['wall_s'] for r in rows]
    wb = [r['b']['wall_s'] for r in rows]
    return {'hosts': n, 'certified_a': sum(certified(r['a']) for r in rows),
            'certified_b': sum(certified(r['b']) for r in rows),
            'lp_upper_a': sum(lp_a), 'lp_upper_b': sum(lp_b),
            'lp_upper_b_not_a': sum(b and not a for a, b in zip(lp_a, lp_b)),
            'lp_upper_a_not_b': sum(a and not b for a, b in zip(lp_a, lp_b)),
            'wall_total_s': {'a': round(sum(wa), 2), 'b': round(sum(wb), 2)},
            'wall_median_s': {'a': round(statistics.median(wa), 3), 'b': round(statistics.median(wb), 3)} if n else None,
            'b_lp_step_cpu_s_median': round(statistics.median(r['b']['lp_step']['cpu_s'] for r in rows), 3) if n else None,
            'b_lp_rows_median': statistics.median(r['b']['lp_step']['rows'] for r in rows) if n else None}


def analyse(out, tasks, scan, record, registry):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    disagreements = [r['task_id'] for r in rows if certified(r['a']) and certified(r['b']) and r['a']['upper'] != r['b']['upper']]
    invalid = [r['task_id'] for r in rows if r['b']['lp_step']['verdict'] != 'VALID']
    pooled = tally(rows)
    p = mcnemar_one_sided(pooled['lp_upper_b_not_a'], pooled['lp_upper_a_not_b'])
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['a']['wall_s'] - r['b']['wall_s'])
    est, ci = boot_mean(by)
    sound = not disagreements and not invalid
    passes = {'sound': sound, 'coverage': pooled['certified_b'] >= pooled['certified_a'], 'mcnemar': p < 0.05,
              'time': ci[0] > 0}
    verdict = ('DEFECT_FOUND' if not sound else 'CERTIFICATION_UTILITY' if all(passes.values())
               else 'NO_CERTIFICATION_UTILITY')
    summary = {'schema': 'genesis-b20r32-generated-certification-v1', 'study': STUDY, 'seed': SEED,
               'budget_s': SECONDS, 'registry': {'sha256': digest(registry), 'package_sha256': registry['package_sha256'],
                                                 'patterns': {k: {'ex': v['ex'], 'vertices': v['vertices']}
                                                              for k, v in registry['patterns'].items()}},
               'checker_identity': V.checker_identity(),
               'calibration': {'record_sha256': digest(record), 'selected': record['selected']},
               'pooled': pooled, 'by_stratum': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)},
               'mcnemar_p_one_sided': round(p, 6),
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
    tasks, scan, record = hosts(log)
    R11.dump(out / 'hosts.json', {'study': STUDY, 'seed': SEED, 'tasks': [t.model_dump(mode='json') for t in tasks]})
    if '--summary' not in argv:
        run(out, tasks, registry, log)
    s = analyse(out, tasks, scan, record, registry)
    log(f'verdict {s["verdict"]}: {s["pooled"]}; McNemar p {s["mcnemar_p_one_sided"]}; '
        f'saving {s["wall_saving_a_minus_b"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
