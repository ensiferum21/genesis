"""Regression tests for the external B14 review, finding F-01 (audit/review_b14_external/).

A requested proposition (e.g. "the optimum is 0 edges") is not what the evidence
establishes. Exported wording must be derived per claim from that claim's own
effective levels; anything requested but unproved is exported only as a marked
conjecture. The six acceptance cases follow the review's list.
"""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from genesis.common import canonical, code_identity
from genesis.graphs import exact_checker
from genesis.kernel.evidence import MATH_SCOPE, EvidenceKernel
from genesis.models import GraphTask
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store
from genesis.verification.certificates import build, persist
from tests_genesis.signed_fixtures import SignedFixture, path4, record_evaluation, witness_payload

REPO = Path(__file__).resolve().parents[1]
SRC = 'a' * 64
MARK = 'NOT ESTABLISHED (requested, unproved): '


def claims_of(bundle):
    with zipfile.ZipFile(bundle) as z:
        name = next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))
        return {c['claim_id']: c for c in json.loads(z.read(name))['claims']}


def report_of(bundle):
    with zipfile.ZipFile(bundle) as z:
        return z.read(next(n for n in z.namelist() if n.endswith('/report.md'))).decode()


def rewrite(bundle, out, victim, fn):
    import hashlib
    with zipfile.ZipFile(bundle) as zin:
        names = zin.namelist(); base = names[0].split('/')[0] + '/'
        files = {n: zin.read(n) for n in names}
    files[base + victim] = fn(files[base + victim])
    manifest = json.loads(files[base + 'MANIFEST.json'])
    manifest['files'][victim] = hashlib.sha256(files[base + victim]).hexdigest()
    files[base + 'MANIFEST.json'] = canonical(manifest)
    with zipfile.ZipFile(out, 'w') as z:
        for n, v in files.items():
            z.writestr(n, v)


class F01(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.root = self.d / 'campaign'
        self.task = path4()

    def store(self):
        s = Store(self.root)
        if s.state('source_hash') is None:
            s.set_state('source_hash', code_identity(REPO)['sha256'])
        return s

    def witness(self, k, value, witness):
        return k.record('witness_check', witness_payload(k.s, self.task, witness), route='genesis.campaign',
                        source_hash=SRC, verdict='VALID')

    def claim(self, k, cid, deps, value, kind):
        problem = {'task_sha256': k.s.put(self.task.model_dump(mode='json')), 'value': value, 'claim': kind}
        return k.create_claim(cid, k.math_statement(problem), MATH_SCOPE, deps, problem=problem)

    def optimum_claim(self, k, cid='true-optimum'):
        b, blobs = build(self.task, {'lower': 3, 'witness': self.task.edges, 'upper': 3,
                                     'upper_certificate': {'method': 'HOST_EDGE_COUNT', 'upper': 3}})
        ref = persist(k.s, b, blobs)
        w = self.witness(k, 3, self.task.edges)
        sha = k.s.put(self.task.model_dump(mode='json'))
        bound = k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': self.task.task_id,
                                         'task_sha256': sha, 'lower': 3, 'upper': 3, 'gap': 0, 'lower_evidence': w,
                                         'certificate_bundle': ref},
                         parents=[w], route='genesis.verification.sat', source_hash=SRC, verdict='VALID')
        self.claim(k, cid, [bound], 3, 'optimum')
        k.promote(cid, 'math', 'WITNESS_VALID')
        k.promote(cid, 'math', 'OPTIMALITY_CHECKED')
        return bound

    def export(self, name='b.zip'):
        out = self.d / name
        build_bundle(self.root, out)
        return out

    def test_1_false_optimum_is_exported_only_as_a_marked_conjecture(self):
        self.assertEqual(exact_checker(self.task)['value'], 3)
        with self.store() as s:
            k = EvidenceKernel(s)
            self.claim(k, 'false-optimum', [self.witness(k, 0, [])], 0, 'optimum')
            k.promote('false-optimum', 'math', 'WITNESS_VALID')
        bundle = self.export()
        c = claims_of(bundle)['false-optimum']
        self.assertNotIn('optimum', c['current_statement'])
        self.assertTrue(c['current_statement'].endswith('has a valid subgraph with 0 edges'))
        self.assertTrue(c['conjecture'].startswith(MARK) and 'the optimum' in c['conjecture'])
        report = report_of(bundle)
        self.assertIn('Established: c4_host_v2 host path4', report)
        self.assertNotIn('Established: the optimum', report)
        self.assertTrue(verify_bundle(bundle)['ok'])
        # A producer that promotes the conjecture to the asserted statement is rejected.
        lying = self.d / 'lying.zip'

        def promote_conjecture(raw):
            claims = json.loads(raw)
            for x in claims['claims']:
                x['current_statement'], x['conjecture'] = x['requested_statement'], None
            return canonical(claims)
        rewrite(bundle, lying, 'CLAIMS.json', promote_conjecture)
        self.assertFalse(verify_bundle(lying)['ok'])
        edited = self.d / 'edited.zip'
        rewrite(bundle, edited, 'report.md', lambda raw: raw.replace(b'NOT ESTABLISHED (requested, unproved): ', b''))
        self.assertFalse(verify_bundle(edited)['ok'])

    def test_2_correct_lower_bound_is_exportable(self):
        with self.store() as s:
            k = EvidenceKernel(s)
            self.claim(k, 'lower', [self.witness(k, 3, self.task.edges)], 3, 'lower_bound')
            k.promote('lower', 'math', 'WITNESS_VALID')
        bundle = self.export()
        c = claims_of(bundle)['lower']
        self.assertEqual(c['current_statement'], c['requested_statement'])
        self.assertIsNone(c['conjecture'])
        self.assertTrue(verify_bundle(bundle)['ok'])

    def test_3_optimum_with_matching_checked_bounds_is_exportable(self):
        with self.store() as s:
            self.optimum_claim(EvidenceKernel(s))
        bundle = self.export()
        c = claims_of(bundle)['true-optimum']
        self.assertTrue(c['current_statement'].startswith('the optimum for c4_host_v2 host path4'))
        self.assertIsNone(c['conjecture'])
        self.assertTrue(verify_bundle(bundle)['ok'])

    def test_4_losing_the_upper_bound_downgrades_the_wording_and_keeps_history(self):
        with self.store() as s:
            bound = self.optimum_claim(EvidenceKernel(s))
        before = self.export('before.zip')
        with self.store() as s:
            k = EvidenceKernel(s)
            k.revoke(bound, 'certificate custody lost', 'auditor')
        after = self.export('after.zip')
        c = claims_of(after)['true-optimum']
        self.assertIsNone(c['current_statement'])
        self.assertTrue(c['conjecture'].startswith(MARK))
        self.assertEqual(c['historical']['recorded_levels']['math'], 'OPTIMALITY_CHECKED')
        self.assertTrue(verify_bundle(after)['ok'])
        feed = self.d / 'REVOCATIONS.json'
        with zipfile.ZipFile(after) as z:
            feed.write_bytes(z.read(next(n for n in z.namelist() if n.endswith('/REVOCATIONS.json'))))
        r = verify_bundle(before, later_revocations=feed)
        self.assertTrue(r['ok'])
        now = {x['claim_id']: x for x in r['current']['claims']}['true-optimum']
        self.assertIsNone(now['current_statement'])

    def test_5_another_claims_optimality_does_not_strengthen_this_claim(self):
        with self.store() as s:
            k = EvidenceKernel(s)
            self.optimum_claim(k)
            self.claim(k, 'false-optimum', [self.witness(k, 0, [])], 0, 'optimum')
            k.promote('false-optimum', 'math', 'WITNESS_VALID')
        bundle = self.export()
        claims = claims_of(bundle)
        self.assertTrue(claims['true-optimum']['current_statement'].startswith('the optimum'))
        self.assertNotIn('optimum', claims['false-optimum']['current_statement'])
        self.assertTrue(verify_bundle(bundle)['ok'])

    def test_6_scope_is_confined_and_checked_per_claim(self):
        with self.store() as s:
            k = EvidenceKernel(s)
            w = self.witness(k, 3, self.task.edges)
            problem = {'task_sha256': s.put(self.task.model_dump(mode='json')), 'value': 3, 'claim': 'lower_bound'}
            with self.assertRaisesRegex(ValueError, 'confined to its checked problem'):
                k.create_claim('wide', k.math_statement(problem), 'every graph family and domain', [w],
                               problem=problem)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            k.create_claim('free', 'a run happened', 'the result generalises to every domain', [run])
        with self.assertRaisesRegex(ValueError, 'scope'):
            self.export('scope.zip')

    def test_free_text_is_never_asserted(self):
        with self.store() as s:
            k = EvidenceKernel(s)
            w = self.witness(k, 3, self.task.edges)
            k.create_claim('free', 'host path4 needs at most 0 edges', 'host path4', [w])
            self.assertEqual(k.current_wording('free')['contract'], 'FREE_TEXT_NOT_ASSERTED')
            self.assertIsNone(k.current_wording('free')['current_statement'])

    def test_bound_claims_are_established_only_while_confirmed(self):
        fx = SignedFixture(self.tmp.name)
        with Store(self.d / 'bound') as s:
            fx.bind_store(s)
            k = EvidenceKernel.with_fixture_registry(s, fx.registry)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            from genesis.kernel import receipts as R
            request = fx.request()
            _, node = record_evaluation(k, fx, request, [run])
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node],
                           binding=R.binding_from_requests([request]))
            before = k.current_wording('claim-1')
            k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
            after = k.current_wording('claim-1')
        self.assertIsNone(before['current_statement'])
        self.assertTrue(before['conjecture'].startswith(MARK))
        self.assertEqual(after['current_statement'], SignedFixture.STATEMENT)


if __name__ == '__main__':
    unittest.main()
