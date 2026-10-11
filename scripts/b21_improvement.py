#!/usr/bin/env python3
"""B21: repeated improvement (roadmap W21–W23; E4 as DEV transitions), DEV only.

  b21_improvement.py OUT_DIR [--quick]

All rules are fixed in this file before the run.
  e4   three successor transitions on Wolfram's single axiom for Boolean algebra (the
       system where B20 found research matters). Each transition starts from a frozen
       parent (library + policy), runs two independent research runs under the parent's
       policy with the parent's library as memory, and retrains the policy on the
       accumulated trajectories. Evaluation: a fresh panel per transition plus every
       earlier panel (retention). Decision rule: generations.RULE. Rolled-back children
       are kept as REJECTED.
  w22  an operator-completeness adversary proposes a primitive from failed development
       targets. Its definitional contract is checked by round trip, migration/rollback
       and a Lean bridge to the base statement. Research with the primitive is compared
       at equal budgets with base research and with a renaming control (the same
       conjectures unfolded into the base language).
  w23  heterogeneous routes (decider, prover, kernel, countermodel) on clean and
       fault-injected claims, with false acceptance and detection counted. Expert
       questions for inconclusive decisions go to a SIMULATED expert (error rate 0.1)
       under an intervention budget.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import faults as FT  # noqa: E402
from genesis.learning import generations as GEN  # noqa: E402
from genesis.learning import primitives as PR  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SYSTEM = 'ba_wolfram'
CFG = {'budget_s': 60, 'prove_s': 10, 'eval_s': 3, 'premise_k': 8, 'panel_targets': 15, 'dev_targets': 10,
       'target_range': [5, 8], 'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30, 'runs_per_transition': 2,
       'transitions': 3}
W22 = {'seeds': [610, 611], 'adversary_seed': 600, 'pattern_size': [1, 3]}
W23 = {'seed': 700, 'items': 10, 'expert_error': 0.1, 'expert_budget': 6, 'inconclusive_prove_s': 1, 'model_size': 2}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def materials(system, seed):
    pool = Q.true_equations(system, CFG['pool_size'], per_bucket=CFG['per_bucket'], seed=seed) + \
        Q.false_equations(system, CFG['pool_size'], CFG['false_conjectures'], seed=seed)
    lo, hi = CFG['target_range']
    dev = Q.sample_targets(system, CFG['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
    return pool, dev


def panel(seed, exclude):
    lo, hi = CFG['target_range']
    return Q.sample_targets(SYSTEM, CFG['panel_targets'], min_total=lo, max_total=hi, seed=seed, exclude=exclude)


def phase_e4(out, log, quick):
    weights0 = json.loads((ROOT / 'evidence' / 'learning_b20' / 'train' / 'policy.json').read_text())['weights']
    parent = {'library': [], 'weights': weights0, 'trajectories': [], 'lineage': [0], 'X': [], 'y': []}
    frozen = [GEN.freeze(parent['library'], parent['weights'], parent['lineage'])]
    panels, used = {}, []
    records = []
    n_trans = 1 if quick else CFG['transitions']
    for g in range(1, n_trans + 1):
        mats = [materials(SYSTEM, 400 + 10 * g + k) for k in range(CFG['runs_per_transition'])]
        for p, d in mats:
            used += p + d
        panels[f'P{g}'] = panel(500 + g, used)
        used += panels[f'P{g}']
        child = GEN.transition(SYSTEM, parent, {'runs': mats}, CFG, generation=g, log=log)
        ps = {name: GEN.score(SYSTEM, parent['library'], P, CFG)['proved'] for name, P in panels.items()}
        cs = {name: GEN.score(SYSTEM, child['library'], P, CFG)['proved'] for name, P in panels.items()}
        dec = GEN.decide(ps, cs)
        fz = GEN.freeze(child['library'], child['weights'], child['lineage'])
        rec = {'generation': g, 'parent_sha256': frozen[-1]['sha256'], 'child_sha256': fz['sha256'],
               'parent_scores': ps, 'child_scores': cs, **dec, 'research_cpu_s': child['research_cpu_s'],
               'child_library': len(child['library']), 'parent_library': len(parent['library']),
               'human_interventions': 0, 'panel_sizes': {k: len(v) for k, v in panels.items()}}
        records.append(rec)
        log(f'transition {g}: parent {ps} child {cs} -> {dec["decision"]}')
        if dec['decision'] == 'ACCEPTED':
            parent = child
            frozen.append(fz)
    accepted = [r for r in records if r['decision'] == 'ACCEPTED']
    summary = {'rule': GEN.RULE, 'transitions': len(records), 'accepted': len(accepted),
               'fresh_gains': [r['fresh_gain'] for r in records],
               'research_cpu_s': round(sum(r['research_cpu_s'] for r in records), 1),
               'cpu_per_accepted_s': round(sum(r['research_cpu_s'] for r in records) / len(accepted), 1)
               if accepted else None,
               'lineage': [f['sha256'][:16] for f in frozen],
               'claim': 'compounding generations (GV5): NOT ESTABLISHED; DEV transitions only, no sealed panels'}
    dump(out / 'e4' / 'transitions.json', {'records': records, 'summary': summary,
                                           'panels': {k: [Q.text(e) for e in v] for k, v in panels.items()}})
    return summary


def phase_w22(out, log, quick):
    pool0, dev0 = materials(SYSTEM, W22['adversary_seed'])
    ev0 = RS.evaluate_successor(SYSTEM, [], dev0, eval_s=CFG['eval_s'])
    failed = [d for d, r in zip(dev0, ev0['rows']) if r['status'] != 'PROVED']
    lo, hi = W22['pattern_size']
    proposals = PR.propose(failed, top=5, min_size=lo, max_size=hi)
    pattern = next(p for p, c in proposals if p[0] == 'fn')
    prim = PR.primitive(pattern, name='p1')
    ext = PR.extend(SYSTEM, prim)
    contract = {'pattern': repr(pattern), 'proposals': [[repr(p), c] for p, c in proposals],
                'round_trip': PR.round_trip(prim, pool0), 'definition': Q.SYSTEMS[ext]['axioms'][-1]}
    log(f'w22 primitive {prim["name"]}({",".join(prim["params"])}) := {repr(pattern)}; round trip {contract["round_trip"]}')
    rows = []
    for seed in (W22['seeds'][:1] if quick else W22['seeds']):
        base_pool, dev = materials(SYSTEM, seed)
        ext_pool = Q.true_equations(ext, CFG['pool_size'], per_bucket=CFG['per_bucket'], seed=seed) + \
            Q.false_equations(ext, CFG['pool_size'], CFG['false_conjectures'], seed=seed)
        renamed = []
        seen = set()
        for e in ext_pool:
            u = Q.canon((PR.unfold(e[0], prim), PR.unfold(e[1], prim)))
            if u not in seen and u[0] != u[1]:
                seen.add(u); renamed.append(u)
        ev = panel(seed * 3 + 1, base_pool + dev + renamed)
        arms = {'base': (SYSTEM, base_pool), 'primitive': (ext, ext_pool), 'renaming_control': (SYSTEM, renamed)}
        scores, libs = {}, {}
        for arm, (sysname, pool) in arms.items():
            res = RS.run(sysname, RS.Fixed(seed), pool, budget_s=CFG['budget_s'], dev_targets=dev,
                         prove_s=CFG['prove_s'], premise_k=CFG['premise_k'])
            e = RS.evaluate_successor(sysname, res['library'], ev, eval_s=CFG['eval_s'], premise_k=CFG['premise_k'])
            scores[arm] = e['proved']
            libs[arm] = (res, e)
            log(f'w22 seed {seed} {arm}: library {len(res["library"])}, successor {e["proved"]}/{len(ev)}')
        empty = RS.evaluate_successor(SYSTEM, [], ev, eval_s=CFG['eval_s'])['proved']
        res, e = libs['primitive']
        migrated = PR.migrate(libs['base'][0]['library'], prim)
        back = PR.rollback(migrated, prim)
        mig_ok = all(Q.canon(a['eq']) == Q.canon(b['eq']) for a, b in zip(back, libs['base'][0]['library']))
        rows.append({'seed': seed, 'scores': scores, 'empty': empty, 'targets': len(ev),
                     'pools': {k: len(v[1]) for k, v in arms.items()}, 'migration_round_trip': mig_ok,
                     'primitive_library_uses_p1': sum('p1(' in l['text'] for l in res['library'])})
        if not rows[1:]:
            lean_rows = lean_bridge(log, ext, prim, res, e)
            rows[-1]['lean'] = lean_rows
    return {'contract': contract, 'rows': rows, 'primitive': prim, 'extended_system': ext}, None


def lean_bridge(log, ext, prim, res, ev):
    """Replay the primitive arm's successor proofs that used lemmas: each is bound to the
    *base* statement, with the primitive instantiated by its λ-term (definition by rfl)."""
    from genesis.formal_research import fof_lean as F
    out = []
    for r in ev['rows']:
        if r['status'] != 'PROVED':
            continue
        entries, gd, gp = RS.lean_chain(res['library'], r['proof'], r['premise_ids'], len(Q.axioms(ext)))
        rec = F.replay(f'b21-w22-{digest(r["target"])[:10]}', Q.axioms(SYSTEM), Q.closed(r['eq']), r['proof'],
                       lemmas=entries, goal_deps=gd, goal_positions=gp, definitions=[PR.lean_definition(prim)])
        out.append({'target': r['target'], 'chain_lemmas': len(entries), 'status': rec['status'],
                    'reason': rec.get('reason')})
        log(f'w22 lean: {rec["status"]} ({len(entries)} chained lemmas)')
    return out


def phase_w23(out, log, quick):
    rng = random.Random(W23['seed'])
    sysname = 'ba_sheffer'
    pool, dev = Q.true_equations(sysname, 4, per_bucket=4, seed=W23['seed']), []
    res = RS.run(sysname, RS.Fixed(), pool, budget_s=1000, prove_s=1)          # exhausts the pool
    lib = [l for l in res['library'] if not l['uses']]                         # proofs from the axioms alone
    rng.shuffle(lib)
    items = lib[:4 if quick else W23['items']]
    falses = Q.false_equations(sysname, 4, len(items), seed=W23['seed'])
    for it, f in zip(items, falses):
        it['false_eq'] = f
        it['decider'] = Q.SYSTEMS[sysname]['decider']
    rows = []

    def record(kind, truth, eq, r):
        d = FT.diagnose(r)
        rows.append({'kind': kind, 'truth': truth, 'claim': Q.text(eq), 'routes': {k: r[k] for k in
                                                                                  ('decider', 'prover', 'kernel',
                                                                                   'countermodel')},
                     **d, 'false_acceptance': d['verdict'] == 'ACCEPTED' and not (truth and kind in
                                                                                    ('clean_true', 'decider_flip'))})
    for it in items:
        record('clean_true', True, it['eq'], FT.routes(sysname, it['eq'], proof=it['proof']))
        record('clean_false', False, it['false_eq'], FT.routes(sysname, it['false_eq'], prove_s=1))
        for kind in ('corrupt_proof', 'swapped_proof', 'false_claim_with_proof', 'decider_flip'):
            eq, proof, dec, truth = FT.inject(kind, it, items, rng)
            if proof is None:
                continue
            record(kind, truth, eq, FT.routes(sysname, eq, proof=proof, decider=dec))
        log(f'w23 item {it["text"][:40]}: {[r["verdict"] for r in rows[-6:]]}')
    by = {}
    for r in rows:
        b = by.setdefault(r['kind'], {'n': 0, 'false_acceptance': 0, 'verdicts': {}})
        b['n'] += 1
        b['false_acceptance'] += r['false_acceptance']
        b['verdicts'][r['verdict']] = b['verdicts'].get(r['verdict'], 0) + 1
    # expert questions on inconclusive decisions (decider withheld), SIMULATED expert
    # decisions on Wolfram's axiom, where a 1-second prover call rarely settles a true claim
    esys = SYSTEM
    claims = Q.sample_targets(esys, 8, min_total=5, max_total=8, seed=W23['seed'] + 1) + \
        Q.false_equations(esys, 4, 4, seed=W23['seed'] + 2)
    expert = FT.SimulatedExpert(esys, W23['expert_error'], W23['seed'])
    decisions, questions, spent = [], [], 0.0
    for eq in claims:
        r = FT.routes(esys, eq, prove_s=W23['inconclusive_prove_s'], model_size=W23['model_size'], model_s=2,
                      decider=lambda e: True, kernel=False)        # decider withheld: its answer is ignored
        if r['prover'] == 'THEOREM':
            base = True
        elif r['countermodel'] == 'FOUND':
            base = False
        else:
            base = None
        final, asked = base, False
        if base is None and spent + 1.0 <= W23['expert_budget']:
            q = expert.answer(FT.question(Q.text(eq), 'prover gave up and no countermodel up to size 2'), eq)
            questions.append(q)
            spent += q['cost']
            final, asked = q['answer'], True
        truth = Q.holds(eq, Q.SYSTEMS[esys]['decider'])
        decisions.append({'claim': Q.text(eq), 'truth': truth, 'without_expert': base, 'with_expert': final,
                          'asked': asked})
    acc = lambda key: sum(d[key] == d['truth'] for d in decisions)
    expert_summary = {'claims': len(decisions), 'correct_without_expert': acc('without_expert'),
                      'undecided_without_expert': sum(d['without_expert'] is None for d in decisions),
                      'correct_with_expert': acc('with_expert'), 'questions': len(questions),
                      'intervention_cost': spent, 'budget': W23['expert_budget'],
                      'expert': 'SIMULATED (decider with error rate %.2f); not evidence about real experts'
                                % W23['expert_error']}
    dump(out / 'w23' / 'routes.json', {'rows': rows, 'by_kind': by})
    dump(out / 'w23' / 'expert.json', {'decisions': decisions, 'questions': questions, 'summary': expert_summary})
    return {'by_kind': by, 'false_acceptances': sum(r['false_acceptance'] for r in rows), 'expert': expert_summary}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--phases', default='w23,w22,e4')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    dump(out / 'rules.json', {'cfg': CFG, 'w22': W22, 'w23': W23, 'generation_rule': GEN.RULE,
                              'code_identity': code_identity(ROOT)['sha256']})
    summary = {}
    phases = a.phases.split(',')
    if 'w23' in phases:
        summary['w23'] = phase_w23(out, log, a.quick)
    if 'w22' in phases:
        w22, _ = phase_w22(out, log, a.quick)
        dump(out / 'w22' / 'summary.json', w22)
        summary['w22'] = {k: w22[k] for k in ('contract', 'rows')}
    if 'e4' in phases:
        summary['e4'] = phase_e4(out, log, a.quick)
    summary['wall_seconds'] = round(time.monotonic() - t0, 1)
    dump(out / 'summary.json', summary)
    print(json.dumps(summary, indent=1, default=str)[:4000])
    return 0


if __name__ == '__main__':
    sys.exit(main())
