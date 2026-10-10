"""GEN-AUD-027 local negative tests for repeat use of synthetic sealed tasks.

No real sealed data or externally controlled custody. These tests exercise only
custodian-side replay protection; not a claim of independently held secrets.
"""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest
from custody_reference.evaluator import canonical, evaluate_frozen, file_sha
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


class TestCustodianTaskReservation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pool=self.root/'pool.json'
        self.pool.write_bytes(canonical([
            {'id':'dev-A','features':{'x':2},'answer':4},
            {'id':'dev-B','features':{'x':3},'answer':6},
        ]))
        self.candidates={}
        for arm in ('D','U','V2n','V2p'):
            p=self.root/f'{arm}.json'
            p.write_bytes(canonical({'expr':{'op':'const','value':0}}))
            self.candidates[arm]=p
        self.prereg=self.root/'prereg.json'
        self.prereg.write_bytes(canonical({
            'protocol':'genesis-reference-evaluator-v1',
            'pool_sha256':file_sha(self.pool),
            'candidate_sha256':{arm:file_sha(p) for arm,p in self.candidates.items()},
            'evaluation_budget_per_arm':2,'campaign_id':'dev-first',
        }))
        self.key=self.root/'key.pem'
        self.key.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        self.reservation_dir=self.root/'reservations'
        self.reservation_dir.mkdir(mode=0o700); self.reservation_dir.chmod(0o700)
        from custody_reference.private_evidence import configure_semantics
        configure_semantics(self.reservation_dir,domain='synthetic-linear-v1',required_features=['x'],ignored_features=['unused'])

    def run_eval(self, name, *, pool=None, prereg=None, reservation_dir=None):
        x = self
        return evaluate_frozen(pool or x.pool, x.candidates, prereg or x.prereg,
                               x.key, x.root / name, custodian_id='local-reference',
                               reservation_dir=x.reservation_dir if reservation_dir is None else reservation_dir)

    def rewrite_prereg(self, **changes):
        x=self
        p=json.loads(x.prereg.read_bytes());p.update(changes)
        x.prereg.write_bytes(canonical(p))

    def test_unreserved_evaluation_fails_closed(self):
        x=self
        with self.assertRaisesRegex(ValueError,'reservation directory required'):
            evaluate_frozen(x.pool,x.candidates,x.prereg,x.key,x.root/'out',
                            custodian_id='local-reference')
        self.assertFalse((x.root/'out').exists())

    def test_same_pool_different_campaign_cannot_run_again(self):
        self.run_eval('out1')
        self.rewrite_prereg(campaign_id='new-campaign-same-pool')
        with self.assertRaisesRegex(FileExistsError,'already reserved'):
            self.run_eval('out2')

    def test_same_pool_different_candidate_cannot_run_again(self):
        x=self
        self.run_eval('out1')
        x.candidates['V2p'].write_bytes(canonical({'expr':{'op':'const','value':3}}))
        h={arm:file_sha(p) for arm,p in x.candidates.items()}
        self.rewrite_prereg(candidate_sha256=h)
        with self.assertRaisesRegex(FileExistsError,'already reserved'):
            self.run_eval('out2')

    def test_renamed_reordered_pool_cannot_run_again(self):
        x=self
        self.run_eval('out1')
        pool=json.loads(x.pool.read_bytes())[::-1]
        for i,t in enumerate(pool):t['id']=f'renamed-{i}'
        x.pool.write_bytes(canonical(pool))
        self.rewrite_prereg(pool_sha256=file_sha(x.pool),campaign_id='different-campaign')
        with self.assertRaisesRegex(FileExistsError,'already reserved'):
            self.run_eval('out2')

    def test_partial_overlap_cannot_run_again(self):
        x=self
        self.run_eval('out1')
        pool=json.loads(x.pool.read_bytes())
        pool=[pool[0],{'id':'new-task','features':{'x':7},'answer':14}]
        x.pool.write_bytes(canonical(pool))
        self.rewrite_prereg(pool_sha256=file_sha(x.pool),campaign_id='partial-overlap')
        with self.assertRaisesRegex(FileExistsError,'already reserved'):
            self.run_eval('out2')

    def test_disjoint_pool_with_new_prereg_is_allowed_in_dev(self):
        x=self
        self.run_eval('out1')
        x.pool.write_bytes(canonical([{'id':'new-1','features':{'x':70},'answer':140}]))
        self.rewrite_prereg(pool_sha256=file_sha(x.pool),campaign_id='disjoint-campaign')
        self.run_eval('out2')
        self.assertTrue((x.root/'out2'/'receipt.json').exists())

    def test_duplicate_content_with_different_ids_rejected(self):
        x=self
        task=json.loads(x.pool.read_bytes())[0]
        x.pool.write_bytes(canonical([task,{'id':'other-id','features':task['features'],
                                            'answer':task['answer']}]))
        self.rewrite_prereg(pool_sha256=file_sha(x.pool))
        with self.assertRaisesRegex(ValueError,'duplicate sealed task contents'):
            self.run_eval('out1')

    def test_symlink_reservation_dir_rejected(self):
        x=self
        link=x.root/'reservations_link';link.symlink_to(x.reservation_dir,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'preexist and not be a symlink'):
            self.run_eval('out1',reservation_dir=link)

    def test_failed_signing_consumes_attempt_and_blocks_retry(self):
        x=self
        x.key.write_bytes(b'not-a-valid-Ed25519-key')
        with self.assertRaises(ValueError):
            self.run_eval('bad_signer')
        x.key.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        with self.assertRaisesRegex(FileExistsError,'already reserved'):
            self.run_eval('retry_forbidden')

    def test_group_writable_reservation_dir_rejected(self):
        import os
        if os.name != 'posix': self.skipTest('POSIX owner-mode check')
        x=self
        x.reservation_dir.chmod(0o770)
        with self.assertRaisesRegex(ValueError,'owner-controlled'):
            self.run_eval('unsafe_dir')

    def test_group_readable_reservation_dir_rejected(self):
        import os
        if os.name != 'posix': self.skipTest('POSIX owner-mode check')
        self.reservation_dir.chmod(0o750)
        with self.assertRaisesRegex(ValueError,'owner-controlled'):
            self.run_eval('readable_dir')

    def test_concurrent_same_task_claim_exactly_one_succeeds(self):
        x=self
        def run(i):
            try:
                self.run_eval(f'out{i}')
                return 'success'
            except FileExistsError:
                return 'duplicate'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(run, range(2)))
        self.assertCountEqual(result,['success','duplicate'])


if __name__=='__main__': unittest.main()
