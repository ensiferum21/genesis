import tempfile,unittest
from pathlib import Path
from gap_engine.kernel.lean_custody.evidence_custody import regular_beneath

class CustodyTests(unittest.TestCase):
    def test_regular(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'positive').mkdir();(p/'positive'/'stdout.bin').write_bytes(b'ok')
            self.assertEqual(regular_beneath(p,'positive','stdout.bin'),b'ok')
    def test_symlinked_directory(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'actual').mkdir();(p/'actual'/'stdout.bin').write_bytes(b'ok');(p/'positive').symlink_to(p/'actual',target_is_directory=True)
            with self.assertRaises(ValueError):regular_beneath(p,'positive','stdout.bin')
    def test_symlinked_file(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'actual').write_bytes(b'ok');(p/'positive').mkdir();(p/'positive'/'stdout.bin').symlink_to(p/'actual')
            with self.assertRaises(ValueError):regular_beneath(p,'positive','stdout.bin')
    def test_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):regular_beneath(t,'..','secret')
    def test_oversize(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_bytes(b'a'*9)
            with self.assertRaises(ValueError):regular_beneath(p,'x',max_bytes=8)
    def test_missing(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):regular_beneath(t,'missing')
if __name__=='__main__':unittest.main()
