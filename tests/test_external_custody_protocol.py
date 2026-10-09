import base64
import unittest
from scripts.external_custody_protocol import FIELDS, canonical_bytes, verify_receipt, promotion_custody_preflight
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

class CustodyProtocolTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.key = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)).decode()
        self.claims = {k: 'a'*64 for k in FIELDS[:6]}
        self.claims.update(custodian_id='test-custodian',protocol_version='genesis-custody-v1')
    def signed(self,claims):
        return {'claims':claims,'signature_b64':base64.b64encode(self.private.sign(canonical_bytes(claims))).decode()}
    def test_valid_signature_not_isolation(self):
        self.assertFalse(verify_receipt(self.signed(self.claims),self.key)['custody_isolation_proven'])
    def test_tampering_rejected(self):
        receipt=self.signed(self.claims)
        receipt['claims']['pool_sha256']='b'*64
        with self.assertRaises(Exception): verify_receipt(receipt,self.key)
    def test_self_declared_key_not_trusted(self):
        receipt=self.signed(self.claims)
        receipt['public_key_b64']=self.key
        with self.assertRaises(ValueError): verify_receipt(receipt,self.key)
    def test_missing_custody_blocks(self):
        self.assertEqual(promotion_custody_preflight(None,None)['status'],'BLOCK')
    def test_signature_without_audit_blocks(self):
        self.assertEqual(promotion_custody_preflight(self.signed(self.claims),self.key)['status'],'BLOCK')
