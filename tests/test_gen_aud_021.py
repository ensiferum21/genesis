"""GEN-AUD-021: signed impossible aggregate must not pass reference verification."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from custody_reference.evaluator import (
    ARMS, SCHEMA, canonical, evaluate_frozen, file_sha, sha256, verify_bundle)
from scripts.external_custody_protocol import canonical_bytes


class TestSignedImpossibleScores(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pool = self.root / 'private.json'
        self.pool.write_bytes(canonical([{'id': 'synthetic-task', 'features': {'x': 1}, 'answer': 2}]))
        self.candidates = {}
        for arm in ARMS:
            p = self.root / f'{arm}.json'
            p.write_bytes(canonical({'expr': {'op': 'const', 'value': 2}}))
            self.candidates[arm] = p
        self.hashes = {arm: file_sha(p) for arm, p in self.candidates.items()}
        self.prereg = self.root / 'prereg.json'
        self.prereg.write_bytes(canonical({'protocol': SCHEMA,
            'pool_sha256': file_sha(self.pool), 'candidate_sha256': self.hashes,
            'evaluation_budget_per_arm': 1, 'campaign_id': 'SYNTHETIC_DEV_ONLY'}))
        self.key = Ed25519PrivateKey.generate()  # Test signer, not external custody
        self.key_path = self.root / 'key.pem'
        self.key_path.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.public = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.reservations = self.root/'reservations'; self.reservations.mkdir(mode=0o700); self.reservations.chmod(0o700)
        from custody_reference.private_evidence import configure_semantics
        configure_semantics(self.reservations,domain='synthetic-linear-v1',required_features=['x'],ignored_features=['unused'])
        self.out = self.root / 'out'
        evaluate_frozen(self.pool, self.candidates, self.prereg, self.key_path,
                        self.out, custodian_id='LOCAL_TEST_NOT_INDEPENDENT', reservation_dir=self.reservations)

    def resign(self, modify):
        aggregate = json.loads((self.out / 'aggregate.json').read_bytes())
        modify(aggregate)
        raw = canonical(aggregate)
        (self.out / 'aggregate.json').write_bytes(raw)
        manifest = json.loads((self.out / 'manifest.json').read_bytes())
        manifest['results_sha256'] = sha256(raw)
        mraw = canonical(manifest)
        (self.out / 'manifest.json').write_bytes(mraw)
        receipt = json.loads((self.out / 'receipt.json').read_bytes())
        receipt['claims']['results_sha256'] = sha256(raw)
        receipt['claims']['manifest_sha256'] = sha256(mraw)
        receipt['signature_b64'] = base64.b64encode(
            self.key.sign(canonical_bytes(receipt['claims']))).decode()
        (self.out / 'receipt.json').write_bytes(canonical(receipt))

    def verify(self):
        return verify_bundle(self.out, self.public,
            expected_prereg_sha256=file_sha(self.prereg),
            expected_pool_sha256=file_sha(self.pool),
            expected_candidate_hashes=self.hashes,
            expected_task_count=1, expected_campaign_id='SYNTHETIC_DEV_ONLY',
            expected_custodian_id='LOCAL_TEST_NOT_INDEPENDENT',
            expected_prereg_budget_per_arm=1, expected_prereg_bytes=self.prereg.read_bytes(), expected_evaluator_sha256=file_sha(Path(__file__).parents[1] / 'custody_reference' / 'evaluator.py'))

    def test_unmodified_bundle_valid_but_not_independent(self):
        r = self.verify()
        self.assertTrue(r['signature_valid'])
        self.assertFalse(r['independent_custody_proven'])

    def test_signed_impossible_score_rejected(self):
        self.resign(lambda a: a['arms']['D'].__setitem__('correct', 999))
        with self.assertRaisesRegex(ValueError, 'impossible per-arm score'):
            self.verify()

    def test_signed_unequal_budget_rejected(self):
        self.resign(lambda a: a['arms']['U'].__setitem__('budget_charged', 0))
        with self.assertRaisesRegex(ValueError, 'budget/task mismatch'):
            self.verify()

    def test_signed_missing_arm_rejected(self):
        self.resign(lambda a: a['arms'].pop('V2n'))
        with self.assertRaisesRegex(ValueError, 'comparison arm'):
            self.verify()

    def test_signed_fake_private_export_flag_rejected(self):
        self.resign(lambda a: a.__setitem__('sealed_task_payloads_exported', True))
        with self.assertRaisesRegex(ValueError, 'custody/export'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
