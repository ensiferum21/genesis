"""B20_R48: branch-and-bound certificates over generated C4 rows.

  * The route's certified value equals the exact optimum (HiGHS MILP, re-checked; brute force on the
    smallest) on fixed small hosts, and its certificates check VALID.
  * The checker rejects every tampering: the claimed bound, a branch on a fixed or non-host edge, a
    missing child, a leaf weight, slack on a fixed edge, an infeasible leaf that is not overfilled, a
    row outside the host, another task, another registry.
  * An infeasible leaf is accepted only when its row's fixed-in edges overfill it.
"""
import copy
import itertools
import random
import unittest

from genesis.common import digest
from genesis.discovery import generated_bnb_c4 as GB
from genesis.discovery import generated_certify_c4 as GC4
from genesis.invention import cuts_c4 as C4
from genesis.models import GraphTask
from genesis.verification import lp_dual_tree_c4 as VT


def host(n, edges, tid='t-tree', domain='c4_host_v2'):
    return GraphTask(task_id=tid, domain=domain, family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


def brute(edges):
    E = list(edges)
    return max(len(s) for k in range(len(E) + 1) for s in itertools.combinations(E, k) if C4.c4free(list(s)))


def random_host(seed, n, p, tid):
    rng = random.Random(seed)
    return host(n, [e for e in itertools.combinations(range(n), 2) if rng.random() < p], tid=tid)


HOSTS = [random_host(5, 16, 0.3, 'h16'), random_host(7, 14, 0.4, 'h14'), random_host(11, 12, 0.4, 'h12')]
PETERSEN = host(10, [(i, (i + 1) % 5) for i in range(5)] + [(i, i + 5) for i in range(5)] +
                [(5 + i, 5 + (i + 2) % 5) for i in range(5)], tid='petersen')


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GC4.load_registry()
        cls.recs = {t.task_id: GB.certify_with_tree(t, [], cls.reg, seconds=60, lp_rounding_seconds=None)
                    for t in HOSTS + [PETERSEN]}

    def test_certified_values_are_the_optima(self):
        for t in HOSTS:
            rec = self.recs[t.task_id]
            ex, witness = C4.ex_milp(list(t.edges))
            self.assertTrue(C4.c4free(witness))
            self.assertEqual((rec['lower'], rec['upper']), (ex, ex), t.task_id)
            self.assertTrue(C4.c4free(rec['witness']))
            self.assertEqual(len(rec['witness']), ex)
            v = VT.check_certificate(t, rec['certificate'], self.reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', ex), (t.task_id, v['reason']))
        self.assertEqual(self.recs['petersen']['upper'], 15)          # Petersen has girth 5: no 4-cycle

    def test_branching_is_used_and_checked(self):
        t = next(t for t in HOSTS if self.recs[t.task_id]['method'] == GB.METHOD_TREE and self.recs[t.task_id]['leaves'] > 1)
        cert = self.recs[t.task_id]['certificate']
        self.assertIn('branch', cert['tree'])
        self.assertGreater(VT.check_certificate(t, cert, self.reg)['leaves'], 1)

    def test_small_host_against_brute_force(self):
        t = random_host(3, 8, 0.45, 'h8')
        rec = GB.certify_with_tree(t, [], self.reg, seconds=30, lp_rounding_seconds=None)
        self.assertEqual(rec['upper'], brute(t.edges))
        self.assertEqual(VT.check_certificate(t, rec['certificate'], self.reg)['verdict'], 'VALID')


class Tampering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GC4.load_registry()
        cls.t = next(t for t in HOSTS
                     if GB.certify_with_tree(t, [], cls.reg, seconds=60, lp_rounding_seconds=None)['leaves'] > 1)
        cls.cert = GB.certify_with_tree(cls.t, [], cls.reg, seconds=60, lp_rounding_seconds=None)['certificate']

    def verdict(self, f, task=None):
        c = copy.deepcopy(self.cert)
        f(c)
        return VT.check_certificate(task or self.t, c, self.reg)['verdict']

    @staticmethod
    def first_leaf(c, want=lambda leaf: leaf['kind'] == 'dual' and leaf['inequalities']):
        stack = [c['tree']]
        while stack:
            n = stack.pop()
            if 'leaf' in n:
                if want(n['leaf']):
                    return n
                continue
            stack += [n['zero'], n['one']]
        raise AssertionError('no such leaf')

    def test_accepts_the_original(self):
        self.assertEqual(self.verdict(lambda c: None), 'VALID')

    def test_tampering_is_rejected(self):
        def lower_bound(c):
            c['upper'] -= 1
        def fixed_branch(c):
            n = c['tree']
            n['one'] = {'branch': list(n['branch']), 'zero': n['one'], 'one': copy.deepcopy(n['one'])}
        def non_host_branch(c):
            c['tree']['branch'] = [0, 99]
        def missing_child(c):
            del c['tree']['zero']
        def weight(c):
            for q in self.first_leaf(c)['leaf']['inequalities']:
                q['weight'] = '1/1000000'
        def slack_on_fixed(c):
            leaf = self.first_leaf(c)['leaf']
            leaf['slack'].append([list(c['tree']['branch']), '1'])
        def outside_row(c):
            leaf = self.first_leaf(c, lambda l: l['kind'] == 'dual' and any(q['kind'] == 'cycle' for q in l['inequalities']))['leaf']
            q = next(q for q in leaf['inequalities'] if q['kind'] == 'cycle')
            q['cycle'] = [0, 1, 2, 99]
        def registry(c):
            c['registry_sha256'] = '0' * 64
        def schema(c):
            c['schema'] = 'genesis-lp-dual-rows-c4-certificate-v1'
        for f in (lower_bound, fixed_branch, non_host_branch, missing_child, weight, slack_on_fixed, outside_row,
                  registry, schema):
            self.assertEqual(self.verdict(f), 'REJECTED', f.__name__)
        other = host(self.t.n, self.t.edges, tid='other')
        self.assertEqual(self.verdict(lambda c: None, task=other), 'REJECTED')

    def test_infeasible_leaves(self):
        t = host(4, [(0, 1), (1, 2), (2, 3), (0, 3)], tid='c4')                     # one 4-cycle: optimum 3
        reg = self.reg
        row = {'kind': 'cycle', 'cycle': [0, 1, 2, 3], 'rhs': 3}
        dual = {'kind': 'dual', 'inequalities': [dict(row, weight='1')], 'slack': []}

        def chain(edges, last):
            node = last
            for e in reversed(edges):
                node = {'branch': list(e), 'one': node, 'zero': {'leaf': dual}}
            return node
        good = {'schema': VT.SCHEMA, 'task_sha256': digest(t.model_dump(mode='json')), 'domain': t.domain,
                'registry_sha256': digest(reg), 'upper': 3,
                'tree': chain([(0, 1), (1, 2), (2, 3), (0, 3)], {'leaf': {'kind': 'infeasible', 'row': row}})}
        self.assertEqual(VT.check_certificate(t, good, reg)['verdict'], 'VALID')
        short = copy.deepcopy(good)
        short['tree'] = chain([(0, 1), (1, 2), (2, 3)], {'leaf': {'kind': 'infeasible', 'row': row}})
        self.assertEqual(VT.check_certificate(t, short, reg)['verdict'], 'REJECTED')
        too_low = copy.deepcopy(good)
        too_low['upper'] = 2
        self.assertEqual(VT.check_certificate(t, too_low, reg)['verdict'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
