import copy, hashlib, tempfile, unittest
from pathlib import Path
from gap_engine.kernel.lean_custody.canary_receipts import verify_pair
A='a'*64;P='b'*64;N='c'*64
class PairReceipts(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.pair={'status':'DEV_CANARY_PAIR_PASS','promotion_allowed':False}
  for label,pin,code in [('positive',P,0),('negative',N,1)]:
   d=self.root/label;d.mkdir()
   for stream in ('stdout','stderr'):(d/(stream+'.bin')).write_bytes(b'')
   self.pair[label]={'schema':'genesis-real-lean-attempt-v1','promotion_allowed':False,'manifest_sha256':pin,'status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED' if code==0 else 'REPLAY_REJECTED','proof_replayed':False,'evidence':{'lean_sha256':A,'exit_code':code,**{x+y:v for x in ('stdout','stderr') for y,v in [('_sha256',hashlib.sha256(b'').hexdigest()),('_bytes',0)]}}}
 def check(self):return verify_pair(self.pair,self.root,A,P,N)
 def test_consistent(self):self.assertEqual(self.check()['status'],'DEV_CANARY_RECEIPTS_CONSISTENT')
 def test_no_promotion(self):self.assertFalse(self.check()['promotion_allowed'])
 def test_forged_negative(self):self.pair['negative']['evidence']['exit_code']=0;self.assertEqual(self.check()['status'],'BLOCKED')
 def test_forged_positive(self):self.pair['positive']['proof_replayed']=True;self.assertEqual(self.check()['status'],'BLOCKED')
 def test_negative_missing(self):(self.root/'negative'/'stderr.bin').unlink();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_tampered_stream(self):(self.root/'positive'/'stdout.bin').write_bytes(b'changed');self.assertEqual(self.check()['status'],'BLOCKED')
 def test_wrong_manifest(self):self.pair['negative']['manifest_sha256']=P;self.assertEqual(self.check()['status'],'BLOCKED')
 def test_wrong_executable(self):self.pair['positive']['evidence']['lean_sha256']=N;self.assertEqual(self.check()['status'],'BLOCKED')
 def test_symlink(self):
  f=self.root/'positive'/'stdout.bin';f.unlink();f.symlink_to(self.root/'positive'/'stderr.bin');self.assertEqual(self.check()['status'],'BLOCKED')
 def test_oversize(self):(self.root/'negative'/'stdout.bin').write_bytes(b'x'*(1024*1024+1));self.assertEqual(self.check()['status'],'BLOCKED')
 def test_legacy_false_proof_receipt_blocked(self):
  self.pair['positive']['status']='DEV_REPLAY_PASS';self.pair['positive']['proof_replayed']=True
  self.assertEqual(self.check()['status'],'BLOCKED')
 def test_bad_promotion(self):self.pair['promotion_allowed']=True;self.assertEqual(self.check()['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
