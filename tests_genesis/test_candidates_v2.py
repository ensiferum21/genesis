"""B20_R40: candidate registry v2 (kinds with their own implementation identity; built, not wired).
Descriptors rebuild and refuse alteration. A kind's identity does not include registry v1, so the
frozen E1/E1b descriptors are untouched. The MILP kind solves exactly and its witness is
re-checked, the child sees only the candidate view, and v1 refuses v2 descriptors."""
import itertools
import json
from pathlib import Path
import unittest

from genesis import candidates as C1
from genesis import candidates_v2 as C2
from genesis.models import GraphTask

ROOT = Path(__file__).resolve().parents[1]


def host(n, edges, tid='t-v2'):
    return GraphTask(task_id=tid, domain='triangle_free_host_v1', family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


K6 = host(6, itertools.combinations(range(6), 2))


class Descriptors(unittest.TestCase):
    def setUp(self):
        self.d = C2.build_descriptor('milp-highs-v1', 'triangle_free_host_v1', {'cpu_seconds': 1.0}, cpu_seconds=1.0)

    def test_descriptor_rebuilds_and_refuses_alteration(self):
        self.assertEqual(C2.descriptor_problems(self.d), [])
        self.assertEqual(C2.build_descriptor('milp-highs-v1', 'triangle_free_host_v1', {'cpu_seconds': 1.0},
                                             cpu_seconds=1.0)['descriptor_id'], self.d['descriptor_id'])
        for change in ({'parameters': {'cpu_seconds': 2.0}}, {'kind': 'milp-gurobi-v1'}, {'domain': 'c4_host_v2'},
                       {'schema': C1.SCHEMA}, {'implementation': {}}):
            self.assertNotEqual(C2.descriptor_problems(dict(self.d, **change)), [], change)
        with self.assertRaises(C2.CandidateError):
            C2.build_descriptor('milp-highs-v1', 'c4_host_v2', {'cpu_seconds': 1.0}, cpu_seconds=1.0)
        with self.assertRaises(C2.CandidateError):
            C2.build_descriptor('milp-highs-v1', 'triangle_free_host_v1', {'cpu_seconds': 1.0, 'cuts': 'all'}, cpu_seconds=1.0)

    def test_identity_is_per_kind_and_excludes_registry_v1(self):
        files = set(self.d['implementation'])
        self.assertEqual(files, {'candidates_v2.py', 'graphs.py', 'models.py', 'candidate_kinds/milp_highs.py'})
        self.assertNotIn('candidates.py', files)
        for pkg in ('e1', 'e1b'):
            frozen = json.loads((ROOT / 'handoff' / pkg / 'candidate_descriptor.json').read_text())
            self.assertEqual(C1.descriptor_problems(frozen), [])

    def test_registries_refuse_each_others_descriptors(self):
        self.assertNotEqual(C1.descriptor_problems(self.d), [])
        frozen = json.loads((ROOT / 'handoff' / 'e1b' / 'candidate_descriptor.json').read_text())
        self.assertEqual(C2.descriptor_problems(frozen), ['not a v2 candidate descriptor'])
        self.assertEqual(C2.run(K6, frozen, seed=0)['status'], 'REFUSED')


class Execution(unittest.TestCase):
    def test_milp_kind_is_exact_and_checked(self):
        d = C2.build_descriptor('milp-highs-v1', 'triangle_free_host_v1', {'cpu_seconds': 2.0}, cpu_seconds=2.0)
        r = C2.run(K6, d, seed=0, isolation='process')
        self.assertEqual((r['status'], r['result']['value']), ('SUCCESS', 9))       # Turán: K_{3,3}
        self.assertEqual(r['check']['status'], 'VALID')
        self.assertEqual(r['isolation'], 'PROCESS_RLIMITS')

    def test_child_request_is_the_candidate_view(self):
        d = C2.build_descriptor('milp-highs-v1', 'triangle_free_host_v1', {'cpu_seconds': 1.0}, cpu_seconds=1.0)
        req = C2.child_request(K6, d, 3)
        self.assertEqual(set(req), {'view', 'kind', 'parameters', 'cpu_seconds', 'queries', 'seed'})
        self.assertNotIn('task_id', json.dumps(req['view']))
        self.assertNotIn('family', req['view'])

    def test_strict_decoder(self):
        for raw in ('[]', '{"selected": [], "value": "9"}', '{"selected": [[0, 1, 2]], "value": 1}',
                    '{"selected": [], "value": 0, "x": 1}'):
            with self.assertRaises(C2.CandidateError):
                C2.decode_output(raw, 15)


if __name__ == '__main__':
    unittest.main()
