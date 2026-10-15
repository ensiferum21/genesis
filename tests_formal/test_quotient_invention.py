"""B20_R26 (s15.3, W10): the quotient family's package replays from its sources, and the recorded
evidence keeps its contract: the obligations are checked, the hosts are fresh, and the verdict is
the preregistered one. Needs the formal workspace and the sandbox; the formal suite accepts no
skips."""
import copy
import json
from pathlib import Path
import unittest

from genesis.formal_research import theory_package as TP

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'quotient_invention_b20r26'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.a = json.loads((EVIDENCE / 'part_a.json').read_text())
        cls.b = json.loads((EVIDENCE / 'part_b.json').read_text())
        cls.rows = json.loads((EVIDENCE / 'part_b_rows.json').read_text())

    def test_obligations_checked_and_package_replays(self):
        self.assertEqual(self.a['obligations'], {'image': 'CHECKED', 'sound_tf': 'CHECKED'})
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        r = TP.replay(self.pkg)
        self.assertEqual(r['verdict'], 'REPLAYED', r.get('differences'))
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_verdict_follows_from_the_rows(self):
        self.assertEqual(len(self.rows), 32)
        for other, c in self.b['comparisons'].items():
            diffs = [r['values']['new'] - r['values'][other] for r in self.rows]
            self.assertEqual(c['wins_ties_losses'], [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs),
                                                     sum(d < 0 for d in diffs)])
            self.assertEqual(c['passes'], c['mean'] >= 0.5 and c['interval_90'][0] > 0)
        verdict = 'UTILITY_AFTER_COST' if all(c['passes'] for c in self.b['comparisons'].values()) \
            else 'NO_UTILITY_AFTER_COST'
        self.assertEqual(self.b['verdict'], verdict)
        self.assertEqual(verdict, 'NO_UTILITY_AFTER_COST')

    def test_hosts_are_fresh(self):
        ids = {r['task_id'] for r in self.rows}
        for d in ('relation_invention_b20r17', 'relation_invention_b20r19'):
            prior = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())
            self.assertFalse(ids & {t['task_id'] for v in prior.values() for k in v for t in v[k]})


if __name__ == '__main__':
    unittest.main()
