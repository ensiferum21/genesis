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
from tests_genesis.signed_fixtures import (SignedFixture, chain_requests, math_claim, record_evaluation,
                                          witness_payload)
from genesis.kernel.wording import lint, require_clean
from genesis.store import Store

SRC = 'a' * 64
ANCHOR_IMPL = 'f' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name); self.addCleanup(self.store.close)
        self.store.set_state('campaign_id', 'a' * 64); self.store.set_state('source_hash', 'c' * 64)
        self.k = EvidenceKernel(self.store, anchors={ANCHOR_IMPL: 'pinned fixture checker'})
        self.k.register_verifier('dual-predicates', ANCHOR_IMPL)
        self.k.register_verifier('exact-b', 'e' * 64)
        self.run = self.k.record('execution_receipt', {'status': 'SUCCESS'}, route='genesis.campaign',
                                 source_hash=SRC, verdict='VALID', effects=['UNCHECKED_PROPOSAL'])

    def check(self, kind, parents, verifier='dual-predicates', verdict='VALID', payload=None, effects=(),
              route='genesis.campaign'):
        if payload is None:
            payload = witness_payload(self.store) if kind == 'witness_check' else {'kind': kind, 'parents': parents}
        return self.k.record(kind, payload, parents=parents, route=route,
                             source_hash=SRC, verdict=verdict, verifier=verifier, effects=effects)

    def rejects(self, claim, axis, level, fragment):
        with self.assertRaises(PromotionRejected) as ctx:
            self.k.promote(claim, axis, level)
        self.assertTrue(any(fragment in r for r in ctx.exception.args[0]), ctx.exception.args[0])


class MathPromotion(Base):
    def test_witness_valid_needs_a_passing_witness_check(self):
        math_claim(self.k, 'c1', [self.run])
        self.rejects('c1', 'math', 'WITNESS_VALID', 'witness_check')
        w = self.check('witness_check', [self.run])
        math_claim(self.k, 'c2', [w])
        self.k.promote('c2', 'math', 'WITNESS_VALID')
        self.assertEqual(self.k.levels('c2')['math'], 'WITNESS_VALID')

    def test_unchecked_proposal_taints_until_checked(self):
        math_claim(self.k, 'c', [self.run])
        self.rejects('c', 'math', 'FINITE_CERTIFIED', 'speculative')

    def test_declared_verdicts_without_a_replay_contract_license_nothing(self):
        # B14 red team round 2 (C2): exact/formal/causal/replication nodes are producer-written verdicts
        # until a replay contract exists, however many there are. B20_R8 added contracts for exact_check,
        # formal_check and dev_comparison (tests_genesis/test_replay_contracts.py): a declared verdict
        # still licenses nothing there, because its payload does not replay.
        a = self.check('exact_check', [self.run])
        b = self.check('exact_check', [self.run], verifier='exact-b')
        math_claim(self.k, 'two', [a, b], claim='optimum')
        self.rejects('two', 'math', 'FINITE_CERTIFIED', 'not a replayable exact check')
        for kind, axis, level, fragment in (
                ('formal_check', 'math', 'THEOREM_CHECKED', 'not a replayable formal check'),
                ('ablation', 'causality', 'ABLATION_SUPPORTED', 'no replay contract for ablation'),
                ('internal_replication', 'replication', 'INTERNAL_INDEPENDENT',
                 'no replay contract for internal_replication'),
                ('dev_comparison', 'utility', 'DEV_ONLY', 'not a replayable DEV comparison'),
                ('priority_check', 'novelty', 'REDISCOVERY', 'no replay contract for priority_check')):
            n = self.check(kind, [self.run], verdict='PASS')
            math_claim(self.k, f'declared-{kind}', [n])
            self.rejects(f'declared-{kind}', axis, level, fragment)
        # A witness check is replayed: a wrong witness or a declared value does not pass.
        bad = self.check('witness_check', [self.run], payload=dict(witness_payload(self.store), value=4))
        math_claim(self.k, 'badw', [bad])
        self.rejects('badw', 'math', 'WITNESS_VALID', 'does not replay')
        v1 = self.check('witness_check', [self.run], payload={'value': 7})
        math_claim(self.k, 'v1', [v1])
        self.rejects('v1', 'math', 'WITNESS_VALID', 'not a replayable witness check')

    PATH4 = None

    def path4(self):
        from genesis.common import digest
        from genesis.models import GraphTask
        task = GraphTask(task_id='path4', n=4, edges=((0, 1), (1, 2), (2, 3)), family='path')
        return task, digest(task.model_dump(mode='json'))

    def bound(self, *, lower=3, upper=3, bundle=None, payload=None, sha=None, task=None):
        from genesis.verification.certificates import build, persist
        task = task or self.path4()[0]
        if bundle is None:
            b, blobs = build(task, {'lower': 3, 'witness': task.edges, 'upper': 3,
                                    'upper_certificate': {'method': 'HOST_EDGE_COUNT', 'upper': 3}})
            bundle = persist(self.store, b, blobs)
        b = self.store.get(bundle)
        wp = witness_payload(self.store, task, b['lower']['witness'])
        if wp['value'] != lower:  # an inconsistent bound state on purpose: witness of another value
            wp = witness_payload(self.store, task, task.edges[:lower])
        w = self.check('witness_check', [self.run], payload=wp)
        sha = sha or wp['task_sha256']
        body = payload or {'schema': 'genesis-bound-state-v2', 'task': task.task_id, 'task_sha256': sha, 'lower': lower,
                           'upper': upper, 'gap': upper - lower, 'lower_evidence': w, 'certificate_bundle': bundle}
        return self.check('bound_state', [w], payload=body)

    def opt_claim(self, cid, node, value=3, sha=None):
        problem = {'task_sha256': sha or self.store.put(self.path4()[0].model_dump(mode='json')), 'value': value,
                   'claim': 'optimum'}
        self.k.create_claim(cid, self.k.math_statement(problem), 'this finite host only', [node], problem=problem)

    def test_optimality_needs_gap_zero_and_certificate_custody(self):
        self.opt_claim('c', self.bound(lower=2, upper=3))
        self.rejects('c', 'math', 'OPTIMALITY_CHECKED', 'gap is not 0')
        self.opt_claim('d', self.bound())
        self.k.promote('d', 'math', 'OPTIMALITY_CHECKED')
        self.k.create_claim('noproblem', 'opt', 'H', [self.bound()])
        self.rejects('noproblem', 'math', 'OPTIMALITY_CHECKED', 'must name its exact problem')
        # B13-style bound state: numbers and a verifier name, no references.
        self.opt_claim('e', self.check('bound_state', [self.run], payload={'lower': 8, 'upper': 8, 'gap': 0}))
        self.rejects('e', 'math', 'OPTIMALITY_CHECKED', 'lacks certificate custody')
        # A SAT_DRAT bundle whose proof objects are not in the store.
        from genesis.common import digest
        task, sha = self.path4()
        fake = self.store.put({'schema': 'genesis-certificate-bundle-v1',
                               'problem': {'domain': 'c4_host_v2', 'task': task.model_dump(mode='json'),
                                           'task_sha256': sha},
                               'lower': {'value': 3, 'witness': [list(e) for e in task.edges]},
                               'upper': {'method': 'SAT_DRAT', 'value': 3, 'cnf_sha256': '1' * 64,
                                         'proof_sha256': '2' * 64, 'checker_verdict': 'VALID'},
                               'gap': 0, 'status': 'OPTIMALITY_CHECKED'})
        self.opt_claim('f', self.bound(bundle=fake))
        self.rejects('f', 'math', 'OPTIMALITY_CHECKED', 'object missing or altered')
        # A theorem-based bound is recorded but cannot certify optimality.
        from genesis.models import GraphTask
        from genesis.verification.certificates import build, persist
        b, blobs = build(task, {'lower': 3, 'witness': task.edges, 'upper': 3,
                                'upper_certificate': {'method': 'reiman', 'upper': 3}})
        self.assertEqual(b['upper']['method'], 'HOST_EDGE_COUNT')  # 3 == edge count: trivial bound wins
        k4 = GraphTask(task_id='k4', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='k')
        b, blobs = build(k4, {'lower': 4, 'witness': ((0, 1), (0, 2), (0, 3), (1, 2)), 'upper': 4,
                              'upper_certificate': {'method': 'reiman', 'upper': 4}})
        self.assertEqual((b['upper']['method'], b['status']), ('THEOREM', 'OPTIMALITY_BY_THEOREM_UNCHECKED'))
        k4sha = digest(k4.model_dump(mode='json'))
        self.opt_claim('g', self.bound(bundle=persist(self.store, b, blobs), lower=4, upper=4, task=k4),
                       value=4, sha=k4sha)
        self.rejects('g', 'math', 'OPTIMALITY_CHECKED', 'not independently certified')

    def test_approximate_and_self_judged_dependencies_rejected(self):
        a = self.check('exact_check', [self.run], effects=['APPROXIMATE'])
        b = self.check('exact_check', [self.run], verifier='exact-b')
        math_claim(self.k, 'approx', [a, b])
        self.rejects('approx', 'math', 'FINITE_CERTIFIED', 'approximate')
        w = self.check('witness_check', [self.run], effects=['SELF_JUDGED'])
        math_claim(self.k, 'self', [w])
        self.rejects('self', 'math', 'WITNESS_VALID', 'self-judged')

    def test_failed_checker_receipt_never_licenses(self):
        w = self.check('witness_check', [self.run], verdict='CHECKER_ERROR')
        math_claim(self.k, 'c', [w])
        self.rejects('c', 'math', 'WITNESS_VALID', 'witness_check')

    def test_negative_states_are_not_promotion_targets(self):
        w = self.check('witness_check', [self.run])
        math_claim(self.k, 'c', [w])
        self.rejects('c', 'math', 'UNSETTLED', 'not a promotable')

    def test_unknown_effect_names_are_refused(self):
        with self.assertRaises(ValueError):
            self.k.record('note', {}, route='genesis.campaign', source_hash=SRC, effects=['TOUCHED_SEALED'])


class Confirmation(Base):
    """Confirmation levels need receipts signed by the role trusted code assigns (kernel.receipts)."""

    def setUp(self):
        super().setUp()
        self.fx = SignedFixture(self.tmp.name)
        self.fx.bind_store(self.store)
        self.k = EvidenceKernel.with_fixture_registry(self.store, self.fx.registry,
                                                      anchors={ANCHOR_IMPL: 'pinned fixture checker'})

    def sealed(self, request=None, route='genesis.custodian.evaluate', effects=(), **kw):
        request = request or self.fx.request()
        _, node = record_evaluation(self.k, self.fx, request, [self.run], route=route, **kw)
        return node, request

    def test_no_external_role_registry_means_no_confirmation(self):
        node, request = self.sealed()
        production = EvidenceKernel(self.store)  # trust root absent / research account is root here
        production.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node],
                                binding=binding_from_requests([request]))
        with self.assertRaises(PromotionRejected) as ctx:
            production.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertTrue(any('role registry' in r for r in ctx.exception.args[0]))

    def test_externally_signed_eligible_evaluation_confirms(self):
        node, request = self.sealed()
        self.k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node], binding=binding_from_requests([request]))
        decision = self.k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
        self.assertEqual(decision['registry'], 'FIXTURE')
        self.assertEqual(len(decision['evaluations']), 1)

    def test_ineligible_route_revoked_source_and_unbound_claims_rejected(self):
        for name, route, fragment in (('route', 'genesis.campaign', 'ineligible'),
                                      ('legacy', 'legacy_batch42.sealed_benchmark', 'ineligible')):
            request = self.fx.request(claim_id=name)
            node, _ = self.sealed(request, route=route)
            self.k.create_claim(name, SignedFixture.STATEMENT, SignedFixture.SCOPE, [node], binding=binding_from_requests([request]))
            self.rejects(name, 'utility', 'CONFIRMED_SAME_DOMAIN', fragment)
        request = self.fx.request(claim_id='nobinding')
        node, _ = self.sealed(request)
        math_claim(self.k, 'nobinding', [node])
        self.rejects('nobinding', 'utility', 'CONFIRMED_SAME_DOMAIN', 'bound to its preregistered')

    def test_contaminated_dependency_rejected(self):
        leak = self.k.record('note', {'leak': True}, route='genesis.campaign', source_hash=SRC,
                             effects=['TOUCHED_SEALED_SET'])
        request = self.fx.request(claim_id='leak')
        _, node = record_evaluation(self.k, self.fx, request, [self.run, leak])
        self.k.create_claim('leak', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node], binding=binding_from_requests([request]))
        self.rejects('leak', 'utility', 'CONFIRMED_SAME_DOMAIN', 'contaminated')

    def test_multigeneration_needs_three_signed_generations_and_no_manual_rescue(self):
        requests = chain_requests(self.fx, 'multigen', 3)
        nodes = [record_evaluation(self.k, self.fx, r, [self.run])[1] for r in requests]
        binding = binding_from_requests(requests)
        self.k.create_claim('multigen', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes, binding=binding)
        self.k.promote('multigen', 'improver', 'MULTIGEN_CONFIRMED')
        manual = self.k.record('note', {'rescue': True}, route='genesis.campaign', source_hash=SRC,
                               effects=['MANUAL_INTERVENTION'])
        self.k.create_claim('rescued', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes + [manual], binding=binding)
        self.rejects('rescued', 'improver', 'MULTIGEN_CONFIRMED', 'manual intervention')
        self.k.create_claim('two', SignedFixture.STATEMENT, SignedFixture.SCOPE, nodes[:2], binding=binding_from_requests(requests[:2]))
        self.rejects('two', 'improver', 'MULTIGEN_CONFIRMED', 'needs 3 consecutive')


class Revocation(Base):
    def test_revoking_an_ancestor_invalidates_dependent_claims(self):
        w = self.check('witness_check', [self.run])
        math_claim(self.k, 'c', [w])
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
        math_claim(self.k, 'c', [w])
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
