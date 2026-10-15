#!/usr/bin/env python3
"""B20_R31 (handoff s15.3, W10; GV4): generated valid inequalities as a component.

    b20r31_relaxation_invention.py OUT_DIR

Attempt 1 of the relaxation family, preregistered here. Every attempt counts. Families so far:
relational (retired after B20_R17 and B20_R19), quotient (B20_R26, NO_UTILITY_AFTER_COST) and
decomposition (B20_R27, NO_UTILITY_AFTER_COST).

The family is `invention.cuts`. The generator enumerates every graph F on at most six vertices
and keeps F when the inequality "a triangle-free subgraph has at most ex(F) edges on any copy of F"
is not implied by the triangle rows and the patterns kept before it. Lean checks every kept
inequality before it is used. The component solves the triangle LP strengthened by every copy of
the checked patterns, then runs the B20_RX3 LP-ordered greedy on those values. Earlier families
competed with the menu decoders; this one competes with the existing LP component itself.

Part A — generation and checking (rules fixed here, before running):
  * generation: cuts.generate() over the networkx atlas, every graph on at most six vertices;
  * obligations, stated over the repository definitions and PCDefs (PC.adj, 0/1 adjacency):
    pc_adj_le_one, pc_bridge, and one bound per kept pattern. Each is screened by sampling, then
    proved through formal_research.loop with the builder-written recipes in cuts.recipes (named
    in the receipts);
  * a pattern is usable iff its bound, pc_adj_le_one and pc_bridge are CHECKED;
    NEW_CHECKED iff at least one pattern is usable; otherwise NO_NEW_CHECKED_RELAXATION, and
    Parts B and C do not run;
  * construction cost as in B20_R17: the larger of this process's CPU (generation included, its
    waited-for children included) and the checker's own report.

Part B — utility after cost, the B20_R17 design on the decided E1b family:
  * hosts from the adopted e1b calibration's three selected settings (calibration.calibrated_panel,
    round-robin): SELECT 24 (8 per setting) with generator seed 20263101, EVAL 48 (16 per setting)
    with seed 20263102;
  * excluded: every identity b20r24_repilots.exposure excludes (every graph host named under
    evidence/ and handoff/, B20_R30's included; the regenerated E1 hosts; the calibration hosts),
    plus six DEV hosts the builder looked at while developing this family (generator seed 999101,
    two per selected setting);
  * every arm 1.0 CPU s per host, children included (discovery.construct.Budget). The domain
    checker validates every witness. Seeds come from the task identity;
  * arms:
    - new: cuts.cut_lp_greedy with every usable pattern;
    - control: discovery.construct.lp_greedy, the same component on the triangle LP alone. This
      isolates the generated rows;
    - menu: the best SELECT total among cross_2, ordered_2, adjacent_2 and adjacent_3;
    - conventional: the best SELECT total among the time-matched DSL programs;
    - matched: the control with 1.0 s + construction / 100 hosts. The control, not the menu, is
      the existing method this family must beat;
  * paired differences new − control, new − menu, new − conventional and new − matched,
    stratified by setting, bootstrap 4000 resamples, seed 20263199;
  * verdict: UTILITY_AFTER_COST iff every comparison has mean ≥ 0.5 edge per host and a 90%
    interval lower bound > 0; otherwise NO_UTILITY_AFTER_COST.

Part C — a certification diagnostic (no verdict, no evaluator change):
  * hosts: B20_R30's 90 hosts (evidence/certification_budget_b20r30), which the evaluator
    certified at 600 s. They are already exposed, and Part C makes no utility claim;
  * per certified host: the triangle-LP value, the strengthened-LP value (every copy, no time
    limit), the copies, the CPU time, and the certified optimum;
  * reported: hosts where floor(LP + 1e-6) equals the optimum, with and without the generated
    rows. An LP whose floor meets a known solution is the kind of bound the evaluator's exact LP
    dual turns into a certificate. The float LP here is a measurement, never a certificate.

While developing this family, before preregistration, the builder looked at the six excluded
hosts. It computed the LP bound with and without K5 and W5 rows, plain lp_greedy, and a certified
optimum. The rows moved the LP bound little. The cut-ordered greedy was not run on them. The builder
also timed the component on three B20_R30 hosts. Separation and LP took at most 0.28 CPU s. It saw
their LP values, but not the greedy's values. Those hosts are excluded from Part B, as all of
B20_R30's are, and Part C includes them. The design was not changed after either look.

A DEV study. It licenses no claim, its hosts are exposed, and this is attempt 1 of the relaxation
family.
"""
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r17_relation_invention as R17  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
from genesis import calibration as CAL  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery.construct import Budget, lp_greedy  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.invention import cuts as C  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

STUDY = 'e1b'
SEEDS = (20263101, 20263102)
SELECT_PER, EVAL_PER = 8, 16
BOOT_SEED = 20263199
DEVELOPMENT_LOOK = (999101, 2)
R30 = ROOT / 'evidence' / 'certification_budget_b20r30'
TOL = 1e-6


# ---------------------------------------------------------------- Part A

def part_a(out, log):
    budget = Budget(1e9)
    stats = {}
    patterns = C.generate(stats=stats)
    conjs = C.conjectures(patterns)
    screened = {}
    for c in conjs:
        cx, relevant = L.screen(c)
        screened[c['id']] = {'result': 'COUNTEREXAMPLE' if cx is not None else 'NO_COUNTEREXAMPLE',
                             'instances_meeting_hypotheses': relevant}
    base = [R17.DEFS, {'name': C.MODULE, 'source': C.SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='PCConj', proof_prefix='PCP',
                        unfold=['GT.TriangleFree'], extra_recipes=C.recipes(patterns), log=log)
    statuses, usable = C.obligations_ok(state, patterns)
    prop = C.proposal(usable)
    pkg, _ = L.assemble(state, name='generated pattern inequalities (s15.3, attempt 1 of the relaxation family)',
                        domain=R17.TF,
                        scope=('0/1 adjacency of an edge set, the triangle bridge, and one bound per generated '
                               'pattern: on every assignment of the pattern\'s vertices, a triangle-free edge set in '
                               'host form has at most ex(F) of the pattern\'s edges. Conservative definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'pattern statements quantify over every assignment of the pattern vertices, '
                                     'degenerate ones included'],
                        extra={'candidates': [R17.public(prop)], 'generation': stats,
                               'patterns': [{k: p[k] for k in ('id', 'vertices', 'edges', 'ex', 'lp', 'lp_triangle_rows')}
                                            for p in patterns]})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    R17.dump(out / 'package.json', pkg)
    summary = {'generation': stats, 'patterns': [p['id'] for p in patterns], 'usable': [p['id'] for p in usable],
               'obligations': statuses, 'screen': screened, 'candidate': prop['id'],
               'construction_cpu_s': round(construction, 3), 'checker_cpu_s_reported': round(checker, 3),
               'verdict_a': 'NEW_CHECKED' if usable else 'NO_NEW_CHECKED_RELAXATION'}
    R17.dump(out / 'part_a.json', summary)
    log(f'Part A: {statuses}; construction {construction:.1f} CPU s -> {summary["verdict_a"]}')
    return usable, max(construction, checker), summary


# ---------------------------------------------------------------- Part B

def development_look(record):
    a = ADAPTERS[R17.TF]
    seed, count = DEVELOPMENT_LOOK
    out = []
    for s in record['selected']:
        tasks, _, _ = a.generate(seed, count, 'DEV', s['family'], s['params'])
        out += tasks
    return out


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    record = CAL.load(R17.TF, ROOT, study=STUDY)
    look = development_look(record)
    excluded = set(excluded) | RD.identities(look)
    k = len(record['selected'])
    sel, seen = CAL.calibrated_panel(record, SEEDS[0], SELECT_PER * k, 'DEV', excluded=excluded)
    ev, _ = CAL.calibrated_panel(record, SEEDS[1], EVAL_PER * k, 'DEV', excluded=seen)
    if RD.identities(sel + ev) & excluded:
        raise RuntimeError('a generated host collides with an excluded host')
    scan = dict(scan, development_look_hosts=len(look))
    return {'select': sel, 'eval': ev}, scan, record


def run_arm(task, arm, seed, seconds):
    if arm['kind'] in ('representation', 'program'):
        value, cpu = R17.run_arm(task, arm, seed, seconds)
        return value, cpu, None
    b = Budget(seconds)
    if arm['kind'] == 'cuts':
        o = C.cut_lp_greedy(task, arm['patterns'], b, seed)
        diag = {'copies': o['copies'], 'lp_value': round(o['lp_value'], 4)}
    else:
        o = lp_greedy(task, b, seed)
        diag = None
    cpu = b.used()
    value = check_witness(task, [tuple(e) for e in o['witness']])['value']      # raises on an invalid witness
    return value, cpu, diag


def part_b(out, log, usable, construction):
    hs, scan, record = hosts(log)
    seed_of = lambda t: int(digest({'b20r31': t.task_id})[:12], 16)
    reps = {r['id']: r for r in RP.proposals()}
    arms = {'new:cut_lp_greedy': {'kind': 'cuts', 'patterns': usable}, 'control:lp_greedy': {'kind': 'lp'}}
    arms.update({f'menu:{m}': {'kind': 'representation', 'rep': reps[m]} for m in R17.MENU})
    arms.update({f'conv:{n}_tm': {'kind': 'program', 'program': p.model_dump(mode='json')}
                 for n, p in sorted(baseline_programs().items())})
    select = {name: 0 for name in arms if name.startswith(('menu:', 'conv:'))}
    for t in hs['select']:
        for name in select:
            select[name] += run_arm(t, arms[name], seed_of(t), R17.BUDGET_S)[0]
    pick = lambda prefix: max((n for n in select if n.startswith(prefix)), key=lambda n: (select[n], n))
    chosen = {'new': 'new:cut_lp_greedy', 'control': 'control:lp_greedy', 'menu': pick('menu:'),
              'conventional': pick('conv:')}
    extra_s = construction / R17.HORIZON
    log(f'SELECT totals {select} -> {chosen}; matched arm gets {R17.BUDGET_S + extra_s:.3f} s')
    rows = []
    for t in hs['eval']:
        s = seed_of(t)
        v, cpu, diag = {}, {}, {}
        for role in ('new', 'control', 'menu', 'conventional'):
            v[role], cpu[role], diag[role] = run_arm(t, arms[chosen[role]], s, R17.BUDGET_S)
        v['matched'], cpu['matched'], _ = run_arm(t, arms[chosen['control']], s, R17.BUDGET_S + extra_s)
        rows.append({'setting': t.family, 'task_id': t.task_id, 'values': v, 'cpu_s': cpu,
                     'diagnostics': {k: x for k, x in diag.items() if x is not None}})
        log(f'{t.family} {t.task_id[-4:]}: {v}')
    real = R17.BOOT_SEED
    R17.BOOT_SEED = BOOT_SEED
    try:
        comparisons = {}
        for other in ('control', 'menu', 'conventional', 'matched'):
            by = {}
            for r in rows:
                by.setdefault(r['setting'], []).append(r['values']['new'] - r['values'][other])
            est, ci = R17.boot(by)
            flat = [d for ds in by.values() for d in ds]
            comparisons[other] = {'mean': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                  'by_setting': {k: round(statistics.fmean(d), 4) for k, d in sorted(by.items())},
                                  'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat),
                                                       sum(d < 0 for d in flat)],
                                  'passes': est >= R17.MUE and ci[0] > 0}
    finally:
        R17.BOOT_SEED = real
    verdict = 'UTILITY_AFTER_COST' if all(c['passes'] for c in comparisons.values()) else 'NO_UTILITY_AFTER_COST'
    summary = {'select_totals': select, 'chosen': chosen, 'budget_s': R17.BUDGET_S, 'horizon': R17.HORIZON,
               'construction_cpu_s': round(construction, 3), 'matched_extra_s_per_host': round(extra_s, 4),
               'comparisons': comparisons, 'verdict': verdict, 'exposure_scan': scan,
               'calibration': {'study': STUDY, 'record_sha256': digest(record), 'selected': record['selected']},
               'hosts': {k: [t.task_id for t in v] for k, v in hs.items()},
               'mean_cpu_s': {role: round(statistics.fmean(r['cpu_s'][role] for r in rows), 3)
                              for role in ('new', 'control', 'menu', 'conventional', 'matched')}}
    R17.dump(out / 'part_b_rows.json', rows)
    R17.dump(out / 'hosts.json', {k: [t.model_dump(mode='json') for t in v] for k, v in hs.items()})
    R17.dump(out / 'part_b.json', summary)
    log(f'Part B: {json.dumps(comparisons)} -> {verdict}')
    return summary


# ---------------------------------------------------------------- Part C

def part_c(out, log, usable):
    tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t)) for t in json.loads((R30 / 'hosts.json').read_text())['tasks']}
    r30 = [json.loads(l) for l in (R30 / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in r30} != set(tasks):
        raise RuntimeError('B20_R30 is incomplete; Part C needs its 90 rows')
    rows = []
    for r in r30:
        if r['evaluator']['status'] != 'FINITE_CERTIFIED':
            continue
        t = tasks[r['task_id']]
        opt = r['evaluator']['value']
        _, _, tri = C.cut_lp_values(t, [])
        b = Budget(1e9)
        _, copies, cut = C.cut_lp_values(t, usable)
        rows.append({'task_id': t.task_id, 'setting': t.family, 'optimum': opt, 'lp_triangle': round(tri, 6),
                     'lp_generated': round(cut, 6), 'cpu_s': round(b.used(), 3),
                     'copies': {k: list(v) for k, v in copies.items()},
                     'floor_meets_optimum': {'triangle': math.floor(tri + TOL) == opt,
                                             'generated': math.floor(cut + TOL) == opt}})
    by = {}
    for r in rows:
        by.setdefault(r['setting'], []).append(r)

    def tally(rs):
        n = len(rs)
        return {'certified_hosts': n,
                'floor_meets_optimum_triangle': sum(r['floor_meets_optimum']['triangle'] for r in rs),
                'floor_meets_optimum_generated': sum(r['floor_meets_optimum']['generated'] for r in rs),
                'newly_met_by_generated_rows': sum(r['floor_meets_optimum']['generated'] and
                                                   not r['floor_meets_optimum']['triangle'] for r in rs),
                'mean_gap_triangle': round(statistics.fmean(r['lp_triangle'] - r['optimum'] for r in rs), 4) if n else None,
                'mean_gap_generated': round(statistics.fmean(r['lp_generated'] - r['optimum'] for r in rs), 4) if n else None,
                'median_cpu_s': round(statistics.median(r['cpu_s'] for r in rs), 3) if n else None}
    summary = {'source': 'evidence/certification_budget_b20r30 (evaluator at 600 s)', 'pooled': tally(rows),
               'by_setting': {k: tally(v) for k, v in sorted(by.items())},
               'status': 'diagnostic; float LP values are measurements, not certificates; no evaluator change'}
    R17.dump(out / 'part_c_rows.json', rows)
    R17.dump(out / 'part_c.json', summary)
    log(f'Part C: {summary["pooled"]}')
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    if (out / 'summary.json').exists():
        raise FileExistsError(out / 'summary.json')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    usable, construction, a = part_a(out, log)
    b = part_b(out, log, usable, construction) if usable else None
    c = part_c(out, log, usable) if usable else None
    verdict = b['verdict'] if b else a['verdict_a']
    R17.dump(out / 'summary.json', {'schema': 'genesis-b20r31-relaxation-invention-v1', 'part_a': a, 'part_b': b,
                                    'part_c': c, 'verdict': verdict, 'family': C.FAMILY,
                                    'attempts_in_family': ['B20_R31'],
                                    'other_families': {'relational': {'attempts': ['B20_R17', 'B20_R19'],
                                                                      'state': 'retired'},
                                                       'quotient': {'attempts': ['B20_R26']},
                                                       'decomposition': {'attempts': ['B20_R27']}},
                                    'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
