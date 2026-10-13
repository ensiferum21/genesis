"""W22 (handoff s21.1-21.2): derived primitives, contracts, conformance, comparison, IR evolution."""
from itertools import combinations, product
import json
import unittest
from unittest import mock

from genesis import mrdl
from genesis import primitives as P
from genesis.common import canonical
from genesis.models import GraphTask


def host(n, edges, i=0):
    return GraphTask(task_id=f'prim-{n}-{i}', domain='c4_host_v2', n=n, edges=tuple(sorted(edges)), family='fixture')


def all_hosts(n):
    pairs = list(combinations(range(n), 2))
    return [host(n, [p for p, b in zip(pairs, bits) if b], i) for i, bits in enumerate(product((0, 1), repeat=len(pairs)))]


def deg_sq():
    return {'kind': 'sum_vertices', 'term': {'op': 'Mul', 'args': [{'op': 'Degree', 'params': {'u': '$v'}},
                                                                   {'op': 'Degree', 'params': {'u': '$v'}}]}}


class Contracts(unittest.TestCase):
    def setUp(self):
        self.reg = P.starting_registry()

    def test_identity_is_deterministic(self):
        rec = self.reg.record()
        again = P.Registry(json.loads(canonical(rec['contracts'])))
        self.assertEqual(again.identity(), self.reg.identity())
        self.assertEqual(P.cognitive_kernel(again), P.cognitive_kernel(self.reg))

    def test_refusals(self):
        good = P.contract('Feature', expansion=deg_sq(), semantics='s', hypothesis='h')
        self.assertEqual(P.contract_problems(good, self.reg.contracts), [])
        cases = [
            (dict(good, name='Degree'), 'new identifier'),
            (dict(good, effects=['NETWORK']), 'no effects'),
            (dict(good, native='os.system', implementation_sha256='0' * 64), 'trusted table'),
            (dict(good, native='edge_count_v1', implementation_sha256='0' * 64), 'pinned digest'),
            (dict(good, expansion={'kind': 'fixed', 'expr': {'op': 'Mystery'}}), 'unknown operation'),
            (dict(good, expansion={'kind': 'loop', 'expr': {}}), 'template kind'),
            (dict(good, expansion={'kind': 'fixed', 'expr': {'op': 'Degree', 'params': {'u': '$x'}}}), 'unbound'),
            (dict(good, resource_bounds={'max_nodes': 10 ** 6}), 'language cap'),
            (dict(good, semantics=' '), 'semantics'),
            (dict(good, extra=1), 'exact field set'),
        ]
        for c, msg in cases:
            self.assertTrue(any(msg in p for p in P.contract_problems(c, self.reg.contracts)), (msg, c))
        deep = {'kind': 'fixed', 'expr': {'op': 'Const', 'params': {'value': 1}}}
        for _ in range(P.MAX_TEMPLATE_DEPTH + 2):
            deep = {'kind': 'scaled', 'num': 1, 'den': 1, 'of': deep}
        self.assertTrue(any('deep' in p for p in P.contract_problems(dict(good, expansion=deep), {})))

    def test_recursion_is_refused(self):
        a = P.contract('Alpha', expansion={'kind': 'fixed', 'expr': {'op': 'EdgeCount'}}, semantics='s', hypothesis='h')
        reg = self.reg.revise([a], reason='add Alpha')
        b = P.contract('Alpha', version=2, expansion={'kind': 'fixed', 'expr': {'op': 'Beta'}}, semantics='s',
                       hypothesis='h')
        beta = P.contract('Beta', expansion={'kind': 'fixed', 'expr': {'op': 'Alpha'}}, semantics='s', hypothesis='h')
        with self.assertRaises(P.PrimitiveError):
            reg.revise([b, beta], reason='cycle')
        with self.assertRaisesRegex(P.PrimitiveError, 'higher version'):
            reg.revise([dict(a, semantics='changed')], reason='silent change')

    def test_derived_on_derived(self):
        half = P.contract('HalfDegreeSquares', output='rational', semantics='s', hypothesis='h',
                          expansion={'kind': 'scaled', 'num': 1, 'den': 2,
                                     'of': {'kind': 'fixed', 'expr': {'op': 'SumDegreeSquares'}}})
        reg = self.reg.revise([half], reason='derived on derived')
        t = host(5, [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)])
        e = P.expand({'op': 'HalfDegreeSquares'}, t.n, reg)
        ops = set()

        def walk(x):
            ops.add(x['op'])
            for a in x.get('args') or []:
                walk(a)
        walk(e)
        self.assertTrue(ops <= mrdl.OPS)
        self.assertEqual(P.licensing_value({'op': 'HalfDegreeSquares'}, t, reg), 10)

    def test_parameters_are_typed(self):
        c = P.contract('Deg2', params={'x': 'vertex'}, semantics='s', hypothesis='h',
                       expansion={'kind': 'fixed', 'expr': {'op': 'Mul', 'args': [
                           {'op': 'Degree', 'params': {'u': {'$param': 'x'}}},
                           {'op': 'Degree', 'params': {'u': {'$param': 'x'}}}]}})
        reg = self.reg.revise([c], reason='param')
        t = host(4, [(0, 1), (0, 2), (0, 3)])
        self.assertEqual(P.licensing_value({'op': 'Deg2', 'params': {'x': 0}}, t, reg), 9)
        for bad in ({'x': 9}, {'x': '0'}, {}, {'x': 0, 'y': 1}):
            with self.assertRaises(P.PrimitiveError):
                P.expand({'op': 'Deg2', 'params': bad}, t.n, reg)


class Semantics(unittest.TestCase):
    def setUp(self):
        self.reg = P.starting_registry()

    def test_native_agrees_with_expansion_on_every_graph_with_four_vertices(self):
        hosts = all_hosts(4)
        for name in self.reg.contracts:
            rec = P.conformance(name, self.reg, hosts)
            self.assertEqual(rec['verdict'], 'CONFORMANT', name)
            self.assertEqual(len(rec['rows']), 64)

    def test_language_bounds_refuse_rather_than_approximate(self):
        t = host(12, [(u, u + 1) for u in range(11)])
        with self.assertRaisesRegex(ValueError, 'MRDL syntax bounds'):
            P.licensing_value({'op': 'PairCodegreeFalling2'}, t, self.reg)
        self.assertEqual(P.native_value({'op': 'PairCodegreeFalling2'}, t, self.reg), 0)

    def test_changed_native_code_is_refused(self):
        with mock.patch.dict(P.NATIVE, {'edge_count_v1': lambda task, p: 0}):
            with self.assertRaisesRegex(P.PrimitiveError, 'changed'):
                P.native_value({'op': 'EdgeCount'}, host(3, [(0, 1)]), self.reg)

    def test_compare_verdicts(self):
        # Fresh hosts large enough for the use the hypothesis names; the conformance run is charged in full.
        fresh = [host(40, [(u, v) for u in range(40) for v in range(u + 1, 40) if (u * v + i) % 3], i) for i in range(3)]
        conf = P.conformance('TriangleCount', self.reg, all_hosts(4))
        cmp = P.compare('TriangleCount', self.reg, conf, fresh)
        self.assertEqual(cmp['verdict'], 'USEFUL', (cmp['incumbent_cpu_ns'], cmp['native_cpu_ns_with_conformance']))
        self.assertTrue(all(r['agree'] for r in cmp['rows']))
        # The same expansion without a native implementation is a macro: no capability gain.
        macro = P.contract('TriangleMacro', output='rational', semantics='s', hypothesis='h',
                           expansion=self.reg.contracts['TriangleCount']['expansion'])
        reg = self.reg.revise([macro], reason='macro')
        conf2 = P.conformance('TriangleMacro', reg, all_hosts(4))
        self.assertEqual(P.compare('TriangleMacro', reg, conf2, fresh)['verdict'], 'NOT_A_CAPABILITY_GAIN')
        # Native reach beyond the trusted language is not licensed.
        big = [host(12, [(u, u + 1) for u in range(11)])]
        conf3 = P.conformance('PairCodegreeFalling2', self.reg, all_hosts(4))
        self.assertEqual(P.compare('PairCodegreeFalling2', self.reg, conf3, big)['verdict'], 'REJECTED')

    def test_nonconformant_native_is_rejected(self):
        buggy = lambda task, p: len(task.edges) + (1 if task.n == 4 and len(task.edges) == 6 else 0)
        with mock.patch.dict(P.NATIVE, {'edge_count_v1': buggy}):
            reg = P.Registry([P.contract('EdgeCount', output='rational', semantics='s', hypothesis='h',
                                         native='edge_count_v1',
                                         expansion=P.starting_registry().contracts['EdgeCount']['expansion'])])
            conf = P.conformance('EdgeCount', reg, all_hosts(4))
            self.assertEqual(conf['verdict'], 'NONCONFORMANT')
            self.assertEqual(sum(not r['agree'] for r in conf['rows']), 1)
            self.assertEqual(P.compare('EdgeCount', reg, conf, all_hosts(3))['verdict'], 'REJECTED')


class Evolution(unittest.TestCase):
    def test_historical_programs_keep_their_semantics(self):
        v1 = P.Registry([P.contract('Feature', expansion={'kind': 'fixed', 'expr': {'op': 'TracePower',
                                                                                    'params': {'k': 2}}},
                                    semantics='2m', hypothesis='h')])
        prog = P.program_record('p', [{'op': 'Feature'}], v1)
        v2 = v1.revise([P.contract('Feature', version=2, expansion={'kind': 'fixed', 'expr': {
            'op': 'TracePower', 'params': {'k': 3}}}, semantics='6 * triangles', hypothesis='h')], reason='redefine')
        t = host(3, [(0, 1), (0, 2), (1, 2)])
        regs = {v1.identity(): v1, v2.identity(): v2}
        self.assertEqual(P.replay(prog, t, regs), [6])                                   # tr A^2 of a triangle
        self.assertEqual(P.licensing_value({'op': 'Feature'}, t, v2), 6)                  # tr A^3 = 6 as well here
        t2 = host(3, [(0, 1), (1, 2)])
        self.assertEqual((P.replay(prog, t2, regs), P.licensing_value({'op': 'Feature'}, t2, v2)), ([4], 0))
        self.assertEqual(v2.history[-1]['identity'], v1.identity())
        with self.assertRaisesRegex(P.PrimitiveError, 'not available'):
            P.replay(prog, t, {v2.identity(): v2})
        self.assertNotEqual(P.cognitive_kernel(v1), P.cognitive_kernel(v2))
        # A migration adapter is recorded only if it reproduces the old semantics.
        good = P.migration(v1, v2, {'Feature': {'op': 'TracePower', 'params': {'k': 2}}}, all_hosts(4))
        bad = P.migration(v1, v2, {'Feature': {'op': 'Feature'}}, all_hosts(4))
        self.assertEqual((good['accepted'], bad['accepted']), (True, False))

    def test_mining_repeated_trace_shapes(self):
        corpus = [{'op': 'Add', 'args': [{'op': 'Mul', 'args': [{'op': 'Degree', 'params': {'u': i}},
                                                                {'op': 'Degree', 'params': {'u': i}}]},
                                         {'op': 'Const', 'params': {'value': i}}]} for i in range(5)]
        found = P.mine(corpus, min_count=3, min_size=3)
        self.assertEqual(found[0]['count'], 5)
        self.assertEqual(found[0]['shape']['op'], 'Mul')


if __name__ == '__main__':
    unittest.main()
