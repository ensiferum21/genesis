#!/usr/bin/env python3
"""B20_R160 (F1, engineering): the development look at the Frontier engine on planted worlds (DEV; disclosed).

    taskset -c 1 python3 scripts/b20r160_frontier_devlook.py evidence/frontier_dev_b20r160

Development worlds 1001-1008 (4 problems each, budget 8,000, quantum 10), one run per arm and world: the Frontier's
allocation alone (no abstraction, no branching out), the Frontier with both, and the comparators (successive
halving, uniform, UCB1, random). Value: the total verified value over a world's problems divided by the world's
reference (`PlantedWorld.oracle`: each initial problem's best planted curve at an equal share of the budget; it
ignores successors and invented representations, so the full Frontier can exceed 1). These numbers shaped the
design (the exploration share, the value of opening a direction, the material-improvement rule) and license
nothing: F3 (B20_R156) tests the engine on sealed worlds from held-out families.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402
from genesis.frontier.world import PlantedWorld  # noqa: E402

BUDGET, WORLDS = 8000, range(1001, 1009)
ARMS = (('frontier', False), ('frontier+', True), ('halving', False), ('uniform', False), ('ucb', False),
        ('random', False))


def main(argv=None):
    out = Path((sys.argv[1:] if argv is None else argv)[0])
    out.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.time()
    for ws in WORLDS:
        for arm, ab in ARMS:
            w = PlantedWorld(ws, problems=4, horizon=BUDGET)
            e = Frontier(Manifest(w, w.verify, BUDGET, quantum=10), arm.rstrip('+'), seed=ws - 1000,
                         abstraction=ab, branch_out=ab)
            e.run()
            s = e.summary()
            rows.append({'world': ws, 'arm': arm, 'value': s['total'] / w.oracle(BUDGET), 'total': s['total'],
                         'reference': w.oracle(BUDGET), 'branches': s['branches'], 'abstracted': s['abstracted'],
                         'invented': len(s['invented']), 'revealed': s['revealed'], 'verify_calls': s['verify_calls']})
    means = {arm: statistics.mean(r['value'] for r in rows if r['arm'] == arm) for arm, _ in ARMS}
    wins = {arm: sum(1 for ws in WORLDS
                     if [r for r in rows if r['world'] == ws and r['arm'] == 'frontier'][0]['value'] >
                     [r for r in rows if r['world'] == ws and r['arm'] == arm][0]['value'])
            for arm, _ in ARMS if arm not in ('frontier', 'frontier+')}
    summary = {'schema': 'genesis-b20r160-frontier-devlook-v1', 'budget': BUDGET, 'worlds': list(WORLDS),
               'means': means, 'frontier_allocation_wins_of_8': wins, 'rows': rows,
               'seconds': round(time.time() - t0, 1), 'status': 'DEV look; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
