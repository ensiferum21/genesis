"""B20_R30: the certification-budget measurement keeps its contract. The summary follows from the
rows, the verdict is the preregistered rule, the bound is a correct one-sided Clopper–Pearson
bound, and the hosts are in the handoff exposure addenda."""
import json
from math import comb
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'certification_budget_b20r30'
sys.path.insert(0, str(ROOT / 'scripts'))


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.hosts = json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']

    def test_every_host_measured_once(self):
        self.assertEqual(len(self.rows), 90)
        self.assertEqual(sorted(r['task_id'] for r in self.rows), sorted(t['task_id'] for t in self.hosts))

    def test_summary_follows_from_the_rows(self):
        p = self.s['pooled']
        cert = lambda side: sum(r[side]['status'] == 'FINITE_CERTIFIED' for r in self.rows)
        self.assertEqual(p['certified_60s_calibration'], cert('calibration'))
        self.assertEqual(p['certified_600s_evaluator'], cert('evaluator'))
        self.assertEqual(p['evaluator_unsupported'], 90 - cert('evaluator'))
        self.assertEqual(p['value_disagreements'], [])
        for r in self.rows:
            if r['calibration']['status'] == r['evaluator']['status'] == 'FINITE_CERTIFIED':
                self.assertEqual(r['calibration']['value'], r['evaluator']['value'])
        self.assertEqual(sum(s['hosts'] for s in self.s['by_stratum'].values()), 90)

    def test_verdict_is_the_preregistered_rule(self):
        k, n = self.s['pooled']['evaluator_unsupported'], 90
        u, bound = k / n, self.s['evaluator_unsupported_upper95']
        want = 'LIMITS_CONSISTENT' if bound <= 0.05 else 'LIMITS_INCONCLUSIVE' if u <= 0.05 else 'LIMITS_INCONSISTENT'
        self.assertEqual(self.s['verdict'], want)

    def test_clopper_pearson_bound(self):
        import b20r30_certification_budget as R30
        tail = lambda k, n, p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
        for k, n in ((0, 90), (1, 90), (4, 90), (3, 30)):
            b = R30.clopper_pearson_upper(k, n)
            self.assertAlmostEqual(tail(k, n, b), 0.05, places=6)
        self.assertAlmostEqual(R30.clopper_pearson_upper(0, 90), 1 - 0.05 ** (1 / 90), places=9)
        self.assertEqual(R30.clopper_pearson_upper(90, 90), 1.0)

    def test_hosts_are_in_the_exposure_addenda(self):
        ids = {t['task_id'] for t in self.hosts}
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
