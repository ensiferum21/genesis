"""Evidence kernel: illegal promotions are rejected, revocation propagates, trust is anchored.

Spec §38 'Evidence wording' row: attempt illegal status/claim promotions; the
kernel must reject every fixture.
"""
import base64
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.kernel.receipts import binding_from_requests
from tests_genesis.signed_fixtures import SignedFixture, record_evaluation
from genesis.kernel.wording import lint, require_clean
from genesis.store import Store

SRC = 'a' * 64
ANCHOR_IMPL = 'f' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name); self.addCleanup(self.store.close)
        self.k = EvidenceKernel(self.store, anchors={ANCHOR_IMPL: 'pinned fixture checker'})
        self.k.register_verifier('dual-predicates', ANCHOR_IMPL)
        self.k.register_verifier('exact-b', 'e' * 64)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash=SRC, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])

    def check(self, kind, parents, verifier='dual-predicates', verdict='VALID', payload=None, effects=(),
              route='genesis.campaign'):
        return self.k.record(kind, payload or {'kind': kind, 'parents': parents}, parents=parents, route=route,
                             source_hash=SRC, verdict=verdict, verifier=verifier, effects=effects)

    def rejects(self, claim, axis, level, fragment):
        with self.assertRaises(PromotionRejected) as ctx:
            self.k.promote(claim, axis, level)
        self.assertTrue(any(fragment in r for r in ctx.exception.args[0]), ctx.exception.args[0])


class MathPromotion(Base):
    def test_witness_valid_needs_a_passing_witness_check(self):
        self.k.create_claim('c1', 'value 7 witnessed', 'host H', [self.run])
        self.rejects('c1', 'math', 'WITNESS_VALID', 'witness_check')
        w = self.check('witness_check', [self.run])
        self.k.create_claim('c2', 'value 7 witnessed', 'host H', [w])
        self.k.promote('c2', 'math', 'WITNESS_VALID')
        self.assertEqual(self.k.levels('c2')['math'], 'WITNESS_VALID')

    def test_unchecked_proposal_taints_until_checked(self):
        self.k.create_claim('c', 'x', 's', [self.run])
        self.rejects('c', 'math', 'FINITE_CERTIFIED', 'speculative')

    def test_finite_certified_needs_two_independent_exact_checkers(self):
        a = self.check('exact_check', [self.run])
        self.k.create_claim('one', 'opt 7', 'H', [a])
        self.rejects('one', 'math', 'FINITE_CERTIFIED', 'independent exact checkers')
        b = self.check('exact_check', [self.run], verifier='exact-b')
        self.k.create_claim('two', 'opt 7', 'H', [a, b])
        self.k.promote('two', 'math', 'FINITE_CERTIFIED')

    def test_optimality_needs_gap_zero(self):
        bs = self.check('bound_state', [self.run], payload={'lower': 7, 'upper': 8, 'gap': 1})
        self.k.create_claim('c', 'opt', 'H', [bs])
        self.rejects('c', 'math', 'OPTIMALITY_CHECKED', 'gap 0')
        bs0 = self.check('bound_state', [self.run], payload={'lower': 8, 'upper': 8, 'gap': 0})
        self.k.create_claim('d', 'opt', 'H', [bs0])
        self.k.promote('d', 'math', 'OPTIMALITY_CHECKED')

    def test_approximate_and_self_judged_dependencies_rejected(self):
        a = self.check('exact_check', [self.run], effects=['APPROXIMATE'])
        b = self.check('exact_check', [self.run], verifier='exact-b')
        self.k.create_claim('approx', 'opt', 'H', [a, b])
        self.rejects('approx', 'math', 'FINITE_CERTIFIED', 'approximate')
        w = self.check('witness_check', [self.run], effects=['SELF_JUDGED'])
        self.k.create_claim('self', 'w', 'H', [w])
        self.rejects('self', 'math', 'WITNESS_VALID', 'self-judged')

    def test_failed_checker_receipt_never_licenses(self):
        w = self.check('witness_check', [self.run], verdict='CHECKER_ERROR')
        self.k.create_claim('c', 'w', 'H', [w])
        self.rejects('c', 'math', 'WITNESS_VALID', 'witness_check')

    def test_negative_states_are_not_promotion_targets(self):
        w = self.check('witness_check', [self.run])
        self.k.create_claim('c', 'w', 'H', [w])
        self.rejects('c', 'math', 'UNSETTLED', 'not a promotable')

    def test_unknown_effect_names_are_refused(self):
        with self.assertRaises(ValueError):
            self.k.record('note', {}, route='genesis.campaign', source_hash=SRC, effects=['TOUCHED_SEALED'])


class Confirmation(Base):
    """Confirmation levels need receipts signed by the role trusted code assigns (kernel.receipts)."""

    def setUp(self):
        super().setUp()
        self.fx = SignedFixture(self.tmp.name)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry,
                                                      anchors={ANCHOR_IMPL: 'pinned fixture checker'})

    def sealed(self, request=None, route='genesis.custodian.evaluate', effects=(), **kw):
        request = request or self.fx.request()
        _, node = record_evaluation(self.k, self.fx, request, [self.run], route=route, **kw)
        return node, request

    def test_no_external_role_registry_means_no_confirmation(self):
        node, request = self.sealed()
        production = EvidenceKernel(self.store)  # trust root absent / research account is root here
        production.create_claim('claim-1', 'better solver', 'graph wedge', [node],
                                binding=binding_from_requests([request]))
        with self.assertRaises(PromotionRejected) as ctx:
            production.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertTrue(any('role registry' in r for r in ctx.exception.args[0]))

    def test_externally_signed_eligible_evaluation_confirms(self):
        node, request = self.sealed()
        self.k.create_claim('claim-1', 'better solver', 'graph wedge', [node], binding=binding_from_requests([request]))
        decision = self.k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertEqual(decision['registry'], 'FIXTURE')
        self.assertEqual(len(decision['evaluations']), 1)

    def test_ineligible_route_revoked_source_and_unbound_claims_rejected(self):
        for name, route, fragment in (('route', 'genesis.campaign', 'ineligible'),
                                      ('legacy', 'legacy_batch42.sealed_benchmark', 'ineligible')):
            request = self.fx.request(claim_id=name)
            node, _ = self.sealed(request, route=route)
            self.k.create_claim(name, 'x', 's', [node], binding=binding_from_requests([request]))
            self.rejects(name, 'utility', 'CONFIRMED_SAME_DOMAIN', fragment)
        request = self.fx.request(claim_id='nobinding')
        node, _ = self.sealed(request)
        self.k.create_claim('nobinding', 'x', 's', [node])
        self.rejects('nobinding', 'utility', 'CONFIRMED_SAME_DOMAIN', 'bound to its preregistered')

    def test_contaminated_dependency_rejected(self):
        leak = self.k.record('note', {'leak': True}, route='genesis.campaign', source_hash=SRC,
                             effects=['TOUCHED_SEALED_SET'])
        request = self.fx.request(claim_id='leak')
        _, node = record_evaluation(self.k, self.fx, request, [self.run, leak])
        self.k.create_claim('leak', 'x', 's', [node], binding=binding_from_requests([request]))
        self.rejects('leak', 'utility', 'CONFIRMED_SAME_DOMAIN', 'contaminated')

    def test_multigeneration_needs_three_signed_generations_and_no_manual_rescue(self):
        versions = ['1' * 64, '2' * 64, '3' * 64, '4' * 64]
        requests = [self.fx.request(claim_id='multigen', kind='sealed_generation_evaluation', candidate=versions[i + 1],
                                    transition={'index': i + 1, 'from_version': versions[i],
                                                'to_version': versions[i + 1]}, seed=i)
                    for i in range(3)]
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in requests]
        binding = binding_from_requests(requests)
        self.k.create_claim('multigen', 'multigen', 's', nodes, binding=binding)
        self.k.promote('multigen', 'improver', 'MULTIGEN_CONFIRMED')
        manual = self.k.record('note', {'rescue': True}, route='genesis.campaign', source_hash=SRC,
                               effects=['MANUAL_INTERVENTION'])
        self.k.create_claim('rescued', 'multigen', 's', nodes + [manual], binding=binding)
        self.rejects('rescued', 'improver', 'MULTIGEN_CONFIRMED', 'manual intervention')
        self.k.create_claim('two', 'multigen', 's', nodes[:2], binding=binding_from_requests(requests[:2]))
        self.rejects('two', 'improver', 'MULTIGEN_CONFIRMED', 'needs 3 consecutive')


class Revocation(Base):
    def test_revoking_an_ancestor_invalidates_dependent_claims(self):
        w = self.check('witness_check', [self.run])
        self.k.create_claim('c', 'w', 'H', [w])
        self.k.promote('c', 'math', 'WITNESS_VALID')
        self.k.revoke(self.run, 'leak audit: lemma exposed a sealed target', 'auditor')
        levels = self.k.levels('c')
        self.assertTrue(levels['invalidated'])
        self.assertEqual(levels['math'], 'UNCHECKED')
        self.assertEqual(self.k.invalidated_claims()[0]['revoked_dependencies'], [self.run])
        self.rejects('c', 'math', 'WITNESS_VALID', 'revoked dependency')
        self.store.verify()  # derived state still matches the immutable event history


class TrustGraph(Base):
    def test_self_validating_generated_verifier_is_circular(self):
        receipt = self.k.record('verifier_test', {'suite': 'self'}, route='genesis.kernel', source_hash=SRC,
                                verdict='PASS', verifier='gen-v')
        self.k.register_verifier('gen-v', '1' * 64, validated_by=[receipt], generated=True)
        self.assertEqual(self.k.verifier_trust('gen-v'), 'CIRCULAR_JUSTIFICATION')
        w = self.check('witness_check', [self.run], verifier='gen-v')
        self.k.create_claim('c', 'w', 'H', [w])
        self.rejects('c', 'math', 'WITNESS_VALID', 'circularly justified')

    def test_mutual_validation_without_anchor_is_circular(self):
        r1 = self.k.record('verifier_test', {'by': 'v2'}, route='genesis.kernel', source_hash=SRC,
                           verdict='PASS', verifier='v2')
        r2 = self.k.record('verifier_test', {'by': 'v1'}, route='genesis.kernel', source_hash=SRC,
                           verdict='PASS', verifier='v1')
        self.k.register_verifier('v1', '2' * 64, validated_by=[r1])
        self.k.register_verifier('v2', '3' * 64, validated_by=[r2])
        self.assertEqual(self.k.verifier_trust('v1'), 'CIRCULAR_JUSTIFICATION')

    def test_validation_by_an_anchored_checker_is_anchored(self):
        r = self.k.record('verifier_test', {'by': 'dual'}, route='genesis.kernel', source_hash=SRC,
                          verdict='PASS', verifier='dual-predicates')
        self.k.register_verifier('new-v', '4' * 64, validated_by=[r], generated=True)
        self.assertEqual(self.k.verifier_trust('new-v'), 'ANCHORED')
        self.assertEqual(self.k.verifier_trust('exact-b'), 'UNANCHORED')


class Wording(unittest.TestCase):
    FLOOR = {'math': 'WITNESS_VALID', 'utility': 'DEV_ONLY', 'causality': 'CORRELATED',
             'improver': 'NOT_TESTED', 'novelty': 'UNKNOWN', 'replication': 'NONE'}
    ILLEGAL = [
        'We proved that the bound holds for all hosts.',
        'This construction is optimal.',
        'The improvement generalizes to triangle-free hosts.',
        'The adaptive policy is confirmed to be better.',
        'The exchange step causes the gain.',
        'This is a novel extremal construction.',
        'Genesis demonstrates recursive self-improvement.',
        'Genesis is a better improver than the baseline.',
        'no ghost found, so the conjecture is proved.',
        'The result was replicated.',
    ]
    LEGAL = [
        'No theorem was formally checked.',
        'Better-improver and recursive-improvement claims remain unestablished.',
        'No novelty or recursive-improvement claim.',
        'The returned witness passed the registered checks.',
        'Utility measurements are development-only; transfer is not established.',
        'Status MATCHES_KNOWN_OPTIMUM rests on a published value.',
        "Answer key [cited: Mantel's theorem: ex(n, K3) = floor(n^2/4)].",
    ]

    def test_illegal_sentences_rejected(self):
        for sentence in self.ILLEGAL:
            self.assertTrue(lint(sentence, self.FLOOR), sentence)

    def test_honest_limitations_pass(self):
        for sentence in self.LEGAL:
            self.assertEqual(lint(sentence, self.FLOOR), [], sentence)

    def test_licensed_language_passes(self):
        levels = dict(self.FLOOR, math='OPTIMALITY_CHECKED', utility='CONFIRMED_TRANSFER')
        require_clean('This construction is optimal. The improvement generalizes to triangle-free hosts.', levels)


if __name__ == '__main__':
    unittest.main()
