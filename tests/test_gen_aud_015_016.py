"""Adversarial regressions: self-attested promotion and ignored symlink artifacts.

These tests use synthetic inputs; they never touch sealed mathematics or external custody.
"""
import base64
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gap_engine.kernel.custody import _canonical
from scripts.evidence_manifest import build_manifest, verify_manifest
from scripts.promotion_preflight import preflight


class TestIndependentPromotionBoundary(unittest.TestCase):
    def test_self_attested_complete_looking_records_cannot_authorize_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'results.json').write_text('{"claimed": "success"}')
            manifest = build_manifest(root)
            (root / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
            evidence = {
                'historical_pool_reused': False,
                'fresh_task_count': 300,
                'completed_jobs': 20,
                'preregistered_jobs': 20,
                'matched_baselines_passed': True,
                'regression_passed': True,
                'near_duplicate_scan_passed': True,
                'checker_replay_passed': True,
            }
            for field in ('candidate_sha256', 'preregistration_sha256',
                          'pool_sha256', 'evaluator_sha256'):
                evidence[field] = '0' * 64
            evidence['results_manifest_root_sha256'] = manifest['root_sha256']
            payload = {k: evidence[k] for k in (
                'candidate_sha256', 'preregistration_sha256', 'pool_sha256',
                'results_manifest_root_sha256', 'evaluator_sha256')}
            payload.update(schema='genesis-external-custody-v1',
                           research_read_access_to_sealed=False,
                           evaluator_isolated_from_research=True,
                           custodian_id='self-declared-not-independent',
                           issued_at_utc='2026-10-09T00:00:00Z')
            key = Ed25519PrivateKey.generate()
            evidence['custody_attestation'] = {
                'payload': payload,
                'signature_ed25519_base64': base64.b64encode(key.sign(_canonical(payload))).decode(),
            }
            public = key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            result = preflight({'status': 'READY_FOR_PROMOTION', 'current_batch': 1},
                               {'audit_status': 'PASS', 'findings': []}, evidence,
                               custodian_public_key_pem=public, evidence_root=root)
            self.assertTrue(result['prerequisites_present'])
            self.assertFalse(result['promotion_allowed_by_this_preflight'])
            self.assertEqual(result['status'], 'PREFLIGHT_PREREQUISITES_PRESENT_NOT_PROMOTION')
            self.assertIn('independent release authority', result['promotion_blocker'])


class TestManifestSymlinkInjection(unittest.TestCase):
    def test_unlisted_symlink_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw.json').write_text('data')
            manifest = build_manifest(root)
            (root / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_manifest(root, manifest), [])
            (root / 'unlisted-private.json').symlink_to(root / 'raw.json')
            self.assertTrue(any('symlink' in issue for issue in verify_manifest(root, manifest)))

    def test_symlink_inside_ignored_cache_directory_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw.json').write_text('data')
            manifest = build_manifest(root)
            (root / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
            (root / '__pycache__').mkdir()
            (root / '__pycache__' / 'hidden-private.json').symlink_to(root / 'raw.json')
            self.assertTrue(any('symlink' in issue for issue in verify_manifest(root, manifest)))

    def test_symlink_manifest_file_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw.json').write_text('data')
            manifest = build_manifest(root)
            (root / 'manifest-target.json').write_text(json.dumps(manifest))
            # Manifest itself must never be allowed to escape the evidence root.
            (root / 'EVIDENCE_MANIFEST.json').symlink_to(root / 'manifest-target.json')
            self.assertTrue(any('symlink' in issue for issue in verify_manifest(root, manifest)))


if __name__ == '__main__':
    unittest.main()
