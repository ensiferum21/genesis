import json
from pathlib import Path
import tempfile
import unittest
from scripts.evidence_manifest import build_manifest, verify_manifest

class TestEvidenceManifest(unittest.TestCase):
    def test_manifest_detects_tamper_and_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'a.txt').write_text('alpha')
            (root/'b.txt').write_text('beta')
            manifest=build_manifest(root)
            (root/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_manifest(root,manifest), [])
            (root/'a.txt').write_text('changed')
            self.assertTrue(any('changed: a.txt' in x for x in verify_manifest(root,manifest)))
            (root/'a.txt').unlink()
            self.assertTrue(any('missing: a.txt' in x for x in verify_manifest(root,manifest)))
            (root/'c.txt').write_text('unexpected')
            self.assertTrue(any('unexpected: c.txt' in x for x in verify_manifest(root,manifest)))
            manifest['files']['b.txt']['bytes'] += 1
            self.assertIn('manifest root mismatch',verify_manifest(root,manifest))

if __name__=='__main__':
    unittest.main()
