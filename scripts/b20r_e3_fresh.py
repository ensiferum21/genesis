#!/usr/bin/env python3
"""H02 exit (B20_R2): a fresh, frozen DEV E3 study on the repaired harness.

    b20r_e3_fresh.py OUT_DIR                  phase 1: material, calibration, training, evaluation, custody
    b20r_e3_fresh.py OUT_DIR --phase lean     phase 2: Lean replay from custody (resumable)
    b20r_e3_fresh.py OUT_DIR --phase report   summary with the three metrics

Purpose: show that the repaired harness (global partition, enforced budgets, successor
custody) runs the B20 E3 design end to end on fresh material, and report what it finds.
DEV only. It cannot establish a better improver (no sealed panel, no custodian).

Rules fixed here before running (B20 main design, repaired):
  * systems ba_sheffer and ba_huntington; seeds: calibration 500, training 501-503,
    evaluation 601-604; pools as in B20 (pool_for); 10 development targets per seed with
    5-11 nodes (drawn BEFORE calibration, so that all research-visible material exists before
    any evaluation material; B20 drew them in the calibrated range).
  * exposure: every equation in prior DEV evidence (evidence/learning_b20 and
    evidence/orbit_probe_b20r, all JSON strings that parse as equations of these
    signatures; Wolfram material counts for Sheffer: same variety and signature), the B20
    pools regenerated and checked against their recorded hashes, and every pool and
    development target of this study. Calibration and evaluation targets are drawn with
    learning.partitions against it (EXACT/ALPHA/INSTANCE rejected, GENERALIZES quarantined,
    cross-unit distinct); calibration targets join the exposure before evaluation is drawn.
  * calibration (B20 rule): the first target range in the grid whose empty-library rate is
    in [0.2, 0.6], else the closest to 0.4; research cap = 0.25 x the CPU the fixed policy
    needs to exhaust the calibration pool, measured under the repaired account (every
    category charged).
  * budgets: StudyBudget OUTER_SUPERVISED, quantum 0.1 s, 1 s prover attempts (+0.25 s
    reserve), kill tolerance 0.05 s held back; identical record for every arm.
  * learned policy: logistic model retrained here on 18 training runs (3 seeds x 2 systems x
    fixed/random/heuristic) under the repaired harness, frozen (weights hashed) before any
    evaluation run.
  * charging, declared: PRIMARY comparison at equal research caps with training cost NOT
    charged to the learned arm (B20-comparable; NOT an equal-total-cost comparison);
    training CPU is reported in full, and the amortized share over the 8 preregistered
    evaluation uses is reported as a number, without a verdict.
  * insertion screen: research lemmas are screened against all evaluation targets (defence in
    depth; expected to block nothing because pools are already disjoint at partition time).
    No blanket rejection of general lemmas beyond the partition relations.
  * evaluation: 25 targets per unit, 1 s per target (PROVER_QUANTUM reservation), 8 most
    relevant lemmas; every scored proof taken into custody.
  * endpoints: per run prover_reported, eligible (budget and exposure) and checked. E3
    primary: learned - fixed on eligible successes per independent run (8 runs), DEV.
  * Lean phase: every prover-reported success of the fixed and learned arms; a 20% sample
    (seed 'b20r-e3-sample') of the other arms. Unchecked successes are reported as such.
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
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.fol import parse  # noqa: E402
from genesis.learning import custody as C  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import partitions as P  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account, StudyBudget  # noqa: E402

STUDY = 'b20r-e3-fresh-dev'
SYSTEMS = ['ba_sheffer', 'ba_huntington']
CAL_SEED, TRAIN_SEEDS, EVAL_SEEDS = 500, [501, 502, 503], [601, 602, 603, 604]
POLICIES = ['fixed', 'random', 'heuristic', 'bandit', 'learned']
TARGET_GRID = [(5, 8), (6, 9), (7, 10), (8, 11)]
RATE_BAND, BUDGET_SHARE = (0.2, 0.6), 0.25
BASE = {'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30, 'dev_targets': 10, 'eval_targets': 25,
        'prove_s': 1, 'eval_s': 1, 'premise_k': 8, 'calibration_targets': 20}
BUDGET_KW = {'enforcement': 'OUTER_SUPERVISED', 'quantum_ns': 100_000_000}
SAMPLE_SHARE, SAMPLE_SEED = 0.2, 'b20r-e3-sample'
SALT = b'b20r-e3-fresh-dev-screen-salt-v1'      # DEV: the builder sees everything anyway
OPS = {'ba_sheffer': {'s'}, 'ba_huntington': {'plus', 'n'}}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def max_term(system):
    return 4 if system == 'ba_huntington' else 5


def pool_for(system, seed):
    return Q.true_equations(system, BASE['pool_size'], per_bucket=BASE['per_bucket'], seed=seed) + \
        Q.false_equations(system, BASE['pool_size'], BASE['false_conjectures'], seed=seed)


def eq_of(text):
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    if f[0] != 'eq':
        raise ValueError('not an equation')
    return (f[1], f[2])


def _symbols(t, out):
    if t[0] == 'fn':
        out.add(t[1])
        for a in t[2]:
            _symbols(a, out)
    return out


def prior_exposure():
    """Every equation in prior DEV evidence, assigned to a system by its signature."""
    found, files = [], 0
    roots = [ROOT / 'evidence' / 'learning_b20', ROOT / 'evidence' / 'orbit_probe_b20r']

    def walk(x, src):
        if isinstance(x, str):
            if x.startswith('!['):
                try:
                    e = eq_of(x)
                except Exception:
                    return
                syms = _symbols(e[0], set()) | _symbols(e[1], set())
                for system, ops in OPS.items():
                    if syms and syms <= ops:
                        found.append((system, e, src))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v, src)
        elif isinstance(x, list):
            for v in x:
                walk(v, src)
    for root in roots:
        for f in sorted(root.rglob('*.json')):
            files += 1
            walk(json.loads(f.read_text()), str(f.relative_to(ROOT)))
    # B20 pools are recorded by hash only: regenerate and check.
    setup = json.loads((ROOT / 'evidence' / 'learning_b20' / 'setup.json').read_text())['material']
    regenerated = 0
    for key, m in setup.items():
        system, seed = key.rsplit('@', 1)
        pool = pool_for(system, int(seed))
        if digest([Q.text(x) for x in pool]) != m['pool_sha256']:
            raise SystemExit(f'B20 pool {key} does not regenerate to its recorded hash')
        found += [(system, e, f'regenerated B20 pool {key}') for e in pool]
        regenerated += 1
    return found, {'files_scanned': files, 'statements': len(found), 'b20_pools_regenerated': regenerated}


def make_policy(name, seed, weights=None):
    return {'fixed': lambda: RS.Fixed(seed), 'random': lambda: RS.Random(seed), 'heuristic': lambda: RS.Heuristic(seed),
            'bandit': lambda: RS.Bandit(seed), 'learned': lambda: RS.Learned(weights, seed)}[name]()


def budget(cap_s):
    return StudyBudget.from_seconds(cap_s, attempt_s=BASE['prove_s'], **BUDGET_KW)


def brier(pairs):
    return round(statistics.mean((p - y) ** 2 for p, y in pairs), 4) if pairs else None


def phase_main(out, log):
    t_start = time.monotonic()
    # ---------------- research-visible material of the whole study, first
    mats = {}
    for s in SYSTEMS:
        for seed in [CAL_SEED] + TRAIN_SEEDS + EVAL_SEEDS:
            pool = pool_for(s, seed)
            dev = Q.sample_targets(s, BASE['dev_targets'], min_total=5, max_total=11, max_term=max_term(s),
                                   seed=seed * 7 + 1, exclude=pool) if seed != CAL_SEED else []
            mats[(s, seed)] = {'pool': pool, 'dev': dev}
    prior, prior_stats = prior_exposure()
    visible = [(s, e, src, 'import') for s, e, src in prior]
    for (s, seed), m in mats.items():
        visible += [(s, e, f'{s}@{seed}', 'pool') for e in m['pool']]
        visible += [(s, e, f'{s}@{seed}', 'development') for e in m['dev']]
    log(f'exposure: {prior_stats}, study-visible {len(visible) - len(prior)}')
    # ---------------- calibration (B20 rule), targets drawn against the global exposure
    cal_units = [(f'cal:{s}:{lo}-{hi}', s) for s in SYSTEMS for lo, hi in TARGET_GRID]
    grid = {u: r for (u, _), r in zip(cal_units, [g for _ in SYSTEMS for g in TARGET_GRID])}

    def cal_sampler(unit, system, rng):
        lo, hi = grid[unit]
        return P.equational_sampler(min_total=lo, max_total=hi, max_term=max_term(system))(unit, system, rng)
    cal_part = P.build_partition(study=STUDY + ':calibration', study_seed=CAL_SEED, visible=visible, units=cal_units,
                                 sampler=cal_sampler, count=BASE['calibration_targets'])
    dump(out / 'partition_calibration.json', cal_part)
    cals = {}
    for s in SYSTEMS:
        rates = []
        for lo, hi in TARGET_GRID:
            T = P.accepted_items(cal_part, f'cal:{s}:{lo}-{hi}')
            ev = RS.evaluate_successor(s, [], T, eval_s=BASE['eval_s'], label=f'cal:{s}:{lo}-{hi}')
            rates.append({'range': [lo, hi], 'rate': round(ev['proved'] / len(T), 3), 'targets': len(T)})
            log(f'calibrate {s} {lo}-{hi}: empty-library rate {rates[-1]["rate"]}')
        inside = [r for r in rates if RATE_BAND[0] <= r['rate'] <= RATE_BAND[1]]
        chosen = inside[0] if inside else min(rates, key=lambda r: (abs(r['rate'] - 0.4), r['range']))
        exhaust = RS.run(s, RS.Fixed(), mats[(s, CAL_SEED)]['pool'], account=Account(budget(10 ** 5), label=f'exhaust:{s}'),
                         prove_s=BASE['prove_s'], premise_k=BASE['premise_k'])
        cap = round(BUDGET_SHARE * exhaust['account']['cpu_ns_total'] / 1e9, 3)
        cals[s] = {'rates': rates, 'chosen_range': chosen['range'], 'exhaust_cpu_s': exhaust['cpu_s'],
                   'exhaust_attempts': exhaust['account']['attempts'], 'budget_s': cap,
                   'rule': f'first range with rate in {RATE_BAND}, else closest to 0.4; cap = {BUDGET_SHARE} x exhaust'}
        log(f'calibrate {s}: range {chosen["range"]}, exhaust {exhaust["cpu_s"]} s -> cap {cap} s')
    dump(out / 'calibration.json', cals)
    # ---------------- evaluation partition (calibration targets join the exposure first)
    visible_eval = visible + [(u['system'], eq_of(a['text']), name, 'import')
                              for name, u in cal_part['units'].items() for a in u['accepted']]
    eval_units = [(f'{s}@{seed}', s) for s in SYSTEMS for seed in EVAL_SEEDS]

    def eval_sampler(unit, system, rng):
        lo, hi = cals[system]['chosen_range']
        return P.equational_sampler(min_total=lo, max_total=hi, max_term=max_term(system))(unit, system, rng)
    part = P.build_partition(study=STUDY, study_seed=600, visible=visible_eval, units=eval_units, sampler=eval_sampler,
                             count=BASE['eval_targets'])
    problems = P.partition_problems(part, visible_eval)
    if problems:
        raise SystemExit(f'partition validator: {problems[:3]}')
    dump(out / 'partition_evaluation.json', part)
    evals = {u: P.accepted_items(part, u) for u, _ in eval_units}
    screen = P.InsertionScreen([(s, e) for (u, s) in eval_units for e in evals[u]], salt=SALT)
    frozen = {'study': STUDY, 'rules_sha256': digest(Path(__file__).read_text()), 'base': BASE,
              'budget': {s: budget(cals[s]['budget_s']).record() for s in SYSTEMS}, 'calibration': cals,
              'partition_id': part['partition_id'], 'exposure_root': part['exposure']['root'],
              'screen_commitment': screen.commitment(), 'prior_exposure': prior_stats,
              'code_identity': code_identity(ROOT)['sha256']}
    dump(out / 'setup.json', dict(frozen, frozen_sha256=digest(frozen)))
    log(f'setup frozen: partition {part["partition_id"][:16]}, rejections '
        f'{ {u: d["rejected_counts"] for u, d in part["units"].items()} }')
    # ---------------- training, then freeze the learned policy
    X, y, train, t_train = [], [], [], time.process_time()
    train_cpu_ns = 0
    for s in SYSTEMS:
        for seed in TRAIN_SEEDS:
            pool, dev = mats[(s, seed)]['pool'], mats[(s, seed)]['dev']
            by_text = {Q.text(e): e for e in pool}
            for pol in ('fixed', 'random', 'heuristic'):
                res = RS.run(s, make_policy(pol, seed), pool, account=Account(budget(cals[s]['budget_s']),
                                                                           label=f'train:{s}@{seed}:{pol}'),
                             dev_targets=dev, prove_s=BASE['prove_s'], premise_k=BASE['premise_k'], screen=screen)
                evd = RS.evaluate_successor(s, res['library'], dev, eval_s=BASE['eval_s'],
                                            label=f'train-dev:{s}@{seed}:{pol}')
                train_cpu_ns += res['account']['cpu_ns_total'] + evd['account']['cpu_ns_total']
                labels = RS.usefulness_labels(res, evd)
                for txt, lab in labels.items():
                    X.append(RS.features(by_text[txt], dev)); y.append(lab)
                train.append({'system': s, 'seed': seed, 'policy': pol, 'library': len(res['library']),
                              'tried': len(res['trajectory']), 'dev_proved': evd['proved'],
                              'positives': sum(labels.values()), 'research_cpu_ns': res['account']['cpu_ns_total'],
                              'within_cap': res['account']['within_cap']})
                log(f'train {s}@{seed} {pol}: library {len(res["library"])}, dev {evd["proved"]}/{len(dev)}')
    c0 = time.process_time_ns()
    weights = RS.fit_logistic(X, y)
    fit_ns = time.process_time_ns() - c0
    policy = {'features': RS.FEATURE_NAMES, 'weights': weights, 'examples': len(y), 'positives': sum(y),
              'training_brier': brier([(RS.predict(weights, x), t) for x, t in zip(X, y)]),
              'weights_sha256': digest(weights), 'frozen_before_evaluation': True,
              'training_cpu_ns': {'research_and_dev_evaluation': train_cpu_ns, 'fit': fit_ns},
              'amortized_share_per_use_ns': (train_cpu_ns + fit_ns) // (len(SYSTEMS) * len(EVAL_SEEDS)),
              'charging': 'PRIMARY comparison does not charge training (declared); see the module docstring'}
    dump(out / 'train' / 'policy.json', policy)
    dump(out / 'train' / 'runs.json', train)
    log(f'learned policy frozen {policy["weights_sha256"][:16]} ({len(y)} examples, {sum(y)} positive); '
        f'training CPU {(train_cpu_ns + fit_ns) / 1e9:.1f} s')
    # ---------------- evaluation runs with custody
    objects = C.ObjectStore(out / 'objects')
    rows = []
    for s in SYSTEMS:
        for seed in EVAL_SEEDS:
            unit = f'{s}@{seed}'
            pool, dev, ev = mats[(s, seed)]['pool'], mats[(s, seed)]['dev'], evals[unit]
            task_ids = [a['structural_sha256'] for a in part['units'][unit]['accepted']]
            base = RS.evaluate_successor(s, [], ev, eval_s=BASE['eval_s'], label=f'empty:{unit}', task_ids=task_ids)
            empty_run = {'system': s, 'policy': 'empty', 'run_id': f'empty:{unit}', 'library': []}
            man0 = C.successor_manifest(empty_run, objects, exposure_root=part['exposure']['root'])
            recs0 = C.target_records(base, man0, objects, panel_id=unit, task_ids=task_ids)
            dump(out / 'runs' / unit / 'empty.json', {'manifest': man0, 'targets': recs0,
                                                      'evaluation_account': base['account']})
            by_text = {Q.text(e): e for e in pool}
            for pol in POLICIES:
                res = RS.run(s, make_policy(pol, seed, weights), pool,
                             account=Account(budget(cals[s]['budget_s']), label=f'eval:{unit}:{pol}'),
                             dev_targets=dev, prove_s=BASE['prove_s'], premise_k=BASE['premise_k'], screen=screen,
                             run_id=f'{STUDY}:{unit}:{pol}')
                evr = RS.evaluate_successor(s, res['library'], ev, eval_s=BASE['eval_s'], label=f'succ:{unit}:{pol}',
                                            task_ids=task_ids)
                man = C.successor_manifest(res, objects, policy_identity=policy['weights_sha256'] if pol == 'learned'
                                           else pol, exposure_root=part['exposure']['root'])
                recs = C.target_records(evr, man, objects, panel_id=unit, task_ids=task_ids)
                sp = C.successor_problems(man, objects)
                row = {'system': s, 'seed': seed, 'policy': pol, 'library': len(res['library']),
                       'tried': len(res['trajectory']), 'research_cpu_ns': res['account']['cpu_ns_total'],
                       'cap_ns': res['account']['budget']['cpu_ns'], 'within_cap': res['account']['within_cap'],
                       'overrun_ns': res['account']['overrun_ns'], 'stop_reason': res['account']['stop_reason'],
                       'attempts': res['account']['attempts'], 'screened_out': len(res['screened_out']),
                       'prover_reported': sum(r['prover_reported'] for r in recs),
                       'eligible': sum(r['prover_reported'] and r['budget_eligible'] and r['exposure_ok'] for r in recs),
                       'empty_eligible': sum(r['prover_reported'] and r['budget_eligible'] for r in recs0),
                       'targets': len(ev), 'custody_problems': [p['code'] for p in sp],
                       'manifest_id': man['manifest_id']}
                if pol == 'learned':
                    labels = RS.usefulness_labels(res, evr)
                    row['calibration_brier'] = brier([(RS.predict(weights, RS.features(by_text[t], dev)), l)
                                                      for t, l in labels.items()])
                dump(out / 'runs' / unit / f'{pol}.json', {'row': row, 'manifest': man, 'targets': recs,
                                                           'research_account': res['account'],
                                                           'evaluation_account': evr['account'],
                                                           'trajectory': res['trajectory']})
                rows.append(row)
                log(f'{unit} {pol}: eligible {row["eligible"]}/{len(ev)} (empty {row["empty_eligible"]}), '
                    f'library {row["library"]}, cpu {row["research_cpu_ns"] / 1e9:.2f}/{row["cap_ns"] / 1e9:.2f} s')
    dump(out / 'rows.json', rows)
    dump(out / 'screen_summary.json', screen.summary())
    log(f'phase 1 done in {time.monotonic() - t_start:.0f} s')


def lean_selection(out):
    rng = random.Random(SAMPLE_SEED)
    chosen = []
    for f in sorted((out / 'runs').glob('*/*.json')):
        d = json.loads(f.read_text())
        pol = f.stem
        for r in d['targets']:
            if not r['prover_reported']:
                continue
            if pol in ('fixed', 'learned') or rng.random() < SAMPLE_SHARE:
                chosen.append((f, r['record_id']))
    return chosen


def phase_lean(out, log):
    objects = C.ObjectStore(out / 'objects')
    tc = {'checker_identity': C.checker_identity()['identity']}
    done_dir = out / 'lean'
    done_dir.mkdir(exist_ok=True)
    sel = lean_selection(out)
    cache = {}
    for i, (f, rid) in enumerate(sel):
        dest = done_dir / f'{rid}.json'
        if dest.exists():
            continue
        if f not in cache:
            cache.clear()
            cache[f] = json.loads(f.read_text())
        d = cache[f]
        rec = next(r for r in d['targets'] if r['record_id'] == rid)
        res = C.replay_target(rec, d['manifest'], objects, task_statement=rec['statement'], trust_context=tc,
                              name=f'e3r{rid[:12]}')
        dump(dest, dict(res, run=str(f.relative_to(out))))
        log(f'lean {i + 1}/{len(sel)} {f.parent.name}/{f.stem}: {res["status"]}')


def phase_report(out, log):
    tc = {'checker_identity': C.checker_identity()['identity']}
    checks = {p.stem: json.loads(p.read_text()) for p in (out / 'lean').glob('*.json')} if (out / 'lean').exists() else {}
    rows, metrics = json.loads((out / 'rows.json').read_text()), {}
    for f in sorted((out / 'runs').glob('*/*.json')):
        d = json.loads(f.read_text())
        metrics[(f.parent.name, f.stem)] = C.score(d['targets'], checks, trust_context=tc)
    paired = []
    for s in SYSTEMS:
        for seed in EVAL_SEEDS:
            unit = f'{s}@{seed}'
            r = {x['policy']: x for x in rows if x['system'] == s and x['seed'] == seed}
            m = {p: metrics[(unit, p)] for p in POLICIES + ['empty']}
            paired.append({'unit': unit, **{f'{p}_eligible': r[p]['eligible'] for p in POLICIES},
                           'empty_eligible': r['fixed']['empty_eligible'],
                           'fixed_checked': m['fixed']['checked'], 'learned_checked': m['learned']['checked'],
                           'learned_minus_fixed': r['learned']['eligible'] - r['fixed']['eligible'],
                           'learned_minus_best_baseline': r['learned']['eligible'] -
                           max(r[p]['eligible'] for p in POLICIES if p != 'learned')})
    d = [x['learned_minus_fixed'] for x in paired]
    report = {
        'study': STUDY, 'independent_runs_per_policy': len(paired),
        'wins_ties_losses_vs_fixed': [sum(v > 0 for v in d), sum(v == 0 for v in d), sum(v < 0 for v in d)],
        'mean_learned_minus_fixed': round(statistics.mean(d), 3),
        'mean_learned_minus_best_baseline': round(statistics.mean(x['learned_minus_best_baseline'] for x in paired), 3),
        'mean_eligible': {p: round(statistics.mean(x[f'{p}_eligible'] for x in paired), 3) for p in POLICIES + ['empty']},
        'all_runs_within_cap': all(r['within_cap'] for r in rows),
        'max_overrun_ns': max(r['overrun_ns'] for r in rows),
        'custody_problems': sum(len(r['custody_problems']) for r in rows),
        'metrics_by_run': {f'{u}:{p}': v for (u, p), v in sorted(metrics.items())},
        'lean_totals': {k: sum(v[k] for v in metrics.values()) for k in ('prover_reported', 'checked', 'replay_attempted',
                                                                         'check_incomplete')},
        'lean_status_counts': {s_: sum(c['status'] == s_ for c in checks.values())
                               for s_ in sorted({c['status'] for c in checks.values()})},
        'paired': paired,
        'claim': 'DEV only; better-improver UNESTABLISHED (no sealed panel, no custodian); primary comparison is at '
                 'equal research caps with training not charged (declared)'}
    dump(out / 'e3_summary.json', report)
    log(json.dumps({k: report[k] for k in ('wins_ties_losses_vs_fixed', 'mean_learned_minus_fixed', 'mean_eligible',
                                            'all_runs_within_cap', 'custody_problems', 'lean_totals',
                                            'lean_status_counts')}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--phase', choices=['main', 'lean', 'report'], default='main')
    a = ap.parse_args(argv)
    out = Path(a.out)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if a.phase == 'main':
        out.mkdir(parents=True, exist_ok=False)
        phase_main(out, log)
    elif a.phase == 'lean':
        phase_lean(out, log)
    else:
        phase_report(out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
