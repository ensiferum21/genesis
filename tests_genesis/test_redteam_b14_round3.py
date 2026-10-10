"""Regression tests for the third internal red-team pass on B14 (audit/redteam_b14_round3/).

F1 candidate not bound to the campaign / one claim registered repeatedly, F2 transfer
domain from one config entity, F3/F4 true certificates or witnesses under false
statements, F5 anchor revocation, F6 campaign binding by a mutable label, F7 preflight
and phase verification ignoring revocations, F8 wording vocabulary. F9 (stale world-loop
summary) is in tests_certificates/test_certificate_custody.py. Fixture keys only.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from genesis.common import digest
from genesis.kernel import receipts as R
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.kernel.phases import advance, verified_phase
from genesis.kernel.wording import lint
from genesis.models import GraphTask, SolverProgram
from genesis.store import Store
from tests_genesis.signed_fixtures import (SignedFixture, fixture_campaign, math_claim, path4, record_evaluation,
                                          witness_payload)

SRC = 'c' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.fx = SignedFixture(self.tmp.name)

    def rejects(self, k, claim, axis, level, fragment):
        with self.assertRaises(PromotionRejected) as ctx:
            k.promote(claim, axis, level)
        self.assertIn(fragment, ' | '.join(ctx.exception.args[0]))


class F1CandidateBinding(Base):
    def test_claim_and_candidate_slots(self):
        a = self.fx.request(claim_id='claim-1')
        other_candidate = self.fx.request(claim_id='claim-1',
                                          candidate_program=SolverProgram(rounds=7).model_dump(mode='json'))
        renamed = self.fx.request(claim_id='claim-1 (v2)')
        self.assertTrue(set(R.registration_slots(a)) & set(R.registration_slots(other_candidate)))  # claim slot
        self.assertTrue(set(R.registration_slots(a)) & set(R.registration_slots(renamed)))  # candidate slot

    def test_one_label_cannot_cover_two_programs(self):
        with Store(self.d / 's') as s:
            self.fx.bind_store(s)
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            sealed = self.fx.request(claim_id='claim-1')
            repro = self.fx.request(claim_id='claim-1', kind='external_reproduction', seed=2,
                                    candidate_program=SolverProgram(rounds=7).model_dump(mode='json'))
            with self.assertRaisesRegex(ValueError, 'different candidates'):
                R.binding_from_requests([sealed, repro])
            nodes = [record_evaluation(k, self.fx, r, [run], role=role)[1]
                     for r, role in ((sealed, 'custodian'), (repro, 'replicator'))]
            binding = R.binding_from_requests([sealed])
            binding = dict(binding, request_hashes=sorted({digest(sealed), digest(repro)}))
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes, binding=binding)
            k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
            self.rejects(k, 'claim-1', 'replication', 'EXTERNAL_REPRODUCTION', 'different candidate version or program')


class F2ConfiguredDomain(Base):
    def test_campaign_refuses_an_edited_config_file(self):
        from genesis.campaign import Campaign
        from genesis.models import Config
        root = Campaign.initialize(self.d / 'c', Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2,
                                                        research_trials=8))
        cfg = (root / 'resolved_config.json').read_text().replace('c4_host_v2', 'triangle_free_host_v1')
        (root / 'resolved_config.json').write_text(cfg)
        with self.assertRaisesRegex(RuntimeError, 'differs from the configuration'):
            Campaign(root)

    def test_custodian_reads_the_domain_research_actually_used(self):
        from genesis.custodian import check_request_against_export
        facts = {'campaign_id': 'a' * 64, 'source_hash': 'c' * 64, 'domain': 'c4_host_v2', 'config_entities': 1,
                 'identity_rewritten': False, 'phase': 'CANDIDATE_FROZEN', 'latest_program': None,
                 'candidate_versions': {}, 'strongest_baseline': 'multistart',
                 'research_domains': ['triangle_free_host_v1']}
        problems = check_request_against_export(self.fx.request(), facts)
        self.assertIn('research ran on a domain other than its configuration', ' '.join(problems))


class F3F4MathStatements(Base):
    def test_math_claims_state_exactly_their_stored_problem(self):
        with Store(self.d / 's') as s:
            k = EvidenceKernel(s)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            w = k.record('witness_check', witness_payload(s), parents=[run], route='genesis.campaign', source_hash=SRC,
                         verdict='VALID')
            k.create_claim('free', 'K63 has a C4-free subgraph with 1000 edges', 'K63', [w])  # no problem
            self.rejects(k, 'free', 'math', 'WITNESS_VALID', 'must name its exact problem')
            sha = s.put(path4().model_dump(mode='json'))
            with self.assertRaisesRegex(ValueError, 'states exactly its problem'):
                k.create_claim('lie', 'path4 has a valid subgraph with 30 edges', 'h', [w],
                               problem={'task_sha256': sha, 'value': 3, 'claim': 'lower_bound'})
            math_claim(k, 'value30', [w], value=30)
            self.rejects(k, 'value30', 'math', 'WITNESS_VALID', 'different problem or value')
            math_claim(k, 'lb', [w])
            k.promote('lb', 'math', 'WITNESS_VALID')
            self.rejects(k, 'lb', 'math', 'OPTIMALITY_CHECKED', 'not of a lower bound')

    def test_statement_names_the_stored_domain(self):
        with Store(self.d / 's') as s:
            k = EvidenceKernel(s)
            k6 = GraphTask(task_id='k6-c4', n=6, edges=tuple((i, j) for i in range(6) for j in range(i + 1, 6)),
                           family='k', domain='triangle_free_host_v1')
            problem = {'task_sha256': s.put(k6.model_dump(mode='json')), 'value': 9, 'claim': 'optimum'}
            self.assertTrue(k.math_statement(problem).startswith('the optimum for triangle_free_host_v1 host k6-c4'))


class F5AnchorRevocation(Base):
    def test_revoking_an_anchor_follows_the_envelope(self):
        first = self.d / 'first'
        with Store(first) as s:
            self.fx.bind_store(s)
            request = self.fx.request()
            anchor = self.fx.anchor(request); receipt = self.fx.receipt(request, anchor)
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run = k.record('execution_receipt', {'store': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            a_node, _ = record_evaluation(k, self.fx, request, [run], anchor=anchor, receipt=receipt)
        second = self.d / 'second'
        shutil.copytree(first, second)
        with Store(first) as s:
            k = EvidenceKernel(s)
            k.revoke(a_node, 'registration voided', 'custodian')
            records = k.revocations()
        self.assertIn('evaluation', {r['target_type'] for r in records})
        with Store(second) as s:
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run2 = k.record('execution_receipt', {'store': 2}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            _, node2 = record_evaluation(k, self.fx, request, [run2], anchor=anchor, receipt=receipt)
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node2],
                           binding=R.binding_from_requests([request]))
            k.apply_revocations(records)
            self.assertEqual(k.levels('claim-1')['utility'], 'NOT_TESTED')


class F6CampaignHistory(Base):
    def test_relabelled_store_cannot_carry_another_campaigns_claim(self):
        with Store(self.d / 'b') as s:
            s.set_state('campaign_id', 'b' * 64); s.set_state('source_hash', 'c' * 64)
            self.fx.bind_store(s)  # rewrites campaign_id to 'a'*64: identity rewritten
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            request = self.fx.request()
            _, node = record_evaluation(k, self.fx, request, [run])
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node],
                           binding=R.binding_from_requests([request]))
            self.rejects(k, 'claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN', 'rewritten')


class F7Revocations(Base):
    def test_preflight_applies_a_revocation_feed(self):
        from genesis.custodian import release_preflight
        request = self.fx.request(task_count=40)
        anchor = self.fx.anchor(request); receipt = self.fx.receipt(request, anchor)
        audit = self.fx.sign({'request_hash': digest(request), 'receipt_hash': digest(receipt), 'status': 'PASS',
                              'open_critical': 0, 'independent_operation_verified': True, 'raw_replay_verified': True,
                              'formal_replay_verified': True}, 'auditor')
        reg = dict(self.fx.registry, trust_root='fixture', root_key_sha256='0' * 64)
        with mock.patch('genesis.custodian.load_role_registry', return_value=(reg, [])), \
                mock.patch('genesis.custodian.validate_request', return_value=None):
            ok = release_preflight(request, anchor, receipt, audit)
            self.assertEqual(ok['status'], 'EXTERNAL_RELEASE_REVIEW_READY', ok['reasons'])
            feed = [{'target_type': 'evaluation', 'artifact': R.evaluation_identity(receipt['payload']),
                     'reason': 'receipt revoked', 'actor': 'auditor', 'at': '2026-10-10T00:00:00+00:00'}]
            self.assertEqual(release_preflight(request, anchor, receipt, audit, revocations=feed)['status'], 'BLOCKED')
            keys = [{'target_type': 'key', 'artifact': self.fx.keys['custodian'][1], 'reason': 'compromised',
                     'actor': 'security', 'at': '2026-10-10T00:00:00+00:00'}]
            self.assertEqual(release_preflight(request, anchor, receipt, audit, revocations=keys)['status'], 'BLOCKED')

    def test_verified_phase_reports_a_revoked_judged_receipt(self):
        root, request = fixture_campaign(self.d, self.fx)
        with mock.patch('genesis.kernel.phases.load_role_registry', return_value=(self.fx.registry, [])), \
                Store(root) as s:
            for p in ('VALIDATED_CONFIG', 'DEV_RUNNING', 'CANDIDATE_FROZEN'):
                advance(s, p)
            anchor = self.fx.anchor(request); receipt = self.fx.receipt(request, anchor)
            for target, env in (('LEAK_SCAN_PASSED', anchor), ('SEALED_RUNNING', receipt), ('JUDGED', receipt)):
                advance(s, target, envelope=env)
            self.assertTrue(verified_phase(s)['consistent'])
            EvidenceKernel(s).revoke_evaluation(R.evaluation_identity(receipt['payload']), 'raw evidence lost', 'auditor')
            v = verified_phase(s)
        self.assertEqual(v['phase'], 'INVALIDATED'); self.assertFalse(v['consistent'])


class F8Vocabulary(unittest.TestCase):
    def test_stems_and_phrasings(self):
        floor = {'math': 'WITNESS_VALID'}
        for s in ('K6 has an optimal construction.', 'It is provably optimal.', 'The optimum is 9.',
                  'The maximum C4-free subgraph has 9 edges.', 'The gain transferred to K3 hosts.',
                  'The method is generalizable.', 'This confirms the effect.', 'The exchange step drives the gain.',
                  'A previously unknown construction.', 'A first ever result.', 'The system improves itself.'):
            self.assertTrue(lint(s, floor), s)
        for s in ('The CONFIRM panel was sealed.', 'The maximum CPU budget was 60 s.',
                  'Utility measurements are development-only; no improver, transfer or novelty claim is made.'):
            self.assertEqual(lint(s, floor), [], s)


if __name__ == '__main__':
    unittest.main()
