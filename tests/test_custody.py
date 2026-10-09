import base64
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from gap_engine.kernel.custody import CustodyError, verify_external_attestation


class TestExternalCustody(unittest.TestCase):
    def setUp(self):
        # Ephemeral test key ONLY. Never use it for real custody attestation.
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)
        self.expected = {k: str(i) * 64 for i, k in enumerate((
            'candidate_sha256', 'preregistration_sha256', 'pool_sha256',
            'results_manifest_root_sha256', 'evaluator_sha256'), 1)}
        self.payload = {'schema': 'genesis-external-custody-v1',
                        'custodian_id': 'test-only', 'issued_at_utc': '2026-10-08T00:00:00Z',
                        'research_read_access_to_sealed': False,
                        'evaluator_isolated_from_research': True, **self.expected}

    def attestation(self, payload):
        message = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True, allow_nan=False).encode('utf-8')
        return {'payload': payload,
                'signature_ed25519_base64': base64.b64encode(self.private.sign(message)).decode()}

    def test_signed_custody_contract_accepts_matching_hashes(self):
        self.assertEqual(len(verify_external_attestation(self.attestation(self.payload),
                                                          self.public, self.expected)), 64)

    def test_rejects_changed_result_or_unauthorized_access(self):
        good = self.attestation(self.payload)
        good['payload']['research_read_access_to_sealed'] = True
        with self.assertRaises(CustodyError):
            verify_external_attestation(good, self.public, self.expected)
        bad = self.attestation(self.payload)
        wrong = dict(self.expected, pool_sha256='f' * 64)
        with self.assertRaises(CustodyError):
            verify_external_attestation(bad, self.public, wrong)
        bad['signature_ed25519_base64'] = base64.b64encode(b'bad').decode()
        with self.assertRaises(CustodyError):
            verify_external_attestation(bad, self.public, self.expected)

if __name__ == '__main__':
    unittest.main()
