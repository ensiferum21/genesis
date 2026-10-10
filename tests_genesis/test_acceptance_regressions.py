"""Regression tests for the reviewer's blocking defects R-01 and R-02 (roadmap §3.1-3.2).

R-01 acceptance: the exact reproduced attacks fail; an authentic matching receipt
succeeds; signature tampering, wrong keys, wrong role, wrong candidate, wrong
claim, wrong panel, duplicate generation, missing raw evidence and non-supportive
analysis all fail closed.

R-02 acceptance lives in test_export_revocation.py.

Fixture keys prove protocol behaviour only, not independent custody.
"""
import tempfile
import unittest

from genesis.common import digest
from genesis.kernel import receipts as R
from genesis.kernel.evidence import FLOOR, EvidenceKernel, PromotionRejected
from genesis.store import Store
from tests_genesis.signed_fixtures import SignedFixture, record_evaluation

SRC = 'c' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name + '/store'); self.addCleanup(self.store.close)
        self.fx = SignedFixture(self.tmp.name)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash=SRC, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])

    def claim(self, claim_id, nodes, requests, statement='candidate beats baseline'):
        self.k.create_claim(claim_id, statement, 'c4_host_v2 sealed panel', nodes,
                            binding=R.binding_from_requests(requests))

    def rejects(self, claim_id, fragment, axis='utility', level='CONFIRMED_SAME_DOMAIN'):
        with self.assertRaises(PromotionRejected) as ctx:
            self.k.promote(claim_id, axis, level)
        joined = ' | '.join(ctx.exception.args[0])
        self.assertIn(fragment, joined)
        self.assertEqual(self.k.levels(claim_id)[axis], FLOOR[axis])
        return joined

    def single(self, claim_id='claim-1', **receipt_kw):
        request = self.fx.request(claim_id=claim_id)
        _, node = record_evaluation(self.k, self.fx, request, [self.run], **receipt_kw)
        return node, request


class ReproducedAttacks(Base):
    def test_r01a_unrelated_auditor_signed_failed_note_cannot_confirm(self):
        note = self.fx.sign({'campaign': 'some-other-campaign', 'result': 'FAILED', 'note': 'audit memo'}, 'auditor')
        request = self.fx.request()
        anchor = self.fx.anchor(request)
        a = self.k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash=SRC)
        # B13 wrapper shape: role named by the payload, unsigned SUPPORTED verdict on the node.
        b13 = self.k.record('sealed_evaluation', {'signing_role': 'auditor_key', 'signed_envelope': note},
                            parents=[self.run, a], route='genesis.custodian.evaluate', source_hash=SRC,
                            verdict='SUPPORTED', verifier='dual-predicates')
        self.claim('claim-1', [b13], [request])
        self.rejects('claim-1', 'not a bare signed-evidence wrapper')
        # Current wrapper shape: the trusted role map demands the custodian key.
        wrapped = self.k.record_signed('sealed_evaluation', note, parents=[self.run, a],
                                       route='genesis.custodian.evaluate', source_hash=SRC)
        self.k.create_claim('claim-1b', 'x', 's', [wrapped], binding=R.binding_from_requests([request]))
        self.rejects('claim-1b', 'signature does not verify under the pinned custodian_key')

    def test_r01b_one_envelope_in_three_wrapper_nodes_is_one_generation(self):
        request = self.fx.request(claim_id='multigen', kind='sealed_generation_evaluation', candidate='2' * 64,
                                  transition={'index': 1, 'from_version': '1' * 64, 'to_version': '2' * 64})
        anchor = self.fx.anchor(request)
        receipt = self.fx.receipt(request, anchor)
        a = self.k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash=SRC)
        extra = [self.k.record('note', {'i': i}, route='genesis.campaign', source_hash=SRC) for i in range(3)]
        nodes = [self.k.record_signed('sealed_generation_evaluation', receipt, parents=[self.run, a, extra[i]],
                                      route='genesis.custodian.evaluate', source_hash=SRC) for i in range(3)]
        self.assertEqual(len(set(nodes)), 3)  # three differently identified wrapper nodes
        self.claim('multigen', nodes, [request])
        self.rejects('multigen', 'found 1', axis='improver', level='MULTIGEN_CONFIRMED')


class AuthenticAndForged(Base):
    def test_authentic_matching_receipt_succeeds(self):
        node, request = self.single()
        self.claim('claim-1', [node], [request])
        decision = self.k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertEqual(self.k.levels('claim-1')['utility'], 'CONFIRMED_SAME_DOMAIN')
        self.assertIn(node, decision['evidence_used'])

    def test_signature_tampering(self):
        request = self.fx.request()
        anchor = self.fx.anchor(request)
        receipt = self.fx.receipt(request, anchor, wins=5, losses=30, ties=5)
        receipt['payload'] = self.fx.receipt_payload(request, anchor, wins=30, losses=5, ties=5)  # swap content
        _, node = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor, receipt=receipt)
        self.claim('claim-1', [node], [request])
        self.rejects('claim-1', 'signature does not verify')

    def test_wrong_key_and_wrong_role(self):
        for i, role in enumerate(('outsider', 'auditor', 'prereg', 'release', 'replicator')):
            request = self.fx.request(claim_id=f'role-{i}')
            _, node = record_evaluation(self.k, self.fx, request, [self.run], role=role)
            self.claim(f'role-{i}', [node], [request])
            self.rejects(f'role-{i}', 'signature does not verify under the pinned custodian_key')

    def test_anchor_signed_by_the_wrong_role_is_not_an_anchor(self):
        request = self.fx.request()
        anchor = self.fx.anchor(request, role='custodian')
        _, node = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor)
        self.claim('claim-1', [node], [request])
        self.rejects('claim-1', 'no verified preregistration anchor')

    def test_wrong_candidate(self):
        node, request = self.single(candidate_version='f' * 64)
        self.claim('claim-1', [node], [request])
        self.rejects('claim-1', 'different candidate version')

    def test_wrong_claim_and_replay_under_another_claim(self):
        node, request = self.single(claim_id='claim-A')
        self.claim('claim-A', [node], [request])
        self.k.promote('claim-A', 'utility', 'CONFIRMED_SAME_DOMAIN')
        other = self.fx.request(claim_id='claim-B')
        self.k.create_claim('claim-B', 'another claim', 's', [node], binding=R.binding_from_requests([other]))
        joined = self.rejects('claim-B', 'different claim')
        self.assertIn('not for a preregistered request', joined)

    def test_wrong_panel(self):
        node, request = self.single(panel_commitment='7' * 64)
        self.claim('claim-1', [node], [request])
        self.rejects('claim-1', 'preregistered panel commitment')

    def test_replay_as_another_kind_or_domain(self):
        request = self.fx.request()
        anchor = self.fx.anchor(request)
        receipt = self.fx.receipt(request, anchor)
        a = self.k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash=SRC)
        as_transfer = self.k.record_signed('sealed_transfer_evaluation', receipt, parents=[self.run, a],
                                           route='genesis.custodian.evaluate', source_hash=SRC)
        transfer_request = self.fx.request(kind='sealed_transfer_evaluation', domain='triangle_free_host_v1',
                                           transfer='c4_host_v2')
        self.k.create_claim('claim-1', 'x', 's', [as_transfer], binding=R.binding_from_requests([transfer_request]))
        self.rejects('claim-1', "evidence kind 'sealed_evaluation'", level='CONFIRMED_TRANSFER')

    def test_duplicate_generation_transitions(self):
        v = ['1' * 64, '2' * 64, '3' * 64, '4' * 64]
        reqs = [self.fx.request(claim_id='mg', kind='sealed_generation_evaluation', candidate=v[i + 1], seed=i,
                                transition={'index': i + 1, 'from_version': v[i], 'to_version': v[i + 1]})
                for i in range(3)]
        # A second, different evaluation of transition 2 makes the chain ambiguous.
        dup = self.fx.request(claim_id='mg', kind='sealed_generation_evaluation', candidate=v[2], seed=99,
                              transition={'index': 2, 'from_version': v[1], 'to_version': v[2]})
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in reqs + [dup]]
        self.claim('mg', nodes, reqs + [dup])
        self.rejects('mg', 'consecutive', axis='improver', level='MULTIGEN_CONFIRMED')
        # Out-of-order indices do not form a chain either.
        bad = [self.fx.request(claim_id='mg2', kind='sealed_generation_evaluation', candidate=v[i + 1], seed=10 + i,
                               transition={'index': [1, 3, 2][i], 'from_version': v[i], 'to_version': v[i + 1]})
               for i in range(3)]
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in bad]
        self.claim('mg2', nodes, bad)
        self.rejects('mg2', 'consecutive', axis='improver', level='MULTIGEN_CONFIRMED')

    def test_missing_raw_evidence(self):
        node, request = self.single(raw_evidence_complete=False, outcome='SUPPORTED')
        self.claim('claim-1', [node], [request])
        self.rejects('claim-1', 'contradicts the signed analysis')
        request2 = self.fx.request(claim_id='claim-2')
        anchor = self.fx.anchor(request2)
        p = self.fx.receipt_payload(request2, anchor, raw_evidence_complete=False)
        p['outcome'] = R.derive_outcome(p)
        self.assertEqual(p['outcome'], 'INVALID')
        _, node2 = record_evaluation(self.k, self.fx, request2, [self.run], anchor=anchor,
                                     receipt=self.fx.sign(p, 'custodian'))
        self.claim('claim-2', [node2], [request2])
        self.rejects('claim-2', 'reports INVALID')

    def test_non_supportive_analysis(self):
        for i, (w, l, t, fragment) in enumerate(((5, 30, 5, 'reports NOT_SUPPORTED'),
                                                (12, 8, 20, 'reports NOT_SUPPORTED'))):
            node, request = self.single(claim_id=f'neg-{i}', wins=w, losses=l, ties=t)
            self.claim(f'neg-{i}', [node], [request])
            self.rejects(f'neg-{i}', fragment)
        node, request = self.single(claim_id='lie', wins=5, losses=30, ties=5, outcome='SUPPORTED')
        self.claim('lie', [node], [request])
        self.rejects('lie', 'contradicts the signed analysis')
        node, request = self.single(claim_id='failures', execution_failures=2, outcome='INCONCLUSIVE')
        self.claim('failures', [node], [request])
        self.rejects('failures', 'reports INCONCLUSIVE')

    def test_negative_receipt_is_not_outvoted_by_a_positive_one(self):
        good, request = self.single(claim_id='mixed')
        anchor2 = self.fx.anchor(request, panel='6' * 64)
        bad = self.fx.receipt(request, anchor2, wins=5, losses=30, ties=5, raw='5' * 64)
        _, node2 = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor2, receipt=bad)
        self.claim('mixed', [good, node2], [request])
        self.rejects('mixed', 'reports NOT_SUPPORTED')

    def test_panel_reuse_across_evaluations(self):
        request = self.fx.request(claim_id='reuse')
        anchor = self.fx.anchor(request)
        r1 = self.fx.receipt(request, anchor, raw='1' * 64)
        r2 = self.fx.receipt(request, anchor, raw='2' * 64)
        n1 = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor, receipt=r1)[1]
        n2 = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor, receipt=r2)[1]
        self.claim('reuse', [n1, n2], [request])
        self.rejects('reuse', 'panel commitment supports more than one evaluation')

    def test_schema_strictness(self):
        cases = {'extra': {'note': 'x'}, 'schema': {'schema': 'genesis-evaluation-receipt-v1'},
                 'bool-count': {'wins': True}, 'domain': {'domain_contract_hash': '0' * 64}}
        for i, (name, override) in enumerate(cases.items()):
            request = self.fx.request(claim_id=f'schema-{i}')
            anchor = self.fx.anchor(request)
            p = self.fx.receipt_payload(request, anchor)
            p.update(override)
            _, node = record_evaluation(self.k, self.fx, request, [self.run], anchor=anchor,
                                        receipt=self.fx.sign(p, 'custodian'))
            self.claim(f'schema-{i}', [node], [request])
            self.rejects(f'schema-{i}', 'rejected')
        # A wrapper with anything beside the envelope (e.g. an unsigned verdict) is refused.
        request = self.fx.request(claim_id='wrapper')
        anchor = self.fx.anchor(request)
        a = self.k.record_signed('preregistration_anchor', anchor, route='genesis.custodian.evaluate', source_hash=SRC)
        node = self.k.record('sealed_evaluation', {**R.wrap(self.fx.receipt(request, anchor)), 'verdict': 'SUPPORTED'},
                             parents=[self.run, a], route='genesis.custodian.evaluate', source_hash=SRC,
                             verdict='SUPPORTED')
        self.claim('wrapper', [node], [request])
        self.rejects('wrapper', 'bare signed-evidence wrapper')


class RevocationAndTrust(Base):
    def test_revoked_key_and_revoked_evaluation(self):
        node, request = self.single()
        self.claim('claim-1', [node], [request])
        self.k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.k.revoke_key(self.fx.keys['custodian'][1], 'custodian key reported compromised', 'security')
        self.assertEqual(self.k.levels('claim-1')['utility'], 'NOT_TESTED')
        self.assertEqual(self.k.recorded_levels('claim-1')['utility'], 'CONFIRMED_SAME_DOMAIN')  # history kept

        node2, request2 = self.single(claim_id='claim-2', raw='9' * 64)
        k2 = EvidenceKernel.with_fixture_registry(self.store, {'pins': dict(self.fx.registry['pins'],
                                                                            custodian_key=self.fx.keys['outsider'][1])})
        self.assertEqual(k2.levels('claim-1')['utility'], 'NOT_TESTED')  # rotated pin: old receipts stop counting
        receipt_payload = R.unwrap_unverified(self.k.payload(node2))
        self.k.revoke_evaluation(R.evaluation_identity(receipt_payload), 'panel exposed during debugging', 'custodian')
        self.claim('claim-2', [node2], [request2])
        self.assertTrue(self.k.levels('claim-2').get('invalidated'))

    def test_fixture_grants_do_not_survive_a_production_kernel(self):
        node, request = self.single()
        self.claim('claim-1', [node], [request])
        self.assertEqual(self.k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')['registry'], 'FIXTURE')
        production = EvidenceKernel(self.store)  # no externally controlled trust root here
        self.assertEqual(production.levels('claim-1')['utility'], 'NOT_TESTED')
        production._load_roles = lambda: (self.fx.registry, [])  # the B13 test hook no longer exists
        self.assertEqual(production.levels('claim-1')['utility'], 'NOT_TESTED')

    def test_cross_domain_and_transfer_rules(self):
        reqs = [self.fx.request(claim_id='xd', kind='sealed_improver_evaluation', seed=i) for i in range(2)]
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in reqs]
        self.claim('xd', nodes, reqs)
        self.rejects('xd', 'at least two domains', axis='improver', level='CROSS_DOMAIN_CONFIRMED')
        reqs = [self.fx.request(claim_id='xd2', kind='sealed_improver_evaluation', seed=5),
                self.fx.request(claim_id='xd2', kind='sealed_improver_evaluation', seed=6,
                                domain='triangle_free_host_v1')]
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in reqs]
        self.claim('xd2', nodes, reqs)
        self.k.promote('xd2', 'improver', 'CROSS_DOMAIN_CONFIRMED')
        with self.assertRaises(ValueError):
            R.binding_from_requests([self.fx.request(kind='sealed_transfer_evaluation', transfer='c4_host_v2')])

    def test_priority_adjudication(self):
        statement = 'construction X is new for hosts of family F'
        base = {'schema': R.PRIORITY_ADJUDICATION, 'evidence_kind': 'external_priority_adjudication',
                'claim_id': 'nov', 'statement_hash': digest(statement), 'scope': 'family F only',
                'reviewer_id': 'FIXTURE_REVIEWER', 'search_record_root': '3' * 64,
                'decided_at': '2026-10-10T00:00:00+00:00', 'outcome': 'NOVEL_IN_SCOPE'}
        for cid, override, role, fragment in (
                ('nov', {}, 'priority_reviewer', None),
                ('nov2', {'claim_id': 'nov2', 'statement_hash': digest('something else')}, 'priority_reviewer',
                 'different claim, statement or scope'),
                ('nov3', {'claim_id': 'nov3', 'outcome': 'PRIOR_ART_FOUND'}, 'priority_reviewer', 'PRIOR_ART_FOUND'),
                ('nov4', {'claim_id': 'nov4'}, 'auditor', 'signature does not verify')):
            node = self.k.record_signed('external_priority_adjudication', self.fx.sign({**base, **override}, role),
                                        parents=[self.run], route='genesis.custodian.evaluate', source_hash=SRC)
            self.k.create_claim(cid, statement, 'family F only', [node])
            if fragment is None:
                self.k.promote(cid, 'novelty', 'EXTERNALLY_CHECKED_NOVEL')
            else:
                self.rejects(cid, fragment, axis='novelty', level='EXTERNALLY_CHECKED_NOVEL')


class SharedSemantics(unittest.TestCase):
    """Kernel, phases and preflight agree because they call the same validator."""

    def test_entry_points_use_kernel_receipts(self):
        import inspect
        from genesis import custodian
        from genesis.kernel import phases
        for module, names in ((phases, ('check_receipt', 'check_anchor', 'anchor_mismatches')),
                              (custodian, ('open_signed', 'anchor_mismatches', 'derive_outcome', 'check_receipt',
                                           'check_anchor'))):
            src = inspect.getsource(module)
            for name in names:
                self.assertIn(f'R.{name}(', src, (module.__name__, name))

    def test_derive_outcome_matches_signed_counts(self):
        fx = SignedFixture(tempfile.mkdtemp())
        request = fx.request()
        anchor = fx.anchor(request)
        self.assertEqual(fx.receipt_payload(request, anchor)['outcome'], 'SUPPORTED')
        self.assertEqual(fx.receipt_payload(request, anchor, wins=10, losses=10, ties=20)['outcome'], 'NOT_SUPPORTED')
        p = fx.receipt_payload(request, anchor)
        self.assertEqual(R.check_receipt(p, 'sealed_evaluation'), [])
        self.assertTrue(R.check_receipt(dict(p, paired_p=0.5), 'sealed_evaluation'))


if __name__ == '__main__':
    unittest.main()
