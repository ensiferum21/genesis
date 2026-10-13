"""B20_RX3: LP- and SAT-guided construction components (search only; witnesses are re-checked)."""
import random
import unittest

from genesis.discovery import construct as K
from genesis.graphs import certified_optimum, check_witness
from genesis.models import GraphTask


def complete(n, domain='c4_host_v2'):
    return GraphTask(task_id=f'k{n}-{domain[:2]}', domain=domain, n=n,
                     edges=tuple((u, v) for u in range(n) for v in range(u + 1, n)), family='complete')


def random_host(n, p, seed, domain):
    rng = random.Random(seed)
    return GraphTask(task_id=f'r{seed}', domain=domain, n=n,
                     edges=tuple((u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p), family='r')


class Components(unittest.TestCase):
    def test_greedy_is_motif_free_and_maximal(self):
        for dom in ('c4_host_v2', 'triangle_free_host_v1'):
            t = random_host(12, 0.5, 3, dom)
            order = list(range(len(t.edges)))
            random.Random(1).shuffle(order)
            w = K.greedy(t, order)
            self.assertEqual(check_witness(t, w)['value'], len(w))
            for e in set(t.edges) - set(w):                      # maximal: no host edge can be added
                with self.assertRaises(ValueError):
                    check_witness(t, w + (e,))

    def test_lp_values_and_lp_greedy(self):
        t = complete(6)
        x = K.lp_values(t)
        self.assertEqual(len(x), len(t.edges))
        self.assertTrue(all(-1e-9 <= v <= 1 + 1e-9 for v in x))
        r = K.lp_greedy(t, 0.2, seed=0, x=x)
        self.assertEqual(check_witness(t, r['witness'])['value'], len(r['witness']))
        self.assertGreaterEqual(r['restarts'], 1)

    def test_sat_climb_reaches_the_optimum_and_stops_on_unsat(self):
        for t in (complete(6), complete(6, 'triangle_free_host_v1'), random_host(8, 0.6, 5, 'c4_host_v2')):
            opt = certified_optimum(t)['value']
            r = K.sat_climb(t, (), 30.0)
            self.assertEqual(len(r['witness']), opt)
            self.assertEqual(r['stop'], 'UNSAT')
            self.assertEqual(check_witness(t, r['witness'])['value'], opt)

    def test_budget_charges_the_sat_solver(self):
        t = random_host(30, 0.25, 11, 'c4_host_v2')
        b = K.Budget(1.0)
        r = K.sat_climb(t, (), b)
        self.assertGreaterEqual(r['sat_calls'], 1)
        self.assertLessEqual(b.used(), 1.5)                       # the child process is charged and stopped
        self.assertGreater(b.used(), 0.0)


if __name__ == '__main__':
    unittest.main()
