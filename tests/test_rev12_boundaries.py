"""GEN-AUD-017/018/019 negative tests; synthetic only, no real sealed tasks."""
import base64
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gap_engine.experiments.prereg import PreregViolation, write_prereg
from gap_engine.kernel.sealed import SealedStore, SealedAccessError
from scripts.evidence_manifest import build_manifest, verify_manifest
from scripts.prereg_anchor import verify_prereg_anchor


class TestCacheInventory(unittest.TestCase):
    def test_untracked_regular_cache_file_rejected(self):
        for dirname in ('__pycache__', '.pytest_cache'):
            with self.subTest(dirname=dirname), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'raw.json').write_text('public')
                m = build_manifest(root)
                (root / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(m))
                self.assertEqual(verify_manifest(root, m), [])
                (root / dirname).mkdir()
                (root / dirname / 'hidden.json').write_text('synthetic-private-marker')
                self.assertTrue(any('forbidden cache file' in issue for issue in verify_manifest(root, m)))
                with self.assertRaisesRegex(ValueError, 'forbidden cache file'):
                    build_manifest(root)

    def test_pycache_extension_and_custom_exclusions_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'x.pyc').write_bytes(b'not a real pyc')
            with self.assertRaisesRegex(ValueError, 'forbidden cache file'):
                build_manifest(root)
            (root / 'x.pyc').unlink()
            with self.assertRaisesRegex(ValueError, 'only EVIDENCE_MANIFEST'):
                build_manifest(root, exclude=('EVIDENCE_MANIFEST.json', 'private.json'))


class TestLegacySealedUnsafeByDefault(unittest.TestCase):
    def test_default_denies_payload_callback_before_execution(self):
        s = SealedStore()
        s.seal('SYNTHETIC', [('fake', {'marker': 'SYNTHETIC_ONLY'})])
        observed = []
        with self.assertRaisesRegex(SealedAccessError, 'disabled'):
            s.judge('SYNTHETIC', lambda x: observed.append(x) or True,
                    actor='attacker', purpose='probe')
        self.assertEqual(observed, [])
        self.assertEqual(s.ledger.entries[-1]['kind'], 'sealed.judge.blocked')
        dev = s.judge('SYNTHETIC', lambda x: True, actor='dev', purpose='DEV',
                      unsafe_dev_callback=True)
        self.assertFalse(dev['independent_custody_proven'])
        self.assertFalse(dev['eligible_for_scientific_promotion'])


class TestExternalPreregAnchor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'plan.json'
        h = write_prereg(str(self.path), {'arm': 'D', 'budget': 100})
        self.expected = {'preregistration_sha256': h, 'candidate_sha256': 'a'*64,
                         'evaluator_sha256': 'b'*64, 'pool_sha256': 'c'*64}
        self.private = Ed25519PrivateKey.generate()  # TEST ONLY, never a real custodian
        self.public = self.private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.claims = dict(self.expected, schema='genesis-prereg-anchor-v1',
                           custodian_id='SYNTHETIC_TEST_NOT_EXTERNAL',
                           issued_at_utc='2026-10-08T00:00:00Z')

    def anchor(self, claims=None):
        claims = claims or self.claims
        data = json.dumps(claims, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode()
        return {'payload': claims, 'signature_ed25519_base64':
                base64.b64encode(self.private.sign(data)).decode()}

    def check(self, anchor=None, **kwargs):
        return verify_prereg_anchor(self.path, anchor or self.anchor(),
                                    kwargs.get('key', self.public),
                                    kwargs.get('expected', self.expected),
                                    kwargs.get('start', '2026-10-09T00:00:00Z'))

    def test_valid_signature_is_not_release_or_custody_proof(self):
        r = self.check()
        self.assertTrue(r['signature_valid'])
        self.assertFalse(r['promotion_allowed'])
        self.assertFalse(r['independent_custody_proven'])

    def test_rewritten_prereg_and_local_lock_cannot_pass_old_external_anchor(self):
        doc = json.loads(self.path.read_text())
        doc['plan']['arm'] = 'V2p'
        from gap_engine.kernel.ledger import _canonical, sha256_hex
        new_h = sha256_hex(_canonical(doc['plan']))
        doc['sha256'] = new_h
        self.path.write_text(json.dumps(doc))
        Path(str(self.path) + '.lock').write_text(new_h)
        with self.assertRaisesRegex(PreregViolation, 'external anchor'):
            self.check()

    def test_anchor_after_start_rejected(self):
        with self.assertRaisesRegex(PreregViolation, 'not earlier'):
            self.check(start='2026-10-08T00:00:00Z')

    def test_self_declared_public_key_not_accepted(self):
        a = self.anchor()
        a['public_key_pem'] = self.public.decode()
        with self.assertRaisesRegex(PreregViolation, 'envelope'):
            self.check(a)

    def test_untrusted_key_and_tampered_signature_rejected(self):
        wrong = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaisesRegex(PreregViolation, 'signature'):
            self.check(key=wrong)
        a = self.anchor()
        a['signature_ed25519_base64'] = base64.b64encode(b'0'*64).decode()
        with self.assertRaisesRegex(PreregViolation, 'signature'):
            self.check(a)

    def test_external_digest_mismatch_rejected(self):
        wrong = dict(self.expected, candidate_sha256='d'*64)
        with self.assertRaisesRegex(PreregViolation, 'digest mismatch'):
            self.check(expected=wrong)


if __name__ == '__main__':
    unittest.main()
