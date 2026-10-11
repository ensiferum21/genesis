"""B15 internal red-team pass: regressions for what attacking the new surfaces found.

R1  recover() adopted any file at public_receipt.json naming the request id.
R2  backups dropped quarantined database files (forensic history) by name.
R3  restore followed a destination symlink.
R4  the pin history could be deleted and re-initialised from any pins.
R5  a resumed run that no longer reproduces its frozen successor must abort, not re-freeze.
"""
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from genesis.backup import backup, restore
from genesis.campaign import Campaign
from genesis.common import canonical
from genesis.custodian import recover, sign
from genesis import deployment as D
from genesis.models import Config, SolverProgram
from genesis.store import Store, rebuild_from_export
from tests_genesis.test_crash_consistency import CFG, CustodianCrashes, crash, events

B14_R1_PINS_SHA256 = '9d6982ad0b738296f299f1c1a271b324f7fe268d2834a5680a8659af863e9533'


class R1ForgedPublishedReceipt(CustodianCrashes):
    def _forge(self, payload_edit, key=None):
        self.run_evaluation('custodian.publish')
        path = self.root / 'evaluations' / self.rid / 'public_receipt.json'
        receipt = json.loads(path.read_bytes())
        payload = dict(receipt['payload'], **payload_edit)
        if key is None:
            forged = {'payload': payload, 'signature': receipt['signature']}       # signature no longer matches
        else:
            forged = sign(payload, key)
        path.write_bytes(canonical(forged))

    def test_tampered_published_receipt_is_not_adopted(self):
        self._forge({'outcome': 'SUPPORTED', 'wins': 2, 'losses': 0})
        with self.assertRaisesRegex(RuntimeError, 'does not verify'):
            recover(self.root, self.rid, self.pool, self.key, 'fixture')

    def test_receipt_signed_by_another_key_is_not_adopted(self):
        other = Path(self.tmp.name) / 'other.pem'
        other.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self._forge({}, key=other)
        with self.assertRaisesRegex(RuntimeError, 'does not verify'):
            recover(self.root, self.rid, self.pool, self.key, 'fixture')

    # The inherited crash tests are covered in test_crash_consistency; skip re-running them here.
    test_crash_after_reservation_publishes_an_invalid_receipt = None
    test_crash_mid_evaluation_publishes_an_invalid_receipt = None
    test_crash_after_signing_publishes_the_complete_result = None
    test_crash_after_publishing_keeps_the_published_receipt = None
    test_recover_requires_the_committed_pool = None
    test_nothing_to_recover_before_reservation = None


class R2R3BackupEdges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'c'
        with Store(self.root) as s:
            s.save('k', 'a', {'v': 1})
        (self.root / 'campaign.sqlite3').unlink()          # simulate loss; rebuild quarantines nothing yet
        rebuild_from_export(self.root)
        with Store(self.root) as s:
            s.save('k', 'b', {'v': 2})
        # Put a corrupt database into quarantine the way a real rebuild does.
        (self.root / 'campaign.sqlite3-wal').write_bytes(b'junk')
        record = rebuild_from_export(self.root)
        self.quarantine = Path(record['quarantine'])

    def test_quarantined_databases_are_backed_up_and_restored(self):
        rel = self.quarantine.relative_to(self.root)
        self.assertTrue((self.quarantine / 'campaign.sqlite3').exists())
        backup(self.root, self.base / 'b.zip')
        restore(self.base / 'b.zip', self.base / 'r')
        for name in ('campaign.sqlite3', 'campaign.sqlite3-wal'):
            self.assertEqual((self.base / 'r' / rel / name).read_bytes(), (self.quarantine / name).read_bytes())

    def test_restore_refuses_a_symlinked_destination(self):
        backup(self.root, self.base / 'b.zip')
        target = self.base / 'elsewhere'; target.mkdir()
        link = self.base / 'link'; link.symlink_to(target)
        with self.assertRaisesRegex(FileExistsError, 'symlink'):
            restore(self.base / 'b.zip', link)
        self.assertEqual(list(target.iterdir()), [])


class R4PinHistoryAnchor(unittest.TestCase):
    def test_history_starts_at_the_b14_r1_pins(self):
        first = D.read_history()[0][1]
        self.assertEqual((first['seq'], first['prev']), (1, None))
        self.assertEqual(first['pins_sha256'], B14_R1_PINS_SHA256)


class R5ResumeDivergence(unittest.TestCase):
    def test_resume_that_would_freeze_a_different_successor_aborts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(**CFG))
            crash(self, '''
                from genesis.campaign import Campaign
                with Campaign(P['root']) as c: c.run()
            ''', 'campaign.frozen', root=str(root))
            import genesis.campaign as cm
            real = cm.propose

            def different(parent, *a, **k):
                return [SolverProgram(weights=(3, 1, 2, 0), rounds=parent.rounds) for _ in real(parent, *a, **k)]
            with mock.patch.object(cm, 'propose', different), Campaign(root) as c:
                # Either the immutable research record or the frozen-successor check stops it.
                with self.assertRaisesRegex((RuntimeError, ValueError), 'diverged|immutable entity identity reused'):
                    c.run(resume=True)
                self.assertEqual(c.store.state('phase'), 'ABORTED')
                frozen = events(c.store, 'DEV_SUCCESSOR_FROZEN')
            self.assertEqual(len(frozen), 1)        # never re-frozen


if __name__ == '__main__':
    unittest.main()
