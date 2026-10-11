#!/usr/bin/env python3
"""B18: concept invention (roadmap W09–W12), DEV material only.

  b18_invention.py OUT_DIR [--quick] [--phases representations,worlds,recovery]

representations (W10/W11): typed representation grammar → Lean obligations (image,
    soundness, dominance, loss) → the sound representation, ranked on a DEV selection
    panel, drives `represent_and_repair`. On a fresh DEV evaluation panel it is compared
    with every fixed baseline. All witnesses are checked by the domain, and optima are
    certified by the evaluator reference.
worlds (W12): explicit worlds, an intervention, checked consistency and inconsistency,
    implications, non-equivalence, transport decisions, and a discriminating experiment
    on DEV hosts from two families.
recovery (W09): history library → cutoff snapshot → typed anti-unification → reified
    concept with rfl-checked instances → fresh families in four arms.
Every package is replayed from its sources at the end.
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
from genesis.domains import ADAPTERS, Unsupported  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.execution import execute  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.formal_research import triangle_theory as T  # noqa: E402
from genesis.invention import recovery as RV  # noqa: E402
from genesis.invention import recovery_experiment as RX  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.invention import worlds as WD  # noqa: E402

SELECT_SEED, EVAL_SEED, WORLD_SEED = 20261018, 20261019, 20261020
DEFS = {'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True}
G4 = {'name': R.C4_MODULE, 'source': R.C4_SOURCE, 'trusted': True}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def public(rep):
    return {k: v for k, v in rep.items() if not k.startswith('_')}


# ---------------------------------------------------------------- W10 / W11

def phase_representations(out, log, quick):
    reps = R.proposals()
    if quick:
        reps = [r for r in reps if r['id'] in ('cross_2', 'cross_3', 'ordered_2')]
    conjs = R.conjectures(reps)
    sound = set()
    for c in conjs:
        if c['role'] == 'soundness':
            cx, _ = L.screen(c)
            if cx is None:
                sound.add((c['subject'].split('@')[0], 'tf' if 'triangle' in c['subject'] else 'c4'))
    conjs += R.follow_up_conjectures(reps, sound)
    base = [DEFS, G4, {'name': R.REP_MODULE, 'source': R.rep_source(reps), 'trusted': True}]
    unfold = ['GT.TriangleFree', 'G4.C4Free'] + [f'RP.{r["id"]}' for r in reps]
    state = L.prove_all(conjs, base_modules=base, conj_name='RPConj', proof_prefix='RPP', unfold=unfold,
                        extra_recipes=R.extra_recipes, log=log)
    st = {s['id']: s for s in state['statements']}
    records = []
    for r in reps:
        rec = public(r)
        rec['obligations'] = {s['id']: s['status'] for s in state['statements'] if s.get('subject', '').split('@')[0]
                              .split('<=')[0] == r['id'] or s['id'].startswith(r['id'] + '_')}
        rec['sound'] = {d: st.get(f'{r["id"]}_sound_{d}', {}).get('status') for d in ('tf', 'c4')}
        records.append(rec)
    pkg, final = L.assemble(state, name='representation grammar (W10)', domain='triangle_free_host_v1, c4_host_v2',
                            scope=('Typed vertex-class representations of host graphs, their decoders and checked '
                                   'obligations. Conservative definitions only. Rediscovery of known constructions.'),
                            conventions=['hosts list each edge once as (u, v) with u < v',
                                         'statements quantify over all pair sets, loops and reversed pairs included'],
                            extra={'representations': records})
    dump(out / 'representations' / 'package.json', pkg)
    usable = [r for r in reps if st.get(f'{r["id"]}_sound_tf', {}).get('status') == 'CHECKED']
    log(f'Lean-checked sound representations for triangle-free: {[r["id"] for r in usable]}')
    evaluation = evaluate_representation(usable, log, quick)
    dump(out / 'representations' / 'dev_evaluation.json', evaluation)
    return pkg, evaluation


def evaluate_representation(usable, log, quick):
    rec = CAL.load('triangle_free_host_v1', ROOT)
    select, seen = CAL.calibrated_panel(rec, SELECT_SEED, 3 if quick else 6, 'DEV', excluded=set())
    evaluation_tasks, _ = CAL.calibrated_panel(rec, EVAL_SEED, 4 if quick else 12, 'DEV', excluded=seen)
    CAL.require_dev(select + evaluation_tasks)
    adapter = ADAPTERS['triangle_free_host_v1']
    ranking = []
    for r in usable:
        vals = [R.represent_and_repair(t.n, t.edges, r, R.tf_add_ok, cpu_seconds=0.5,
                                       seed=int(digest({'s': t.task_id})[:8], 16))['value'] for t in select]
        ranking.append({'representation': r['id'], 'mean_value': statistics.mean(vals), 'values': vals})
    ranking.sort(key=lambda x: (-x['mean_value'], x['representation']))
    chosen = next(r for r in usable if r['id'] == ranking[0]['representation'])
    log(f'selection panel ranking: {[(x["representation"], x["mean_value"]) for x in ranking]} -> {chosen["id"]}')
    b17 = json.loads((ROOT / 'evidence' / 'formal_research_b17' / 'package' / 'package.json').read_text())
    method = TP.compile_method(b17)
    rows = []
    limits = CAL.CALIBRATION_LIMITS
    for t in evaluation_tasks:
        ref = adapter.reference(t, seconds=120)
        optimum = None if isinstance(ref, Unsupported) else ref['value']
        seed = int(digest({'eval': t.task_id})[:8], 16)
        res = R.represent_and_repair(t.n, t.edges, chosen, R.tf_add_ok, cpu_seconds=limits.cpu_seconds, seed=seed)
        short = R.represent_and_repair(t.n, t.edges, chosen, R.tf_add_ok, cpu_seconds=0.25, seed=seed)
        check = adapter.validate(t, res['witness'])
        base = {}
        for name, prog in sorted(baseline_programs().items()):
            r = execute(t, prog, limits, seed)
            base[name] = {'value': r['result']['value'] if r['status'] == 'SUCCESS' else 0, 'status': r['status'],
                          'cpu_ns': r.get('cpu_ns')}
        strongest = max(base, key=lambda n: (base[n]['value'], n))
        bound = T.packing_bound(t.n, [tuple(e) for e in t.edges], method)['bound'] if method else None
        rows.append({'task_id': t.task_id, 'edges': len(t.edges), 'optimum': optimum,
                     'method': {'value': res['value'], 'valid': check['status'] == 'VALID', 'cpu_seconds_budget':
                                limits.cpu_seconds, 'rounds': res['rounds'],
                                'decoded_before_repair': res['decoded_before_repair']},
                     'method_at_0_25s': short['value'], 'baselines': base, 'strongest_baseline': strongest,
                     'packing_upper_bound': bound,
                     'certified_optimal_by_bound': bound is not None and bound == res['value']})
        log(f'{t.task_id}: method {res["value"]} (valid {check["status"]}) baseline {base[strongest]["value"]} '
            f'({strongest}) optimum {optimum} bound {bound}')
    wins = sum(r['method']['value'] > r['baselines'][r['strongest_baseline']]['value'] for r in rows)
    losses = sum(r['method']['value'] < r['baselines'][r['strongest_baseline']]['value'] for r in rows)
    return {'split': 'DEV', 'selection_seed': SELECT_SEED, 'evaluation_seed': EVAL_SEED, 'ranking': ranking,
            'chosen_representation': chosen['id'], 'rows': rows,
            'summary': {'tasks': len(rows), 'all_witnesses_valid': all(r['method']['valid'] for r in rows),
                        'method_optimum_hits': sum(r['method']['value'] == r['optimum'] for r in rows),
                        'strongest_baseline_optimum_hits': sum(r['baselines'][r['strongest_baseline']]['value'] ==
                                                               r['optimum'] for r in rows),
                        'wins_vs_strongest_baseline': wins, 'losses_vs_strongest_baseline': losses,
                        'ties': len(rows) - wins - losses,
                        'certified_optimal_by_packing_bound': sum(r['certified_optimal_by_bound'] for r in rows)},
            'note': ('DEV only; the strongest baseline is chosen per task after the fact, which favours the baselines. '
                     'The method gets the baselines\' CPU limit; its 0.25 s result is reported too.')}


# ---------------------------------------------------------------- W12

def phase_worlds(out, log, quick):
    W_tf = WD.world('W_tf', ['triangle_free'], solver='keep-all')
    W_bip = WD.world('W_bip', ['bipartite'], solver='keep-all')
    W_dense = WD.world('W_dense', ['has_triangle'], solver='represent-and-repair', representation='cross_2')
    W_conflict = WD.intervene(W_bip, 'W_conflict', add=['has_triangle'])
    W_deg1 = WD.world('W_deg1', ['max_deg_1'], solver='keep-all')
    worlds = [W_tf, W_bip, W_dense, W_conflict, W_deg1]
    transports = [('W_tf', 'W_bip'), ('W_tf', 'W_deg1'), ('W_tf', 'W_conflict')]
    claims = [{'id': 'keep_all_is_valid', 'world': 'W_tf',
               'statement': 'the keep-all solver returns a triangle-free witness'},
              {'id': 'keep_all_is_optimal', 'world': 'W_tf',
               'statement': 'the keep-all witness has |H| edges, the trivial upper bound'},
              {'id': 'keep_all_is_valid_bip', 'world': 'W_conflict',
               'statement': 'keep-all is valid (vacuous if the world is inconsistent)'}]
    conjs = WD.obligations(worlds, transports)
    conjs.append(WD.implication(['triangle_free'], 'bipartite', role='equivalence', subject='W_bip=>W_tf'))
    base = [DEFS, {'name': WD.WORLD_MODULE, 'source': WD.WORLD_SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='WDConj', proof_prefix='WDP',
                        unfold=['GT.TriangleFree', 'WD.Bipartite', 'WD.HasTriangle', 'WD.MaxDegLe', 'WD.deg'],
                        extra_recipes=WD.extra_recipes, log=log)
    verdict = WD.judge(worlds, transports, claims, state['statements'])
    st = {s['id']: s['status'] for s in state['statements']}
    verdict['equivalence'] = {'W_tf~W_bip': WD.equivalence(st.get('imp_triangle_free__bipartite'),
                                                         st.get('imp_bipartite__triangle_free'))}
    pkg, final = L.assemble(state, name='worlds and transport (W12)', domain='triangle_free_host_v1',
                            scope='Explicit assumption worlds over host graphs; checked consistency, implication, '
                                  'separation and transport. Claims keep their world\'s assumptions.',
                            conventions=[f'WD.Bipartite fixes the vertex range {{0..{WD.BIP_N - 1}}} so that it is '
                                         'decidable; the Python model of a DEV host uses the host\'s own n'],
                            extra={'worlds': worlds, 'verdict': verdict})
    dump(out / 'worlds' / 'package.json', pkg)
    experiment = discriminating_experiment(worlds, verdict, log, quick)
    dump(out / 'worlds' / 'experiment.json', experiment)
    return pkg, verdict, experiment


def discriminating_experiment(worlds, verdict, log, quick):
    adapter = ADAPTERS['triangle_free_host_v1']
    rec = CAL.load('triangle_free_host_v1', ROOT)
    erdos, seen = CAL.calibrated_panel(rec, WORLD_SEED, 3 if quick else 6, 'DEV', excluded=set())
    bip, _, _ = adapter.generate(WORLD_SEED, 3 if quick else 6, 'DEV', 'bipartite', {'n': 22, 'p': 0.35}, excluded=seen)
    cross = next(r for r in R.proposals() if r['id'] == 'cross_2')
    rows = []
    for family, tasks in (('erdos', erdos), ('bipartite', bip)):
        for t in tasks:
            H = frozenset(map(tuple, t.edges))
            holds = {'triangle_free': T.tf(H), 'bipartite': WD.bipartite(H, n=t.n), 'has_triangle': not T.tf(H),
                     'max_deg_1': WD.max_deg_le(H, 1)}
            applicable = [w['id'] for w in worlds if all(holds[a] for a in w['assumptions'])
                          and verdict['worlds'][w['id']]['status'] == 'CONSISTENT']
            keep_all = adapter.validate(t, list(t.edges))
            rr = R.represent_and_repair(t.n, t.edges, cross, R.tf_add_ok, cpu_seconds=0.5,
                                        seed=int(digest({'w': t.task_id})[:8], 16))
            rows.append({'task_id': t.task_id, 'family': family, 'edges': len(t.edges), 'assumptions_hold': holds,
                         'applicable_worlds': applicable,
                         'keep_all': {'status': keep_all['status'], 'value': keep_all.get('value')},
                         'represent_and_repair': rr['value'],
                         'certified_optimal_by_trivial_bound': keep_all['status'] == 'VALID'})
    by_family = {}
    for fam in ('erdos', 'bipartite'):
        rs = [r for r in rows if r['family'] == fam]
        by_family[fam] = {'tasks': len(rs), 'keep_all_valid': sum(r['keep_all']['status'] == 'VALID' for r in rs),
                          'worlds_applicable': sorted({w for r in rs for w in r['applicable_worlds']})}
    log(f'discriminating experiment: {by_family}')
    return {'split': 'DEV', 'seed': WORLD_SEED, 'rows': rows, 'by_family': by_family,
            'reading': ('The worlds disagree about which solver is right. Where W_bip applies (every bipartite '
                        'host), keep-all is valid and optimal: the trivial bound |H| certifies it. Where only '
                        'W_dense applies (every erdos host here), keep-all is invalid and represent-and-repair is '
                        'needed. The data pick the world, host by host.')}


# ---------------------------------------------------------------- W09

def phase_recovery(out, log, quick):
    hs = {'name': RX.HS_MODULE, 'source': RX.HS_SOURCE, 'trusted': True}
    history = RX.history_conjectures()
    unfold_h = ['GT.TriangleFree', 'HS.Simple', 'HS.Bounded8']
    sA = L.prove_all(history, base_modules=[DEFS, hs], conj_name='HSConj', proof_prefix='HSP', unfold=unfold_h,
                     extra_recipes=RX.extra_recipes_for('history'), log=log)
    pkgA, finalA = L.assemble(sA, name='history library (before the cutoff)', domain='edge-set predicates',
                              scope='Closure facts about three predicates; the recovery snapshot.',
                              conventions=['the cutoff: recovery reads only HSConj statement trees'],
                              trees=['HSConj'])
    dump(out / 'recovery' / 'history' / 'package.json', pkgA)
    snap, snap_digests = RV.snapshot(finalA['declarations'], {'HSConj'})
    types = RV.type_table(finalA['declarations'])
    cands = RV.candidates(snap, types)
    log(f'anti-unification: {len(cands)} candidates; top members {[c["members"] for c in cands[:3]]}')
    if not cands:
        raise RuntimeError('no abstraction candidate')
    top = cands[0]
    reified = RV.reify(top, 'C0')
    if reified['uses_hidden']:
        raise RuntimeError(f'recovered concept uses hidden constants {reified["uses_hidden"]}')
    rc = {'name': RX.RC_MODULE, 'trusted': True,
          'source': f'import {T.DEFS_MODULE}\nimport HSDefs\n\nnamespace RC\n\n/-- Recovered by typed anti-unification '
                    f'of {", ".join(top["members"])}. -/\n{reified["definition"]}\n\nend RC\n'}
    recovery_record = {'snapshot_modules': ['HSConj'], 'snapshot_tree_sha256': snap_digests,
                       'candidates': [{'members': c['members'], 'size': c['size'], 'holes': [h['type'] for h in c['holes']],
                                       'constants': c['constants']} for c in cands],
                       'chosen': {'members': top['members'], 'definition': reified['definition'],
                                  'hole_types': reified['hole_types'], 'uses_hidden': reified['uses_hidden']},
                       'hidden_constants': list(RV.HIDDEN)}
    # instance checks and generic lemmas over the concept
    hconj = next(m for m in sA['base'] if m['name'] == 'HSConj')
    hist_proofs = [p['module'] for p in sA['proofs']]
    checks = []
    for chk in reified['checks']:
        stmt = chk['lean'].split(' : ', 1)[1].rsplit(' := ', 1)[0]
        checks.append({'id': f'instance_{chk["member"].split(".")[-1]}', 'binders': [], 'concl': stmt, 'model': None,
                       'sampler': None, 'origin': 'generated:reification-check', 'role': 'reification',
                       'subject': chk['member'], 'lean_value': RX.lean_value})
    generic = RX.generic_conjectures('RC.C0', 'concept')

    def extra_c(conj, library):
        if conj.get('role') == 'reification':
            return [('definitional-unfolding', 'rfl')]
        return RX.extra_recipes_for('concept', 'RC.C0')(conj, library)
    sC = L.prove_all(checks + generic, base_modules=[DEFS, hs, hconj, rc], conj_name='RCConj', proof_prefix='RCP',
                     unfold=['RC.C0'], extra_recipes=extra_c, log=log)
    pkgC, _ = L.assemble(sC, name='recovered concept (W09)', domain='edge-set predicates',
                         scope='The recovered abstraction, its rfl-checked instances and generic closure lemmas.',
                         conventions=['RC.C0 is reified from the snapshot alone'], extra={'recovery': recovery_record})
    dump(out / 'recovery' / 'concept' / 'package.json', pkgC)
    # fresh families, four arms
    ff = {'name': RX.FF_MODULE, 'source': RX.FF_SOURCE, 'trusted': True}
    fresh_defs = ['FF.LoopFree', 'FF.Matching', 'FF.NonEmpty', 'G4.C4Free', 'G4.adj', 'G4.verts']
    common = [DEFS, hs, hconj, rc, G4, ff]
    arms = {}
    concept_lib = [{'const': p['binding']['proof'], 'statement': p['statement']} for p in sC['proofs']
                   if p['statement'].startswith('gen_')]
    history_lib = [{'const': p['binding']['proof'], 'statement': p['statement']} for p in sA['proofs']]
    proved_digests = {digest(' '.join(s['lean'].split())) for s in sA['statements'] + sC['statements']
                      if s.get('status') == 'CHECKED' and s.get('lean')}
    plans = {
        'none': (common, [], [], 'FFN'),
        'retrieval': (common + hist_proofs, history_lib, [], 'FFR'),
        'concept': ([DEFS, hs, hconj, rc, next(m for m in sC['base'] if m['name'] == 'RCConj')] +
                    [p['module'] for p in sC['proofs']] + [G4, ff], concept_lib,
                    RX.screen_instances(RX.instance_conjectures('RC.C0', 'concept'), 'RC.C0'), 'FFC'),
        'manual': (common, [], RX.generic_conjectures('RC.C0', 'antitone') +
                   RX.screen_instances(RX.instance_conjectures('RC.C0', 'antitone'), 'RC.C0'), 'FFM'),
    }
    for arm, (base, lib, pre, prefix) in plans.items():
        fresh = RX.fresh_conjectures(f'{arm}')
        if quick:
            fresh = [c for c in fresh if c['id'].endswith(('_inter', '_erase')) and 'c4free' not in c['id']]
            pre = [c for c in pre if 'c4free' not in c['id']]
        kind = {'concept': 'concept', 'manual': 'antitone'}.get(arm, arm)
        extra = RX.extra_recipes_for(kind, 'RC.C0', fresh_defs=fresh_defs)
        t0 = time.monotonic()
        s = L.prove_all(pre + fresh, base_modules=base, conj_name=f'{prefix}Conj', proof_prefix=prefix + 'P',
                        unfold=['RC.C0'] + fresh_defs, extra_recipes=extra, library=lib, log=log)
        pkg, final = L.assemble(s, name=f'fresh families, arm {arm}', domain='edge-set predicates',
                                scope='Fresh-family closure statements after the cutoff.', conventions=[])
        sizes = {d['name']: d.get('value_nodes') for d in final['declarations'] if d['name'].endswith('.proof')}
        fresh_rows = [st for st in s['statements'] if st['id'].startswith(f'{arm}_')]
        arms[arm] = {'package_sha256': pkg['package_sha256'],
                     'fresh_statements': len(fresh_rows),
                     'proved': sum(st['status'] == 'CHECKED' for st in fresh_rows),
                     'disproved': sum(st['status'] == 'DISPROVED' for st in fresh_rows),
                     'unresolved': sum(st['status'] == 'UNRESOLVED' for st in fresh_rows),
                     'support_statements': {st['id']: st['status'] for st in s['statements'] if st not in fresh_rows},
                     'search_candidates': pkg['costs']['search_candidates'],
                     'search_cpu_s': round(pkg['costs']['search_cpu_ns'] / 1e9, 1),
                     'acceptance_cpu_s': round(pkg['costs']['acceptance_check_cpu_ns'] / 1e9, 1),
                     'wall_s': round(time.monotonic() - t0, 1),
                     'proof_nodes_fresh': sum(sizes.get(st.get('proof_const'), 0) or 0 for st in fresh_rows
                                              if st['status'] == 'CHECKED'),
                     'cache_hits': sum(digest(' '.join(st['lean'].split())) in proved_digests for st in fresh_rows),
                     'per_statement': {st['id']: {'status': st['status'], 'recipe': st.get('recipe'),
                                                  'proof_nodes': sizes.get(st.get('proof_const'))} for st in fresh_rows}}
        dump(out / 'recovery' / f'arm_{arm}' / 'package.json', pkg)
        log(f'arm {arm}: proved {arms[arm]["proved"]}/{arms[arm]["fresh_statements"]} '
            f'(disproved {arms[arm]["disproved"]}, unresolved {arms[arm]["unresolved"]})')
    dump(out / 'recovery' / 'comparison.json', {'arms': arms, 'recovery': recovery_record})
    return pkgA, pkgC, arms


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--phases', default='representations,worlds,recovery')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    phases = a.phases.split(',')
    summary = {}
    if 'representations' in phases:
        pkg, ev = phase_representations(out, log, a.quick)
        summary['representations'] = {'package_sha256': pkg['package_sha256'],
                                       'statements': {s['id']: s['status'] for s in pkg['statements']},
                                       'dev_evaluation': ev['summary'], 'chosen': ev['chosen_representation']}
    if 'worlds' in phases:
        pkg, verdict, exp = phase_worlds(out, log, a.quick)
        summary['worlds'] = {'package_sha256': pkg['package_sha256'], 'verdict': verdict,
                             'experiment': exp['by_family']}
    if 'recovery' in phases:
        pkgA, pkgC, arms = phase_recovery(out, log, a.quick)
        summary['recovery'] = {'history_sha256': pkgA['package_sha256'], 'concept_sha256': pkgC['package_sha256'],
                               'arms': {k: {x: v[x] for x in ('proved', 'disproved', 'unresolved', 'fresh_statements',
                                                              'search_candidates', 'search_cpu_s', 'proof_nodes_fresh',
                                                              'cache_hits')} for k, v in arms.items()}}
    replays = {}
    for p in sorted(out.rglob('package.json')):
        pkg = json.loads(p.read_text())
        r = TP.replay(pkg)
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
