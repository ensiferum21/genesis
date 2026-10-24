"""Genesis Ω contract §10, §16.8: a process that improves another process can itself be transformed, at any level,
with lineage; one fuel budget and a depth limit stop runaway execution."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import process as P  # noqa: E402


def hill(proc, task, fuel):
    """A level-1 process: a hill climber over a bit string; its yield is the best fitness it reaches."""
    rng = random.Random(proc['params']['seed'])
    x = [0] * task['n']
    best = 0
    for _ in range(proc['params']['tries']):
        fuel.take()
        i = rng.randrange(task['n'])
        x[i] ^= 1
        f = sum(b == t for b, t in zip(x, task['target']))
        if f >= best:
            best = f
        else:
            x[i] ^= 1
    return best


TASK = {'n': 20, 'target': [1, 0] * 10}
L1 = {'level': 1, 'kind': 'hill', 'params': {'tries': 10, 'seed': 1, 'space': {'tries': [5, 10, 20, 40, 80]}},
      'lineage': []}


class Levels(unittest.TestCase):
    def test_level2_improves_level1_and_level3_transforms_level2(self):
        L2 = {'level': 2, 'kind': 'tuner', 'params': {'variants': 3, 'step': 1, 'subtask': TASK,
                                                      'space': {'variants': [1, 2, 3, 4, 6], 'step': [1, 2]}},
              'lineage': []}
        fuel = P.Fuel(10_000)
        best1, y = P.step(L2, L1, fuel, hill)
        self.assertGreaterEqual(y, P.step(L1, TASK, P.Fuel(1000), hill))
        self.assertEqual(best1['level'], 1)
        L3 = {'level': 3, 'kind': 'meta-tuner', 'params': {'variants': 2, 'step': 1}, 'lineage': []}
        L2t = dict(L2, params=dict(L2['params'], target=L1))
        best2, y2 = P.step(L3, L2t, P.Fuel(100_000), hill)
        self.assertEqual(best2['level'], 2)                    # the improver itself was transformed (or kept)
        child = P.mutate(L2t, L3, random.Random(5))
        self.assertEqual(child['lineage'][-1]['by'], P.key(L3))
        self.assertIn(child['lineage'][-1]['changed'], ('variants', 'step'))

    def test_fuel_and_depth_stop_runaway(self):
        greedy = {'level': 2, 'kind': 'tuner', 'params': {'variants': 10 ** 9, 'step': 1, 'subtask': TASK},
                  'lineage': []}
        fuel = P.Fuel(500)
        with self.assertRaises(P.OutOfFuel):
            P.step(greedy, L1, fuel, hill)
        self.assertEqual(fuel.left, 0)
        with self.assertRaises(P.OutOfFuel):
            P.step(L1, TASK, P.Fuel(10), hill, depth=P.MAX_DEPTH + 1)
        with self.assertRaises(ValueError):
            P.step({'level': 3, 'kind': 'x', 'params': {}}, L1, P.Fuel(10), hill)


if __name__ == '__main__':
    unittest.main()
