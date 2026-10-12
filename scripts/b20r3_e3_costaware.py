#!/usr/bin/env python3
"""B20_R3 (B20R-OPEN-1): frozen DEV study of the redesigned (cost-aware) research policy.

    b20r3_e3_costaware.py OUT_DIR                  phase 1: material, calibration, training, evaluation, custody
    b20r3_e3_costaware.py OUT_DIR --phase lean     phase 2: Lean replay from custody (resumable; --shard i/n)
    b20r3_e3_costaware.py OUT_DIR --phase report   summary and the preregistered verdicts

Question. Does the redesigned learned policy (``research.CostAware``, arm ``learned2``: features
linear in the pool, ranking by expected useful lemmas per CPU second) remove the B20_R2 failure
(learned vs fixed 0W/2T/6L, preparation eating the Huntington cap), and does it beat fixed rules?

Context fixed before this study (``evidence/headroom_pilot_b20r3``, design pilot, DEV): on
every system and target range tried, an oracle library built from the targets themselves
proves at most one more of 12 targets than the fixed policy's library under the same cap;
on Huntington the smallest pool lemma (idempotence) is the expensive key lemma, so
smallest-first is already the oracle. A superiority result is therefore not expected on this
family; the study measures its own discriminating power (the ORACLE diagnostic below) so the
verdict can say whether superiority was possible at all.

Rules fixed here before running (the B20_R2 design, replicated on fresh seeds, plus one arm):
  * systems ba_sheffer and ba_huntington; seeds: calibration 510, training 511-513,
    evaluation 611-614; pools as in B20 (pool_for); 10 development targets per seed with
    5-11 nodes, drawn before calibration.
  * exposure: every equation in prior DEV evidence of these signatures (learning_b20,
    orbit_probe_b20r, e3_fresh_b20r, headroom_pilot_b20r3; Wolfram material counts for Sheffer),
    the B20 pools regenerated and hash-checked, the B20_R2 pools and development targets
    regenerated, and every pool and development target of this study. Calibration and
    evaluation targets drawn with learning.partitions (EXACT/ALPHA/INSTANCE rejected,
    GENERALIZES quarantined); calibration targets join the exposure first.
  * calibration (B20 rule): first range in the grid with empty-library rate in [0.2, 0.6], else
    closest to 0.4; research cap = 0.25 x the fixed policy's pool-exhaustion CPU under the
    repaired account.
  * budgets: StudyBudget OUTER_SUPERVISED, quantum 0.1 s, 1 s prover attempts (+0.25 s reserve),
    kill tolerance 0.05 s held back; identical record for every arm.
  * training: 18 runs (3 seeds x 2 systems x fixed/random/heuristic) under the repaired harness,
    each evaluated on its development targets. From the same runs: the B20_R2 logistic policy
    (arm ``learned``, pooled over systems, its features and labels) and the cost-aware model
    (arm ``learned2``, one model per system, labels = needed by an eligible development-target
    proof). Both frozen (hashes) before any evaluation run.
  * charging, declared: PRIMARY comparison at equal research caps; training NOT charged to the
    learned arms (reported in full, with the amortized share per use as a number).
  * insertion screen against all evaluation targets, as in B20_R2.
  * evaluation: 25 targets per unit, 1 s per target, 8 most relevant lemmas; custody for every
    scored proof; per arm the research account (preparation CPU reported separately).
  * ORACLE diagnostic per unit (not an arm, uses the evaluation targets): the fixed policy
    exhausts the pool without a cap; ORACLE is the dependency closure of the lemmas that
    eligible exhaust-library proofs of the unit's targets used, evaluated like the arms.
  * endpoints: per run prover_reported, eligible (budget and exposure) and checked.
    PRIMARY: learned2 - fixed on eligible successes per unit (8 units), DEV.
  * verdicts (fixed here):
      vs fixed      SUPERIOR_DEV if wins >= 6 of 8 and mean >= +1.0; else NON_INFERIOR_DEV if
                    mean >= -0.5 and no unit below -2; else INFERIOR_DEV.
      material      DISCRIMINATING if mean(ORACLE - fixed) >= 2.0, else NOT_DISCRIMINATING
                    (superiority over fixed was not available on this material for any arm).
      repair        mean(learned2 - learned) and the preparation CPU of both, reported.
  * Lean phase: every prover-reported success of the fixed and learned2 arms; nothing else.
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
from genesis.fol import parse  # noqa: E402
from genesis.learning import custody as C  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import partitions as P  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account, StudyBudget  # noqa: E402

STUDY = 'b20r3-e3-costaware-dev'
SYSTEMS = ['ba_sheffer', 'ba_huntington']
CAL_SEED, TRAIN_SEEDS, EVAL_SEEDS = 510, [511, 512, 513], [611, 612, 613, 614]
R2_SEEDS = [500, 501, 502, 503, 601, 602, 603, 604]
POLICIES = ['fixed', 'random', 'heuristic', 'bandit', 'learned', 'learned2']
TARGET_GRID = [(5, 8), (6, 9), (7, 10), (8, 11)]
RATE_BAND, BUDGET_SHARE = (0.2, 0.6), 0.25
BASE = {'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30, 'dev_targets': 10, 'eval_targets': 25,
        'prove_s': 1, 'eval_s': 1, 'premise_k': 8, 'calibration_targets': 20}
BUDGET_KW = {'enforcement': 'OUTER_SUPERVISED', 'quantum_ns': 100_000_000}
SALT = b'b20r3-e3-costaware-dev-screen-salt-v1'      # DEV: the builder sees everything anyway
OPS = {'ba_sheffer': {'s'}, 'ba_huntington': {'plus', 'n'}}
EXPOSURE_ROOTS = ['learning_b20', 'orbit_probe_b20r', 'e3_fresh_b20r', 'headroom_pilot_b20r3']
LEAN_ARMS = ('fixed', 'learned2')
VERDICT = {'superior_wins': 6, 'superior_mean': 1.0, 'noninferior_mean': -0.5, 'noninferior_floor': -2,
           'discriminating_mean': 2.0}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def max_term(system):
    return 4 if system == 'ba_huntington' else 5


def pool_for(system, seed):
    return Q.true_equations(system, BASE['pool_size'], per_bucket=BASE['per_bucket'], seed=seed) + \
        Q.false_equations(system, BASE['pool_size'], BASE['false_conjectures'], seed=seed)


def dev_for(system, seed, pool):
    return Q.sample_targets(system, BASE['dev_targets'], min_total=5, max_total=11, max_term=max_term(system),
                            seed=seed * 7 + 1, exclude=pool)


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
    """Every equation in prior DEV evidence, assigned to a system by its signature, plus the
    regenerated B20 and B20_R2 pools and B20_R2 development targets."""
    found, files = [], 0

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
    for name in EXPOSURE_ROOTS:
        for f in sorted((ROOT / 'evidence' / name).rglob('*.json')):
            files += 1
            walk(json.loads(f.read_text()), str(f.relative_to(ROOT)))
    setup = json.loads((ROOT / 'evidence' / 'learning_b20' / 'setup.json').read_text())['material']
    regenerated = 0
    for key, m in setup.items():
        system, seed = key.rsplit('@', 1)
        pool = pool_for(system, int(seed))
        if digest([Q.text(x) for x in pool]) != m['pool_sha256']:
            raise SystemExit(f'B20 pool {key} does not regenerate to its recorded hash')
        found += [(system, e, f'regenerated B20 pool {key}') for e in pool]
        regenerated += 1
    for system in SYSTEMS:
        for seed in R2_SEEDS:
            pool = pool_for(system, seed)
            found += [(system, e, f'regenerated B20_R2 pool {system}@{seed}') for e in pool]
            if seed != 500:
                found += [(system, e, f'regenerated B20_R2 development {system}@{seed}')
                          for e in dev_for(system, seed, pool)]
            regenerated += 1
    return found, {'files_scanned': files, 'statements': len(found), 'pools_regenerated': regenerated,
                   'roots': EXPOSURE_ROOTS}


def make_policy(name, seed, weights=None, models=None, system=None):
    return {'fixed': lambda: RS.Fixed(seed), 'random': lambda: RS.Random(seed), 'heuristic': lambda: RS.Heuristic(seed),
            'bandit': lambda: RS.Bandit(seed), 'learned': lambda: RS.Learned(weights, seed),
            'learned2': lambda: RS.CostAware(models[system], seed)}[name]()


def budget(cap_s):
    return StudyBudget.from_seconds(cap_s, attempt_s=BASE['prove_s'], **BUDGET_KW)


def brier(pairs):
    return round(statistics.mean((p - y) ** 2 for p, y in pairs), 4) if pairs else None


def closure(library, ids):
    by, out, stack = {l['id']: l for l in library}, set(), list(ids)
    while stack:
        i = stack.pop()
        if i not in out:
            out.add(i)
            stack += by[i]['uses']
    return [l for l in library if l['id'] in out]


def phase_main(out, log):
    t_start = time.monotonic()
    mats = {}
    for s in SYSTEMS:
        for seed in [CAL_SEED] + TRAIN_SEEDS + EVAL_SEEDS:
            pool = pool_for(s, seed)
            mats[(s, seed)] = {'pool': pool, 'dev': dev_for(s, seed, pool) if seed != CAL_SEED else []}
    prior, prior_stats = prior_exposure()
    visible = [(s, e, src, 'import') for s, e, src in prior]
    for (s, seed), m in mats.items():
        visible += [(s, e, f'{s}@{seed}', 'pool') for e in m['pool']]
        visible += [(s, e, f'{s}@{seed}', 'development') for e in m['dev']]
    log(f'exposure: {prior_stats}, study-visible {len(visible) - len(prior)}')
    # ---------------- calibration
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
    # ---------------- evaluation partition
    visible_eval = visible + [(u['system'], eq_of(a['text']), name, 'import')
                              for name, u in cal_part['units'].items() for a in u['accepted']]
    eval_units = [(f'{s}@{seed}', s) for s in SYSTEMS for seed in EVAL_SEEDS]

    def eval_sampler(unit, system, rng):
        lo, hi = cals[system]['chosen_range']
        return P.equational_sampler(min_total=lo, max_total=hi, max_term=max_term(system))(unit, system, rng)
    part = P.build_partition(study=STUDY, study_seed=610, visible=visible_eval, units=eval_units, sampler=eval_sampler,
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
              'screen_commitment': screen.commitment(), 'prior_exposure': prior_stats, 'verdict_rules': VERDICT,
              'code_identity': code_identity(ROOT)['sha256']}
    dump(out / 'setup.json', dict(frozen, frozen_sha256=digest(frozen)))
    log(f'setup frozen: partition {part["partition_id"][:16]}')
    # ---------------- training (both learned arms from the same runs), then freeze
    X, y, ex2, train = [], [], {s: [] for s in SYSTEMS}, []
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
                e2 = RS.training_examples_v2(res, evd, dev, by_text)
                ex2[s] += e2
                train.append({'system': s, 'seed': seed, 'policy': pol, 'library': len(res['library']),
                              'tried': len(res['trajectory']), 'dev_proved': evd['proved'],
                              'v1_positives': sum(labels.values()), 'v2_examples': len(e2),
                              'v2_used': sum(e['used'] for e in e2), 'research_cpu_ns': res['account']['cpu_ns_total'],
                              'within_cap': res['account']['within_cap']})
                log(f'train {s}@{seed} {pol}: library {len(res["library"])}, dev {evd["proved"]}/{len(dev)}, '
                    f'v2 used {train[-1]["v2_used"]}')
    c0 = time.process_time_ns()
    weights = RS.fit_logistic(X, y)
    fit1_ns = time.process_time_ns() - c0
    c0 = time.process_time_ns()
    models = {s: RS.fit_cost_aware(ex2[s]) for s in SYSTEMS}
    fit2_ns = time.process_time_ns() - c0
    policy = {'learned': {'features': RS.FEATURE_NAMES, 'weights': weights, 'examples': len(y), 'positives': sum(y),
                          'training_brier': brier([(RS.predict(weights, x), t) for x, t in zip(X, y)]),
                          'weights_sha256': digest(weights), 'fit_cpu_ns': fit1_ns},
              'learned2': {'models': models, 'model_sha256': {s: m['model_sha256'] for s, m in models.items()},
                           'fit_cpu_ns': fit2_ns},
              'frozen_before_evaluation': True,
              'training_cpu_ns': {'research_and_dev_evaluation': train_cpu_ns, 'fit': fit1_ns + fit2_ns},
              'amortized_share_per_use_ns': (train_cpu_ns + fit1_ns + fit2_ns) // (len(SYSTEMS) * len(EVAL_SEEDS)),
              'charging': 'PRIMARY comparison does not charge training (declared); see the module docstring'}
    policy['policy_sha256'] = digest(policy)
    dump(out / 'train' / 'policy.json', policy)
    dump(out / 'train' / 'runs.json', train)
    log(f'policies frozen: learned {policy["learned"]["weights_sha256"][:16]}, learned2 '
        f'{ {s: m["model_sha256"][:12] for s, m in models.items()} }; training CPU '
        f'{(train_cpu_ns + fit1_ns + fit2_ns) / 1e9:.1f} s')
    # ---------------- evaluation runs with custody, then the ORACLE diagnostic
    objects = C.ObjectStore(out / 'objects')
    rows, oracle = [], []
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
                res = RS.run(s, make_policy(pol, seed, weights, models, s), pool,
                             account=Account(budget(cals[s]['budget_s']), label=f'eval:{unit}:{pol}'),
                             dev_targets=dev, prove_s=BASE['prove_s'], premise_k=BASE['premise_k'], screen=screen,
                             run_id=f'{STUDY}:{unit}:{pol}')
                evr = RS.evaluate_successor(s, res['library'], ev, eval_s=BASE['eval_s'], label=f'succ:{unit}:{pol}',
                                            task_ids=task_ids)
                ident = {'learned': policy['learned']['weights_sha256'],
                         'learned2': models[s]['model_sha256']}.get(pol, pol)
                man = C.successor_manifest(res, objects, policy_identity=ident, exposure_root=part['exposure']['root'])
                recs = C.target_records(evr, man, objects, panel_id=unit, task_ids=task_ids)
                sp = C.successor_problems(man, objects)
                acct = res['account']
                row = {'system': s, 'seed': seed, 'policy': pol, 'library': len(res['library']),
                       'tried': len(res['trajectory']), 'research_cpu_ns': acct['cpu_ns_total'],
                       'preparation_cpu_ns': acct['cpu_ns_by_category'].get('preparation', 0),
                       'policy_cpu_ns': acct['cpu_ns_by_category'].get('policy', 0),
                       'cap_ns': acct['budget']['cpu_ns'], 'within_cap': acct['within_cap'],
                       'overrun_ns': acct['overrun_ns'], 'stop_reason': acct['stop_reason'],
                       'attempts': acct['attempts'], 'screened_out': len(res['screened_out']),
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
                                                           'research_account': acct,
                                                           'evaluation_account': evr['account'],
                                                           'trajectory': res['trajectory']})
                rows.append(row)
                log(f'{unit} {pol}: eligible {row["eligible"]}/{len(ev)} (empty {row["empty_eligible"]}), '
                    f'library {row["library"]}, cpu {row["research_cpu_ns"] / 1e9:.2f}/{row["cap_ns"] / 1e9:.2f} s, '
                    f'prep {row["preparation_cpu_ns"] / 1e6:.0f} ms')
            ex = RS.run(s, RS.Fixed(), pool, account=Account(budget(10 ** 5), label=f'oracle-exhaust:{unit}'),
                        prove_s=BASE['prove_s'], premise_k=BASE['premise_k'], screen=screen)
            e_ex = RS.evaluate_successor(s, ex['library'], ev, eval_s=BASE['eval_s'], label=f'oracle-exhaust:{unit}')
            used = sorted({u for r in e_ex['rows'] if r['status'] == 'PROVED' for u in r['lemmas_used']})
            orc = closure(ex['library'], used)
            e_or = RS.evaluate_successor(s, orc, ev, eval_s=BASE['eval_s'], label=f'oracle:{unit}')
            oracle.append({'unit': unit, 'exhaust_library': len(ex['library']), 'exhaust_cpu_s': ex['cpu_s'],
                           'exhaust_proved': e_ex['proved'], 'oracle_library': len(orc), 'oracle_proved': e_or['proved'],
                           'oracle_lemmas': [l['text'] for l in orc]})
            log(f'{unit} ORACLE diagnostic: exhaust {e_ex["proved"]}, oracle {e_or["proved"]} ({len(orc)} lemmas)')
    dump(out / 'rows.json', rows)
    dump(out / 'oracle.json', oracle)
    dump(out / 'screen_summary.json', screen.summary())
    log(f'phase 1 done in {time.monotonic() - t_start:.0f} s')


def lean_selection(out):
    chosen = []
    for f in sorted((out / 'runs').glob('*/*.json')):
        if f.stem not in LEAN_ARMS:
            continue
        d = json.loads(f.read_text())
        chosen += [(f, r['record_id']) for r in d['targets'] if r['prover_reported']]
    return chosen


def phase_lean(out, log, shard=0, count=1):
    objects = C.ObjectStore(out / 'objects')
    tc = {'checker_identity': C.checker_identity()['identity']}
    done_dir = out / 'lean'
    done_dir.mkdir(exist_ok=True)
    sel = lean_selection(out)
    for i, (f, rid) in enumerate(sel):
        dest = done_dir / f'{rid}.json'
        if i % count != shard or dest.exists():
            continue
        d = json.loads(f.read_text())
        rec = next(r for r in d['targets'] if r['record_id'] == rid)
        res = C.replay_target(rec, d['manifest'], objects, task_statement=rec['statement'], trust_context=tc,
                              name=f'e3c{rid[:12]}')
        dump(dest, dict(res, run=str(f.relative_to(out))))
        log(f'lean {i + 1}/{len(sel)} {f.parent.name}/{f.stem}: {res["status"]}')


def verdicts(paired, oracle):
    d = [x['learned2_minus_fixed'] for x in paired]
    wins = sum(v > 0 for v in d)
    mean = statistics.mean(d)
    if wins >= VERDICT['superior_wins'] and mean >= VERDICT['superior_mean']:
        vs_fixed = 'SUPERIOR_DEV'
    elif mean >= VERDICT['noninferior_mean'] and min(d) >= VERDICT['noninferior_floor']:
        vs_fixed = 'NON_INFERIOR_DEV'
    else:
        vs_fixed = 'INFERIOR_DEV'
    fixed = {x['unit']: x['fixed_eligible'] for x in paired}
    headroom = [o['oracle_proved'] - fixed[o['unit']] for o in oracle]
    material = 'DISCRIMINATING' if statistics.mean(headroom) >= VERDICT['discriminating_mean'] else 'NOT_DISCRIMINATING'
    return {'vs_fixed': vs_fixed, 'material': material, 'oracle_minus_fixed': headroom,
            'mean_oracle_minus_fixed': round(statistics.mean(headroom), 3)}


def phase_report(out, log):
    tc = {'checker_identity': C.checker_identity()['identity']}
    checks = {p.stem: json.loads(p.read_text()) for p in (out / 'lean').glob('*.json')} if (out / 'lean').exists() else {}
    rows, metrics = json.loads((out / 'rows.json').read_text()), {}
    oracle = json.loads((out / 'oracle.json').read_text())
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
                           'fixed_checked': m['fixed']['checked'], 'learned2_checked': m['learned2']['checked'],
                           'learned2_minus_fixed': r['learned2']['eligible'] - r['fixed']['eligible'],
                           'learned2_minus_learned': r['learned2']['eligible'] - r['learned']['eligible'],
                           'learned2_minus_best_baseline': r['learned2']['eligible'] -
                           max(r[p]['eligible'] for p in POLICIES if p not in ('learned', 'learned2')),
                           'learned_minus_fixed': r['learned']['eligible'] - r['fixed']['eligible']})
    d = [x['learned2_minus_fixed'] for x in paired]
    prep = {p: round(statistics.mean(x['preparation_cpu_ns'] + x['policy_cpu_ns'] for x in rows if x['policy'] == p) / 1e6, 1)
            for p in POLICIES}
    report = {
        'study': STUDY, 'independent_runs_per_policy': len(paired),
        'wins_ties_losses_learned2_vs_fixed': [sum(v > 0 for v in d), sum(v == 0 for v in d), sum(v < 0 for v in d)],
        'mean_learned2_minus_fixed': round(statistics.mean(d), 3),
        'wins_ties_losses_learned_vs_fixed': [sum(x['learned_minus_fixed'] > 0 for x in paired),
                                              sum(x['learned_minus_fixed'] == 0 for x in paired),
                                              sum(x['learned_minus_fixed'] < 0 for x in paired)],
        'mean_learned2_minus_learned': round(statistics.mean(x['learned2_minus_learned'] for x in paired), 3),
        'mean_learned2_minus_best_baseline': round(statistics.mean(x['learned2_minus_best_baseline'] for x in paired), 3),
        'mean_eligible': {p: round(statistics.mean(x[f'{p}_eligible'] for x in paired), 3) for p in POLICIES + ['empty']},
        'mean_oracle': round(statistics.mean(o['oracle_proved'] for o in oracle), 3),
        'mean_policy_and_preparation_cpu_ms': prep,
        'verdicts': verdicts(paired, oracle),
        'all_runs_within_cap': all(r['within_cap'] for r in rows),
        'max_overrun_ns': max(r['overrun_ns'] for r in rows),
        'custody_problems': sum(len(r['custody_problems']) for r in rows),
        'metrics_by_run': {f'{u}:{p}': v for (u, p), v in sorted(metrics.items())},
        'lean_totals': {k: sum(v[k] for (u, p), v in metrics.items() if p in LEAN_ARMS)
                        for k in ('prover_reported', 'checked', 'replay_attempted', 'check_incomplete')},
        'lean_status_counts': {s_: sum(c['status'] == s_ for c in checks.values())
                               for s_ in sorted({c['status'] for c in checks.values()})},
        'paired': paired, 'oracle': oracle,
        'claim': 'DEV only; better-improver UNESTABLISHED (no sealed panel, no custodian); primary comparison at equal '
                 'research caps with training not charged (declared)'}
    dump(out / 'e3_summary.json', report)
    log(json.dumps({k: report[k] for k in ('wins_ties_losses_learned2_vs_fixed', 'mean_learned2_minus_fixed',
                                            'mean_learned2_minus_learned', 'mean_eligible', 'mean_oracle',
                                            'mean_policy_and_preparation_cpu_ms', 'verdicts', 'all_runs_within_cap',
                                            'custody_problems', 'lean_totals', 'lean_status_counts')}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--phase', choices=['main', 'lean', 'report'], default='main')
    ap.add_argument('--shard', default='0/1')
    a = ap.parse_args(argv)
    out = Path(a.out)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if a.phase == 'main':
        out.mkdir(parents=True, exist_ok=False)
        phase_main(out, log)
    elif a.phase == 'lean':
        i, n = (int(x) for x in a.shard.split('/'))
        phase_lean(out, log, i, n)
    else:
        phase_report(out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
