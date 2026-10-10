"""Regression tests for the second internal red-team pass on B14 (audit/redteam_b14_round2/).

C1 transfer label without transfer, C2 declared verdicts, H1 RELEASED without the
signed chain, H2 re-registration under a new claim id, H3 duplicate JSON keys,
M1 unidentified shipped code, M2 wording bypasses, L1 unchecked bundle bytes,
L2 envelope revocation, L3 program identity by encoding, L4 registry key
aliasing, L5 initial phase. C2 and H2 are covered in test_evidence_kernel.py and
test_external_custodian.py. Fixture keys prove protocol behaviour only.
"""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import zipfile

from genesis.common import canonical, code_identity, digest
from genesis.kernel import receipts as R
from genesis.kernel.evidence import EvidenceKernel, PromotionRejected
from genesis.kernel.phases import PhaseError, advance, verified_phase
from genesis.kernel.wording import lint
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store
from tests_genesis.signed_fixtures import (SignedFixture, fixture_campaign, math_claim, record_evaluation,
                                          witness_payload)

REPO = Path(__file__).resolve().parents[1]
SRC = 'a' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.fx = SignedFixture(self.tmp.name)


class C1KernelCampaignBinding(Base):
    def test_receipts_must_be_about_this_store_campaign(self):
        with Store(self.d / 'other') as s:
            s.set_state('campaign_id', 'f' * 64); s.set_state('source_hash', 'c' * 64)
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            request = self.fx.request()  # campaign 'a'*64
            _, node = record_evaluation(k, self.fx, request, [run])
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node],
                           binding=R.binding_from_requests([request]))
            with self.assertRaises(PromotionRejected) as ctx:
                k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
            self.assertIn('different campaign', ' '.join(ctx.exception.args[0]))


class H1PhaseChain(Base):
    def registry(self):
        return mock.patch('genesis.kernel.phases.load_role_registry', return_value=(self.fx.registry, []))

    @staticmethod
    def freeze(store):
        for p in ('VALIDATED_CONFIG', 'DEV_RUNNING', 'CANDIDATE_FROZEN'):
            advance(store, p)

    def walk(self, store, request, outcome_kw):
        anchor = self.fx.anchor(request)
        receipt = self.fx.receipt(request, anchor, **outcome_kw)
        for target, env in (('LEAK_SCAN_PASSED', anchor), ('SEALED_RUNNING', receipt), ('JUDGED', receipt)):
            advance(store, target, envelope=env)
        return anchor, receipt

    def decision(self, request, receipt, kind):
        return self.fx.sign({'schema': 'genesis-release-decision-v1', 'request_hash': digest(request),
                             'decision': kind, 'receipt_hash': digest(receipt)}, 'release')

    def test_forged_released_after_a_reject_is_not_verified(self):
        root, request = fixture_campaign(self.d, self.fx)
        with self.registry(), Store(root) as s:
            self.freeze(s)
            anchor, receipt = self.walk(s, request, {'wins': 5, 'losses': 30, 'ties': 5})
            reject = self.decision(request, receipt, 'REJECT')
            with self.assertRaises(PhaseError):
                advance(s, 'RELEASED', envelope=reject)
            s.set_state('phase_receipt:RELEASED', reject)  # the producer writes the state directly
            s.set_state('phase', 'RELEASED')
            v = verified_phase(s)
        self.assertNotEqual(v['phase'], 'RELEASED')
        self.assertFalse(v['consistent'])

    def test_genuine_release_verifies(self):
        root, request = fixture_campaign(self.d, self.fx)
        with self.registry(), Store(root) as s:
            self.freeze(s)
            anchor, receipt = self.walk(s, request, {})
            advance(s, 'RELEASED', envelope=self.decision(request, receipt, 'RELEASE'))
            v = verified_phase(s)
        self.assertEqual((v['phase'], v['consistent'], v['problems']), ('RELEASED', True, []))

    def test_envelopes_of_another_campaign_cannot_be_replayed(self):
        root_x, request_x = fixture_campaign(self.d, self.fx)
        with self.registry(), Store(root_x) as s:
            self.freeze(s)
            anchor, receipt = self.walk(s, request_x, {})
        root_b, _ = fixture_campaign(self.d, self.fx, campaign='b' * 64)
        with self.registry(), Store(root_b) as s:
            s.save('frozen_request', digest(request_x), request_x)
            s.set_state('frozen_request_hash', digest(request_x))
            self.freeze(s)
            with self.assertRaisesRegex(PhaseError, 'another campaign'):
                advance(s, 'LEAK_SCAN_PASSED', envelope=anchor)
            s.set_state('campaign_id', 'a' * 64)  # impersonate X, with X's export copied in
            shutil.copy(root_x / 'exports' / 'campaign_export.zip', root_b / 'exports' / 'campaign_export.zip')
            with self.assertRaisesRegex(PhaseError, 'prefix'):
                advance(s, 'LEAK_SCAN_PASSED', envelope=anchor)

    def test_initialised_campaign_is_consistent(self):  # L5
        from genesis.campaign import Campaign
        from genesis.models import Config
        Campaign.initialize(self.d / 'c', Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2,
                                                 research_trials=8))
        with Store(self.d / 'c') as s:
            v = verified_phase(s)
        self.assertTrue(v['consistent'], v)


class BundleBytes(Base):
    def setUp(self):
        super().setUp()
        self.root = self.d / 'c'
        with Store(self.root) as s:
            s.set_state('source_hash', code_identity(REPO)['sha256'])
            k = EvidenceKernel(s)
            run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash=SRC, verdict='VALID')
            w = k.record('witness_check', witness_payload(s), parents=[run], route='genesis.campaign',
                         source_hash=SRC, verdict='VALID')
            math_claim(k, 'w', [w])
            k.promote('w', 'math', 'WITNESS_VALID')
        self.bundle = self.d / 'b.zip'
        build_bundle(self.root, self.bundle, report='The returned witness passed the registered checks.')
        self.assertTrue(verify_bundle(self.bundle)['ok'])

    def edit(self, change, name='x.zip'):
        out = self.d / name
        with zipfile.ZipFile(self.bundle) as zin:
            names = zin.namelist(); base = names[0].split('/')[0] + '/'
            files = {n: zin.read(n) for n in names}
        change(files, base)
        manifest = json.loads(files[base + 'MANIFEST.json'])
        manifest['files'] = {n[len(base):]: hashlib.sha256(v).hexdigest() for n, v in files.items()
                             if n.startswith(base) and n != base + 'MANIFEST.json'}
        files[base + 'MANIFEST.json'] = canonical(manifest)
        with zipfile.ZipFile(out, 'w') as z:
            for n, v in files.items():
                z.writestr(n, v)
        return out

    def test_h3_duplicate_keys_in_claims(self):
        def dup(files, base):
            raw = files[base + 'CLAIMS.json']
            files[base + 'CLAIMS.json'] = b'{"ceiling":{"math":"OPTIMALITY_CHECKED"},' + raw[1:]
        self.assertFalse(verify_bundle(self.edit(dup))['ok'])

    def test_m1_unidentified_shipped_code(self):
        def extra(files, base):
            files[base + 'analysis_code/src/sitecustomize.py'] = b'print("not in the code identity")\n'
        r = verify_bundle(self.edit(extra))
        self.assertFalse(r['ok']); self.assertIn('outside its code identity', ' '.join(r['problems']))

    def test_m2_limitations_and_reproduce_are_checked(self):
        def overclaim(files, base):
            files[base + 'LIMITATIONS.md'] += b'- None; the result was replicated and is optimal.\n'
        self.assertFalse(verify_bundle(self.edit(overclaim))['ok'])

        def reproduce(files, base):
            files[base + 'REPRODUCE.md'] = b'Run python -c "import analysis_code" first.\n'
        self.assertFalse(verify_bundle(self.edit(reproduce, 'y.zip'))['ok'])

    def test_l1_nested_manifest_partial_tail_and_outside_entries(self):
        def nested(files, base):
            files[base + 'certificates/MANIFEST.json'] = b'{}'
        r = verify_bundle(self.edit(nested))
        self.assertFalse(r['ok'])

        def partial(files, base):
            files[base + 'events.jsonl'] += b'{"hash":"00'
        self.assertFalse(verify_bundle(self.edit(partial, 'p.zip'))['ok'])

        def outside(files, base):
            files['CLAIMS.json'] = b'{}'
        with self.assertRaisesRegex(ValueError, 'nothing else'):
            verify_bundle(self.edit(outside, 'o.zip'))


class M2Wording(unittest.TestCase):
    def test_bypass_variants_are_caught(self):
        floor = {'math': 'WITNESS_VALID'}
        for s in ('Not surprisingly, this construction is optimal.', 'The result was replicated, no doubt.',
                  'This construction is opti​mal.', 'This construction is opti­mal.',
                  'See `this construction is optimal` above.', 'As shown [cited: we proved it optimal].',
                  'The ｏｐｔｉｍａｌ construction is optimal.'):
            self.assertTrue(lint(s, floor), s)
        for s in ('No theorem was formally checked.', 'Optimality is not established.',
                  "Answer key [cited: Mantel's theorem: ex(n, K3) = floor(n^2/4)].", 'Run `genesis verify-bundle`.'):
            self.assertEqual(lint(s, floor), [], s)


class SmallerFindings(Base):
    def test_l2_revoking_a_receipt_retires_its_envelope_everywhere(self):
        first = self.d / 'first'
        with Store(first) as s:
            self.fx.bind_store(s)
            request = self.fx.request()
            anchor = self.fx.anchor(request); receipt = self.fx.receipt(request, anchor)
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run = k.record('execution_receipt', {'store': 'first'}, route='genesis.campaign', source_hash=SRC,
                           verdict='VALID')
            _, node = record_evaluation(k, self.fx, request, [run], anchor=anchor, receipt=receipt)
        second = self.d / 'second'
        shutil.copytree(first, second)  # same campaign history, before the revocation
        with Store(first) as s:
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            k.revoke(node, 'receipt found faulty', 'auditor')
            records = k.revocations()
        with Store(second) as s:
            k = EvidenceKernel.with_fixture_registry(s, self.fx.registry)
            run2 = k.record('execution_receipt', {'store': 'second'}, route='genesis.campaign', source_hash=SRC,
                            verdict='VALID')
            _, node2 = record_evaluation(k, self.fx, request, [run2], anchor=anchor, receipt=receipt)
            self.assertNotEqual(node, node2)  # the same envelope in a different wrapper node
            k.create_claim('claim-1', SignedFixture.STATEMENT, SignedFixture.SCOPE, [node2],
                           binding=R.binding_from_requests([request]))
            k.promote('claim-1', 'utility', 'CONFIRMED_SAME_DOMAIN')
            k.apply_revocations(records)
            self.assertTrue(k.levels('claim-1').get('invalidated'))

    def test_l3_program_identity_ignores_encoding(self):
        from genesis.models import SolverProgram
        full = SolverProgram(rounds=1).model_dump(mode='json')
        self.assertEqual(R.program_identity({'rounds': 1}), R.program_identity(full))
        same = self.fx.request(baseline_program={'rounds': 1}, candidate_program=full)
        self.assertIn('same program', ' '.join(R.check_request(same)))

    def test_l4_aliased_role_keys_are_one_key(self):
        from genesis.kernel.roles import distinct_role_keys
        pins = dict(self.fx.registry['pins'])
        key = pins['custodian_key']
        raw = base64.b64decode(key)
        alias = base64.b64encode(raw).decode()[:-2] + chr(ord(base64.b64encode(raw).decode()[-2]) + 1) + '='
        self.assertEqual(base64.b64decode(alias, validate=True), raw)  # a different spelling of the same key
        self.assertTrue(distinct_role_keys(pins, self.fx.keys['root'][1]))
        self.assertFalse(distinct_role_keys(dict(pins, prereg_key=alias), self.fx.keys['root'][1]))


if __name__ == '__main__':
    unittest.main()
