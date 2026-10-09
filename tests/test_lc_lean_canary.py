import hashlib, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from gap_engine.kernel.lean_custody.lean_canary import make_project, check_pair, POSITIVE, NEGATIVE
from gap_engine.kernel.lean_custody.replay_package import audit

TC='leanprover/lean4:v4.15.0'
class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.p=root/'p';self.n=root/'n'
        self.pm,self.ph=make_project(self.p,TC,POSITIVE)
        self.nm,self.nh=make_project(self.n,TC,NEGATIVE)
    def test_manifest_audit_both(self):
        for root,manifest,pin in ((self.p,self.pm,self.ph),(self.n,self.nm,self.nh)):
            self.assertTrue(audit(root,Path(manifest).read_bytes(),pin)['verified'])
    def test_tamper_detected(self):
        (self.p/'Main.lean').write_text('theorem x : True := by trivial\n')
        with self.assertRaises(ValueError):audit(self.p,Path(self.pm).read_bytes(),self.ph)
    def test_pair_success(self):
        with patch('gap_engine.kernel.lean_custody.lean_canary.run',side_effect=[{'status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED','proof_replayed':False,'evidence':{'exit_code':0}},{'status':'REPLAY_REJECTED','proof_replayed':False,'evidence':{'exit_code':1}}]) as f:
            result=check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm)
        self.assertEqual(result['status'],'DEV_CANARY_PAIR_PASS');self.assertEqual(f.call_count,2)
    def test_negative_accepted_blocks(self):
        with patch('gap_engine.kernel.lean_custody.lean_canary.run',side_effect=[{'status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED','proof_replayed':False,'evidence':{'exit_code':0}},{'status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED','proof_replayed':False,'evidence':{'exit_code':0}}]):
            result=check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm)
        self.assertEqual(result['status'],'BLOCKED')
    def test_negative_nonexecution_blocks(self):
        with patch('gap_engine.kernel.lean_custody.lean_canary.run',side_effect=[{'status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED','proof_replayed':False,'evidence':{'exit_code':0}},{'status':'BLOCKED','evidence':{}}]):
            result=check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm)
        self.assertEqual(result['status'],'BLOCKED')
    def test_positive_failure_stops(self):
        with patch('gap_engine.kernel.lean_custody.lean_canary.run',return_value={'status':'BLOCKED'}) as f:
            result=check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm)
        self.assertEqual(f.call_count,1);self.assertEqual(result['status'],'BLOCKED')
    def test_same_project_blocks(self):
        self.assertEqual(check_pair(self.p,self.p,'a'*64,self.ph,self.nh,self.pm,self.nm)['status'],'BLOCKED')
    def test_same_manifest_blocks(self):
        self.assertEqual(check_pair(self.p,self.n,'a'*64,self.ph,self.ph,self.pm,self.nm)['status'],'BLOCKED')
    def test_existing_evidence_root_blocks(self):
        self.assertEqual(check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm,self.tmp.name)['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
