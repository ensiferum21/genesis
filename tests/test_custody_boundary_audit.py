import unittest
from pathlib import Path
from scripts.custody_boundary_audit import inspect

class TestCustodyBoundaryAudit(unittest.TestCase):
    def test_legacy_sealed_store_fails_closed(self):
        result=inspect(Path(__file__).resolve().parents[1])
        self.assertEqual(result['status'],'BLOCK')
        self.assertFalse(result['independent_custody_proven'])
        self.assertTrue(any('callback' in r for r in result['reasons']))
