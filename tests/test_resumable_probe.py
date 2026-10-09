"""DEV-only bounded theme orchestration tests; no sealed tasks read."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from scripts.probe_extended_resumable import cache_valid, config_fingerprint, run_resumable


class TestResumableProbe(unittest.TestCase):
    def test_cache_is_hash_and_config_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pool, proof, meta = root / 'x.json', root / 'x_proofs.json', root / 'x.meta.json'
            pool.write_text(json.dumps({'params': {'themes': ['snoc_rev']}, 'tasks': ['Z = Z']}))
            proof.write_text(json.dumps({'proofs': {'Z = Z': {'rule': 'rewrite'}}}))
            import hashlib
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            meta.write_text(json.dumps({'status': 'COMPLETE_DEV_ONLY', 'theme': 'snoc_rev',
                'config_sha256': 'expected', 'pool_sha256': digest(pool), 'proof_sha256': digest(proof)}))
            self.assertTrue(cache_valid(meta, pool, proof, 'expected', 'snoc_rev'))
            self.assertFalse(cache_valid(meta, pool, proof, 'changed', 'snoc_rev'))
            proof.write_text('{}')
            self.assertFalse(cache_valid(meta, pool, proof, 'expected', 'snoc_rev'))

    def test_pending_themes_are_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            history = root / 'history.json'
            history.write_text('{"tasks": []}')
            r = run_resumable(root / 'runs', [history], max_size=3, max_terms=15,
                              themes=['snoc_rev', 'mapdouble'], max_new_themes=0)
            self.assertEqual(r['status'], 'DEV_ONLY_PARTIAL')
            self.assertEqual(r['completed_themes'], [])
            self.assertEqual(len(r['failed_or_pending_themes']), 2)
            self.assertFalse(r['promotion_allowed'])

    def test_worker_timeout_is_checkpointed_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            history = root / 'history.json'
            history.write_text('{"tasks": []}')
            with patch('scripts.probe_extended_resumable.subprocess.run',
                       side_effect=subprocess.TimeoutExpired(cmd='worker', timeout=1)):
                r = run_resumable(root / 'runs', [history], max_size=3, max_terms=15,
                                  themes=['snoc_rev'], timeout=1)
            self.assertEqual(r['status'], 'DEV_ONLY_PARTIAL')
            self.assertEqual(r['completed_themes'], [])
            self.assertEqual(r['failed_or_pending_themes'][0]['reason'], 'TIMEOUT')
            self.assertTrue((Path(r['run_dir']) / 'progress.json').exists())

    def test_invalid_limits_and_themes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run_resumable(Path(d), [], timeout=0)
            with self.assertRaises(ValueError):
                run_resumable(Path(d), [], themes=['snoc_rev', 'snoc_rev'])


if __name__ == '__main__':
    unittest.main()
