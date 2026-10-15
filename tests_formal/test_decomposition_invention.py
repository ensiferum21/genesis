"""B20_R27 (s15.3, W10): the decomposition family's package replays from its sources, and the
recorded evidence keeps its contract: the composition obligation is checked, the `whole` control
is present, the hosts are fresh, and the verdict is the preregistered one. Needs the formal
workspace and the sandbox; the formal suite accepts no skips."""
import copy
import json
from pathlib import Path
import unittest

from genesis.formal_research import theory_package as TP

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'decomposition_invention_b20r27'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.a = json.loads((EVIDENCE / 'part_a.json').read_text())
        cls.b = json.loads((EVIDENCE / 'part_b.json').read_text())
        cls.rows = json.loads((EVIDENCE / 'part_b_rows.json').read_text())

    def test_obligation_checked_and_package_replays(self):
        self.assertEqual(self.a['obligations'], {'composition': 'CHECKED'})
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        self.assertEqual(TP.replay(self.pkg)['verdict'], 'REPLAYED')
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_verdict_follows_from_the_rows(self):
        self.assertEqual(len(self.rows), 32)
        self.assertEqual(set(self.b['comparisons']), {'whole', 'menu', 'conventional', 'matched'})
        for other, c in self.b['comparisons'].items():
            diffs = [r['values']['new'] - r['values'][other] for r in self.rows]
            self.assertEqual(c['wins_ties_losses'], [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs),
                                                     sum(d < 0 for d in diffs)])
            self.assertEqual(c['passes'], c['mean'] >= 0.5 and c['interval_90'][0] > 0)
        self.assertEqual(self.b['verdict'], 'NO_UTILITY_AFTER_COST')

    def test_hosts_are_fresh(self):
        ids = {r['task_id'] for r in self.rows}
        for d in ('relation_invention_b20r17', 'relation_invention_b20r19', 'quotient_invention_b20r26'):
            prior = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())
            self.assertFalse(ids & {t['task_id'] for v in prior.values() for k in v for t in v[k]})


if __name__ == '__main__':
    unittest.main()
