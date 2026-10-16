"""B20_R47: LP dual certificates over generated C4 rows.

  * The registry comes only from CHECKED pattern statements of an intact package with the trusted
    GTDefs, the c4_host_v2 contract's G4Defs and a 0/1 P4.adj.
  * The statement parser demands every pairwise distinctness hypothesis, in order.
  * The exact checker accepts the producer's certificates and rejects every tampering.
  * The route certifies K6 without SAT, where the 4-cycle rows alone stop at 11.
"""
import copy
import itertools
import json
import unittest

from genesis.common import digest
from genesis.discovery import generated_certify_c4 as GC4
from genesis.formal_research.triangle_theory import DEFS_SOURCE
from genesis.invention.representations import C4_SOURCE
from genesis.models import GraphTask
from genesis.verification import lp_dual_rows_c4 as V4


def host(n, edges, tid='t-c4rows', domain='c4_host_v2'):
    return GraphTask(task_id=tid, domain=domain, family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


K6 = host(6, itertools.combinations(range(6), 2))
FRIENDSHIP = [(0, 1), (0, 2), (1, 2), (0, 3), (0, 4), (3, 4), (0, 5)]          # C4-free, 7 edges = ex(K6, C4)


def head(k):
    vs = ' '.join(f'(v{i} : ℕ)' for i in range(k))
    hs = ' '.join(f'(h_v{i}_v{j} : v{i} ≠ v{j})' for i in range(k) for j in range(i + 1, k))
    return f'{V4.HEAD}{vs} {hs}, '


class Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads(GC4.PACKAGE.read_text())
        cls.reg = GC4.load_registry()

    def test_patterns_from_the_checked_package(self):
        pats = self.reg['patterns']
        checked = [s for s in self.pkg['statements'] if s['role'] == 'pattern' and s['status'] == 'CHECKED']
        self.assertEqual(len(pats), len(checked))
        self.assertGreater(len(pats), 0)
        self.assertEqual(self.reg['package_sha256'], self.pkg['package_sha256'])
        k4 = pats.get('p4_c4pat4_6_010203121323')
        if k4 is not None:
            self.assertEqual((k4['vertices'], len(k4['edges']), k4['ex']), (4, 6, 4))
        listed = {'p4_' + p['id']: p for p in self.pkg['patterns']}
        for pid, p in pats.items():
            self.assertEqual((p['vertices'], p['ex']), (listed[pid]['vertices'], listed[pid]['ex']), pid)
            self.assertEqual(sorted(map(tuple, p['edges'])), sorted(map(tuple, listed[pid]['edges'])), pid)

    def test_definitions_and_texts_are_bound(self):
        def raises(pkg, **kw):
            with self.assertRaises(ValueError):
                V4.registry_from_package(pkg, **dict({'defs_source': DEFS_SOURCE, 'c4_source': C4_SOURCE}, **kw))
        bad = copy.deepcopy(self.pkg)
        for m in bad['modules']:
            if m['name'] == 'P4Defs':
                m['source'] = m['source'].replace('then 1 else 0', 'then 0 else 1')
        raises(bad)
        raises(self.pkg, defs_source=DEFS_SOURCE + '\n')
        raises(self.pkg, c4_source=C4_SOURCE + '\n')
        bad = copy.deepcopy(self.pkg)
        s = next(s for s in bad['statements'] if s['role'] == 'pattern' and s['status'] == 'CHECKED')
        s['lean'] = s['lean'][:-1] + str(int(s['lean'][-1]) - 1)
        raises(bad)
        unresolved = copy.deepcopy(self.pkg)
        for s in unresolved['statements']:
            if s['role'] == 'pattern':
                s['status'] = 'UNRESOLVED'
        self.assertEqual(V4.registry_from_package(unresolved, defs_source=DEFS_SOURCE, c4_source=C4_SOURCE)['patterns'], {})

    def test_statement_parser_is_strict(self):
        body = 'P4.adj S v0 v1 + P4.adj S v1 v2 + P4.adj S v0 v2 ≤ 3'
        self.assertEqual(V4.parse_pattern_statement(head(3) + body), (3, [(0, 1), (0, 2), (1, 2)], 3))
        missing = head(3).replace('(h_v0_v2 : v0 ≠ v2) ', '')
        swapped = head(3).replace('(h_v0_v1 : v0 ≠ v1) (h_v0_v2 : v0 ≠ v2)', '(h_v0_v2 : v0 ≠ v2) (h_v0_v1 : v0 ≠ v1)')
        lying = head(3).replace('(h_v1_v2 : v1 ≠ v2)', '(h_v1_v2 : v0 ≠ v2)')
        for text in (missing + body, swapped + body, lying + body, head(3).replace('(hS : G4.C4Free S) ', '') + body,
                     head(3) + body.replace('P4.adj S v1 v2', 'P4.adj S v2 v1'),
                     head(3) + body.replace(' + P4.adj S v0 v2', ''),                       # v-set still 0..2 but a missing edge is fine
                     head(3) + body.replace('P4.adj S v0 v2', 'P4.adj S v0 v1'), head(3) + body.replace('≤', '<'),
                     head(4) + body):
            parsed = V4.parse_pattern_statement(text)
            if text == head(3) + body.replace(' + P4.adj S v0 v2', ''):
                self.assertEqual(parsed, (3, [(0, 1), (1, 2)], 3))
            else:
                self.assertIsNone(parsed, text)


class Certificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GC4.load_registry()
        cls.k6, cls.k6_lp, _, _ = GC4.lp_dual_rows_x(K6, cls.reg)

    def test_generated_rows_tighten_the_bound(self):
        v = V4.check_certificate(K6, self.k6, self.reg)
        self.assertEqual(v['verdict'], 'VALID')
        self.assertEqual(v['bound'], 7)
        none, _, n0, _ = GC4.lp_dual_rows_x(K6, self.reg, max_rows=0)
        self.assertEqual(n0, 45)                                                    # the 45 4-cycles of K6
        self.assertEqual(V4.check_certificate(K6, none, self.reg)['bound'], 11)
        from genesis.discovery import obstruction as O
        self.assertEqual(O.check_certificate(K6, O.lp_dual(K6)[0])['bound'], 11)    # the evaluator's LP

    def tamper(self, f, base=None):
        c = copy.deepcopy(base or self.k6)
        f(c)
        return V4.check_certificate(K6, c, self.reg)['verdict']

    def test_tampering_is_rejected(self):
        pat = next(i for i, q in enumerate(self.k6['inequalities']) if q['kind'] == 'pattern')
        none, _, _, _ = GC4.lp_dual_rows_x(K6, self.reg, max_rows=0)
        cyc = next(i for i, q in enumerate(none['inequalities']) if q['kind'] == 'cycle')

        def lower_weight(c):
            c['inequalities'][pat]['weight'] = '1/1000000'
        def wrong_rhs(c):
            c['inequalities'][pat]['rhs'] -= 1
        def collapse_map(c):
            m = c['inequalities'][pat]['map']; m[1] = m[0]
        def leave_host(c):
            c['inequalities'][pat]['map'][0] = 40
        def unknown(c):
            c['inequalities'][pat]['pattern'] = 'p4_unknown'
        def bound(c):
            c['bound'] -= 1
        def registry(c):
            c['registry_sha256'] = '0' * 64
        def kind(c):
            c['inequalities'][pat]['kind'] = 'clique'
        for f in (lower_weight, wrong_rhs, collapse_map, leave_host, unknown, bound, registry, kind):
            self.assertEqual(self.tamper(f), 'REJECTED', f.__name__)

        def cycle_repeats(c):
            q = c['inequalities'][cyc]; q['cycle'][2] = q['cycle'][0]
        def cycle_rhs(c):
            c['inequalities'][cyc]['rhs'] = 2
        def cycle_short(c):
            c['inequalities'][cyc]['cycle'] = c['inequalities'][cyc]['cycle'][:3]
        def cycle_outside(c):
            c['inequalities'][cyc]['cycle'][1] = 9
        for f in (cycle_repeats, cycle_rhs, cycle_short, cycle_outside):
            self.assertEqual(self.tamper(f, none), 'REJECTED', f.__name__)
        self.assertEqual(self.tamper(lambda c: None, none), 'VALID')
        other = host(6, itertools.combinations(range(6), 2), tid='other')
        self.assertEqual(V4.check_certificate(other, self.k6, self.reg)['verdict'], 'REJECTED')
        tri = host(6, itertools.combinations(range(6), 2), domain='triangle_free_host_v1')
        self.assertEqual(V4.check_certificate(tri, self.k6, self.reg)['verdict'], 'REJECTED')
        smaller = dict(self.reg, patterns={k: v for k, v in self.reg['patterns'].items() if v['vertices'] < 6})
        self.assertEqual(V4.check_certificate(K6, self.k6, smaller)['verdict'], 'REJECTED')

    def test_route_certifies_without_sat_when_the_bound_meets_the_witness(self):
        rec = GC4.certify_with_rows(K6, FRIENDSHIP, self.reg, seconds=30, separation_seconds=30, max_rows=50000,
                                    order='dense-first')
        self.assertEqual((rec['lower'], rec['upper'], rec['method']), (7, 7, 'LP_DUAL_GENERATED_C4_EXACT'))
        self.assertEqual([s['step'] for s in rec['steps']], ['lp-dual-rows-c4'])
        self.assertEqual(rec['certificate']['task_sha256'], digest(K6.model_dump(mode='json')))

    def test_vertex_cycle(self):
        self.assertEqual(GC4.vertex_cycle([(2, 5), (1, 5), (1, 3), (2, 3)]), [1, 3, 2, 5])


if __name__ == '__main__':
    unittest.main()
