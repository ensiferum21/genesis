import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from genesis.store import Store
from genesis.evaluation import transition,paired,sign_test
from genesis.common import load_json


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_writer_lock(self):
        with Store(self.root):
            with self.assertRaises(RuntimeError):Store(self.root)

    def test_content_tampering_rejected(self):
        with Store(self.root) as s:
            h=s.put({'value':1});p=self.root/'objects/sha256'/h;p.chmod(0o600);p.write_text('forged')
            with self.assertRaises(RuntimeError):s.get(h)

    def test_event_corruption_rejected(self):
        with Store(self.root) as s:s.event('fixture',{'a':1})
        p=self.root/'events.jsonl';p.write_bytes(p.read_bytes().replace(b'fixture',b'FAKEONE'))
        with self.assertRaises(RuntimeError):Store(self.root)

    def test_outbox_recovery_after_partial_write(self):
        with Store(self.root) as s:s.event('fixture',{'a':1})
        p=self.root/'events.jsonl';full=p.read_bytes();p.write_bytes(full[:-9])
        with Store(self.root) as s:self.assertEqual(s.verify()['events'],1)
        self.assertEqual(p.read_bytes(),full)

    def test_interrupted_attempt_preserved_and_no_retry(self):
        with Store(self.root) as s:aid=s.start('trial',{'input':1})
        with Store(self.root) as s:
            self.assertEqual(s.interrupt_running(),[aid])
            row=s.db.execute('SELECT status,receipt FROM attempts').fetchone()
            self.assertEqual(row[0],'INTERRUPTED');self.assertTrue(s.get(row[1])['cost_unknown'])
            with self.assertRaises(ValueError):s.finish(aid,{'status':'SUCCESS'})

    def test_immutable_entities(self):
        with Store(self.root) as s:
            s.save('candidate','v1',{'x':1})
            with self.assertRaises(ValueError):s.save('candidate','v1',{'x':2})

    def test_large_state_snapshot_close_reopen(self):
        value={'exposure':[str(i).zfill(64) for i in range(500)],
               'summary':{'generations':[{'value':i} for i in range(600)]}}
        with Store(self.root) as s:
            for i in range(80):s.set_state('iteration',i)
            s.snapshot('before.sqlite3')
            s.set_state('final',value)
            snapshot=s.snapshot('final.sqlite3')
        self.assertFalse((self.root/'campaign.sqlite3-wal').exists())
        with Store(self.root) as s:
            self.assertEqual(s.state('final'),value)
            self.assertEqual(s.verify()['events'],81)
        with sqlite3.connect(snapshot) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(),[('ok',)])
            self.assertEqual(json.loads(db.execute("SELECT value FROM state WHERE key='final'").fetchone()[0]),value)

    def test_committed_state_survives_abrupt_process_exit(self):
        import subprocess,sys
        script="from genesis.store import Store;import os,sys;s=Store(sys.argv[1]);s.set_state('committed',{'value':42});os._exit(9)"
        result=subprocess.run([sys.executable,'-c',script,str(self.root)],capture_output=True)
        self.assertEqual(result.returncode,9,result.stderr)
        with Store(self.root) as s:
            self.assertEqual(s.state('committed'),{'value':42})
            self.assertEqual(s.verify()['events'],1)

    def test_state_machine_cannot_skip_gates(self):
        with Store(self.root) as s:
            with self.assertRaises(ValueError):transition(s,'RELEASED')
            transition(s,'VALIDATED_CONFIG');transition(s,'DEV_RUNNING');transition(s,'CANDIDATE_FROZEN')
            with self.assertRaises(PermissionError):transition(s,'LEAK_SCAN_PASSED',external_receipt={'passed':True})

    def test_duplicate_json_keys(self):
        p=self.root/'a.json';p.write_text('{"x":1,"x":2}')
        with self.assertRaises(ValueError):load_json(p)

    def test_mutated_derived_state_detected(self):
        with Store(self.root) as s:s.set_state('promotion_allowed',False)
        with sqlite3.connect(self.root/'campaign.sqlite3') as db:
            db.execute("UPDATE state SET value=? WHERE key='promotion_allowed'",(b'true',))
        with self.assertRaisesRegex(RuntimeError,'differs from'):Store(self.root)

    def test_exact_paired_and_cluster_statistics(self):
        self.assertEqual(sign_test(2,1),.5);self.assertEqual(sign_test(10,2),.019287109375)
        r=paired([{'task_id':str(i),'family':'single','candidate':1,'baseline':0} for i in range(10)])
        self.assertEqual(r['family_sensitivity_p'],.5)
        self.assertIsNone(r['confirmation_p_value'])
