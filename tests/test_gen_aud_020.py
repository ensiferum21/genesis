"""GEN-AUD-020: cross-campaign receipt confusion and self-asserted isolation."""
import base64
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from scripts.external_custody_protocol import (
    FIELDS, canonical_bytes, promotion_custody_preflight,
)


class TestCrossCampaignReceiptConfusion(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()  # synthetic only
        self.key = base64.b64encode(self.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.expected = {field: 'a' * 64 for field in FIELDS[:6]}

    def signed(self, digests=None, custodian='SYNTHETIC_CUSTODIAN'):
        claims = dict(digests or self.expected,
                      custodian_id=custodian, protocol_version='genesis-custody-v1')
        return {'claims': claims, 'signature_b64': base64.b64encode(
            self.private.sign(canonical_bytes(claims))).decode()}

    def check(self, receipt, **kw):
        return promotion_custody_preflight(receipt, self.key,
            isolation_audit_approved=True,
            expected_digests=kw.get('expected', self.expected),
            expected_custodian_id=kw.get('identity', 'SYNTHETIC_CUSTODIAN'))

    def test_cross_campaign_valid_signature_rejected(self):
        unrelated = {k: 'f' * 64 for k in FIELDS[:6]}
        result = self.check(self.signed(unrelated, 'OTHER_CUSTODIAN'))
        self.assertEqual(result['status'], 'BLOCK')
        self.assertTrue(result['signature_valid'])
        self.assertFalse(result['expected_digests_match'])
        self.assertFalse(result['expected_custodian_id_match'])
        self.assertFalse(result['promotion_allowed'])

    def test_matched_receipt_is_still_not_isolation_proof(self):
        result = self.check(self.signed())
        self.assertTrue(result['signature_valid'])
        self.assertTrue(result['expected_digests_match'])
        self.assertTrue(result['expected_custodian_id_match'])
        self.assertEqual(result['status'], 'BLOCK')
        self.assertFalse(result['independent_custody_proven'])
        self.assertFalse(result['promotion_allowed'])

    def test_missing_expected_hashes_and_identity_fail_closed(self):
        result = promotion_custody_preflight(self.signed(), self.key,
                                            isolation_audit_approved=True)
        self.assertEqual(result['status'], 'BLOCK')
        self.assertFalse(result['expected_digests_match'])
        self.assertFalse(result['expected_custodian_id_match'])

    def test_missing_one_digest_fail_closed(self):
        expected = dict(self.expected)
        del expected['results_sha256']
        self.assertFalse(self.check(self.signed(), expected=expected)['expected_digests_match'])

    def test_self_declared_custodian_id_does_not_override_pinned_identity(self):
        result = self.check(self.signed(custodian='OTHER_CUSTODIAN'))
        self.assertTrue(result['expected_digests_match'])
        self.assertFalse(result['expected_custodian_id_match'])

    def test_untrusted_key_and_tampered_signature_fail_closed(self):
        receipt = self.signed()
        receipt['signature_b64'] = base64.b64encode(b'0'*64).decode()
        self.assertFalse(self.check(receipt)['signature_valid'])


if __name__ == '__main__':
    unittest.main()
