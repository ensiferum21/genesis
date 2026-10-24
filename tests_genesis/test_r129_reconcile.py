"""B20_R129's reconciliation (Daniel's directive of 24 Oct 2026, item 5): recomputed from B20_R129's saved rows; the
preregistered secondary tests agree with B20_R129's summary; the saved reconciliation is the recomputation."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r129_reconcile as M  # noqa: E402


class Reconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads(json.dumps(M.reconcile()))

    def test_selection(self):
        s = self.r['selection']
        self.assertEqual(s['chosen'], 'decfall')
        self.assertEqual([x[0] for x in s['ranking']][:2], ['decfall', 'inv1'])
        self.assertEqual(s['best_invented'], 'inv1')

    def test_preregistered_agree_with_r129(self):
        self.assertTrue(self.r['agrees_with_r129_summary'])
        p = self.r['preregistered']
        self.assertGreater(p['inv1_vs_decfall']['p_wilcoxon'], 0.05)
        self.assertLess(p['inv1_vs_eig']['p_wilcoxon'], 1e-6)

    def test_saved_is_the_recomputation(self):
        saved = json.loads((ROOT / 'evidence' / 'r129_reconciliation' / 'summary.json').read_text())
        self.assertEqual(saved, self.r)

    def test_exploratory_family_is_holm_corrected(self):
        e = self.r['exploratory']
        self.assertEqual(len(e), len(M.EXPLORATORY))
        self.assertTrue(all(x['p_holm'] >= x['p_wilcoxon'] for x in e))
        self.assertEqual([x['label'] for x in e if x['set'] == 'transfer' and x['measure'] == 'needed'],
                         ['NO_DIFFERENCE'])


if __name__ == '__main__':
    unittest.main()
