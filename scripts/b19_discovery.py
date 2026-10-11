#!/usr/bin/env python3
"""B19: useful discovery, part 1 (roadmap W13–W15), DEV material only.

  b19_discovery.py OUT_DIR [--quick] [--phases obstruction,active,catalysis]

obstruction (W13): Lean lemmas for motif-inequality validity, then joint certification
    (construction + LP dual certificate + SAT/DRAT fallback) against the reference
    (greedy start + SAT/DRAT), on fresh hard DEV instances under the same wall budget.
active (W14): real outcome pools (did each method reach the certified optimum?) for
    three families. EIG, round-robin and random selection are compared under equal CPU
    budgets. Identifiability comes from the B18 decoder-equality theorems.
catalysis (W15): a factorial solver experiment (encoding optimisation × repair) with a
    placebo, an effort control and a conventional alternative. Two more proof-domain arms
    run against B18's recovered concept: a placebo concept and an effort control.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import calibration as CAL  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs, solve  # noqa: E402
from genesis.execution import execute  # noqa: E402
from genesis.discovery import active as A  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.formal_research import triangle_theory as T  # noqa: E402
from genesis.invention import recovery_experiment as RX  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402
from genesis.verification.sat import certified_bounds  # noqa: E402

HARD_SEED, POOL_SEED, CAT_SEED = 20261021, 20261022, 20261023
HARD = [(30, 0.3), (36, 0.25), (40, 0.2)]
DEFS = {'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True}
G4 = {'name': R.C4_MODULE, 'source': R.C4_SOURCE, 'trusted': True}
B18 = ROOT / 'evidence' / 'invention_b18'


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def rep(name):
    return next(r for r in R.proposals() if r['id'] == name)


def seed_of(*parts):
    return int(digest({'p': parts})[:8], 16)


# ---------------------------------------------------------------- W13

def inequality_conjectures():
    tf = {'id': 'tri_not_all', 'binders': [{'name': 'S', 'type': 'GT.Edges'}, {'name': 'a', 'type': 'ℕ'},
                                           {'name': 'b', 'type': 'ℕ'}, {'name': 'c', 'type': 'ℕ'},
                                           {'name': 'h1', 'hyp': True, 'lean': 'GT.TriangleFree S',
                                            'model': lambda v: T.tf(v['S'])}],
          'concl': '¬ ((a, b) ∈ S ∧ (b, c) ∈ S ∧ (a, c) ∈ S)',
          'model': lambda v: not ((v['a'], v['b']) in v['S'] and (v['b'], v['c']) in v['S'] and
                                  (v['a'], v['c']) in v['S']),
          'sampler': lambda rng: {'S': frozenset((u, w) for u in range(4) for w in range(4) if rng.random() < 0.3),
                                  'a': rng.randrange(4), 'b': rng.randrange(4), 'c': rng.randrange(4)},
          'origin': 'generated:lp-inequality-validity', 'role': 'inequality', 'subject': 'triangle',
          'lean_value': lambda b, x: R.lean_value(b, x) if b['type'] == 'GT.Edges' else str(x)}
    c4 = {'id': 'c4_not_all', 'binders': [{'name': 'S', 'type': 'GT.Edges'}] +
          [{'name': x, 'type': 'ℕ'} for x in 'abcd'] +
          [{'name': 'h1', 'hyp': True, 'lean': 'G4.C4Free S', 'model': lambda v: R.c4free(v['S'])},
           {'name': 'h2', 'hyp': True, 'lean': 'a ≠ c', 'model': lambda v: v['a'] != v['c']},
           {'name': 'h3', 'hyp': True, 'lean': 'b ≠ d', 'model': lambda v: v['b'] != v['d']}],
          'concl': '¬ (G4.adj S a b ∧ G4.adj S b c ∧ G4.adj S c d ∧ G4.adj S d a)',
          'model': lambda v: not all(((x, y) in v['S'] or (y, x) in v['S']) for x, y in
                                     ((v['a'], v['b']), (v['b'], v['c']), (v['c'], v['d']), (v['d'], v['a']))),
          'sampler': lambda rng: {'S': frozenset((u, w) for u in range(4) for w in range(4) if rng.random() < 0.3),
                                  **{x: rng.randrange(4) for x in 'abcd'}},
          'origin': 'generated:lp-inequality-validity', 'role': 'inequality', 'subject': 'c4',
          'lean_value': lambda b, x: R.lean_value(b, x) if b['type'] == 'GT.Edges' else str(x)}
    return [tf, c4]


def inequality_recipes(conj, library):
    names = ' '.join(b['name'] for b in conj['binders'])
    if conj['subject'] == 'triangle':
        return [('definition-instance', f'intro {names} h\nunfold GT.TriangleFree at h1\n'
                                        'exact h1 _ h.1 _ h.2.1 _ h.2.2 ⟨rfl, rfl, rfl⟩')]
    return [('verts-from-adjacency', '\n'.join([
        f'intro {names} h', 'apply h1 a ?_ b ?_ c ?_ d ?_ h2 h3 h',
        'all_goals (unfold G4.verts G4.adj at *; simp only [Finset.mem_union, Finset.mem_image] at *)',
        'all_goals aesop']))]


def phase_obstruction(out, log, quick):
    base = [DEFS, G4]
    state = L.prove_all(inequality_conjectures(), base_modules=base, conj_name='OBConj', proof_prefix='OBP',
                        unfold=['GT.TriangleFree', 'G4.C4Free', 'G4.adj', 'G4.verts'],
                        extra_recipes=inequality_recipes, log=log)
    pkg, _ = L.assemble(state, name='LP inequality validity (W13)', domain='triangle_free_host_v1, c4_host_v2',
                        scope='Validity of the motif inequalities used by LP dual certificates.',
                        conventions=['an LP dual certificate is checked in exact rational arithmetic by '
                                     'genesis.discovery.obstruction.check_certificate'])
    dump(out / 'obstruction' / 'package.json', pkg)
    st = {s['id']: s['status'] for s in pkg['statements']}
    adapter = ADAPTERS['triangle_free_host_v1']
    rows = []
    budget = 30 if quick else 60
    settings = HARD[:1] if quick else HARD
    for n, p in settings:
        tasks, _, _ = adapter.generate(HARD_SEED, 2 if quick else 4, 'DEV', 'erdos', {'n': n, 'p': p})
        for t in tasks:
            greedy = solve(t, SolverProgram(rounds=8), 100000, 0)['selected']
            t0 = time.monotonic()
            ref = certified_bounds(t, seconds=budget, start_witness=greedy)
            ref_wall = time.monotonic() - t0
            t1 = time.monotonic()
            rr = R.represent_and_repair(t.n, t.edges, rep('cross_2'), R.tf_add_ok, cpu_seconds=1.0,
                                        seed=seed_of('ob', t.task_id))
            joint = O.certify(t, rr['witness'], seconds=budget - (time.monotonic() - t1))
            joint_wall = time.monotonic() - t1
            lp_ok = None
            if joint['upper_evidence']['method'] == 'LP_DUAL_EXACT':
                lp_ok = O.check_certificate(t, joint['upper_evidence']['certificate'])['verdict']
            agree = None
            if ref['status'] == 'OPTIMALITY_CHECKED' and joint['status'] == 'OPTIMALITY_CHECKED':
                agree = ref['upper'] == joint['upper']
            rows.append({'task_id': t.task_id, 'n': n, 'p': p, 'edges': len(t.edges),
                         'reference': {'status': ref['status'], 'lower': ref['lower'], 'upper': ref['upper'],
                                       'gap': ref['gap'], 'wall_s': round(ref_wall, 2)},
                         'joint': {'status': joint['status'], 'lower': joint['lower'], 'upper': joint['upper'],
                                   'gap': joint['gap'], 'wall_s': round(joint_wall, 2),
                                   'upper_method': joint['upper_evidence']['method'],
                                   'lp_certificate_recheck': lp_ok, 'steps': joint['steps']},
                         'optima_agree': agree})
            log(f'{t.task_id} n={n} p={p}: reference {ref["status"]} {ref["lower"]}..{ref["upper"]} '
                f'({ref_wall:.1f}s); joint {joint["status"]} {joint["lower"]}..{joint["upper"]} '
                f'via {joint["upper_evidence"]["method"]} ({joint_wall:.1f}s)')
    summary = {'tasks': len(rows), 'budget_wall_s': budget,
               'reference_certified': sum(r['reference']['status'] == 'OPTIMALITY_CHECKED' for r in rows),
               'joint_certified': sum(r['joint']['status'] == 'OPTIMALITY_CHECKED' for r in rows),
               'reference_mean_gap': statistics.mean(r['reference']['gap'] for r in rows),
               'joint_mean_gap': statistics.mean(r['joint']['gap'] for r in rows),
               'disagreements': sum(r['optima_agree'] is False for r in rows),
               'joint_by_lp': sum(r['joint']['upper_method'] == 'LP_DUAL_EXACT' for r in rows),
               'lean_inequalities': st}
    dump(out / 'obstruction' / 'evaluation.json', {'split': 'DEV', 'seed': HARD_SEED, 'rows': rows,
                                                   'summary': summary})
    log(f'obstruction summary: {summary}')
    return pkg, summary


# ---------------------------------------------------------------- W14 / W15 shared runs

METHODS = ['rr_cross_2', 'rr_adjacent_2', 'rr_ordered_2', 'low_cycle', 'multistart']


def run_method(m, t, cpu=0.5):
    adapter = ADAPTERS[t.domain]
    s = seed_of('m', m, t.task_id)
    start = time.process_time()
    if m.startswith('rr_'):
        res = R.represent_and_repair(t.n, t.edges, rep(m[3:]), R.tf_add_ok, cpu_seconds=cpu, seed=s)
        value, witness = res['value'], res['witness']
        cost = time.process_time() - start
    else:
        r = execute(t, baseline_programs()[m], CAL.CALIBRATION_LIMITS, s)
        ok = r['status'] == 'SUCCESS'
        value, witness = (r['result']['value'], r['result']['selected']) if ok else (0, [])
        cost = (r.get('cpu_ns') or r['wall_ns']) / 1e9
    v = adapter.validate(t, witness) if witness else {'status': 'VALID', 'value': 0}
    return {'value': value if v['status'] == 'VALID' else 0, 'valid': v['status'] == 'VALID', 'cpu_s': cost,
            'witness': witness}


def certified_optimum(t, witnesses, seconds=30):
    best = max(witnesses, key=len)
    rec = O.certify(t, best, seconds=seconds)
    return rec['upper'] if rec['status'] == 'OPTIMALITY_CHECKED' else None, rec['upper_evidence']['method']


def phase_active(out, log, quick):
    rec = CAL.load('triangle_free_host_v1', ROOT)
    adapter = ADAPTERS['triangle_free_host_v1']
    k = 6 if quick else 16
    calibrated, seen = CAL.calibrated_panel(rec, POOL_SEED, k, 'DEV', excluded=set())
    hard, seen2, _ = adapter.generate(POOL_SEED, k, 'DEV', 'erdos', {'n': 30, 'p': 0.3}, excluded=seen)
    bip, _, _ = adapter.generate(POOL_SEED, k, 'DEV', 'bipartite', {'n': 22, 'p': 0.35}, excluded=seen2)
    families = {'erdos22': calibrated, 'erdos30': hard, 'bipartite22': bip}
    pools, costs, raw, values = {}, {}, [], {}
    for f, tasks in families.items():
        per = {m: [] for m in METHODS}
        val = {m: [] for m in METHODS}
        cpu = {m: [] for m in METHODS}
        for t in tasks:
            runs = {m: run_method(m, t) for m in METHODS}
            opt, how = certified_optimum(t, [r['witness'] for r in runs.values()])
            if opt is None:
                raw.append({'task_id': t.task_id, 'family': f, 'dropped': 'optimum not certified'})
                continue
            for m, r in runs.items():
                per[m].append(int(r['value'] == opt))
                val[m].append(r['value'])
                cpu[m].append(r['cpu_s'])
            raw.append({'task_id': t.task_id, 'family': f, 'optimum': opt, 'certified_by': how,
                        'values': {m: r['value'] for m, r in runs.items()}})
        for m in METHODS:
            pools[(m, f)] = per[m]
            values[(m, f)] = val[m]
            costs[(m, f)] = round(max(0.01, statistics.mean(cpu[m])), 4)
        log(f'pool {f}: {len(per[METHODS[0]])} certified tasks; hit rates '
            f'{ {m: round(sum(per[m]) / max(1, len(per[m])), 2) for m in METHODS} }')
    fams = list(families)
    total = sum(costs[(m, f)] * len(pools[(m, f)]) for m in METHODS for f in fams)
    declared = [('rr_cross_2', 'rr_adjacent_2')]       # B18: adjacent_2 ⊆ cross_2 and cross_2 ⊆ adjacent_2, CHECKED
    reps = 10 if quick else 40
    result = {}
    for share in (0.2, 0.4):
        result[str(share)] = A.evaluate(pools, costs, METHODS, fams, budget=total * share, repetitions=reps,
                                        declared=declared, draws=100, identity_pools=values)
        log(f'active selection at {share:.0%} of the pool cost: {result[str(share)]["policies"]}')
    no_decl = A.equivalence_classes(METHODS, fams, pools, identity_pools=values)
    cal = A.calibration(pools, METHODS, fams)
    out_obj = {'split': 'DEV', 'seed': POOL_SEED, 'methods': METHODS, 'families': fams,
               'pool_sizes': {f: len(pools[(METHODS[0], f)]) for f in fams},
               'costs_cpu_s': {f'{m}@{f}': c for (m, f), c in costs.items()}, 'pool_cost_cpu_s': round(total, 2),
               'declared_indistinguishable': declared, 'empirical_classes': no_decl, 'by_budget': result,
               'calibration': cal, 'raw': raw}
    dump(out / 'active' / 'evaluation.json', out_obj)
    return out_obj


def phase_catalysis(out, log, quick):
    rec = CAL.load('triangle_free_host_v1', ROOT)
    adapter = ADAPTERS['triangle_free_host_v1']
    k = 4 if quick else 12
    tasks, seen = CAL.calibrated_panel(rec, CAT_SEED, k, 'DEV', excluded=set())
    hard, _, _ = adapter.generate(CAT_SEED, k, 'DEV', 'erdos', {'n': 30, 'p': 0.3}, excluded=seen)
    cross = rep('cross_2')

    def arm(name, t, cpu):
        s = seed_of('cat', name, t.task_id)
        n, E = t.n, list(t.edges)
        if name in ('full', 'full_x4'):
            r = R.represent_and_repair(n, E, cross, R.tf_add_ok, cpu_seconds=cpu, seed=s)
            return r['value'], r['witness']
        import random as _r
        rng = _r.Random(s)
        best = []
        end = time.process_time() + cpu
        while True:
            if name == 'cut_only':                     # encoding optimised, no repair
                r = R.represent_and_repair(n, E, cross, lambda S, e: False, cpu_seconds=cpu, seed=s)
                return r['value'], r['witness']
            if name in ('placebo', 'random_cut'):      # random encoding, not optimised
                c = {v: rng.randrange(2) for v in range(n)}
                S = set(R.decode(cross, c, E))
                if name == 'placebo':
                    rest = [e for e in E if e not in S]; rng.shuffle(rest)
                    for e in rest:
                        if R.tf_add_ok(S, e):
                            S.add(e)
            elif name in ('repair_only', 'repair_only_x4'):   # no representation: greedy from empty
                S = set()
                order = E[:]; rng.shuffle(order)
                for e in order:
                    if R.tf_add_ok(S, e):
                        S.add(e)
            else:
                raise ValueError(name)
            if len(S) > len(best):
                best = sorted(S)
            if time.process_time() >= end:
                return len(best), best

    arms = [('full', 0.5), ('cut_only', 0.5), ('placebo', 0.5), ('random_cut', 0.5), ('repair_only', 0.5),
            ('full_x4', 2.0), ('repair_only_x4', 2.0)]
    rows = []
    for fam, ts in (('erdos22', tasks), ('erdos30', hard)):
        for t in ts:
            vals, wits = {}, {}
            for name, cpu in arms:
                v, w = arm(name, t, cpu)
                chk = adapter.validate(t, w) if w else {'status': 'VALID'}
                vals[name] = v if chk['status'] == 'VALID' else 0
                wits[name] = w
            base = execute(t, baseline_programs()['low_cycle'], CAL.CALIBRATION_LIMITS, seed_of('lc', t.task_id))
            vals['conventional_low_cycle'] = base['result']['value'] if base['status'] == 'SUCCESS' else 0
            opt, how = certified_optimum(t, [w for w in wits.values() if w])
            rows.append({'task_id': t.task_id, 'family': fam, 'optimum': opt, 'certified_by': how, 'values': vals})
            log(f'catalysis {t.task_id}: {vals} opt {opt}')

    def mean_diff(a, b, fam=None):
        rs = [r for r in rows if fam in (None, r['family'])]
        return round(statistics.mean(r['values'][a] - r['values'][b] for r in rs), 3)
    factorial = {}
    for fam in (None, 'erdos22', 'erdos30'):
        key = fam or 'all'
        rs = [r for r in rows if fam in (None, r['family'])]
        cell = {c: statistics.mean(r['values'][c] for r in rs) for c in ('full', 'cut_only', 'placebo', 'random_cut')}
        factorial[key] = {
            'cells_mean_value': {k: round(v, 3) for k, v in cell.items()},
            'main_effect_encoding': round(((cell['full'] + cell['cut_only']) - (cell['placebo'] + cell['random_cut'])) / 2, 3),
            'main_effect_repair': round(((cell['full'] + cell['placebo']) - (cell['cut_only'] + cell['random_cut'])) / 2, 3),
            'interaction': round(cell['full'] - cell['cut_only'] - cell['placebo'] + cell['random_cut'], 3),
            'full_minus_placebo': mean_diff('full', 'placebo', fam),
            'full_minus_repair_only': mean_diff('full', 'repair_only', fam),
            'repair_only_x4_minus_repair_only': mean_diff('repair_only_x4', 'repair_only', fam),
            'full_minus_repair_only_x4': mean_diff('full', 'repair_only_x4', fam),
            'full_x4_minus_full': mean_diff('full_x4', 'full', fam),
            'full_minus_conventional': mean_diff('full', 'conventional_low_cycle', fam),
            'optimum_hits': {c: sum(r['values'][c] == r['optimum'] for r in rs if r['optimum'] is not None)
                             for c in rows[0]['values']}}
    solver = {'split': 'DEV', 'seed': CAT_SEED, 'arms': dict(arms), 'rows': rows, 'factorial': factorial,
              'reading': ('removal: full vs repair_only (the representation removed); placebo: a random encoding '
                          'with the same repair; effort: repair_only and full at 4x CPU; conventional alternative: '
                          'the DSL low_cycle baseline. Matched CPU within each comparison except the x4 controls.')}
    dump(out / 'catalysis' / 'solver.json', solver)
    log(f'solver catalysis: {factorial["all"]}')
    proofs = concept_controls(out, log, quick)
    return solver, proofs


def concept_controls(out, log, quick):
    """Placebo concept and effort control against B18's recovered concept (W15/E2 shape)."""
    concept_pkg = json.loads((B18 / 'recovery' / 'concept' / 'package.json').read_text())
    mods = {m['name']: m for m in concept_pkg['modules']}
    hs, hconj, rc = (dict(mods[n], trusted=True) for n in ('HSDefs', 'HSConj', 'RCDefs'))
    ff = {'name': RX.FF_MODULE, 'source': RX.FF_SOURCE, 'trusted': True}
    placebo_src = (f'import {T.DEFS_MODULE}\n\nnamespace PC\n\n/-- Placebo: the recovered concept with the order '
                   'reversed (up-closure); same size, no information about down-closed predicates. -/\n'
                   'def C0 (P0 : GT.Edges → Prop) : Prop := ∀ (x0 x1 : GT.Edges), x0 ≤ x1 → P0 x0 → P0 x1\n\n'
                   'end PC\n')
    pc = {'name': 'PCDefs', 'source': placebo_src, 'trusted': True}
    fresh_defs = ['FF.LoopFree', 'FF.Matching', 'FF.NonEmpty', 'G4.C4Free', 'G4.adj', 'G4.verts']
    common = [DEFS, hs, hconj, rc, G4, ff]
    results = {}
    plans = {'placebo': (common + [pc], RX.generic_conjectures('PC.C0', 'concept') +
                         RX.screen_instances(RX.instance_conjectures('PC.C0', 'concept'), 'PC.C0'),
                         RX.extra_recipes_for('concept', 'PC.C0', fresh_defs=fresh_defs), None, 'PLC'),
             'effort': (common, [], RX.extra_recipes_for('none', 'RC.C0', fresh_defs=fresh_defs), 400000, 'EFF')}
    for arm, (base, pre, extra, hb, prefix) in plans.items():
        fresh = RX.fresh_conjectures(arm)
        if quick:
            fresh = [c for c in fresh if c['id'].endswith(('_inter', '_erase')) and 'c4free' not in c['id']]
            pre = [c for c in pre if 'c4free' not in c['id']]
        # rename the generic/instance ids so they do not collide with B18's
        for c in pre:
            c['id'] = c['id'].replace('concept', arm)
        s = L.prove_all(pre + fresh, base_modules=base, conj_name=f'{prefix}Conj', proof_prefix=prefix + 'P',
                        unfold=['PC.C0', 'RC.C0'] + fresh_defs, extra_recipes=extra, log=log,
                        search_heartbeats=hb)
        pkg, _ = L.assemble(s, name=f'concept control, arm {arm}', domain='edge-set predicates',
                            scope='Fresh-family closure statements under a control arm (W15).', conventions=[])
        dump(out / 'catalysis' / f'concept_{arm}' / 'package.json', pkg)
        fr = [st for st in s['statements'] if st['id'].startswith(f'{arm}_')]
        results[arm] = {'proved': sum(st['status'] == 'CHECKED' for st in fr),
                        'disproved': sum(st['status'] == 'DISPROVED' for st in fr),
                        'unresolved': sum(st['status'] == 'UNRESOLVED' for st in fr), 'fresh_statements': len(fr),
                        'support': {st['id']: st['status'] for st in s['statements'] if st not in fr},
                        'search_candidates': pkg['costs']['search_candidates'],
                        'search_cpu_s': round(pkg['costs']['search_cpu_ns'] / 1e9, 1),
                        'search_heartbeats': hb or 'default'}
        log(f'concept control {arm}: {results[arm]["proved"]}/{len(fr)} proved')
    b18 = json.loads((B18 / 'recovery' / 'comparison.json').read_text())['arms']
    out_obj = {'b18_arms': {k: {x: v[x] for x in ('proved', 'disproved', 'unresolved', 'fresh_statements')}
                            for k, v in b18.items()},
               'controls': results,
               'reading': ('concept (B18) vs placebo (same size, reversed order) vs effort (no concept, 4x search '
                           'heartbeats) vs manual (B18, equivalent-information alternative).')}
    dump(out / 'catalysis' / 'concept.json', out_obj)
    return out_obj


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--phases', default='obstruction,active,catalysis')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    phases = a.phases.split(',')
    summary = {}
    if 'obstruction' in phases:
        pkg, s = phase_obstruction(out, log, a.quick)
        summary['obstruction'] = s
    if 'active' in phases:
        r = phase_active(out, log, a.quick)
        summary['active'] = {k: v['policies'] for k, v in r['by_budget'].items()} | {
            'pool_sizes': r['pool_sizes'], 'calibration_mae': r['calibration']['mean_abs_error'],
            'classes': r['by_budget']['0.2']['classes']}
    if 'catalysis' in phases:
        solver, proofs = phase_catalysis(out, log, a.quick)
        summary['catalysis'] = {'solver': solver['factorial'], 'concept': proofs}
    replays = {}
    for p in sorted(out.rglob('package.json')):
        r = TP.replay(json.loads(p.read_text()))
        replays[str(p.relative_to(out))] = {'verdict': r['verdict'], 'differences': r['differences']}
        log(f'replay {p.relative_to(out)}: {r["verdict"]}')
    dump(out / 'replay.json', replays)
    summary['replay'] = {k: v['verdict'] for k, v in replays.items()}
    summary['wall_seconds'] = round(time.monotonic() - t0, 1)
    dump(out / 'summary.json', summary)
    print(json.dumps(summary, indent=1, sort_keys=True, default=str))
    return 0 if all(v['verdict'] == 'REPLAYED' for v in replays.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
