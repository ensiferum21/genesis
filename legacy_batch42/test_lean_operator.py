import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lean_operator import execute, main

class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'run'
    def test_invalid_hash_does_not_create_workdir(self):
        with self.assertRaises(ValueError):execute(self.root,'leanprover/lean4:v4.15.0','0'*63)
        self.assertFalse(self.root.exists())
    def test_invalid_toolchain_does_not_create_workdir(self):
        with self.assertRaises(ValueError):execute(self.root,'latest','a'*64)
        self.assertFalse(self.root.exists())
    def test_existing_directory_rejected(self):
        self.root.mkdir()
        with self.assertRaises(ValueError):execute(self.root,'leanprover/lean4:v4.15.0','a'*64)
    def test_blocked_pair_still_emits_summary(self):
        with patch('lean_operator.check_pair',return_value={'status':'BLOCKED','reason':'missing Lean'}):
            result=execute(self.root,'leanprover/lean4:v4.15.0','a'*64)
        self.assertEqual(result['pair_status'],'BLOCKED')
        self.assertFalse(result['promotion_allowed'])
        self.assertEqual(json.loads((self.root/'verification.json').read_text())['status'],'BLOCKED')
    def test_pass_still_no_scientific_promotion(self):
        with patch('lean_operator.check_pair',return_value={'status':'DEV_CANARY_PAIR_PASS'}),patch('lean_operator.verify_pair',return_value={'status':'DEV_CANARY_RECEIPTS_CONSISTENT'}):
            result=execute(self.root,'leanprover/lean4:v4.15.0','a'*64)
        self.assertFalse(result['independent_proof_replay_verified'])
        self.assertEqual(result['research_claim'],'NONE')
    def test_cli_fails_closed(self):
        self.assertEqual(main(['--workdir',str(self.root),'--toolchain','latest','--trusted-lean-sha256','a'*64]),2)

if __name__=='__main__':unittest.main()
