"""Sense synthesis and the composite-primitive library (`senses/synthesis.py`; Batch R2, second part): the stump and
its cross-validation; charges; the search finds a planted distinction on random graphs (the best choice depends on the
share of positive weights) and does not find one where there is none; library entries are typed, recurring subtrees
used as one-node leaves with bounds on the expanded tree; the gate admits only on paired held-out gains."""
from pathlib import Path
import random
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.senses import graph as SG  # noqa: E402
from genesis.senses import synthesis as SY  # noqa: E402


def graphs(seed, count):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        n, p, rho = rng.randint(30, 60), rng.uniform(0.05, 0.2), rng.uniform(0.05, 0.95)
        E = [[u, v, (1 if rng.random() < rho else -1)] for u in range(n) for v in range(u + 1, n) if rng.random() < p]
        out.append({'n': n, 'edges': E})
    return out


def task(seed, count=80, planted=True, noise=0.3):
    gs = graphs(seed, count)
    ctx = [SG.Context(g) for g in gs]
    rng = np.random.default_rng(seed)
    pos = np.array([SG.evaluate(['frac_pos_e', 'w'], c) for c in ctx])
    M = rng.normal(0, noise, size=(count, 3))
    if planted:
        M[:, 0] += (pos < 0.5)
        M[:, 1] += (pos >= 0.5)
    M[:, 2] += 0.3
    return ctx, M


class Decision(unittest.TestCase):
    def test_stump(self):
        x = np.array([0.1, 0.2, 0.3, 0.8, 0.9])
        M = np.array([[1, 0], [1, 0], [1, 0], [0, 1], [0, 1]], float)
        theta, total = SY.stump(x, M)
        self.assertEqual(total, 5.0)
        self.assertEqual((theta[1], theta[2]), (0, 1))
        self.assertTrue(0.3 < theta[0] < 0.8)
        self.assertEqual(SY.act(theta, x).tolist(), [0, 0, 0, 1, 1])
        flat = SY.stump(np.zeros(5), M)
        self.assertEqual(flat[0][0], float('inf'))

    def test_cross_validation_is_held_out(self):
        rng = np.random.default_rng(0)
        M = rng.normal(size=(60, 2))
        x = rng.normal(size=60)
        fs = SY.folds(60, 4, 1)
        self.assertEqual(sorted(np.concatenate(fs).tolist()), list(range(60)))
        _, total = SY.stump(x, M)
        self.assertLess(SY.cv_value(x, M, fs), total / 60)          # in-sample fit flatters; held out does not

    def test_charges(self):
        ctx, _ = task(1, count=10)
        ch = {}
        SY.values(['mean_n', ['add_n', 'deg', 'clust']], ctx, charges=ch)
        self.assertAlmostEqual(ch['sense'], SY.SENSE_UNIT * 4 * 10)


class Search(unittest.TestCase):
    def test_finds_a_planted_distinction(self):
        ctx, M = task(11)
        r = SY.synthesise(ctx, M, budget=150, seed=3)
        self.assertGreater(r['value'], r['baseline'] + 0.25)
        self.assertGreater(r['value'], r['oracle'] - 0.35)
        self.assertIsNone(SY.check(r['sense']))
        self.assertGreater(r['charges']['sense'], 0)
        self.assertLessEqual(r['evaluated'], 150)
        x = SY.values(r['sense'], ctx)
        pos = np.array([SG.evaluate(['frac_pos_e', 'w'], c) for c in ctx])
        self.assertGreater(abs(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(pos)))[0, 1]), 0.6)

    def test_finds_nothing_where_there_is_nothing(self):
        ctx, M = task(12, planted=False)
        r = SY.synthesise(ctx, M, budget=150, seed=3)
        self.assertLess(r['value'], r['baseline'] + 0.1)

    def test_deterministic(self):
        ctx, M = task(13, count=40)
        a = SY.synthesise(ctx, M, budget=60, seed=5)
        b = SY.synthesise(ctx, M, budget=60, seed=5)
        self.assertEqual((a['sense'], a['value']), (b['sense'], b['value']))


class LibraryOfComposites(unittest.TestCase):
    def test_entries_are_typed_recurring_subtrees(self):
        w = [['mean_e', ['mul_e', 'w', 'wabs']], ['div_s', ['mean_e', ['mul_e', 'w', 'wabs']], 'n'],
             ['q90_n', ['nbr_mean', 'deg']]]
        new = SY.learn(w)
        self.assertEqual(len(new), 1)
        e = new[0]
        self.assertEqual(e['expr'], ['mean_e', ['mul_e', 'w', 'wabs']])
        self.assertEqual((e['type'], e['support']), ('S', 2))
        lib = SY.EMPTY.extend(new)
        self.assertNotEqual(lib.version, SY.EMPTY.version)
        self.assertEqual(lib.parent, SY.EMPTY.version)
        t = ['add_s', ['lib', e['name']], 'n']
        self.assertIsNone(SY.check(t, lib))
        self.assertIsNotNone(SY.check(t))                              # unknown without the library
        ctx = SG.Context(graphs(2, 1)[0])
        self.assertEqual(SY.evaluate(t, ctx, lib), SG.evaluate(['add_s', ['mean_e', ['mul_e', 'w', 'wabs']], 'n'], ctx))
        self.assertIsNotNone(SY.check(['mean_n', ['lib', e['name']]], lib))          # a scalar where N is expected

    def test_bounds_on_the_expanded_tree(self):
        big = ['add_s'] + [['mean_n', ['add_n', ['add_n', 'deg', 'clust'], ['add_n', 'tri', 'core']]]] * 2
        lib = SY.EMPTY.extend([{'name': 'c_big', 'type': 'S', 'expr': big, 'size': SG.size(big), 'support': 2,
                                'lineage': {}}])
        nested = ['add_s', ['lib', 'c_big'], ['add_s', ['lib', 'c_big'], ['add_s', ['lib', 'c_big'], ['lib', 'c_big']]]]
        self.assertIn('expanded', SY.check(nested, lib))

    def test_search_uses_the_library_and_the_gate_pairs(self):
        ctx, M = task(21, count=60)
        lib = SY.EMPTY.extend([{'name': 'c_pos', 'type': 'S', 'expr': ['frac_pos_e', 'w'], 'size': 2, 'support': 3,
                                'lineage': {}}])
        r = SY.synthesise(ctx, M, budget=60, seed=1, lib=lib)
        self.assertIsNone(SY.check(r['sense'], lib))
        tasks = []
        for s in (31, 32):
            c_tr, M_tr = task(s, count=50)
            c_te, M_te = task(s + 100, count=50)
            tasks.append((c_tr, M_tr, c_te, M_te))
        g = SY.gate(SY.EMPTY, lib, tasks, budget=30, seeds=(0, 1))
        self.assertEqual(len(g['pairs']), 4)
        self.assertEqual(g['admitted'], g['mean_gain'] > 0 and g['wins'] > g['losses'])


if __name__ == '__main__':
    unittest.main()
