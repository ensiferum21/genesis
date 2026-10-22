"""B20_R100: the knowledge map (`autonomy.kmap`) and its first prospective test. Design: the cells it reads, the
uncertainty it reports (wider where it has no data), its self-calibration, the prediction grid and the verdict rule;
the predictions refuse to be written once B20_R86 is in the corpus."""
from pathlib import Path
import random
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from genesis.autonomy import kmap as K  # noqa: E402
import b20r100_knowledge_map as M  # noqa: E402


def synthetic(n_methods=('a', 'b'), seed=1, k=60):
    rng = random.Random(seed)
    out = []
    for m in n_methods:
        for _ in range(k):
            t = rng.choice((0.05, 0.1, 0.5, 2.0))
            q = min(1.0, 0.8 + 0.08 * (len(m)) + 0.05 * (t > 0.2) + rng.gauss(0, 0.01))
            out.append((m, K.features(63, 470, True, t), q))
    return out


class Design(unittest.TestCase):
    def test_classes_and_aliases(self):
        self.assertEqual(K.method_key('found'), 'gen1')
        self.assertEqual(K.method_class('gen3'), 'language')
        self.assertEqual(K.method_class('engine'), 'builder_engine')
        self.assertEqual(K.method_class('pasmaxsat'), K.DEFAULT_CLASS)
        f = K.features(63, 470, True, 0.5)
        self.assertAlmostEqual(f[1], 470 / (63 * 62 / 2))
        self.assertEqual(f[2], 1.0)

    def test_cells_read_both_study_shapes(self):
        class P:
            kind = 'tts'
        class S:
            profile = P()
            rows = [{'n': 10, 'edges': 20, 'task_id': 'dev-planted_cluster-x', 'target': 10,
                     'runs': {'found': {'0.5': [{'run': 'SUCCESS', 'value': 9}, {'run': 'SUCCESS', 'value': 11}],
                                        '2.0': [{'run': 'FAILED', 'value': 0}]}}}]
        cs = K.cells(S())
        self.assertEqual(len(cs), 1)
        self.assertEqual((cs[0][0], cs[0][2]), ('gen1', 0.95))

    def test_unseen_methods_get_wider_intervals(self):
        M_ = K.Map(synthetic(('gen1', 'random')))
        mu_seen, sd_seen, lvl_seen = M_.predict('gen1', K.features(63, 470, True, 0.5))
        mu_new, sd_new, lvl_new = M_.predict('gen3', K.features(63, 470, True, 0.5))
        self.assertEqual((lvl_seen, lvl_new), ('method', 'class'))
        self.assertGreater(sd_new, sd_seen)
        lvl = M_.predict('pasmaxsat', K.features(63, 470, True, 0.5))[2]
        self.assertEqual(lvl, 'global')

    def test_self_calibration(self):
        self.assertEqual(K.learned_scale([]), 1.0)
        self.assertEqual(K.learned_scale([0.1, -0.2, 0.3]), 1.0)          # never narrows
        zs = [3.2898] * 10                                                  # all at 2 x Z90
        self.assertAlmostEqual(K.learned_scale(zs), 2.0, places=3)

    def test_grid_reading(self):
        rows = [{'density': 0.2, 'mean': 0.9, 'sd': 0.1}, {'density': 0.25, 'mean': 1.0, 'sd': 0.2}]
        self.assertEqual(M.read(rows, 0.225), (0.95, 0.15000000000000002))
        self.assertEqual(M.read(rows, 0.1), (0.9, 0.1))                     # clamped
        self.assertEqual(M.DENSITIES[0], 0.18)
        self.assertEqual(M.DENSITIES[-1], 0.3)

    def test_rule(self):
        self.assertEqual(M.verdict_of(0.001, 0.02), 'MAP_BETTER')
        self.assertEqual(M.verdict_of(-0.02, -0.001), 'MAP_WORSE')
        self.assertEqual(M.verdict_of(-0.01, 0.01), 'NO_DIFFERENCE')
        self.assertEqual((M.ARMS, M.SEEN, M.UNSEEN), (('gen1', 'gen2', 'gen3', 'control', 'engine'), ('gen1', 'engine'),
                                                      ('gen2', 'gen3', 'control')))
        self.assertEqual(M.LADDER, (0.05, 0.1, 0.25, 0.5, 2.0))

    def test_predictions_must_be_prospective(self):
        with mock.patch.object(K, 'corpus', return_value=[('generations_b20r86', [])]):
            with self.assertRaises(SystemExit):
                M.predict(ROOT / 'evidence' / 'knowledge_map_b20r100')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main(['predict', str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
