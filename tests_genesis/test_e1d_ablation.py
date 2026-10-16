"""B20_R44: the registered ablation of E1's discovered representation, and the E1d ablation re-pilot.

The transform:
  * is registered for represent-and-repair-v1's `representation` only, from cross_2 to ordered_2;
  * rests on B18's Lean-checked dominance (ordered_2 within cross_2 CHECKED, the converse
    DISPROVED) and on ordered_2's soundness;
  * has no placebo;
  * changes no descriptor id.
The kernel's provenance check accepts exactly this ablation, and refuses other representations and
other components."""
import json
from pathlib import Path
import sys
import unittest

from genesis import candidates as C1
from genesis.kernel import replay_contracts as RC

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'e1d_ablation_b20r44'
sys.path.insert(0, str(ROOT / 'scripts'))
TF = 'triangle_free_host_v1'


def rr(rep, **over):
    cand = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
    params = dict(cand['parameters'], representation=rep, **over)
    return C1.build_descriptor('represent-and-repair-v1', TF, params, **cand['resource_profile'])


class Transform(unittest.TestCase):
    def setUp(self):
        self.cand = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())

    def test_the_registered_ablation_is_exactly_cross_2_to_ordered_2(self):
        self.assertEqual(RC.intervention_problems('ablation', self.cand, rr('ordered_2')), ([], ('representation',)))
        for rep in ('adjacent_2', 'adjacent_3'):
            why, _ = RC.intervention_problems('ablation', self.cand, rr(rep))
            self.assertNotEqual(why, [], rep)
        why, _ = RC.intervention_problems('placebo', self.cand, rr('adjacent_2'))
        self.assertTrue(any('no registered placebo' in w for w in why), why)
        why, _ = RC.intervention_problems('ablation', self.cand, rr('ordered_2', seed=1))
        self.assertNotEqual(why, [])                                     # two components changed
        why, _ = RC.intervention_problems('ablation', rr('ordered_2'), rr('cross_2'))
        self.assertNotEqual(why, [])                                     # not from the discovered value

    def test_it_rests_on_checked_dominance_and_soundness(self):
        pkg = json.loads((ROOT / 'evidence' / 'invention_b18' / 'representations' / 'package.json').read_text())
        status = {s['id']: s['status'] for s in pkg['statements']}
        self.assertEqual((status['ordered_2_within_cross_2'], status['cross_2_within_ordered_2'],
                          status['ordered_2_sound_tf']), ('CHECKED', 'DISPROVED', 'CHECKED'))
        self.assertEqual((status['cross_2_within_adjacent_2'], status['adjacent_2_within_cross_2']),
                         ('CHECKED', 'CHECKED'))                         # why no placebo: an identical arm

    def test_descriptor_ids_are_unchanged(self):
        self.assertEqual(C1.descriptor_problems(self.cand, domain=TF), [])
        for pkg in ('e1', 'e1b', 'e1d'):
            p = ROOT / 'handoff' / pkg / 'candidate_descriptor.json'
            if p.exists():
                self.assertEqual(C1.descriptor_problems(json.loads(p.read_text())), [])


class NullControl(unittest.TestCase):
    def test_the_null_control_is_lean_equal_and_not_an_intervention(self):
        cand = json.loads((ROOT / 'handoff' / 'e1' / 'candidate_descriptor.json').read_text())
        why, _ = RC.intervention_problems('ablation', cand, rr('adjacent_2'))
        self.assertNotEqual(why, [])

    def test_verdicts(self):
        import b20r44_e1d_ablation as M
        row = lambda c, n: {'arms': {'candidate': {'value': c}, 'null_control': {'value': n}}}
        clean = [row(10, 10 + (i % 3 == 0) - (i % 3 == 1)) for i in range(30)]
        self.assertEqual(M.null_control(clean)['verdict'], 'NULL_CONTROL_CLEAN')
        self.assertEqual(M.null_control([row(10, 10)] * 30)['verdict'], 'NULL_CONTROL_CLEAN')
        self.assertEqual(M.null_control([row(12, 10)] * 30)['verdict'], 'NULL_CONTROL_FLAGGED')
        wide = [row(10, 10 + (4 if i % 2 else -4)) for i in range(10)]
        self.assertEqual(M.null_control(wide)['verdict'], 'NULL_CONTROL_FLAGGED')


class Record(unittest.TestCase):
    """The run's evidence: the verdicts follow from the rows."""
    @classmethod
    def setUpClass(cls):
        import b20r44_e1d_ablation as M
        cls.M = M
        cls.s = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EVIDENCE / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_verdicts_follow_from_the_rows(self):
        import b20r41_e1d_readiness as R41
        self.assertEqual(len(self.rows), 30)
        analysis, _ = R41.analyse(self.rows, ['candidate', 'ablation', 'null_control'], ['ablation'])
        stored = json.loads((EVIDENCE / 'pilot_summary.json').read_text())
        for k in ('comparator', 'totals', 'mean_difference', 'wins_ties_losses', 'cpu_ratio_candidate_to_comparator',
                  'certified_by_stratum', 'verdict'):
            self.assertEqual(analysis[k], stored[k], k)
        self.assertEqual(self.M.null_control(self.rows), stored['negative_control'])
        self.assertEqual((self.s['verdict'], self.s['negative_control']),
                         (stored['verdict'], stored['negative_control']['verdict']))

    def test_arms_are_the_registered_ones(self):
        A = self.M.arms()
        self.assertEqual(self.s['descriptors'], {n: d['descriptor_id'] for n, d in A.items()})
        for r in self.rows:
            if r['optimum'] is not None:
                self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EVIDENCE / 'hosts.json').read_text())['tasks']]
        self.assertEqual(len(RD.identities(tasks)), 30)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r44.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t)) for t in add]))


if __name__ == '__main__':
    unittest.main()
