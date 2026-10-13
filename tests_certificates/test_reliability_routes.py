"""W23: the SAT/DRAT route is a diverse route for exact optima (different implementation and trust
base from the Python optimizers), so agreement with it is AGREE rather than CORRELATED."""
import unittest

from genesis import graphs as G
from genesis.models import GraphTask
from genesis.verification import reliability as RL

C4 = GraphTask(task_id='rl-sat-c4', domain='c4_host_v2', n=6,
               edges=tuple((u, v) for u in range(6) for v in range(u + 1, 6)), family='complete')
TF = GraphTask(task_id='rl-sat-tf', domain='triangle_free_host_v1', n=5,
               edges=tuple((u, v) for u in range(5) for v in range(u + 1, 5)), family='complete')


class SatRoute(unittest.TestCase):
    def test_sat_route_agrees_and_is_diverse(self):
        for task, want in ((C4, 7), (TF, 6)):                       # ex(6, C4) = 7; Mantel: floor(25/4) = 6
            c = RL.check_optimum_routes(task, sat=True, sat_seconds=60)
            self.assertEqual(c['verdict'], 'AGREE', c['outcomes'])
            self.assertEqual(c['answer'], want)
            self.assertTrue(any('sat-drat' in p for p in c['diverse_pairs']))
            self.assertEqual(c['outcomes']['sat-drat']['method'], 'SAT_DRAT')

    def test_sat_route_disagreeing_with_a_faulty_optimizer_is_quarantinable(self):
        import tempfile
        from unittest import mock
        from genesis.store import Store
        real = G.exact_producer
        with mock.patch.object(G, 'exact_producer', lambda t, *a, **k: dict(real(t, *a, **k), value=8)):
            c = RL.check_optimum_routes(C4, sat=True, sat_seconds=60)
        self.assertEqual(c['verdict'], 'DISAGREE')
        self.assertEqual(sorted(map(sorted, c['answer_groups'])),
                         [['incremental-branch-bound', 'sat-drat'], ['motif-hitting-set']])
        with tempfile.TemporaryDirectory() as d, Store(d) as s:
            q = RL.Quarantine(s)
            rid = q.record(c)
            self.assertTrue(q.problems(c['subject']))
            self.assertIn('PARSER_TRANSLATION', q.get(rid)['check']['candidate_causes'])   # the CNF encoding step


if __name__ == '__main__':
    unittest.main()
