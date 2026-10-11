#!/usr/bin/env python3
"""B19 / W14, second DEV evaluation on fresh pools (written after the first one).

  b19_active_v2.py OUT_DIR          (OUT_DIR/active_v2 must not exist)

The first evaluation (`b19_discovery.py`, phase active) found expected-information-gain
selection worse than round-robin and random at both budgets. That result is kept as it
is. Two policies were then added (`kg`, a lookahead knowledge gradient, and `top_two`,
top-two Thompson sampling). Because they were designed after seeing the first result,
they are evaluated here on fresh DEV pools from a new seed, together with the three
original policies, under the same budgets, repetitions and identifiability rules.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b19_discovery as D  # noqa: E402
from genesis import calibration as CAL  # noqa: E402
from genesis.discovery import active as A  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402

POOL_SEED2 = 20261027
POLICIES = ('eig', 'round_robin', 'random', 'kg', 'top_two')


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0]) / 'active_v2'
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rec = CAL.load('triangle_free_host_v1', ROOT)
    adapter = ADAPTERS['triangle_free_host_v1']
    k = 16
    calibrated, seen = CAL.calibrated_panel(rec, POOL_SEED2, k, 'DEV', excluded=set())
    hard, seen2, _ = adapter.generate(POOL_SEED2, k, 'DEV', 'erdos', {'n': 30, 'p': 0.3}, excluded=seen)
    bip, _, _ = adapter.generate(POOL_SEED2, k, 'DEV', 'bipartite', {'n': 22, 'p': 0.35}, excluded=seen2)
    families = {'erdos22': calibrated, 'erdos30': hard, 'bipartite22': bip}
    pools, costs, values, raw = {}, {}, {}, []
    for f, tasks in families.items():
        per, val, cpu = ({m: [] for m in D.METHODS} for _ in range(3))
        for t in tasks:
            runs = {m: D.run_method(m, t) for m in D.METHODS}
            opt, how = D.certified_optimum(t, [r['witness'] for r in runs.values()])
            if opt is None:
                raw.append({'task_id': t.task_id, 'family': f, 'dropped': 'optimum not certified'})
                continue
            for m, r in runs.items():
                per[m].append(int(r['value'] == opt)); val[m].append(r['value']); cpu[m].append(r['cpu_s'])
            raw.append({'task_id': t.task_id, 'family': f, 'optimum': opt, 'certified_by': how,
                        'values': {m: r['value'] for m, r in runs.items()}})
        for m in D.METHODS:
            pools[(m, f)], values[(m, f)] = per[m], val[m]
            costs[(m, f)] = round(max(0.01, statistics.mean(cpu[m])), 4)
        log(f'pool {f}: {len(per[D.METHODS[0]])} certified tasks')
    fams = list(families)
    total = sum(costs[(m, f)] * len(pools[(m, f)]) for m in D.METHODS for f in fams)
    declared = [('rr_cross_2', 'rr_adjacent_2')]
    result = {}
    for share in (0.2, 0.4):
        result[str(share)] = A.evaluate(pools, costs, D.METHODS, fams, budget=total * share, repetitions=40,
                                        declared=declared, draws=100, identity_pools=values, policies=POLICIES)
        log(f'{share:.0%}: {result[str(share)]["policies"]}')
    obj = {'split': 'DEV', 'seed': POOL_SEED2, 'methods': D.METHODS, 'families': fams, 'policies': list(POLICIES),
           'pool_sizes': {f: len(pools[(D.METHODS[0], f)]) for f in fams},
           'costs_cpu_s': {f'{m}@{f}': c for (m, f), c in costs.items()}, 'pool_cost_cpu_s': round(total, 2),
           'declared_indistinguishable': declared, 'by_budget': result,
           'calibration': A.calibration(pools, D.METHODS, fams), 'raw': raw,
           'note': 'kg and top_two were added after the first evaluation; these pools are fresh (new seed)'}
    D.dump(out / 'evaluation.json', obj)
    print(json.dumps({k: v['policies'] for k, v in result.items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
