"""B20_R65: why rehearsal hosts were unsupported (statistician's brief, finding 5).

Checks: each rehearsal's CONFIRM hosts match its analysed tasks; every E1d exclusion is a host above the
200-edge certificate bound and every such host was excluded (so the bound, not the reference, explains them);
E1b's single exclusion is within the bound (a reference limit); the brief quotes the derived table verbatim."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r65_unsupported_hosts as M  # noqa: E402


class Diagnosis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = M.table()

    def test_e1d_exclusions_are_the_size_bound(self):
        for name in ('E1d (B20_R43)', 'E1d ablation (B20_R45)'):
            d = self.t[name]
            self.assertTrue(d['unsupported'])
            self.assertTrue(all(r['reason'] == 'SIZE_BOUND' and r['edges'] > M.BOUND for r in d['unsupported']))
            self.assertTrue(d['every_over_bound_host_is_unsupported'])
            self.assertEqual(set(d['confirm_hosts_over_bound']), {'planted_cluster:9491bde8'})

    def test_other_rehearsals(self):
        self.assertEqual(self.t['E1 (B20_R24)']['unsupported'], [])
        self.assertEqual(self.t['E1b-C4 (B20_R52)']['unsupported'], [])
        e1b = self.t['E1b (B20_R24)']['unsupported']
        self.assertEqual([(r['edges'], r['reason']) for r in e1b], [(166, 'REFERENCE_LIMIT')])

    def test_the_brief_quotes_the_table(self):
        self.assertIn(M.markdown(), (ROOT / 'docs' / 'STATISTICIAN_BRIEF.md').read_text())


if __name__ == '__main__':
    unittest.main()
