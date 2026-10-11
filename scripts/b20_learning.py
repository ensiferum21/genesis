#!/usr/bin/env python3
"""B20: learning to research (roadmap W18–W20, E3), DEV material only.

  b20_learning.py OUT_DIR [--quick]

Domain: equational research in Boolean algebra, axiomatized three ways (Sheffer's basis
and Wolfram's single axiom in the Sheffer stroke; Huntington's basis in + and n). Truth is
decided exactly (genesis.learning.equational). Lemmas enter a library only with an E
proof, and the lemmas a successor uses are replayed in Lean.

Phases, in order:
  calibrate  rules fixed in this file before any run: per system, the target size range
             whose empty-library success rate on calibration targets lies in [0.2, 0.6]
             (else the closest to 0.4), and a research budget of a quarter of the CPU the
             fixed policy needs to exhaust the calibration pool.
  setup      frozen initial solver, tools and information access; pools and targets per
             (system, seed), hashed.
  train      research runs on training seeds; the learned policy is fitted and frozen
             (weights hashed) before any evaluation run.
  w19 / e3   five policies × systems × evaluation seeds at equal research budgets; each
             successor frozen and evaluated on unused targets.
  w18        macros induced on training runs: faithful replay; transfer to unseen seeds
             of the same system and to Wolfram's single axiom, against uncompressed
             research at equal budgets with the induction cost charged; revocation.
  w20        memory across the evaluation seeds of one system with contamination
             screening; retrieval vs replaying everything vs none; failure-driven
             curriculum from development targets only; demotion.
  lean       Lean replay (with lemma chains) of every target proof that used library
             lemmas, for the fixed and learned successors.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import macros as M  # noqa: E402
from genesis.learning import memory as MEM  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SYSTEMS = ['ba_sheffer', 'ba_huntington']
TRANSFER_SYSTEM = 'ba_wolfram'
CAL_SEED = 100
TRAIN_SEEDS = [101, 102, 103]
EVAL_SEEDS = [201, 202, 203, 204]
POLICIES = ['fixed', 'random', 'heuristic', 'bandit', 'learned']
TARGET_GRID = [(5, 8), (6, 9), (7, 10), (8, 11)]
RATE_BAND = (0.2, 0.6)
BUDGET_SHARE = 0.25
BASE = {'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30, 'dev_targets': 10, 'eval_targets': 25,
        'prove_s': 1, 'eval_s': 1, 'premise_k': 8, 'calibration_targets': 20}
WOLFRAM = {'prove_s': 10, 'budget_s': 240, 'eval_s': 3, 'eval_targets': 15}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def max_term(system):
    return 4 if system == 'ba_huntington' else 5


def pool_for(system, seed):
    return Q.true_equations(system, BASE['pool_size'], per_bucket=BASE['per_bucket'], seed=seed) + \
        Q.false_equations(system, BASE['pool_size'], BASE['false_conjectures'], seed=seed)


def calibrate(system, log):
    pool = pool_for(system, CAL_SEED)
    rates = []
    for lo, hi in TARGET_GRID:
        T = Q.sample_targets(system, BASE['calibration_targets'], min_total=lo, max_total=hi, max_term=max_term(system),
                             seed=CAL_SEED, exclude=pool)
        ev = RS.evaluate_successor(system, [], T, eval_s=BASE['eval_s'])
        rates.append({'range': [lo, hi], 'rate': round(ev['proved'] / len(T), 3), 'targets': len(T)})
        log(f'calibrate {system} {lo}-{hi}: empty-library rate {rates[-1]["rate"]}')
    inside = [r for r in rates if RATE_BAND[0] <= r['rate'] <= RATE_BAND[1]]
    chosen = inside[0] if inside else min(rates, key=lambda r: (abs(r['rate'] - 0.4), r['range']))
    res = RS.run(system, RS.Fixed(), pool, budget_s=10 ** 6, prove_s=BASE['prove_s'], premise_k=BASE['premise_k'])
    budget = max(1.0, round(BUDGET_SHARE * res['cpu_s'], 2))
    log(f'calibrate {system}: range {chosen["range"]}, exhaust cpu {res["cpu_s"]}s -> budget {budget}s')
    return {'rates': rates, 'chosen_range': chosen['range'], 'exhaust_cpu_s': res['cpu_s'], 'budget_s': budget,
            'rule': f'first range with rate in {RATE_BAND}, else closest to 0.4; budget = {BUDGET_SHARE} x exhaust'}


def material(system, seed, cal):
    pool = pool_for(system, seed)
    lo, hi = cal['chosen_range']
    dev = Q.sample_targets(system, BASE['dev_targets'], min_total=lo, max_total=hi, max_term=max_term(system),
                           seed=seed * 7 + 1, exclude=pool)
    ev = Q.sample_targets(system, BASE['eval_targets'], min_total=lo, max_total=hi, max_term=max_term(system),
                          seed=seed * 7 + 2, exclude=pool + dev)
    return pool, dev, ev


def make_policy(name, seed, weights=None):
    return {'fixed': lambda: RS.Fixed(seed), 'random': lambda: RS.Random(seed), 'heuristic': lambda: RS.Heuristic(seed),
            'bandit': lambda: RS.Bandit(seed), 'learned': lambda: RS.Learned(weights, seed)}[name]()


def research(system, policy, pool, dev, cal):
    return RS.run(system, policy, pool, budget_s=cal['budget_s'], dev_targets=dev, prove_s=BASE['prove_s'],
                  premise_k=BASE['premise_k'])


def successor(system, library, targets, k=None):
    return RS.evaluate_successor(system, library, targets, eval_s=BASE['eval_s'], premise_k=k or BASE['premise_k'])


def brier(pairs):
    return round(statistics.mean((p - y) ** 2 for p, y in pairs), 4) if pairs else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--quick', action='store_true')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    systems = SYSTEMS[:1] if a.quick else SYSTEMS
    train_seeds = TRAIN_SEEDS[:1] if a.quick else TRAIN_SEEDS
    eval_seeds = EVAL_SEEDS[:2] if a.quick else EVAL_SEEDS
    # ---------------- calibrate (rules above, fixed before running)
    cals = {s: calibrate(s, log) for s in systems}
    dump(out / 'calibration.json', cals)
    # ---------------- setup
    frozen = {'solver': 'E prover pinned in toolchain/PINS.json, --auto, per-call CPU limit',
              'tools': ['exact deciders (genesis.learning.equational)', 'E prover'], 'starting_memory': 'empty',
              'information_access': 'conjecture pool and development targets; evaluation targets are never visible '
                                    'to research, training or the policy', 'base': BASE, 'calibration': cals,
              'code_identity': code_identity(ROOT)['sha256']}
    mats = {(s, seed): material(s, seed, cals[s]) for s in systems for seed in train_seeds + eval_seeds}
    dump(out / 'setup.json', {'frozen': frozen, 'frozen_sha256': digest(frozen),
                              'material': {f'{s}@{seed}': {'pool': len(p), 'pool_sha256': digest([Q.text(x) for x in p]),
                                                           'dev': [Q.text(x) for x in d], 'eval': [Q.text(x) for x in e]}
                                           for (s, seed), (p, d, e) in mats.items()}})
    # ---------------- train and freeze the learned policy
    X, y, train = [], [], []
    for s in systems:
        for seed in train_seeds:
            pool, dev, _ = mats[(s, seed)]
            by_text = {Q.text(e): e for e in pool}
            for pol in ('fixed', 'random', 'heuristic'):
                res = research(s, make_policy(pol, seed), pool, dev, cals[s])
                evd = successor(s, res['library'], dev)
                labels = RS.usefulness_labels(res, evd)
                for txt, lab in labels.items():
                    X.append(RS.features(by_text[txt], dev)); y.append(lab)
                train.append({'system': s, 'seed': seed, 'policy': pol, 'library': len(res['library']),
                              'tried': len(res['trajectory']), 'dev_proved': evd['proved'],
                              'positives': sum(labels.values()), 'trajectory_sha256': digest(res['trajectory'])})
                log(f'train {s}@{seed} {pol}: library {len(res["library"])}, dev {evd["proved"]}/{len(dev)}')
    weights = RS.fit_logistic(X, y)
    policy_record = {'features': RS.FEATURE_NAMES, 'weights': weights, 'examples': len(y), 'positives': sum(y),
                     'training_brier': brier([(RS.predict(weights, x), t) for x, t in zip(X, y)]),
                     'weights_sha256': digest(weights), 'frozen_before_evaluation': True}
    dump(out / 'train' / 'policy.json', policy_record)
    dump(out / 'train' / 'runs.json', train)
    log(f'learned policy frozen {policy_record["weights_sha256"][:16]}: {len(y)} examples, {sum(y)} positive')
    # ---------------- W19 / E3
    rows, runs, bases = [], {}, {}
    for s in systems:
        for seed in eval_seeds:
            pool, dev, ev = mats[(s, seed)]
            bases[(s, seed)] = successor(s, [], ev)
            by_text = {Q.text(e): e for e in pool}
            classes = {RS.Bandit.cls(e) for e in pool}
            for pol in POLICIES:
                res = research(s, make_policy(pol, seed, weights), pool, dev, cals[s])
                evr = successor(s, res['library'], ev)
                runs[(s, seed, pol)] = (res, evr)
                tried = {t['eq'] for t in res['trajectory']}
                row = {'system': s, 'seed': seed, 'policy': pol, 'successor_proved': evr['proved'],
                       'empty_successor_proved': bases[(s, seed)]['proved'], 'targets': len(ev),
                       'library': len(res['library']), 'tried': len(res['trajectory']), 'research_cpu_s': res['cpu_s'],
                       'classes_tried': len({RS.Bandit.cls(by_text[t]) for t in tried}), 'classes': len(classes),
                       'false_tried': sum(t['outcome'] == 'FALSE' for t in res['trajectory']),
                       'budget_exhausted': res['cpu_s'] >= cals[s]['budget_s'],
                       'library_sha256': res['library_sha256']}
                if pol == 'learned':
                    labels = RS.usefulness_labels(res, evr)
                    row['calibration_brier'] = brier([(RS.predict(weights, RS.features(by_text[t], dev)), l)
                                                      for t, l in labels.items()])
                rows.append(row)
                log(f'{s}@{seed} {pol}: successor {evr["proved"]}/{len(ev)} (empty {bases[(s, seed)]["proved"]}), '
                    f'library {len(res["library"])}, tried {len(res["trajectory"])}')
    dump(out / 'w19' / 'rows.json', rows)
    paired = []
    for s in systems:
        for seed in eval_seeds:
            r = {x['policy']: x['successor_proved'] for x in rows if x['system'] == s and x['seed'] == seed}
            paired.append({'system': s, 'seed': seed, **{f'{p}': r[p] for p in POLICIES},
                           'empty': bases[(s, seed)]['proved'], 'learned_minus_fixed': r['learned'] - r['fixed'],
                           'learned_minus_best_baseline': r['learned'] - max(r[p] for p in POLICIES if p != 'learned')})
    diffs = [x['learned_minus_fixed'] for x in paired]
    e3 = {'independent_runs_per_policy': len(paired),
          'wins_ties_losses_vs_fixed': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)],
          'mean_learned_minus_fixed': round(statistics.mean(diffs), 3),
          'mean_learned_minus_best_baseline': round(statistics.mean(x['learned_minus_best_baseline'] for x in paired), 3),
          'mean_successor': {p: round(statistics.mean(x[p] for x in paired), 3) for p in POLICIES + ['empty']},
          'claim': 'better-improver: explicitly UNESTABLISHED (DEV research runs only; no sealed panels, no custodian)'}
    dump(out / 'e3' / 'summary.json', {'paired': paired, 'summary': e3})
    log(f'E3: {e3}')
    w18 = phase_w18(out, log, mats, cals, systems, train_seeds[0], eval_seeds, quick=a.quick)
    w20 = phase_w20(out, log, mats, cals, systems, eval_seeds)
    lean = phase_lean(out, log, runs, systems, eval_seeds[0])
    summary = {'calibration': {s: {k: c[k] for k in ('chosen_range', 'budget_s')} for s, c in cals.items()},
               'e3': e3, 'w18': w18, 'w20': w20, 'lean': lean, 'policy_weights_sha256': policy_record['weights_sha256'],
               'wall_seconds': round(time.monotonic() - t0, 1)}
    dump(out / 'summary.json', summary)
    print(json.dumps(summary, indent=1, default=str))
    return 0


def phase_w18(out, log, mats, cals, systems, train_seed, eval_seeds, *, quick):
    """Macros: induced on a training run; faithful replay; transfer to unseen seeds and to
    Wolfram's single axiom against uncompressed research at equal budgets with induction
    charged; revocation."""
    rows, record = [], {}
    for s in systems:
        pool, dev, _ = mats[(s, train_seed)]
        c0 = RS._cpu()
        res = RS.run(s, RS.Fixed(), pool, budget_s=cals[s]['budget_s'] * 4, dev_targets=dev,
                     prove_s=BASE['prove_s'], premise_k=BASE['premise_k'])
        evd = successor(s, res['library'], dev)
        macro = M.induce(res, evd, name=f'{s}-macro')
        induction = round(RS._cpu() - c0, 2)
        replay = M.replay_faithful(macro)
        rev = M.revoke(macro, 0, 'revocation test: the first step withdrawn') if macro['steps'] else macro
        lib_rev, _ = M.expand(rev, s) if rev['steps'] else ([], [])
        record[s] = {'steps': len(macro['steps']), 'faithful': replay['faithful'], 'induction_cpu_s': induction,
                     'description_length': macro['induction']['description_length'],
                     'revocation': {'invalidated': len(rev['revoked'][0]['invalidated']) if rev['revoked'] else 0,
                                    'remaining_steps': len(rev['steps']),
                                    'expanded_after_revocation': len(lib_rev)}}
        dump(out / 'w18' / f'{s}_macro.json', {'macro': macro, 'faithful_replay': replay, 'after_revocation': rev})
        per_run_charge = induction / len(eval_seeds)
        for seed in eval_seeds:
            pool2, dev2, ev2 = mats[(s, seed)]
            budget = cals[s]['budget_s']
            lib, mlog = M.expand(macro, s, budget_s=max(0.5, budget - per_run_charge))
            ev_macro = successor(s, lib, ev2)
            plain = RS.run(s, RS.Fixed(seed), pool2, budget_s=budget, dev_targets=dev2, prove_s=BASE['prove_s'],
                           premise_k=BASE['premise_k'])
            ev_plain = successor(s, plain['library'], ev2)
            rows.append({'system': s, 'seed': seed, 'macro_successor': ev_macro['proved'],
                         'uncompressed_successor': ev_plain['proved'], 'targets': len(ev2),
                         'macro_steps_proved': sum(x['outcome'] == 'PROVED' for x in mlog),
                         'induction_charge_cpu_s': round(per_run_charge, 2), 'budget_s': budget})
            log(f'w18 {s}@{seed}: macro {ev_macro["proved"]} vs uncompressed {ev_plain["proved"]} of {len(ev2)}')
    # transfer to Wolfram's single axiom (same signature as ba_sheffer)
    wolf = None
    if 'ba_sheffer' in record and not quick:
        macro = json.loads((out / 'w18' / 'ba_sheffer_macro.json').read_text())['macro']
        macro = dict(macro, steps=[dict(st, schema=_tuple_eq(st['schema']), budget_s=WOLFRAM['prove_s'])
                                   for st in macro['steps']])
        wpool = pool_for(TRANSFER_SYSTEM, EVAL_SEEDS[0])
        wt = Q.sample_targets(TRANSFER_SYSTEM, WOLFRAM['eval_targets'], min_total=5, max_total=8, seed=EVAL_SEEDS[0] * 11,
                              exclude=wpool)
        charge = record['ba_sheffer']['induction_cpu_s']
        lib_m, mlog = M.expand(macro, TRANSFER_SYSTEM, budget_s=WOLFRAM['budget_s'] - charge)
        ev_m = RS.evaluate_successor(TRANSFER_SYSTEM, lib_m, wt, eval_s=WOLFRAM['eval_s'], premise_k=BASE['premise_k'])
        plain = RS.run(TRANSFER_SYSTEM, RS.Fixed(), wpool, budget_s=WOLFRAM['budget_s'], prove_s=WOLFRAM['prove_s'],
                       premise_k=BASE['premise_k'])
        ev_p = RS.evaluate_successor(TRANSFER_SYSTEM, plain['library'], wt, eval_s=WOLFRAM['eval_s'],
                                     premise_k=BASE['premise_k'])
        ev_0 = RS.evaluate_successor(TRANSFER_SYSTEM, [], wt, eval_s=WOLFRAM['eval_s'])
        wolf = {'targets': len(wt), 'empty': ev_0['proved'], 'macro_successor': ev_m['proved'],
                'macro_lemmas': len(lib_m), 'uncompressed_successor': ev_p['proved'],
                'uncompressed_lemmas': len(plain['library']), 'budget_s': WOLFRAM['budget_s'],
                'induction_charge_cpu_s': charge, 'macro_log': mlog}
        log(f'w18 transfer to {TRANSFER_SYSTEM}: macro {ev_m["proved"]} ({len(lib_m)} lemmas) vs uncompressed '
            f'{ev_p["proved"]} ({len(plain["library"])} lemmas) vs empty {ev_0["proved"]} of {len(wt)}')
        dump(out / 'w18' / 'wolfram_transfer.json', wolf)
    dump(out / 'w18' / 'same_system.json', rows)
    return {'macros': record, 'same_system_macro_minus_uncompressed': [r['macro_successor'] - r['uncompressed_successor']
                                                                      for r in rows],
            'wolfram': None if wolf is None else {k: v for k, v in wolf.items() if k != 'macro_log'}}


def _tuple_eq(e):
    def t(x):
        return (x[0], x[1]) if x[0] == 'var' else (x[0], x[1], tuple(t(a) for a in x[2]))
    return (t(e[0]), t(e[1]))


def phase_w20(out, log, mats, cals, systems, eval_seeds):
    rows = []
    for s in systems:
        memory, evaluations = [], []
        for i, seed in enumerate(eval_seeds):
            pool, dev, ev = mats[(s, seed)]
            usable, excluded = MEM.screen(memory, ev)
            res = RS.run(s, RS.Fixed(seed), pool, budget_s=cals[s]['budget_s'], dev_targets=dev, prove_s=BASE['prove_s'],
                         premise_k=BASE['premise_k'])
            fresh = res['library']
            evd = successor(s, fresh + usable, dev)
            failed = [d for d, r in zip(dev, evd['rows']) if r['status'] != 'PROVED']
            variants = [v for d in failed for v in MEM.variants(d, Q.SYSTEMS[s]['decider']) if v['valid']]
            seen, cur = set(), []
            for v in variants:
                if v['eq'] not in seen:
                    seen.add(v['eq']); cur.append(v)
            cres = RS.run(s, RS.Fixed(seed), [v['eq'] for v in cur], budget_s=cals[s]['budget_s'] / 2,
                          dev_targets=dev, prove_s=BASE['prove_s'], premise_k=BASE['premise_k']) if cur else \
                {'library': [], 'cpu_s': 0.0}
            cur_lib = [dict(l, id=f'C{seed}:{l["id"]}') for l in cres['library']]
            arms = {'none': (fresh, None), 'retrieval': (fresh + usable, None),
                    'replay_all': (fresh + usable, len(fresh) + len(usable)),
                    'curriculum': (fresh + usable + cur_lib, None)}
            scores = {}
            for arm, (lib, k) in arms.items():
                e = successor(s, lib, ev, k)
                scores[arm] = e['proved']
                if arm == 'retrieval':
                    evaluations.append(e)
            rows.append({'system': s, 'seed': seed, 'memory_size': len(memory), 'usable': len(usable),
                         'excluded': excluded, 'curriculum_variants': len(cur), 'curriculum_solved': len(cur_lib),
                         'curriculum_cpu_s': cres['cpu_s'], 'scores': scores, 'targets': len(ev)})
            log(f'w20 {s}@{seed}: memory {len(memory)} (usable {len(usable)}, excluded {len(excluded)}), {scores}')
            for lem in fresh:
                memory.append(dict(lem, id=f'{seed}:{lem["id"]}', uses=[f'{seed}:{u}' for u in lem['uses']],
                                   premise_ids=[f'{seed}:{u}' for u in lem['premise_ids']],
                                   provenance={'system': s, 'seed': seed, 'policy': 'fixed'}))
            if i >= 1:
                memory, demoted = MEM.demote(memory, evaluations)
                rows[-1]['demoted'] = len(demoted)
    dump(out / 'w20' / 'rows.json', rows)
    return {'runs': len(rows),
            'mean_scores': {arm: round(statistics.mean(r['scores'][arm] for r in rows), 3)
                            for arm in ('none', 'retrieval', 'replay_all', 'curriculum')},
            'excluded': {'EXACT': sum(x['reason'] == 'EXACT' for r in rows for x in r['excluded']),
                         'INSTANCE': sum(x['reason'] == 'INSTANCE' for r in rows for x in r['excluded'])}}


def phase_lean(out, log, runs, systems, seed):
    from genesis.formal_research import fof_lean as F
    rows = []
    for s in systems:
        for pol in ('fixed', 'learned'):
            res, evr = runs[(s, seed, pol)]
            for r in evr['rows']:
                if r['status'] != 'PROVED' or not r['lemmas_used']:
                    continue
                entries, gd, gp = RS.lean_chain(res['library'], r['proof'], r['premise_ids'], len(Q.axioms(s)))
                rec = F.replay(f'b20-{s}-{seed}-{pol}-{digest(r["target"])[:10]}', Q.axioms(s), Q.closed(r['eq']),
                               r['proof'], lemmas=entries, goal_deps=gd, goal_positions=gp)
                rows.append({'system': s, 'policy': pol, 'target': r['target'], 'chain_lemmas': len(entries),
                             'status': rec['status'], 'reason': rec.get('reason')})
                log(f'lean {s} {pol}: {rec["status"]} ({len(entries)} chained lemmas)')
    dump(out / 'lean' / 'replays.json', rows)
    return {'target_proofs_with_lemmas': len(rows), 'checked': sum(r['status'] == 'THEOREM_CHECKED' for r in rows),
            'chained_lemmas': sum(r['chain_lemmas'] for r in rows)}


if __name__ == '__main__':
    sys.exit(main())
