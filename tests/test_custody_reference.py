import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from custody_reference.evaluator import (ARMS, canonical, evaluate_frozen, file_sha, sha256,
                                         validate_expr, verify_bundle)


def program(op, **kwargs):
    return {'op':op,**kwargs}


class ReferenceCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pool=self.root/'private_pool.json'
        self.pool.write_bytes(canonical([{'id':'secret-A','features':{'x':2},'answer':4},
                                         {'id':'secret-B','features':{'x':3},'answer':6}]))
        self.candidates={}
        for arm in ARMS:
            path=self.root/f'{arm}.json'
            expr=(program('mul',a=program('input',name='x'),b=program('const',value=2))
                  if arm == 'V2p' else program('const',value=0))
            path.write_bytes(canonical({'expr':expr}))
            self.candidates[arm]=path
        self.prereg=self.root/'prereg.json'
        self.candidate_hashes={arm:file_sha(path) for arm,path in self.candidates.items()}
        self.prereg.write_bytes(canonical({'protocol':'genesis-reference-evaluator-v1',
                                          'pool_sha256':file_sha(self.pool),
                                          'candidate_sha256':self.candidate_hashes,
                                          'evaluation_budget_per_arm':2,
                                          'campaign_id':'synthetic-dev-only'}))
        self.reservation_dir=self.root/'reservations'
        self.reservation_dir.mkdir(mode=0o700); self.reservation_dir.chmod(0o700)
        from custody_reference.private_evidence import configure_semantics
        configure_semantics(self.reservation_dir,domain='synthetic-linear-v1',required_features=['x'],ignored_features=['unused'])
        self.private=Ed25519PrivateKey.generate()
        self.key=self.root/'private_key.pem'
        self.key.write_bytes(self.private.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        self.public=base64.b64encode(self.private.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()

    def evaluate(self):
        out=self.root/'out'
        result=evaluate_frozen(self.pool,self.candidates,self.prereg,self.key,out,
                               custodian_id='local-reference-not-independent',reservation_dir=self.reservation_dir)
        return out,result

    def test_end_to_end_signed_four_arm_bundle(self):
        out,r=self.evaluate()
        self.assertEqual(r['aggregate']['arms']['V2p']['correct'],2)
        self.assertEqual(r['aggregate']['arms']['D']['correct'],0)
        self.assertEqual(set(r['aggregate']['arms']),set(ARMS))
        self.assertEqual(verify_bundle(out,self.public,
            expected_prereg_sha256=file_sha(self.prereg),
            expected_pool_sha256=file_sha(self.pool),
            expected_candidate_hashes=self.candidate_hashes,
                          expected_task_count=2, expected_campaign_id='synthetic-dev-only',
                          expected_custodian_id='local-reference-not-independent',
                          expected_prereg_budget_per_arm=2, expected_prereg_bytes=self.prereg.read_bytes(), expected_evaluator_sha256=file_sha(Path(__file__).parents[1]/"custody_reference"/"evaluator.py"))['signature_valid'],True)
        for filename in ('aggregate.json','manifest.json','receipt.json'):
            self.assertNotIn('secret-A',(out/filename).read_text())
            self.assertNotIn('secret-B',(out/filename).read_text())
            self.assertNotIn('"features"',(out/filename).read_text())
        self.assertFalse(r['aggregate']['independent_custody_proven'])

    def test_same_prereg_cannot_run_twice(self):
        reservation_dir=self.reservation_dir
        evaluate_frozen(self.pool,self.candidates,self.prereg,self.key,self.root/'out1',
                        custodian_id='local-reference',reservation_dir=reservation_dir)
        with self.assertRaises(FileExistsError):
            evaluate_frozen(self.pool,self.candidates,self.prereg,self.key,self.root/'out2',
                            custodian_id='local-reference',reservation_dir=reservation_dir)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(reservation_dir/'sealed_attempts.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM reservations').fetchone()[0],2)

    def test_wrong_expected_evaluator_hash_rejected(self):
        out,_=self.evaluate()
        with self.assertRaises(ValueError):
            verify_bundle(out,self.public,expected_prereg_sha256=file_sha(self.prereg),
                          expected_pool_sha256=file_sha(self.pool),
                          expected_candidate_hashes=self.candidate_hashes,
                          expected_task_count=2, expected_campaign_id='synthetic-dev-only',
                          expected_custodian_id='local-reference-not-independent',
                          expected_prereg_budget_per_arm=2, expected_prereg_bytes=self.prereg.read_bytes(), expected_evaluator_sha256='0'*64)

    def test_tamper_aggregate_rejected(self):
        out,_=self.evaluate()
        p=out/'aggregate.json'; data=json.loads(p.read_text())
        data['arms']['V2p']['correct']=999
        p.write_bytes(canonical(data))
        with self.assertRaises(ValueError):
            verify_bundle(out,self.public,expected_prereg_sha256=file_sha(self.prereg),
                          expected_pool_sha256=file_sha(self.pool),
                          expected_candidate_hashes=self.candidate_hashes,
                          expected_task_count=2, expected_campaign_id='synthetic-dev-only',
                          expected_custodian_id='local-reference-not-independent',
                          expected_prereg_budget_per_arm=2, expected_prereg_bytes=self.prereg.read_bytes(), expected_evaluator_sha256=file_sha(Path(__file__).parents[1]/"custody_reference"/"evaluator.py"))

    def test_wrong_key_rejected(self):
        out,_=self.evaluate()
        other=Ed25519PrivateKey.generate()
        wrong=base64.b64encode(other.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        with self.assertRaises(Exception):
            verify_bundle(out,wrong,expected_prereg_sha256=file_sha(self.prereg),
                          expected_pool_sha256=file_sha(self.pool),
                          expected_candidate_hashes=self.candidate_hashes,
                          expected_task_count=2, expected_campaign_id='synthetic-dev-only',
                          expected_custodian_id='local-reference-not-independent',
                          expected_prereg_budget_per_arm=2, expected_prereg_bytes=self.prereg.read_bytes(), expected_evaluator_sha256=file_sha(Path(__file__).parents[1]/"custody_reference"/"evaluator.py"))

    def test_changed_candidate_after_prereg_rejected(self):
        self.candidates['V2p'].write_bytes(canonical({'expr':program('const',value=99)}))
        with self.assertRaisesRegex(ValueError,'preregistration'):
            self.evaluate()

    def test_changed_pool_after_prereg_rejected(self):
        self.pool.write_bytes(canonical([{'id':'other','features':{'x':1},'answer':2}]))
        with self.assertRaisesRegex(ValueError,'preregistration'):
            self.evaluate()

    def test_missing_or_extra_arm_rejected(self):
        self.candidates.pop('D')
        with self.assertRaisesRegex(ValueError,'exactly four'):
            self.evaluate()

    def test_no_python_execution_expression(self):
        for bad in ({'op':'__import__','value':'os'},
                    {'op':'const','value':'__import__("os")'},
                    {'op':'input','name':'../../private_key.pem'},
                    {'op':'const','value':True}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_expr(bad)

    def test_depth_and_size_rejected(self):
        deep=program('const',value=1)
        for _ in range(15):
            deep=program('add',a=deep,b=program('const',value=1))
        with self.assertRaises(ValueError):validate_expr(deep)

    def test_duplicate_task_ids_rejected(self):
        self.pool.write_bytes(canonical([{'id':'same','features':{},'answer':1}]*2))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.evaluate()

    def test_budget_fails_closed(self):
        prereg=json.loads(self.prereg.read_text());prereg['evaluation_budget_per_arm']=1
        self.prereg.write_bytes(canonical(prereg))
        with self.assertRaisesRegex(ValueError,'budget'):
            self.evaluate()

    @unittest.skipUnless(os.geteuid()==0 and Path('/usr/bin/setpriv').exists(),
                         'requires Linux root and setpriv for real UID permission test')
    def test_research_uid_cannot_read_private_pool_or_key(self):
        # Test only a same-host DAC barrier; root/operator and side channels remain trusted.
        probe=subprocess.run(['/usr/bin/setpriv','--reuid=65534','--regid=65534','--clear-groups','/usr/bin/true'],capture_output=True,text=True)
        if probe.returncode and 'setresuid failed' in probe.stderr:
            self.skipTest('environment cannot switch to research UID; isolation remains UNVERIFIED')
        self.root.chmod(0o700)
        self.pool.chmod(0o600)
        self.key.chmod(0o600)
        for private in (self.pool,self.key):
            proc=subprocess.run(['/usr/bin/setpriv','--reuid=65534','--regid=65534',
                                 '--clear-groups',sys.executable,'-c',
                                 'import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()',
                                 str(private)],capture_output=True,text=True,timeout=5)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('PermissionError',proc.stderr)

if __name__=='__main__': unittest.main()
