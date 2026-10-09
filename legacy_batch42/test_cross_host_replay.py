import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cross_host_replay import compare

H=lambda x:hashlib.sha256(x).hexdigest()
EXE=H(b'lean');P=H(b'positive');N=H(b'negative')

def fixture(root, label):
    root.mkdir()
    (root/'evidence').mkdir()
    pair={'status':'DEV_CANARY_PAIR_PASS','promotion_allowed':False}
    for name,code,status,proof in [('positive',0,'DEV_REPLAY_PASS',True),('negative',1,'REPLAY_REJECTED',False)]:
        d=root/'evidence'/name;d.mkdir()
        (d/'stdout.bin').write_bytes(b'')
        (d/'stderr.bin').write_bytes(b'')
        pair[name]={'schema':'genesis-real-lean-attempt-v1','promotion_allowed':False,
                    'manifest_sha256':P if name=='positive' else N,
                    'status':status,'proof_replayed':proof,
                    'evidence':{'lean_sha256':EXE,'exit_code':code,'stdout_sha256':H(b''),'stderr_sha256':H(b''),'stdout_bytes':0,'stderr_bytes':0}}
    (root/'pair.json').write_text(json.dumps(pair))
    (root/'SUMMARY.json').write_text(json.dumps({'pair_status':'DEV_CANARY_PAIR_PASS','receipt_status':'DEV_CANARY_RECEIPTS_CONSISTENT','promotion_allowed':False}))
    return pair

class CrossHostTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.a=Path(self.t.name)/'a';self.b=Path(self.t.name)/'b'
        fixture(self.a,'a');fixture(self.b,'b')
    def check(self):return compare(self.a,self.b,EXE,P,N)
    def test_two_runs_consistent_but_not_independent(self):
        x=self.check();self.assertEqual(x['status'],'DEV_TWO_RUNS_CONSISTENT');self.assertFalse(x['promotion_allowed']);self.assertFalse(x['independent_hosts_verified'])
    def test_same_run_rejected(self):self.assertEqual(compare(self.a,self.a,EXE,P,N)['status'],'BLOCKED')
    def test_wrong_binary_pin(self):self.assertEqual(compare(self.a,self.b,H(b'fake'),P,N)['status'],'BLOCKED')
    def test_wrong_manifest_pin(self):self.assertEqual(compare(self.a,self.b,EXE,H(b'fake'),N)['status'],'BLOCKED')
    def test_tampered_raw_stream(self):
        (self.b/'evidence'/'positive'/'stdout.bin').write_bytes(b'tampered');self.assertEqual(self.check()['status'],'BLOCKED')
    def test_tampered_pair(self):
        pair=json.loads((self.b/'pair.json').read_text());pair['negative']['evidence']['exit_code']=0
        (self.b/'pair.json').write_text(json.dumps(pair));self.assertEqual(self.check()['status'],'BLOCKED')
    def test_summary_not_verified(self):
        s=json.loads((self.b/'SUMMARY.json').read_text());s['receipt_status']='BLOCKED'
        (self.b/'SUMMARY.json').write_text(json.dumps(s));self.assertEqual(self.check()['status'],'BLOCKED')
    def test_symlink_metadata(self):
        (self.b/'pair.json').unlink();(self.b/'pair.json').symlink_to(self.a/'pair.json');self.assertEqual(self.check()['status'],'BLOCKED')
    def test_missing_receipt(self):
        (self.b/'evidence'/'negative'/'stderr.bin').unlink();self.assertEqual(self.check()['status'],'BLOCKED')
    def test_no_self_report_independence(self):
        s=json.loads((self.a/'SUMMARY.json').read_text());s['independent_hosts_verified']=True
        (self.a/'SUMMARY.json').write_text(json.dumps(s));self.assertFalse(self.check().get('independent_hosts_verified',True))

if __name__=='__main__':unittest.main()
