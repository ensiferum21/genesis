"""B20_R28: the E1b causal re-pilot's record keeps its contract. The interventions are the
registered ones, the certification gate and the verdicts follow from the rows, and the hosts are
listed in the handoff exposure addenda."""
import json
import math
from pathlib import Path
import statistics
import unittest

from genesis.kernel import replay_contracts as RC

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'e1b_causal_repilot_b20r28'


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_gate_and_verdicts_follow_from_the_rows(self):
        self.assertEqual(len(self.rows), 30)
        cert = self.s['triangle_free']['certified_by_stratum']
        for stratum, (c, n) in cert.items():
            self.assertEqual(c, sum(r['optimum'] is not None for r in self.rows if r['stratum'] == stratum))
            self.assertGreaterEqual(c, math.ceil(0.75 * n))
        scored = [r for r in self.rows if r['optimum'] is not None]
        for other in ('ablation', 'placebo'):
            c = self.s['triangle_free'][other]
            mean = statistics.fmean(r['arms']['candidate']['value'] - r['arms'][other]['value'] for r in scored)
            self.assertAlmostEqual(c['mean_difference'], round(mean, 4))
            self.assertTrue(mean >= 0.5 and c['cpu_ratio_candidate_to_intervened'] <= 3.0
                            and (c['power_centred']['chosen'] or {}).get('tasks_per_stratum'))
            self.assertEqual(c['verdict'], 'READY_FOR_REVIEW')

    def test_interventions_are_the_registered_ones(self):
        from genesis import candidates as C
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import b20r23_e1b_causal_readiness as R23C
        arms = R23C.arms('triangle_free_host_v1')
        self.assertEqual({n: a['descriptor_id'] for n, a in arms.items()}, self.s['descriptors'])
        for kind in ('ablation', 'placebo'):
            self.assertEqual(RC.intervention_problems(kind, arms['candidate'], arms[kind]), ([], ('init',)))
        self.assertEqual(C.descriptor_problems(arms['candidate']), [])

    def test_hosts_are_in_the_exposure_addenda(self):
        ids = {r['task_id'] for r in self.rows}
        for pkg in ('handoff/e1', 'handoff/e1b'):
            add = {t['task_id'] for t in json.loads((ROOT / pkg / 'exposure_hosts_addendum_b20r28.json').read_text())}
            self.assertTrue(ids <= add)


if __name__ == '__main__':
    unittest.main()
