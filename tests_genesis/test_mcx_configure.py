"""B20_R105: the system configures `mcx-v1` on generated graphs only (design).

Fresh seed; the classes rotate through Gset's generator settings and never use Gset's own torus shapes; the two order
parameters separate the classes; the configurations drawn are valid, distinct and start with DEFAULT; successive
halving keeps the best and costs what the design says; the held-out labels; the registered output."""
from pathlib import Path
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r105_mcx_configure as M  # noqa: E402
from genesis.candidate_kinds import mcx as K  # noqa: E402
from genesis.domains import adapter  # noqa: E402

A = adapter('maxcut_v1')


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r105_mcx_configure.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_settings(self):
        self.assertEqual(M.CLASSES, ('random', 'toroidal', 'planar'))
        shapes = [M.setting('toroidal', i) for i in range(M.PER_CLASS)]
        plus = [p for f, p in shapes if f == 'torus2d']
        self.assertEqual(len(plus), M.PER_CLASS // 3)
        keys = {tuple(sorted((p['rows'], p['cols']))) for p in plus}
        self.assertEqual(len(keys), len(plus))                                  # distinct up to rotation
        self.assertFalse(keys & {(50, 60), (30, 100), (25, 120)})               # never G48-G50's shapes
        for f, p in shapes:
            self.assertTrue(2800 <= p['rows'] * p['cols'] <= 3200 or f == 'torus2d_pm1')
        for cls in M.CLASSES:
            for i in range(M.PER_CLASS):
                fam, params = M.setting(cls, i)
                self.assertIn(fam, A.families())
                self.assertEqual(set(params), set(A.families()[fam]))

    def test_order_parameters_separate_the_classes(self):
        small = {'random': ('erdos_pm1', {'n': 300, 'p': 0.06}), 'toroidal': ('torus2d_pm1', {'rows': 30, 'cols': 8}),
                 'planar': ('planar2', {'n': 300, 'density': 0.99})}
        train, test = [], []
        for cls, (fam, params) in small.items():
            ts, _, _ = A.generate(7, 6, 'DEV', fam, params)
            train += [(M.features(t), cls) for t in ts[:4]]
            test += [(M.features(t), cls) for t in ts[4:]]
        model = M.fit_classifier(train)
        self.assertTrue(all(M.classify(model, f) == c for f, c in test))
        self.assertEqual(M.features(A.generate(7, 1, 'DEV', 'torus2d', {'rows': 10, 'cols': 9})[0][0]), (0.0, 0.0))

    def test_configurations(self):
        for cls in M.CLASSES:
            cs = M.draw_configs(cls)
            self.assertEqual(len(cs), M.CANDIDATES)
            self.assertEqual(cs[0], K.DEFAULT)
            self.assertEqual(len({tuple(sorted(c.items())) for c in cs}), M.CANDIDATES)
            self.assertTrue(all(K.check_config(c) is None for c in cs))
            self.assertEqual(cs, M.draw_configs(cls))
        self.assertNotEqual(M.draw_configs('random'), M.draw_configs('planar'))

    def test_race(self):
        arms = [f'a{i}' for i in range(32)]
        quality = {a: random.Random(i).random() for i, a in enumerate(arms)}
        quality['a17'] = 2.0
        calls = set()

        def values_of(a, g):
            calls.add((a, g))
            return 1000 + 10 * quality[a] + random.Random(f'{a}{g}').random()
        graphs = [f'g{i}' for i in range(16)]
        win, hist = M.race(values_of, arms, M.ROUNDS_1S, graphs)
        self.assertEqual(win, 'a17')
        self.assertEqual(len(calls), 32 * 4 + 10 * 4 + 3 * 8)                  # 192 runs per class at 1 s
        self.assertEqual([len(h['ranked']) for h in hist], [32, 10, 3])
        same = lambda a, g: 1000                                                 # all tied: DEFAULT (first) wins
        self.assertEqual(M.race(same, arms, M.ROUNDS_1S, graphs)[0], 'a0')

    def test_labels(self):
        def held(chosen, default, burer):
            return {f'g{i}': {'chosen@1': chosen + i, 'default@1': default + i, 'burer@1': burer + i,
                              'chosen@10': chosen + i, 'default@10': default + i, 'burer@10': burer + i}
                    for i in range(24)}
        lab = M.labels(held(1010, 1000, 1000))
        self.assertEqual((lab['tuning@1']['label'], lab['vs_burer@10']['label']), ('TUNED_BETTER', 'MCX_AHEAD'))
        self.assertEqual(lab['vs_burer@1']['wins'], 24)
        lab = M.labels(held(1000, 1000, 1010))
        self.assertEqual((lab['tuning@10']['label'], lab['vs_burer@1']['label']), ('NO_DIFFERENCE', 'MCX_BEHIND'))
        self.assertEqual(M.compare([0.1] * 5, [0.2] * 5), (None, 1.0))         # fewer than 6 non-zero differences

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
