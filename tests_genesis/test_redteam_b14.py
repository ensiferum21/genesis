"""Regression tests for the B14 internal red-team findings F1-F11 (audit/redteam_b14/).

Each test re-expresses one demonstrated attack against the current schemas and
asserts that it now fails closed. The original scripts and their outputs on the
pre-fix tree are kept in audit/redteam_b14/ (logs_before_fix/). The reviewer was
a fresh agent under the same operator: useful, but not external independence.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from genesis.common import canonical, code_identity, digest
from genesis.kernel import receipts as R
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.kernel.index import build_index
from genesis.models import GraphTask
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store
from genesis.verification.certificates import build, persist
from tests_genesis.signed_fixtures import SignedFixture, chain_requests, record_evaluation

REPO = Path(__file__).resolve().parents[1]
SRC = 'a' * 64


def rewrite(bundle, out, change):
    """change(files: relpath->bytes) edits a bundle; MANIFEST is re-hashed (a producer lying consistently)."""
    with zipfile.ZipFile(bundle) as zin:
        names = zin.namelist(); base = names[0].split('/')[0] + '/'
        files = {n[len(base):]: zin.read(n) for n in names}
    manifest = json.loads(files.pop('MANIFEST.json'))
    change(files, manifest)
    manifest['files'] = {n: hashlib.sha256(v).hexdigest() for n, v in sorted(files.items())}
    with zipfile.ZipFile(out, 'w') as zout:
        for n, v in files.items():
            zout.writestr(base + n, v)
        zout.writestr(base + 'MANIFEST.json', canonical(manifest))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def rejects(self, k, claim, axis, level, fragment):
        with self.assertRaises(PromotionRejected) as ctx:
            k.promote(claim, axis, level)
        self.assertIn(fragment, ' | '.join(ctx.exception.args[0]))


class F1BundleWholeObject(Base):
    """F1: CLAIMS.json, certificates, report and MANIFEST must all match the re-derived bundle."""

    def setUp(self):
        super().setUp()
        self.root = self.d / 'c'
        with Store(self.root) as s:
            s.set_state('source_hash', code_identity(REPO)['sha256'])
            k = EvidenceKernel(s)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            w = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash=SRC,
                         verdict='VALID', verifier='dual-predicates')
            k.create_claim('w', 'host H has a valid subgraph with 7 edges', 'host H', [w])
            k.promote('w', 'math', 'WITNESS_VALID')
        self.bundle = self.d / 'b.zip'
        build_bundle(self.root, self.bundle, report='The returned witness passed the registered checks.')
        self.assertTrue(verify_bundle(self.bundle)['ok'])

    def attempt(self, change):
        out = self.d / f'x{len(list(self.d.glob("x*.zip")))}.zip'
        rewrite(self.bundle, out, change)
        return verify_bundle(out)

    def claims_edit(self, fn):
        def change(files, manifest):
            c = json.loads(files['CLAIMS.json']); fn(c); files['CLAIMS.json'] = canonical(c)
        return change

    def test_duplicate_claim_entry(self):
        top = {'math': 'OPTIMALITY_CHECKED', 'utility': 'CONFIRMED_TRANSFER', 'causality': 'PLACEBO_CONTROLLED',
               'improver': 'MULTIGEN_CONFIRMED', 'novelty': 'EXTERNALLY_CHECKED_NOVEL',
               'replication': 'EXTERNAL_REPRODUCTION'}
        r = self.attempt(self.claims_edit(lambda c: c['claims'].insert(0, dict(c['claims'][0], effective_levels=top))))
        self.assertFalse(r['ok'])

    def test_ceiling_statement_and_history_edits(self):
        for fn in (lambda c: c['ceiling'].update(utility='CONFIRMED_TRANSFER'),
                   lambda c: c['claims'][0].update(statement='Our solver beats every solver on every family'),
                   lambda c: c['claims'][0]['historical']['recorded_levels'].update(math='OPTIMALITY_CHECKED')):
            self.assertFalse(self.attempt(self.claims_edit(fn))['ok'])

    def test_overclaiming_report_certificate_edit_and_source_mismatch(self):
        def report(files, manifest):
            files['report.md'] = b'This construction is optimal and the result was replicated.'
        self.assertFalse(self.attempt(report)['ok'])

        def cert(files, manifest):
            name = next(n for n in files if n.startswith('certificates/'))
            body = json.loads(files[name]); body['payload']['value'] = 999; files[name] = canonical(body)
        self.assertFalse(self.attempt(cert)['ok'])

        def source(files, manifest):
            manifest['source_hash'] = manifest['shipped_code_identity'] = '0' * 64
        self.assertFalse(self.attempt(source)['ok'])

        def stray(files, manifest):
            files['checker_receipts/forged.json'] = canonical({'status': 'VALID'})
        self.assertFalse(self.attempt(stray)['ok'])

    def test_cli_verify_bundle_exits_nonzero_on_rejection(self):  # F7
        from genesis.cli import main
        out = self.d / 'bad.zip'
        rewrite(self.bundle, out, lambda files, m: files.__setitem__('report.md', b'This construction is optimal.'))
        with self.assertRaises(SystemExit) as ctx:
            main(['verify-bundle', str(out)])
        self.assertEqual(ctx.exception.code, 1)
        with self.assertRaises(SystemExit) as ctx:
            main(['verify-bundle', str(self.bundle)])
        self.assertEqual(ctx.exception.code, 0)


class KernelFindings(Base):
    def setUp(self):
        super().setUp()
        self.store = Store(self.d / 's'); self.addCleanup(self.store.close)
        self.fx = SignedFixture(self.tmp.name)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry)
        self.run = self.k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC,
                                 verdict='VALID')

    def test_f2_revoked_verifier_identity_stays_revoked(self):
        reg = self.k.register_verifier('checker-x', 'e' * 64)
        self.k.register_verifier('checker-x', 'e' * 64, validated_by=[self.run])  # a second registration up front
        w = self.k.record('witness_check', {'value': 7}, parents=[self.run], route='genesis.campaign',
                          source_hash=SRC, verdict='VALID', verifier='checker-x')
        self.k.create_claim('c', 'host H has a valid subgraph with 7 edges', 'host H', [w])
        self.k.promote('c', 'math', 'WITNESS_VALID')
        self.k.revoke(reg, 'verifier bug: accepts a 4-cycle', 'auditor')  # revoking ONE registration
        self.assertTrue(self.k.levels('c').get('invalidated'))
        self.assertEqual(self.k.verifier_trust('checker-x'), 'REVOKED')
        with self.assertRaises(PermissionError):
            self.k.register_verifier('checker-x', 'e' * 64)

    def test_f3_revoked_priority_adjudication(self):
        statement = 'construction X is new for hosts of family F'
        env = self.fx.sign({'schema': R.PRIORITY_ADJUDICATION, 'evidence_kind': 'external_priority_adjudication',
                            'claim_id': 'nov', 'statement_hash': digest(statement), 'scope': 'family F only',
                            'reviewer_id': 'FIXTURE', 'search_record_root': '3' * 64,
                            'decided_at': '2026-10-10T00:00:00+00:00', 'outcome': 'NOVEL_IN_SCOPE'},
                           'priority_reviewer')
        node = self.k.record_signed('external_priority_adjudication', env, parents=[self.run],
                                    route='genesis.custodian.evaluate', source_hash=SRC)
        self.k.create_claim('nov', statement, 'family F only', [node])
        decision = self.k.promote('nov', 'novelty', 'EXTERNALLY_CHECKED_NOVEL')
        self.k.revoke_evaluation(decision['evaluations'][0], 'prior art found later', 'reviewer')
        self.assertTrue(self.k.levels('nov').get('invalidated'))
        self.assertEqual(self.k.levels('nov')['novelty'], 'UNKNOWN')

    def test_f4_cyclic_or_same_program_lineage(self):
        same = self.fx.request(claim_id='same', kind='sealed_generation_evaluation', candidate='2' * 64,
                               transition={'index': 1, 'from_version': '1' * 64, 'to_version': '2' * 64},
                               baseline_program={'rounds': 1}, candidate_program={'rounds': 1})
        self.assertTrue(R.check_request(same))
        v1, v2, v3 = '1' * 64, '2' * 64, '3' * 64
        cyc = chain_requests(self.fx, 'cyc', 3, versions=[v1, v2, v3, v1])
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in cyc]
        self.k.create_claim('cyc', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes,
                            binding=R.binding_from_requests(cyc))
        self.rejects(self.k, 'cyc', 'improver', 'MULTIGEN_CONFIRMED', 'consecutive')
        # A chain whose links do not compare each successor against its predecessor is not a lineage.
        good = chain_requests(self.fx, 'unlinked', 3, seed=20)
        good[1] = dict(good[1], programs=dict(good[1]['programs'], baseline={'rounds': 9}))
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in good]
        self.k.create_claim('unlinked', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes,
                            binding=R.binding_from_requests(good))
        self.rejects(self.k, 'unlinked', 'improver', 'MULTIGEN_CONFIRMED', 'consecutive')

    def test_f8_claim_statement_must_be_the_committed_one(self):
        request = self.fx.request()
        _, node = record_evaluation(self.k, self.fx, request, [self.run])
        with self.assertRaisesRegex(ValueError, 'committed before evaluation'):
            self.k.create_claim('claim-1', 'The solver generalises to every family and transfers to all domains.',
                                SignedFixture.SCOPE, [node], binding=R.binding_from_requests([request]))
        other_statement = self.fx.request(claim_id='claim-1', statement='a different claim text')
        self.k.create_claim('claim-1', 'a different claim text', SignedFixture.SCOPE, [node],
                            binding=R.binding_from_requests([other_statement]))
        self.rejects(self.k, 'claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN', 'different claim statement')

    def path4(self):
        task = GraphTask(task_id='p', n=4, edges=((0, 1), (1, 2), (2, 3)), family='path')
        return task, digest(task.model_dump(mode='json'))

    def bound(self, task, bundle_ref, lower, sha):
        w = self.k.record('witness_check', {'task_sha256': sha, 'value': lower}, parents=[self.run],
                          route='genesis.campaign', source_hash=SRC, verdict='VALID', verifier='dual-predicates')
        return self.k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': task.task_id,
                                             'task_sha256': sha, 'lower': lower, 'upper': lower, 'gap': 0,
                                             'lower_evidence': w, 'certificate_bundle': bundle_ref},
                             parents=[w], route='genesis.verification.sat', source_hash=SRC, verdict='VALID')

    def test_f5_false_trivial_bound_is_replayed_and_rejected(self):
        k5 = GraphTask(task_id='k5', n=5, edges=tuple((i, j) for i in range(5) for j in range(i + 1, 5)), family='k')
        sha = digest(k5.model_dump(mode='json'))
        witness = ((0, 1), (0, 2), (0, 3), (0, 4))  # a star: valid, 4 edges (the true optimum is 6)
        b, blobs = build(k5, {'lower': 4, 'witness': witness, 'upper': 4,
                              'upper_certificate': {'method': 'HOST_EDGE_COUNT', 'upper': 4}})
        b['upper'] = {'method': 'HOST_EDGE_COUNT', 'value': 4, 'justification': 'forged'}
        b['status'] = 'OPTIMALITY_CHECKED'
        ref = persist(self.store, b, blobs)
        self.k.create_claim('k5', 'the optimum for host k5 is 4', 'host k5', [self.bound(k5, ref, 4, sha)],
                            problem={'task_sha256': sha, 'value': 4})
        self.rejects(self.k, 'k5', 'math', 'OPTIMALITY_CHECKED', 'does not replay')

    def test_f9_certificate_for_another_problem(self):
        task, sha = self.path4()
        b, blobs = build(task, {'lower': 3, 'witness': task.edges, 'upper': 3,
                                'upper_certificate': {'method': 'HOST_EDGE_COUNT', 'upper': 3}})
        ref = persist(self.store, b, blobs)
        k6 = GraphTask(task_id='k6', n=6, edges=tuple((i, j) for i in range(6) for j in range(i + 1, 6)), family='k')
        node = self.bound(task, ref, 3, sha)
        self.k.create_claim('k6', 'the optimum for host k6 is 3', 'host k6', [node],
                            problem={'task_sha256': digest(k6.model_dump(mode='json')), 'value': 3})
        self.rejects(self.k, 'k6', 'math', 'OPTIMALITY_CHECKED', 'different problem')
        self.k.create_claim('p', 'the optimum for host p is 3', 'host p', [node], problem={'task_sha256': sha, 'value': 3})
        self.k.promote('p', 'math', 'OPTIMALITY_CHECKED')  # the honest claim on the certified problem passes

    def test_f6_index_and_history_and_phase_are_not_taken_from_mutable_records(self):
        w = self.k.record('witness_check', {'value': 7}, parents=[self.run], route='genesis.campaign',
                          source_hash=SRC, verdict='VALID')
        self.k.create_claim('forged', 'host H has a valid subgraph with 7 edges', 'host H', [w])
        fake = {'claim': 'forged', 'axis': 'utility', 'level': 'CONFIRMED_TRANSFER', 'dependencies': [],
                'effects': [], 'evidence_used': [], 'evaluations': [], 'registry': 'external-board',
                'revocation_context': '0' * 64, 'at': '2026-10-10T00:00:00+00:00'}
        self.store.save('promotion', 'f' * 64, fake)            # not content-addressed: ignored entirely
        self.store.save('promotion', digest(fake), fake)        # content-addressed: history only, never effective
        self.assertEqual(self.k.levels('forged')['utility'], 'NOT_TESTED')
        self.store.set_state('campaign_id', 'campaign-1')
        self.store.set_state('phase', 'RELEASED')
        build_index(self.store, self.d / 'i.sqlite3')
        db = sqlite3.connect(self.d / 'i.sqlite3')
        evidence = db.execute("SELECT claim_id, axis, status FROM evidence WHERE claim_id='forged'").fetchall()
        status = db.execute('SELECT status FROM campaigns').fetchone()[0]
        db.close()
        self.assertNotIn(('forged', 'utility', 'CONFIRMED_TRANSFER'), evidence)
        self.assertTrue(status.startswith('UNVERIFIED'), status)


class F10SharedAcceptance(Base):
    def test_revoked_source_and_wrong_role_rejected_by_the_shared_acceptor(self):
        from genesis.eligibility import REVOKED_SOURCES
        from genesis.kernel.phases import PhaseError, _open
        fx = SignedFixture(self.tmp.name)
        request = fx.request()
        request['source_hash'] = next(iter(REVOKED_SOURCES))
        anchor = fx.anchor(request)
        payload, problems = R.accept_receipt(fx.receipt(request, anchor), 'sealed_evaluation', fx.registry['pins'])
        self.assertIsNone(payload); self.assertIn('revoked source', ' '.join(problems))
        repro = fx.request(kind='external_reproduction')
        a = fx.anchor(repro)
        custodian_signed = fx.receipt(repro, a, role='custodian')
        payload, problems = R.accept_receipt(custodian_signed, 'external_reproduction', fx.registry['pins'])
        self.assertIsNone(payload); self.assertIn('replicator_key', ' '.join(problems))
        with Store(self.d / 'phase') as s:
            s.save('frozen_request', digest(repro), repro)
            s.set_state('frozen_request_hash', digest(repro))
            with self.assertRaises(PhaseError):
                _open(s, 'SEALED_RUNNING', custodian_signed, fx.registry['pins'])
            self.assertEqual(_open(s, 'SEALED_RUNNING', fx.receipt(repro, a, role='replicator'),
                                   fx.registry['pins'])['evidence_kind'], 'external_reproduction')


if __name__ == '__main__':
    unittest.main()
