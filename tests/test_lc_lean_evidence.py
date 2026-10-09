import copy,hashlib,json,pathlib,tempfile,unittest
from gap_engine.kernel.lean_custody.lean_evidence import verify,sha
A='a'*64;B='b'*64
class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=pathlib.Path(self.t.name)
  (self.p/'out').write_bytes(b'');(self.p/'err').write_bytes(b'')
  self.r={'schema':'genesis-real-lean-attempt-v1','status':'DEV_LEAN_EXIT_ZERO_UNTRUSTED','proof_replayed':False,'promotion_allowed':False,'manifest_sha256':B,'evidence':{'lean_sha256':A,'exit_code':0,'stdout_sha256':sha(b''),'stderr_sha256':sha(b''),'stdout_bytes':0,'stderr_bytes':0}}
  self.save()
 def save(self):(self.p/'receipt').write_text(json.dumps(self.r))
 def check(self):return verify(self.p/'receipt',self.p/'out',self.p/'err',A,B)
 def test_consistent_dev(self):self.assertEqual(self.check()['status'],'DEV_EXIT_RECEIPT_CONSISTENT')
 def test_no_promotion(self):self.assertFalse(self.check()['promotion_allowed'])
 def test_changed_output(self):(self.p/'out').write_text('tamper');self.assertEqual(self.check()['status'],'BLOCKED')
 def test_wrong_binary(self):self.r['evidence']['lean_sha256']=B;self.save();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_wrong_manifest(self):self.r['manifest_sha256']=A;self.save();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_failed_exit(self):self.r['evidence']['exit_code']=1;self.save();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_fabricated_promotion(self):self.r['promotion_allowed']=True;self.save();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_legacy_false_proof_receipt_blocked(self):
  self.r['status']='DEV_REPLAY_PASS';self.r['proof_replayed']=True;self.save()
  self.assertEqual(self.check()['status'],'BLOCKED')
 def test_missing_receipt(self):(self.p/'receipt').unlink();self.assertEqual(self.check()['status'],'BLOCKED')
 def test_symlink_stream(self):(self.p/'out').unlink();(self.p/'out').symlink_to(self.p/'err');self.assertEqual(self.check()['status'],'BLOCKED')
 def test_missing_external_pin(self):self.assertEqual(verify(self.p/'receipt',self.p/'out',self.p/'err','',B)['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
