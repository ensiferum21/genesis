"""B20_R113: does renormalisation close the planar gap? (design): fresh seed, the two configurations read as recorded,
the planar graphs, the Part A label, the Part B summary with record candidates flagged, and the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r113_planar_renorm as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r113_planar_renorm.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_configs(self):
        c = M.configs()
        self.assertEqual((c['INCUMBENT']['rs'], c['RENORM']['rs'], c['RENORM']['L0']), (1, 2, 0.2))

    def test_planar_instances(self):
        from genesis import gset as GS
        fams = {t.family for t in GS.tasks(list(M.PLANAR_GSET))}
        self.assertEqual(len(M.PLANAR_GSET), 20)
        self.assertTrue(all('planar' in f for f in fams))

    def test_part_a_label(self):
        v = {f'g{i}': {'INCUMBENT': 1000 + i, 'RENORM': 1003 + i} for i in range(40)}
        self.assertEqual(M.part_a_label(v)['label'], 'RENORM_BETTER')
        v = {f'g{i}': {'INCUMBENT': 1000 + i, 'RENORM': 1000 + i} for i in range(40)}
        self.assertEqual(M.part_a_label(v)['label'], 'NO_DIFFERENCE')

    def test_part_b_summary(self):
        best = {f'G{i}': 100 for i in M.PLANAR_GSET}
        rows = [{'instance': f'G{i}', 'value': 100, 'incumbent_60': 99} for i in M.PLANAR_GSET]
        s = M.part_b_summary(rows, best)
        self.assertEqual((s['label'], s['reach_best_known'], s['record_candidates']), ('RENORM_BETTER', 20, []))
        rows[0]['value'] = 101
        self.assertEqual(len(M.part_b_summary(rows, best)['record_candidates']), 1)

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
