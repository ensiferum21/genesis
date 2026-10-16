#!/usr/bin/env python3
"""B20_R37 (s15.3 / W10, W13; GV4 and GV3 paths): generated rows on up to seven vertices, and
certification coverage in the dense regime (DEV).

    b20r37_generator_v2.py OUT_DIR            run (resumable in Part B) and analyse

**Why.** B20_R35 found CERTIFICATION_UTILITY for B20_R31's generated rows (K5 ≤ 6, W5 ≤ 7) in two
dense settings: 27/40 hosts certified within 60 s, against the evaluator's 7/40. That is still
below the 90% limit a calibrated family needs. B20_R36 found, exploratorily, that in the dense
planted regime E1's representation (`cross_2`) is optimal where an exact MIP at 2 s is far
below. A certifiable dense family would therefore let GV3's "beyond strong baselines" be tested
(B20R33-OPEN-1). On B20_R35's uncertified hosts, rows from 7-vertex patterns closed most LP gaps
in a development look. This step generates and checks those rows and measures what they add.
Everything below is fixed before running.

**Part A — generation and checking.**
  * `invention.cuts_v2.generate()`: every graph on at most seven vertices (networkx atlas). F is
    kept by B20_R31's rule extended to seven vertices: F connected, every edge in a triangle, and
    F's LP under the triangle rows and the earlier kept patterns' copies above ex(F). ex(F) comes
    from HiGHS's MILP, re-checked as a triangle-free subset.
  * Lean (PCDefs, unchanged): pc_adj_le_one, pc_adj_comm (new), pc_bridge, and one bound per kept
    pattern. Each is screened by sampling, then proved through formal_research.loop. The
    builder-written recipes are in cuts_v2.recipes: an integer rounding certificate from the
    pattern's LP dual, as summed facts, then omega. Patterns with 17 or more edges get a larger
    elaboration budget, `set_option maxHeartbeats 4000000 in`, before the theorem
    (formal_research.search.split_options).
  * A pattern is usable iff its bound and the three base lemmas are CHECKED. The registry
    (verification.lp_dual_rows.registry_from_package) is built from this package.
  * Part B runs iff at least one usable pattern is not in B20_R31's registry.

**Part B — certification coverage, preregistered.**
  * Hosts: 20 fresh DEV hosts per setting (planted_cluster n40 p_in 0.8 p_out 0.06, and erdos n30
    p0.42), generator seeds 20263701 and 20263711. They exclude every identity
    b20r24_repilots.exposure excludes, and are reloaded from hosts.json on resume.
  * Per host, both routes start from the evaluator's seed witness (B20_R32 seed_witness), each at
    60 s wall, back to back. v1 runs first on even-numbered hosts and v2 first on odd ones.
      v1  B20_R35's route exactly: B20_R31's registry, generic enumeration, size order, 10 s or
          50,000 copies per pattern.
      v2  this package's registry; `cuts_v2.maps_fast` enumeration; patterns densest first;
          enumeration stops at 15 s wall, 50,000 copies per pattern or 80,000 copies in all.
    The exact checker (verification.lp_dual_rows) checks every LP certificate first.
  * Endpoints: hosts certified within 60 s by each route; discordant pairs with an exact one-sided
    McNemar test; per-host wall saving (v1 − v2), stratified bootstrap of 4000 resamples (seed
    20263799), 90% interval; and per setting, whether v2 reaches the 90% limit (18 of 20).
  * Soundness: every certificate VALID and, where both routes certify, equal values; otherwise
    DEFECT_FOUND.
  * Verdict (fixed): V2_EXTENDS_COVERAGE iff sound, v2 certifies at least as many hosts as v1, and
    McNemar p < 0.05; otherwise NO_COVERAGE_GAIN. The 90% flags are reported, not gating.

**Development looks before preregistration.** All on B20_R35 hosts, which are excluded here:
  * LP bounds with K5, K7 and K7−e rows, and with the 7-vertex sparse patterns, against MILP
    optima on that study's 13 uncertified hosts;
  * copy-enumeration timings on two of those hosts;
  * the Lean pre-test of every obligation, which checked all of them after the recipe was made
    to hoist the heartbeat option;
  * a smoke run of route v2, with a registry made directly from the generated patterns, on two
    of the B20_R35 hosts the v1 route had not certified. v2 certified both in 30.6 s and 18.1 s,
    with LP steps of about 80,000 rows taking 19.4 s and 9.7 s.
The design was not changed after these looks, except that development settled the separation
limits above.

A DEV study. It licenses no claim, changes no evaluator, and persists no certificate to custody.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import construct as K  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.formal_research.triangle_theory import DEFS_SOURCE  # noqa: E402
from genesis.invention import cuts_v2 as C2  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.verification import lp_dual_rows as V  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r17_relation_invention as R17  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402

TF = RD.TF
SETTINGS = [('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 30, 'p': 0.42})]
PER, SEEDS = 20, (20263701, 20263711)
SECONDS = 60
V1 = {'separation_seconds': 10, 'max_rows': 50000}
V2 = {'separation_seconds': 15, 'max_rows': 50000, 'max_total': 80000, 'order': 'dense-first', 'enumerator': 'fast'}
BOOT_SEED = 20263799
LIMIT = 18


def part_a(out, log):
    path = out / 'package.json'
    if path.exists():                                     # resume: never rebuild the package
        pkg = json.loads(path.read_text())
        return pkg, json.loads((out / 'part_a.json').read_text())
    budget = K.Budget(1e9)
    stats = {}
    patterns = C2.generate(stats=stats)
    conjs = C2.conjectures(patterns)
    screened = {}
    for c in conjs:
        cx, relevant = L.screen(c)
        screened[c['id']] = {'result': 'COUNTEREXAMPLE' if cx is not None else 'NO_COUNTEREXAMPLE',
                             'instances_meeting_hypotheses': relevant}
    base = [R17.DEFS, {'name': C2.MODULE, 'source': C2.SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='PC2Conj', proof_prefix='PC2P',
                        unfold=['GT.TriangleFree'], extra_recipes=C2.recipes(patterns), log=log)
    statuses, usable = C2.obligations_ok(state, patterns)
    pkg, _ = L.assemble(state, name='generated pattern inequalities v2 (s15.3, relaxation family; seven vertices)',
                        domain=R17.TF,
                        scope=('0/1 adjacency, its symmetry, the triangle bridge, and one bound per pattern generated '
                               'over every graph on at most seven vertices. Conservative definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'pattern statements quantify over every assignment of the pattern vertices'],
                        extra={'generation': stats,
                               'patterns': [{k: p[k] for k in ('id', 'vertices', 'edges', 'ex', 'ex_witness', 'lp',
                                                               'lp_triangle_rows')} for p in patterns]})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    R17.dump(path, pkg)
    v1 = GC.load_registry()
    summary = {'generation': stats, 'patterns': [p['id'] for p in patterns], 'usable': [p['id'] for p in usable],
               'new_usable': [p['id'] for p in usable if f'pc_{p["id"]}' not in v1['patterns']],
               'obligations': statuses, 'screen': screened, 'construction_cpu_s': round(construction, 3),
               'checker_cpu_s_reported': round(checker, 3)}
    R17.dump(out / 'part_a.json', summary)
    log(f'Part A: {statuses}; construction {construction:.1f} CPU s')
    return pkg, summary


def registry_v2(pkg):
    problems = TP.integrity_problems(pkg)
    if problems:
        raise RuntimeError(f'package integrity: {problems}')
    return V.registry_from_package(pkg, defs_source=DEFS_SOURCE)


def hosts(out, log):
    path = out / 'hosts.json'
    excluded, scan, _ = R24.exposure(log)
    if path.exists():
        log('resume: hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']], scan
    seen, tasks = set(excluded), []
    for seed, (family, params) in zip(SEEDS, SETTINGS):
        ts, seen, _ = ADAPTERS[TF].generate(seed, PER, 'DEV', family, params, excluded=seen)
        tasks += ts
    if RD.identities(tasks) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'seeds': list(SEEDS), 'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
                    'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks, scan


def route(task, w, registry, cfg):
    rec = GC.certify_with_rows(task, w, registry, seconds=SECONDS, **cfg)
    return {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['method'], 'wall_s': rec['wall_s'],
            'lp_step': rec['steps'][0], 'certificate': rec['certificate']}


def certified(side):
    return side['lower'] == side['upper']


def tally(rows):
    import statistics
    c1 = [certified(r['v1']) for r in rows]
    c2 = [certified(r['v2']) for r in rows]
    return {'hosts': len(rows), 'certified_v1': sum(c1), 'certified_v2': sum(c2),
            'certified_v2_not_v1': sum(b and not a for a, b in zip(c1, c2)),
            'certified_v1_not_v2': sum(a and not b for a, b in zip(c1, c2)),
            'reaches_limit_v2': sum(c2) >= LIMIT if len(rows) == PER else None,
            'wall_total_s': {k: round(sum(r[k]['wall_s'] for r in rows), 2) for k in ('v1', 'v2')},
            'wall_median_s': {k: round(statistics.median(r[k]['wall_s'] for r in rows), 3) for k in ('v1', 'v2')},
            'lp_rows_median': {k: statistics.median(r[k]['lp_step']['rows'] for r in rows) for k in ('v1', 'v2')},
            'lp_step_wall_s_max': {k: max(r[k]['lp_step']['wall_s'] for r in rows) for k in ('v1', 'v2')}}


def part_b(out, log, reg1, reg2):
    import statistics
    tasks, scan = hosts(out, log)
    path = out / 'part_b_rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    t0 = time.monotonic()
    with path.open('a') as fh:
        for i, t in enumerate(tasks):
            if t.task_id in done:
                continue
            w = R32.seed_witness(t)
            if i % 2 == 0:
                a = route(t, w, reg1, V1); b = route(t, w, reg2, V2)
            else:
                b = route(t, w, reg2, V2); a = route(t, w, reg1, V1)
            ca, cb = a.pop('certificate'), b.pop('certificate')
            a['certificate_sha256'], b['certificate_sha256'] = ca and digest(ca), cb and digest(cb)
            if cb is not None and certified(b) and not certified(a):
                (certs / f'{t.task_id}.json').write_text(json.dumps(cb, sort_keys=True))
            r = {'task_id': t.task_id, 'stratum': t.family, 'edges': len(t.edges), 'order': 'v1v2' if i % 2 == 0 else 'v2v1',
                 'witness': len(w), 'v1': a, 'v2': b}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id}: v1 {a["lower"]}..{a["upper"]} {a["wall_s"]:.1f}s; v2 {b["lower"]}..{b["upper"]} '
                f'{b["wall_s"]:.1f}s rows {b["lp_step"]["rows"]} [{time.monotonic() - t0:.0f}s]')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    disagreements = [r['task_id'] for r in rows if certified(r['v1']) and certified(r['v2'])
                     and r['v1']['upper'] != r['v2']['upper']]
    invalid = [r['task_id'] for r in rows for k in ('v1', 'v2') if r[k]['lp_step']['verdict'] != 'VALID']
    pooled = tally(rows)
    p = R32.mcnemar_one_sided(pooled['certified_v2_not_v1'], pooled['certified_v1_not_v2'])
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['v1']['wall_s'] - r['v2']['wall_s'])
    real = R32.BOOT_SEED
    R32.BOOT_SEED = BOOT_SEED
    try:
        est, ci = R32.boot_mean(by)
    finally:
        R32.BOOT_SEED = real
    sound = not disagreements and not invalid
    verdict = ('DEFECT_FOUND' if not sound else 'V2_EXTENDS_COVERAGE'
               if pooled['certified_v2'] >= pooled['certified_v1'] and p < 0.05 else 'NO_COVERAGE_GAIN')
    summary = {'pooled': pooled, 'by_stratum': {s: tally([r for r in rows if r['stratum'] == s]) for s in sorted(by)},
               'mcnemar_p_one_sided': round(p, 8),
               'wall_saving_v1_minus_v2': {'mean': round(est, 3), 'interval_90': [round(ci[0], 3), round(ci[1], 3)],
                                           'by_stratum': {s: round(statistics.fmean(d), 3) for s, d in sorted(by.items())}},
               'value_disagreements': disagreements, 'invalid_certificates': invalid, 'sound': sound,
               'verdict': verdict, 'exposure_scan': scan, 'routes': {'v1': V1, 'v2': V2}, 'budget_s': SECONDS}
    R17.dump(out / 'part_b.json', summary)
    log(f'Part B: {verdict}; {pooled}; McNemar p {p}; saving {summary["wall_saving_v1_minus_v2"]}')
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    if (out / 'summary.json').exists():
        raise FileExistsError(out / 'summary.json')
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    pkg, a = part_a(out, log)
    reg1, reg2 = GC.load_registry(), registry_v2(pkg)
    b = part_b(out, log, reg1, reg2) if a['new_usable'] else None
    verdict = b['verdict'] if b else 'NO_NEW_CHECKED_PATTERN'
    R17.dump(out / 'summary.json', {'schema': 'genesis-b20r37-generator-v2-v1', 'part_a': a, 'part_b': b,
                                    'registry_v2': {'sha256': digest(reg2), 'patterns': sorted(reg2['patterns'])},
                                    'checker_identity': V.checker_identity(), 'verdict': verdict,
                                    'code_identity': code_identity(ROOT)['sha256'],
                                    'status': 'DEV; licenses no claim; no evaluator change'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
