import os
import tempfile
import unittest
from pathlib import Path
from evidence_custody import regular_beneath

class DescriptorCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)/'evidence'
        (self.base/'positive').mkdir(parents=True)
        (self.base/'positive'/'stdout.bin').write_bytes(b'ok')
    def test_reads_valid_file(self):
        self.assertEqual(regular_beneath(self.base,'positive','stdout.bin'),b'ok')
    def test_rejects_symlink_file(self):
        (self.base/'positive'/'stderr.bin').symlink_to('stdout.bin')
        with self.assertRaises((OSError,ValueError)):
            regular_beneath(self.base,'positive','stderr.bin')
    def test_rejects_symlink_directory(self):
        (self.base/'linked').symlink_to(self.base/'positive',target_is_directory=True)
        with self.assertRaises((OSError,ValueError)):
            regular_beneath(self.base,'linked','stdout.bin')
    def test_rejects_symlink_root(self):
        alias=Path(self.temp.name)/'alias';alias.symlink_to(self.base,target_is_directory=True)
        with self.assertRaises((OSError,ValueError)):
            regular_beneath(alias,'positive','stdout.bin')
    def test_rejects_symlink_ancestor(self):
        alias=Path(self.temp.name)/'alias';alias.symlink_to(self.base,target_is_directory=True)
        with self.assertRaises((OSError,ValueError)):
            regular_beneath(alias/'positive','stdout.bin')
    def test_rejects_traversal(self):
        for component in ('..','.','a/b','a\\b','\x00'):
            with self.subTest(component=component):
                with self.assertRaises(ValueError):regular_beneath(self.base,component,'stdout.bin')
    def test_rejects_fifo_without_blocking(self):
        os.mkfifo(self.base/'positive'/'fifo')
        with self.assertRaises(ValueError):regular_beneath(self.base,'positive','fifo')
    def test_rejects_oversized(self):
        with self.assertRaises(ValueError):regular_beneath(self.base,'positive','stdout.bin',max_bytes=1)
    def test_rejects_bad_bounds(self):
        for value in (-1,1.0,True,9*1024*1024):
            with self.assertRaises(ValueError):regular_beneath(self.base,'positive','stdout.bin',max_bytes=value)
    def test_rejects_missing(self):
        with self.assertRaises(ValueError):regular_beneath(self.base,'positive','missing')

if __name__=='__main__':unittest.main()
