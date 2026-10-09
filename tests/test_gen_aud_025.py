"""GEN-AUD-025: signed partial runs and unrelated identities cannot pass a full-run check.

Synthetic local signer only; does not establish independently held sealed custody.
"""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from custody_reference.evaluator import ARMS, SCHEMA, canonical, evaluate_frozen, file_sha, sha256, verify_bundle
from scripts.external_custody_protocol import canonical_bytes


class SignedPartialRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.pool = self.root / 'pool.json'
        self.pool.write_bytes(canonical([
            {'id': 'synthetic-1', 'features': {'x': 1}, 'answer': 2},
            {'id': 'synthetic-2', 'features': {'x': 2}, 'answer': 4},
        ]))
        self.candidates = {}
        for arm in ARMS:
            p = self.root / (arm + '.json')
            p.write_bytes(canonical({'expr': {'op': 'const', 'value': 2}}))
            self.candidates[arm] = p
        self.hashes = {arm: file_sha(p) for arm, p in self.candidates.items()}
        self.prereg = self.root / 'prereg.json'
        self.prereg.write_bytes(canonical({
            'protocol': SCHEMA, 'pool_sha256': file_sha(self.pool),
            'candidate_sha256': self.hashes, 'evaluation_budget_per_arm': 2,
            'campaign_id': 'expected-campaign',
        }))
        self.key = Ed25519PrivateKey.generate()
        keyfile = self.root / 'key.pem'
        keyfile.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.public = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.reservations = self.root/'reservations'; self.reservations.mkdir(mode=0o700); self.reservations.chmod(0o700)
        self.out = self.root / 'out'
        evaluate_frozen(self.pool, self.candidates, self.prereg, keyfile, self.out,
                        custodian_id='expected-custodian', reservation_dir=self.reservations)

    def verify(self, **overrides):
        kw = dict(expected_prereg_sha256=file_sha(self.prereg),
                  expected_pool_sha256=file_sha(self.pool),
                  expected_candidate_hashes=self.hashes,
                  expected_evaluator_sha256=file_sha(Path(__file__).parents[1] / 'custody_reference' / 'evaluator.py'),
                  expected_task_count=2, expected_campaign_id='expected-campaign',
                  expected_custodian_id='expected-custodian', expected_prereg_budget_per_arm=2,
                  expected_prereg_bytes=self.prereg.read_bytes())
        kw.update(overrides)
        return verify_bundle(self.out, self.public, **kw)

    def resign(self, *, count=None, campaign=None, custodian=None):
        aggregate = json.loads((self.out / 'aggregate.json').read_bytes())
        if count is not None:
            for arm in ARMS:
                aggregate['arms'][arm] = {'tasks': count, 'correct': count,
                                          'execution_failures': 0, 'budget_charged': count}
        if campaign is not None:
            aggregate['campaign_id'] = campaign
        ab = canonical(aggregate)
        (self.out / 'aggregate.json').write_bytes(ab)
        manifest = json.loads((self.out / 'manifest.json').read_bytes())
        manifest['results_sha256'] = sha256(ab)
        mb = canonical(manifest)
        (self.out / 'manifest.json').write_bytes(mb)
        receipt = json.loads((self.out / 'receipt.json').read_bytes())
        receipt['claims']['results_sha256'] = sha256(ab)
        receipt['claims']['manifest_sha256'] = sha256(mb)
        if custodian is not None:
            receipt['claims']['custodian_id'] = custodian
        receipt['signature_b64'] = base64.b64encode(self.key.sign(canonical_bytes(receipt['claims']))).decode()
        (self.out / 'receipt.json').write_bytes(canonical(receipt))

    def test_original_bundle_is_only_internally_consistent(self):
        result = self.verify()
        self.assertTrue(result['signature_valid'])
        self.assertFalse(result['independent_custody_proven'])
        self.assertFalse(result['promotion_allowed'])

    def test_validly_resigned_one_of_two_task_run_rejected(self):
        self.resign(count=1)
        with self.assertRaisesRegex(ValueError, 'partial or unexpected per-arm task count'):
            self.verify()

    def test_validly_resigned_other_campaign_rejected(self):
        self.resign(campaign='unrelated-campaign')
        with self.assertRaisesRegex(ValueError, 'campaign ID'):
            self.verify()

    def test_validly_resigned_other_custodian_rejected(self):
        self.resign(custodian='unrelated-custodian')
        with self.assertRaisesRegex(ValueError, 'custodian ID'):
            self.verify()

    def test_validly_resigned_combined_partial_identity_swap_rejected(self):
        self.resign(count=1, campaign='unrelated-campaign', custodian='unrelated-custodian')
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_or_invalid_external_expected_values_rejected(self):
        for kwargs in ({'expected_task_count': True}, {'expected_task_count': 0},
                       {'expected_prereg_budget_per_arm': 1},
                       {'expected_campaign_id': ''}, {'expected_custodian_id': ''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.verify(**kwargs)


if __name__ == '__main__':
    unittest.main()
