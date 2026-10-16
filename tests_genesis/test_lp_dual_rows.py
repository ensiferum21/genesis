"""B20_R32: LP dual certificates over generated rows. The registry comes only from CHECKED pattern
statements of an intact package with the trusted definitions. The exact checker accepts the
producer's certificates and rejects every tampering. The route certifies without SAT when the
generated LP bound meets the witness."""
import copy
import itertools
import json
import unittest

from genesis.common import digest
from genesis.discovery import generated_certify as GC
from genesis.formal_research.triangle_theory import DEFS_SOURCE
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows as V


def host(n, edges, tid='t-rows', domain='triangle_free_host_v1'):
    return GraphTask(task_id=tid, domain=domain, family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


K6 = host(6, itertools.combinations(range(6), 2))
W5 = [(0, 1), (0, 4), (0, 5), (1, 2), (1, 5), (2, 3), (2, 5), (3, 4), (3, 5), (4, 5)]
TWO_W5 = host(12, W5 + [(u + 6, v + 6) for u, v in W5])


class Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads(GC.PACKAGE.read_text())
        cls.reg = GC.load_registry()

    def test_patterns_from_the_checked_package(self):
        pats = self.reg['patterns']
        self.assertEqual(sorted((p['vertices'], len(p['edges']), p['ex']) for p in pats.values()),
                         [(5, 10, 6), (6, 10, 7)])
        self.assertEqual(self.reg['package_sha256'], self.pkg['package_sha256'])

    def test_definitions_and_texts_are_bound(self):
        bad = copy.deepcopy(self.pkg)
        for m in bad['modules']:
            if m['name'] == 'PCDefs':
                m['source'] = m['source'].replace('then 1 else 0', 'then 0 else 1')
        with self.assertRaises(ValueError):
            V.registry_from_package(bad, defs_source=DEFS_SOURCE)
        with self.assertRaises(ValueError):
            V.registry_from_package(self.pkg, defs_source=DEFS_SOURCE + '\n')
        bad = copy.deepcopy(self.pkg)
        s = next(s for s in bad['statements'] if s['role'] == 'pattern')
        s['lean'] = s['lean'].replace('≤ 6', '≤ 5').replace('≤ 7', '≤ 6')
        with self.assertRaises(ValueError):
            V.registry_from_package(bad, defs_source=DEFS_SOURCE)
        unresolved = copy.deepcopy(self.pkg)
        for s in unresolved['statements']:
            if s['role'] == 'pattern':
                s['status'] = 'UNRESOLVED'
        self.assertEqual(V.registry_from_package(unresolved, defs_source=DEFS_SOURCE)['patterns'], {})

    def test_statement_parser_is_strict(self):
        head = V.HEAD + '(v0 : ℕ) (v1 : ℕ) (v2 : ℕ), '
        self.assertEqual(V.parse_pattern_statement(head + 'PC.adj S v0 v1 + PC.adj S v1 v2 ≤ 1'),
                         (3, [(0, 1), (1, 2)], 1))
        for body in ('PC.adj S v1 v0 + PC.adj S v1 v2 ≤ 1', 'PC.adj S v0 v1 ≤ 1', 'PC.adj S v0 v1 + PC.adj S v0 v1 + '
                     'PC.adj S v1 v2 ≤ 2', 'PC.adj S v0 v1 + PC.adj T v1 v2 ≤ 1', 'PC.adj S v0 v1 + PC.adj S v1 v2 < 1'):
            self.assertIsNone(V.parse_pattern_statement(head + body))
        self.assertIsNone(V.parse_pattern_statement(head.replace('(hH : ∀ e ∈ S, e.1 < e.2) ', '') +
                                                    'PC.adj S v0 v1 + PC.adj S v1 v2 ≤ 1'))


class Certificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GC.load_registry()
        cls.k6, cls.k6_lp, _ = GC.lp_dual_rows(K6, cls.reg)

    def test_generated_rows_tighten_the_bound(self):
        self.assertEqual(V.check_certificate(K6, self.k6, self.reg), {'verdict': 'VALID', 'bound': 9, 'reason': None})
        cert, _, _ = GC.lp_dual_rows(TWO_W5, self.reg)
        self.assertEqual(V.check_certificate(TWO_W5, cert, self.reg)['bound'], 14)
        from genesis.discovery import obstruction as O
        self.assertEqual(O.check_certificate(K6, O.lp_dual(K6)[0])['bound'], 10)          # triangle rows alone

    def tamper(self, f):
        c = copy.deepcopy(self.k6)
        f(c)
        return V.check_certificate(K6, c, self.reg)['verdict']

    def test_tampering_is_rejected(self):
        pat = next(i for i, q in enumerate(self.k6['inequalities']) if q['kind'] == 'pattern')

        def lower_weight(c):
            c['inequalities'][pat]['weight'] = '1/1000000'
        def wrong_rhs(c):
            c['inequalities'][pat]['rhs'] -= 1
        def collapse_map(c):
            m = c['inequalities'][pat]['map']; m[1] = m[0]
        def leave_host(c):
            c['inequalities'][pat]['map'][0] = 40
        def unknown(c):
            c['inequalities'][pat]['pattern'] = 'pc_k7'
        def bound(c):
            c['bound'] -= 1
        def registry(c):
            c['registry_sha256'] = '0' * 64
        def kind(c):
            c['inequalities'][pat]['kind'] = 'clique'
        for f in (lower_weight, wrong_rhs, collapse_map, leave_host, unknown, bound, registry, kind):
            self.assertEqual(self.tamper(f), 'REJECTED', f.__name__)
        other = host(6, itertools.combinations(range(6), 2), tid='other')
        self.assertEqual(V.check_certificate(other, self.k6, self.reg)['verdict'], 'REJECTED')
        c4 = host(6, itertools.combinations(range(6), 2), domain='c4_host_v2')
        self.assertEqual(V.check_certificate(c4, self.k6, self.reg)['verdict'], 'REJECTED')
        smaller = dict(self.reg, patterns={k: v for k, v in self.reg['patterns'].items() if v['vertices'] == 6})
        self.assertEqual(V.check_certificate(K6, self.k6, smaller)['verdict'], 'REJECTED')

    def test_limited_separation_stays_valid(self):
        self.assertEqual(GC.pattern_order(self.reg)[0], next(k for k, v in self.reg['patterns'].items() if v['vertices'] == 5))
        none, _, n0 = GC.lp_dual_rows(K6, self.reg, max_rows=0, order='size')
        self.assertEqual(V.check_certificate(K6, none, self.reg)['bound'], 10)
        self.assertEqual(n0, 20)                                          # the 20 triangles of K6 only
        stopped, _, _ = GC.lp_dual_rows(K6, self.reg, stop=lambda: True, order='size')
        self.assertEqual(V.check_certificate(K6, stopped, self.reg)['bound'], 10)
        witness = [(u, v) for u, v in K6.edges if (u < 3) != (v < 3)]
        rec = GC.certify_with_rows(K6, witness, self.reg, seconds=30, separation_seconds=30, max_rows=50000)
        self.assertEqual((rec['lower'], rec['upper'], rec['method']), (9, 9, 'LP_DUAL_GENERATED_EXACT'))

    def test_route_certifies_without_sat_when_the_bound_meets_the_witness(self):
        witness = [(u, v) for u, v in K6.edges if (u < 3) != (v < 3)]                    # K_{3,3}: 9 edges
        rec = GC.certify_with_rows(K6, witness, self.reg, seconds=30)
        self.assertEqual((rec['lower'], rec['upper'], rec['method']), (9, 9, 'LP_DUAL_GENERATED_EXACT'))
        self.assertEqual([s['step'] for s in rec['steps']], ['lp-dual-rows'])
        self.assertEqual(rec['certificate']['task_sha256'], digest(K6.model_dump(mode='json')))


if __name__ == '__main__':
    unittest.main()
