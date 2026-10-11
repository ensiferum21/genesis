#!/usr/bin/env python3
"""B20 / E3 on a system with headroom (added after the main run; DEV only).

  b20_e3_hard.py OUT_DIR SEED [SEED ...]       (writes OUT_DIR/e3_hard/seed_<n>.json)

The main run (`b20_learning.py`) found no room for research to matter on its two systems:
E proves most evaluation targets without a library, and Huntington's targets sat at the
ceiling. Its W18 phase showed one system where research matters: from Wolfram's single
axiom, E proves none of the evaluation targets without help, and 240 s of plain
research raised that to 6 of 15. This script was therefore written after the main run.
Its rules are fixed below, before it runs:
  * system ba_wolfram, fresh seeds (311 and up), 15 evaluation targets of 5–8 nodes;
  * the same five policies, with 10 s per proof attempt. The research budget follows the
    main run's rule: a quarter of the CPU that the fixed policy needs to exhaust a
    calibration pool (seed 300), measured here and recorded. A first attempt with a fixed
    240 s budget was stopped after two runs: both exhausted the whole pool, so the policies
    could not differ. Its log is kept as e3_hard/attempt1_nonbinding_budget.log;
  * the learned policy is the main run's frozen policy, used as is. It was trained on
    other systems, so this is also a cross-system use of the policy;
  * each successor is evaluated with 3 s per target and the 8 most relevant lemmas.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SYSTEM = 'ba_wolfram'
CAL_SEED = 300
BUDGET_SHARE = 0.25
RULES = {'budget_s': None, 'prove_s': 10, 'eval_s': 3, 'eval_targets': 15, 'dev_targets': 10, 'premise_k': 8,
         'target_range': [5, 8], 'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30,
         'policies': ['fixed', 'random', 'heuristic', 'bandit', 'learned']}


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0]) / 'e3_hard'
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in argv[1:]]
    policy = json.loads((Path(argv[0]) / 'train' / 'policy.json').read_text())
    weights = policy['weights']
    assert digest(weights) == policy['weights_sha256']
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    cal_path = out / 'calibration.json'
    if cal_path.exists():
        cal = json.loads(cal_path.read_text())
    else:
        cpool = Q.true_equations(SYSTEM, RULES['pool_size'], per_bucket=RULES['per_bucket'], seed=CAL_SEED) + \
            Q.false_equations(SYSTEM, RULES['pool_size'], RULES['false_conjectures'], seed=CAL_SEED)
        res = RS.run(SYSTEM, RS.Fixed(), cpool, budget_s=10 ** 6, prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
        cal = {'seed': CAL_SEED, 'exhaust_cpu_s': res['cpu_s'], 'pool': len(cpool), 'library': len(res['library']),
               'budget_s': max(1.0, round(BUDGET_SHARE * res['cpu_s'], 2)), 'rule': f'{BUDGET_SHARE} x exhaust'}
        cal_path.write_text(json.dumps(cal, indent=1, sort_keys=True) + '\n')
        log(f'calibration: exhaust {res["cpu_s"]}s -> budget {cal["budget_s"]}s')
    RULES['budget_s'] = cal['budget_s']
    for seed in seeds:
        path = out / f'seed_{seed}.json'
        if path.exists():
            raise FileExistsError(path)
        pool = Q.true_equations(SYSTEM, RULES['pool_size'], per_bucket=RULES['per_bucket'], seed=seed) + \
            Q.false_equations(SYSTEM, RULES['pool_size'], RULES['false_conjectures'], seed=seed)
        lo, hi = RULES['target_range']
        dev = Q.sample_targets(SYSTEM, RULES['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
        ev = Q.sample_targets(SYSTEM, RULES['eval_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 2,
                              exclude=pool + dev)
        empty = RS.evaluate_successor(SYSTEM, [], ev, eval_s=RULES['eval_s'])
        rows = {}
        for name in RULES['policies']:
            pol = {'fixed': RS.Fixed(seed), 'random': RS.Random(seed), 'heuristic': RS.Heuristic(seed),
                   'bandit': RS.Bandit(seed), 'learned': RS.Learned(weights, seed)}[name]
            res = RS.run(SYSTEM, pol, pool, budget_s=RULES['budget_s'], dev_targets=dev, prove_s=RULES['prove_s'],
                         premise_k=RULES['premise_k'])
            evr = RS.evaluate_successor(SYSTEM, res['library'], ev, eval_s=RULES['eval_s'], premise_k=RULES['premise_k'])
            rows[name] = {'successor_proved': evr['proved'], 'library': len(res['library']),
                          'tried': len(res['trajectory']), 'research_cpu_s': res['cpu_s'],
                          'library_sha256': res['library_sha256'],
                          'lemmas_used': sorted(evr['lemma_use']), 'eval_rows': [
                              {k: r[k] for k in ('target', 'status', 'lemmas_used', 'premise_ids', 'proof')}
                              for r in evr['rows']],
                          'library_entries': [{k: l[k] for k in ('id', 'text', 'uses', 'premise_ids', 'proof')}
                                              for l in res['library']] if name in ('fixed', 'learned') else None}
            log(f'seed {seed} {name}: successor {evr["proved"]}/{len(ev)} (empty {empty["proved"]}), '
                f'library {len(res["library"])}, tried {len(res["trajectory"])}')
        path.write_text(json.dumps({'system': SYSTEM, 'seed': seed, 'rules': RULES, 'empty': empty['proved'],
                                    'targets': [Q.text(e) for e in ev], 'policies': rows,
                                    'policy_weights_sha256': policy['weights_sha256']},
                                   indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
