"""Crash recovery (spec §33.2) and rebuild-equals-online property (spec §38.1)."""
import json
from pathlib import Path
import random
import shutil
import sqlite3
import tempfile
import unittest

from genesis.store import Store, rebuild_from_export


def random_history(root, rng, steps):
    with Store(root) as s:
        running = []
        for i in range(steps):
            op = rng.random()
            if op < 0.25:
                s.save(rng.choice(('world', 'claim', 'macro')), f'id{rng.randrange(50)}-{i}', {'v': rng.random()})
            elif op < 0.45:
                s.set_state(rng.choice(('phase', 'k1', 'k2')), rng.randrange(10))
            elif op < 0.7:
                running.append(s.start(f't{i}', {'i': i}))
            elif op < 0.9 and running:
                s.finish(running.pop(rng.randrange(len(running))), {'status': rng.choice(('SUCCESS', 'TIMEOUT'))})
            else:
                s.event('NOTE', {'i': i})
        return snapshot(s)


def snapshot(s):
    return {'state': sorted(s.db.execute('SELECT key,value FROM state').fetchall()),
            'entities': sorted(s.db.execute('SELECT * FROM entities').fetchall()),
            'attempts': sorted(s.db.execute('SELECT * FROM attempts').fetchall()),
            'head': s.verify()['head']}


class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_rebuild_equals_online_state_for_random_histories(self):
        rng = random.Random(20261010)
        for trial in range(25):
            root = self.base / f'r{trial}'
            online = random_history(root, rng, rng.randrange(1, 60))
            (root / 'campaign.sqlite3').unlink()
            rebuild_from_export(root)
            with Store(root) as s:
                self.assertEqual(snapshot(s), online, trial)

    def test_corrupted_database_is_rebuilt_and_quarantined(self):
        root = self.base / 'c'
        online = random_history(root, random.Random(1), 80)
        db = root / 'campaign.sqlite3'
        data = bytearray(db.read_bytes())
        data[4096:4096 + 512] = b'\xff' * 512   # smash a page
        db.write_bytes(bytes(data))
        with self.assertRaises(Exception):
            Store(root)
        record = rebuild_from_export(root)
        self.assertEqual(record['head'], online['head'])
        self.assertEqual(record['quarantined'], ['campaign.sqlite3'])
        self.assertTrue((Path(record['quarantine']) / 'campaign.sqlite3').exists())
        with Store(root) as s:
            self.assertEqual(snapshot(s), online)

    def test_partial_tail_is_dropped_and_preserved(self):
        root = self.base / 'p'
        random_history(root, random.Random(2), 20)
        export = root / 'events.jsonl'
        export.write_bytes(export.read_bytes() + b'{"hash":"abc","event":{"se')
        (root / 'campaign.sqlite3').unlink()
        record = rebuild_from_export(root)
        self.assertTrue(record['partial_tail_dropped'])
        self.assertTrue((Path(record['quarantine']) / 'events.jsonl.partial-tail').exists())
        with Store(root) as s:
            s.verify()

    def test_tampered_export_refuses_rebuild_without_moving_files(self):
        root = self.base / 't'
        random_history(root, random.Random(3), 20)
        export = root / 'events.jsonl'
        lines = export.read_bytes().split(b'\n')
        record = json.loads(lines[3]); record['event']['kind'] = 'FORGED'
        lines[3] = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
        export.write_bytes(b'\n'.join(lines))
        with self.assertRaises(RuntimeError):
            rebuild_from_export(root)
        self.assertTrue((root / 'campaign.sqlite3').exists())
        self.assertFalse((root / 'quarantine').exists())

    def test_missing_object_refuses_rebuild(self):
        root = self.base / 'm'
        random_history(root, random.Random(4), 20)
        victim = next((root / 'objects' / 'sha256').iterdir())
        victim.chmod(0o600); victim.unlink()
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            rebuild_from_export(root)

    def test_wal_sidecars_block_open_and_survive(self):
        root = self.base / 'w'
        random_history(root, random.Random(5), 5)
        (root / 'campaign.sqlite3-wal').write_bytes(b'legacy wal')
        with self.assertRaisesRegex(RuntimeError, 'WAL sidecar'):
            Store(root)
        self.assertEqual((root / 'campaign.sqlite3-wal').read_bytes(), b'legacy wal')
        rebuild_from_export(root)
        with Store(root) as s:
            s.verify()

    def test_rebuild_refuses_while_a_writer_holds_the_lock(self):
        root = self.base / 'l'
        random_history(root, random.Random(6), 5)
        with Store(root):
            with self.assertRaisesRegex(RuntimeError, 'active writer'):
                rebuild_from_export(root)

    def test_interrupted_attempts_become_interrupted_never_success(self):
        root = self.base / 'i'
        with Store(root) as s:
            aid = s.start('t', {'x': 1})
        with Store(root) as s:
            self.assertEqual(s.interrupt_running(), [aid])
            status = s.db.execute('SELECT status FROM attempts WHERE id=?', (aid,)).fetchone()[0]
            self.assertEqual(status, 'INTERRUPTED')


if __name__ == '__main__':
    unittest.main()


class CrossHostReopen(unittest.TestCase):
    def test_directory_copied_between_commits_reopens_cleanly(self):
        # Simulates the hosting runtime snapshotting a live campaign directory.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'live'
            with Store(root) as s:
                for i in range(40):
                    s.finish(s.start(f't{i}', {'i': i}), {'status': 'SUCCESS'})
                    if i in (9, 25, 39):
                        copy = Path(d) / f'copy{i}'
                        shutil.copytree(root, copy, ignore=shutil.ignore_patterns('writer.lock'))
            for i in (9, 25, 39):
                with Store(Path(d) / f'copy{i}') as c:
                    self.assertEqual(c.verify()['events'], 2 * (i + 1))
