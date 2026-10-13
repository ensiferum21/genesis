"""H05 (B19-OPEN-3): the trusted runner for executable candidates (not yet wired into the custodian).

A valid frozen non-DSL candidate (represent-and-repair over a representation whose checked
soundness mode licenses lifting) executes on a DEV task and yields a receipt whose value the
domain checker recomputes. The s13.3 failures are refused safely: wrong digest, swapped
domain, mutated artifact after freeze, changed implementation, malformed output, code-like
parameters, exposed reference fields, resource overrun; unlicensed representations
(every C4 decoder) are refused.
"""
import json
import unittest

from genesis import candidates as CA
from genesis.common import canonical, digest
from genesis.domains import ADAPTERS
from genesis.models import SolverProgram

TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'


def task(domain=TF, seed=9101, n=14, p=0.45):
    return ADAPTERS[domain].generate(seed, 1, 'DEV', 'erdos', {'n': n, 'p': p})[0][0]


def rr(rep='cross_2', domain=TF, **kw):
    return CA.build_descriptor('represent-and-repair-v1', domain, {'representation': rep, 'cpu_seconds': 0.3, 'seed': 5},
                               cpu_seconds=kw.pop('cpu_seconds', 1), **kw)


def rehash(d):
    body = {k: v for k, v in d.items() if k != 'descriptor_id'}
    return dict(body, descriptor_id=digest(body))


class Positive(unittest.TestCase):
    def test_frozen_represent_and_repair_candidate_runs_and_is_rechecked(self):
        t, d = task(), rr()
        r = CA.run(t, d, seed=1, expected_id=d['descriptor_id'])
        self.assertEqual(r['status'], 'SUCCESS', r)
        self.assertEqual(ADAPTERS[TF].validate(t, r['result']['selected'])['value'], r['result']['value'])
        self.assertEqual(r['execution_mode'], 'TRUSTED_REGISTERED_RUNNER')
        self.assertFalse(r['arbitrary_code_sandbox'])
        self.assertEqual(r['candidate_view_sha256'], digest(ADAPTERS[TF].candidate_view(t).model_dump(mode='json')))
        self.assertGreater(r['cpu_ns'], 0)

    def test_the_dsl_kind_is_the_existing_path(self):
        t = task()
        d = CA.build_descriptor('dsl-program-v1', TF, {'program': SolverProgram(rounds=8).model_dump(mode='json')},
                                cpu_seconds=1)
        r = CA.run(t, d, seed=0)
        self.assertEqual(r['status'], 'SUCCESS')
        self.assertEqual(r['execution_mode'], 'TRUSTED_REGISTERED_RUNNER')


class Refusals(unittest.TestCase):
    def test_unlicensed_representations_are_refused(self):
        for rep, dom in (('cross_2', C4), ('cross_3', TF), ('adjacent_2', C4)):
            with self.assertRaises(CA.CandidateError) as cm:
                rr(rep, dom)
            self.assertEqual(cm.exception.code, 'REPRESENTATION_NOT_LICENSED', (rep, dom))
        with self.assertRaises(CA.CandidateError):
            rr('no_such_representation')

    def test_wrong_digest_and_not_the_frozen_candidate(self):
        t, d = task(), rr()
        bad = dict(d, descriptor_id='0' * 64)
        self.assertIn('DESCRIPTOR_ID_MISMATCH', CA.run(t, bad, seed=1)['problems'])
        other = rr(cpu_seconds=2)
        self.assertIn('NOT_THE_FROZEN_CANDIDATE', CA.run(t, other, seed=1, expected_id=d['descriptor_id'])['problems'])

    def test_swapped_domain(self):
        r = CA.run(task(C4), rr(), seed=1)
        self.assertEqual(r['status'], 'REFUSED')
        self.assertIn('DOMAIN_MISMATCH', r['problems'])

    def test_mutated_artifact_after_freeze(self):
        d = rr()
        mutated = json.loads(canonical(d))
        mutated['parameters']['representation'] = 'cross_3'               # an unsound decoder, id kept
        self.assertIn('DESCRIPTOR_ID_MISMATCH', CA.descriptor_problems(mutated))
        self.assertIn('REPRESENTATION_NOT_LICENSED', CA.descriptor_problems(rehash(mutated)))
        changed = rehash(dict(d, parameters=dict(d['parameters'], seed=6)))
        self.assertEqual(CA.descriptor_problems(changed, expected_id=d['descriptor_id']), ['NOT_THE_FROZEN_CANDIDATE'])

    def test_changed_implementation(self):
        d = rr()
        impl = dict(d['implementation'])
        impl['invention/representations.py'] = '0' * 64
        self.assertIn('IMPLEMENTATION_CHANGED', CA.descriptor_problems(rehash(dict(d, implementation=impl))))

    def test_code_like_or_unknown_inputs(self):
        for kind, params in (('represent-and-repair-v1', {'representation': 'cross_2', 'cpu_seconds': 0.3, 'seed': 1,
                                                           'module': 'os'}),
                             ('represent-and-repair-v1', {'command': 'rm -rf /'}),
                             ('represent-and-repair-v1', {'representation': 'cross_2', 'cpu_seconds': 999, 'seed': 1}),
                             ('dsl-program-v1', {'program': {'schema_version': 'graph-priority-v1'}, 'path': '/tmp/x'})):
            with self.assertRaises(CA.CandidateError):
                CA.build_descriptor(kind, TF, params, cpu_seconds=1)
        with self.assertRaises(CA.CandidateError) as cm:
            CA.build_descriptor('python-source-v1', TF, {'source': 'print(1)'}, cpu_seconds=1)
        self.assertEqual(cm.exception.code, 'UNKNOWN_KIND')
        self.assertEqual(CA.descriptor_problems({'kind': 'x'}), ['MALFORMED_DESCRIPTOR'])

    def test_malformed_output_is_never_scored(self):
        bad = ['not json', '[]', json.dumps({'selected': [], 'value': 0, 'extra': 1}),
               json.dumps({'selected': [[0, 1, 2]], 'value': 1}), json.dumps({'selected': [['0', 1]], 'value': 1}),
               json.dumps({'selected': [[0, 1]] * 50, 'value': 50}), json.dumps({'selected': [], 'value': 1.5}),
               'x' * (CA.MAX_OUTPUT + 1)]
        for raw in bad:
            with self.assertRaises(CA.CandidateError):
                CA.decode_output(raw, 10)
        self.assertEqual(CA.decode_output(json.dumps({'selected': [[0, 1]], 'value': 1}), 10), ([(0, 1)], 1))

    def test_no_reference_fields_reach_the_child(self):
        t, d = task(), rr()
        req = CA.child_request(t, d, 3)
        self.assertEqual(set(req), {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'})   # queries: a resource cap
        self.assertEqual(set(req['view']), {'domain', 'n', 'edges'})
        raw = canonical(req).decode()
        for secret in (t.task_id, t.family, t.split):
            self.assertNotIn(secret, raw)

    def test_resource_overrun_is_not_a_result(self):
        t = task()
        d = rr(wall_seconds=0.05)                    # the child cannot even start inside this wall budget
        r = CA.run(t, d, seed=1)
        self.assertIn(r['status'], ('TIMEOUT', 'CPU_LIMIT', 'EXECUTION_ERROR'))
        self.assertNotIn('result', r)


class CustodianDispatch(unittest.TestCase):
    def test_v3_validates_dsl_programs_and_v4_rebuilds_descriptors(self):
        # B20_R5: v3 requests keep the DSL path; v4 requests name descriptors that the custodian
        # rebuilds (tests_genesis/test_candidate_custody.py exercises the whole route).
        import inspect
        from genesis import custodian
        self.assertIn('SolverProgram.model_validate_json', inspect.getsource(custodian.validate_request))
        self.assertIn('descriptor_problems', inspect.getsource(custodian._validate_v4))
        self.assertIn('descriptor_problems', inspect.getsource(custodian.descriptor_export_problems))


if __name__ == '__main__':
    unittest.main()
