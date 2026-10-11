"""B16 / W05: every domain adapter conforms to the DomainAdapter contract.

The conformance cases run against each registered adapter, so a later domain (the
Lean domain of W08) is checked by the same suite when it is registered.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from genesis import domains as DM
from genesis.common import canonical, digest
from genesis.execution import execute
from genesis.graphs import relabel
from genesis.kernel import receipts as R
from genesis.models import GraphTask, Limits, SolverProgram

C5_PLUS = GraphTask(task_id='t-c5', domain='c4_host_v2', n=5, family='cycle',
                    edges=((0, 1), (0, 4), (1, 2), (2, 3), (3, 4)), split='DEV')


def task_for(adapter, **kw):
    base = dict(task_id='conf-1', domain=adapter.name, n=5, family='cycle',
                edges=((0, 1), (0, 2), (0, 4), (1, 2), (2, 3), (3, 4)), split='DEV')
    base.update(kw)
    return GraphTask(**base)


class Conformance(unittest.TestCase):
    def each(self):
        self.assertGreaterEqual(len(DM.ADAPTERS), 2)
        for name, a in DM.ADAPTERS.items():
            with self.subTest(domain=name):
                yield a

    def test_contract_is_the_signed_domain_meaning(self):
        for a in self.each():
            self.assertEqual(a.contract_hash(), R.domain_contract_hash(a.name))

    def test_parse_never_raises_and_rejects_explicitly(self):
        for a in self.each():
            good = task_for(a)
            self.assertEqual(a.parse(good.model_dump(mode='json')), good)
            for bad in (None, 'x', [], {'domain': a.name}, dict(good.model_dump(mode='json'), n=64),
                        dict(good.model_dump(mode='json'), edges=[[1, 0]]),
                        dict(good.model_dump(mode='json'), domain='other'),
                        dict(good.model_dump(mode='json'), task_id='a\nb'),
                        dict(good.model_dump(mode='json'), extra=1)):
                out = a.parse(bad)
                self.assertIsInstance(out, DM.Unsupported, bad)
                self.assertEqual(out.record()['status'], 'UNSUPPORTED')

    def test_supports_is_explicit_per_purpose(self):
        for a in self.each():
            t = task_for(a)
            for purpose in DM.PURPOSES:
                self.assertIsNone(a.supports(t, purpose))
            self.assertIsInstance(a.supports(t, 'telepathy'), DM.Unsupported)
            other = DM.ADAPTERS[next(n for n in DM.ADAPTERS if n != a.name)]
            self.assertIsInstance(other.supports(t, 'execute'), DM.Unsupported)
            with mock.patch.object(type(a), 'CERTIFICATE_MAX_EDGES', 3):
                self.assertIsInstance(a.supports(t, 'exact_reference'), DM.Unsupported)
                self.assertIsInstance(a.reference(t), DM.Unsupported)

    def test_exposure_identity_ignores_labels_and_vertex_names(self):
        for a in self.each():
            t = task_for(a)
            key = a.exposure_identity(t)['canonical']
            renamed = task_for(a, task_id='other', family='other', split='CONFIRM')
            self.assertEqual(a.exposure_identity(renamed)['canonical'], key)
            self.assertEqual(a.exposure_identity(relabel(t, (4, 3, 2, 1, 0)))['canonical'], key)
            k10 = GraphTask(task_id='k10', domain=a.name, n=10, family='complete', split='DEV',
                            edges=tuple((u, v) for u in range(10) for v in range(u + 1, 10)))
            self.assertIsInstance(a.exposure_identity(k10), DM.Unsupported)   # never a false freshness pass

    def test_candidate_view_holds_no_evaluator_information(self):
        for a in self.each():
            t = task_for(a, task_id='SECRET-confirm-0001', family='SECRET-family', split='CONFIRM')
            view = a.candidate_view(t).model_dump(mode='json')
            self.assertEqual(set(view), {'domain', 'n', 'edges'})
            self.assertNotIn('SECRET', canonical(view).decode())
            for key in DM.EVALUATOR_ONLY:
                self.assertNotIn(key, view)

    def test_execution_child_receives_only_the_candidate_view(self):
        import genesis.execution as ex
        sent = []
        real = ex.canonical

        def spy(value):
            sent.append(value)
            return real(value)
        t = task_for(DM.ADAPTERS['c4_host_v2'], task_id='SECRET-confirm-0002', family='SECRET', split='CONFIRM')
        with mock.patch.object(ex, 'canonical', spy):
            receipt = execute(t, SolverProgram(rounds=2), Limits(), 7)
        self.assertEqual(receipt['status'], 'SUCCESS')
        request = next(v for v in sent if isinstance(v, dict) and 'program' in v)
        self.assertEqual(set(request['task']), {'domain', 'n', 'edges'})
        self.assertNotIn('SECRET', real(request).decode())
        self.assertEqual(receipt['candidate_view_sha256'],
                         digest(DM.ADAPTERS['c4_host_v2'].candidate_view(t).model_dump(mode='json')))

    def test_validate_and_score(self):
        for a in self.each():
            t = task_for(a)
            ok = a.validate(t, [(0, 1), (2, 3)])
            self.assertEqual((ok['status'], ok['value']), ('VALID', 2))
            self.assertEqual(a.score(t, [(0, 1)]), 1)
            self.assertEqual(a.validate(t, [(0, 3)])['status'], 'INVALID')          # not a host edge
            self.assertEqual(a.validate(t, 'garbage')['status'], 'INVALID')
            self.assertIsNone(a.score(t, [(0, 3)]))
        tri = task_for(DM.ADAPTERS['triangle_free_host_v1'])
        self.assertEqual(DM.ADAPTERS['triangle_free_host_v1'].validate(tri, [(0, 1), (0, 2), (1, 2)])['status'],
                         'INVALID')
        c4 = GraphTask(task_id='c4', domain='c4_host_v2', n=4, family='c', split='DEV',
                       edges=((0, 1), (0, 3), (1, 2), (2, 3)))
        self.assertEqual(DM.ADAPTERS['c4_host_v2'].validate(c4, list(c4.edges))['status'], 'INVALID')

    def test_reference_is_certified_or_explicitly_unsupported(self):
        for a in self.each():
            small = task_for(a)
            r = a.reference(small)
            self.assertEqual((r['status'], r['method']), ('FINITE_CERTIFIED', 'DUAL_EXACT_SEARCH'))
            self.assertEqual(a.validate(small, [])['status'], 'VALID')
        a = DM.ADAPTERS['c4_host_v2']
        big, _, _ = a.generate(5, 1, 'DEV', 'erdos', {'n': 11, 'p': 0.5})
        self.assertGreater(len(big[0].edges), 24)
        r = a.reference(big[0], seconds=120)
        self.assertEqual((r['status'], r['method']), ('FINITE_CERTIFIED', 'SAT_DRAT_UPPER+CHECKED_WITNESS'))
        self.assertEqual(a.validate(big[0], r['witness'])['value'], r['value'])
        with tempfile.TemporaryDirectory() as empty, mock.patch.dict(os.environ, {'GENESIS_TOOLCHAIN': empty}):
            self.assertIsInstance(a.reference(big[0], seconds=5), DM.Unsupported)

    def test_certificate_obligations(self):
        for a in self.each():
            self.assertEqual([o['obligation'] for o in a.certificate_obligations('lower_bound', 3)], ['lower_bound'])
            self.assertEqual([o['obligation'] for o in a.certificate_obligations('optimum', 3)],
                             ['lower_bound', 'upper_bound'])
            self.assertEqual(a.certificate_obligations('beauty', 3)[0]['status'], 'UNSUPPORTED')

    def test_cost_from_a_real_receipt(self):
        a = DM.ADAPTERS['c4_host_v2']
        cost = a.cost(execute(task_for(a), SolverProgram(rounds=2), Limits(), 1))
        self.assertEqual(cost['status'], 'SUCCESS')
        for k in ('wall_ns', 'cpu_ns', 'queries'):
            self.assertIsInstance(cost[k], int)

    def test_families_generate_deterministically_and_distinctly(self):
        for a in self.each():
            fam = a.families()
            self.assertEqual(set(fam), {'erdos', 'bipartite', 'planted_cluster'})
            tasks, seen, stats = a.generate(3, 6, 'DEV', 'erdos', {'n': 8, 'p': 0.5})
            again, _, _ = a.generate(3, 6, 'DEV', 'erdos', {'n': 8, 'p': 0.5})
            self.assertEqual(tasks, again)
            self.assertEqual(len({a.exposure_identity(t)['canonical'] for t in tasks}), 6)
            self.assertTrue(all(t.split == 'DEV' and t.domain == a.name for t in tasks))
            fresh, _, _ = a.generate(4, 3, 'DEV', 'erdos', {'n': 8, 'p': 0.5}, excluded=seen)
            self.assertFalse({a.exposure_identity(t)['canonical'] for t in fresh} & seen)
            for bad in ({'n': 8}, {'n': 8, 'p': 1.5}, {'n': 100, 'p': 0.5}):
                with self.assertRaises(ValueError):
                    a.generate(1, 1, 'DEV', 'erdos', bad)
            with self.assertRaises(ValueError):
                a.generate(1, 1, 'DEV', 'mystery', {'n': 5})

    def test_replay(self):
        for a in self.each():
            t = task_for(a)
            record = {'task': t.model_dump(mode='json'), 'witness': [[0, 1], [2, 3]], 'value': 2}
            self.assertEqual(a.replay(record), {'status': 'REPLAYED', 'value': 2})
            self.assertEqual(a.replay(dict(record, value=3))['status'], 'INVALID')
            self.assertEqual(a.replay(dict(record, task={'domain': 'elsewhere'}))['status'], 'UNSUPPORTED')

    def test_unknown_domain_and_unsupported_execution_are_explicit(self):
        self.assertIsInstance(DM.adapter('lean_theorems_v0'), DM.Unsupported)
        a = DM.ADAPTERS['c4_host_v2']
        with mock.patch.object(type(a), 'supports', lambda self, task, purpose: DM.Unsupported('test gate')):
            receipt = execute(task_for(a), SolverProgram(rounds=2), Limits(), 1)
        self.assertEqual((receipt['status'], receipt['reason']), ('UNSUPPORTED', 'test gate'))


if __name__ == '__main__':
    unittest.main()
