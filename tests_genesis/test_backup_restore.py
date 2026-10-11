"""B15 / W04: store backup and restore."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

from genesis.backup import backup, restore
from genesis.campaign import Campaign
from genesis.common import canonical
from genesis.models import Config
from genesis.store import Store

ROOT = Path(__file__).resolve().parents[1]


def state_of(root):
    with Store(root) as s:
        return {'verify': s.verify(),
                'entities': sorted(s.db.execute('SELECT * FROM entities').fetchall()),
                'attempts': sorted(s.db.execute('SELECT * FROM attempts').fetchall()),
                'state': sorted(s.db.execute('SELECT * FROM state').fetchall())}


def rewrite(archive, out, change):
    """Copy a zip, letting `change(name, data)` return new bytes, None to drop, or a list of extra members."""
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(out, 'w') as dst:
        for info in src.infolist():
            data = change(info.filename, src.read(info.filename))
            if data is not None:
                dst.writestr(info.filename, data)


class BackupRestore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.campaign = cls.base / 'campaign'
        Campaign.initialize(cls.campaign, Config(seed=20261102, generations=1, tasks_per_panel=3,
                                                 proposals_per_epoch=2, research_trials=8))
        with Campaign(cls.campaign) as c:
            c.run()
        cls.archive = cls.base / 'campaign-backup.zip'
        cls.record = backup(cls.campaign, cls.archive)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def dest(self, name):
        return self.base / 'restores' / name

    def test_round_trip_reproduces_the_store(self):
        out = restore(self.archive, self.dest('round-trip'))
        self.assertEqual(out['event_head'], self.record['event_head'])
        self.assertEqual(state_of(self.dest('round-trip')), state_of(self.campaign))
        self.assertEqual((self.dest('round-trip') / 'events.jsonl').read_bytes(),
                         (self.campaign / 'events.jsonl').read_bytes())
        self.assertEqual((self.dest('round-trip') / 'resolved_config.json').read_bytes(),
                         (self.campaign / 'resolved_config.json').read_bytes())
        with Campaign(self.dest('round-trip')) as c:       # usable as a campaign, not just a store
            self.assertEqual(c.store.state('phase'), 'CANDIDATE_FROZEN')

    def test_backup_excludes_derived_files(self):
        with zipfile.ZipFile(self.archive) as z:
            names = z.namelist()
        self.assertNotIn('campaign.sqlite3', names)
        self.assertNotIn('writer.lock', names)
        self.assertFalse(any(n.startswith('snapshots/') or n.startswith('objects/tmp/') for n in names))
        self.assertIn('events.jsonl', names)

    def test_backup_needs_the_writer_lock(self):
        with Store(self.campaign):
            with self.assertRaisesRegex(RuntimeError, 'writer'):
                backup(self.campaign, self.base / 'concurrent.zip')
        self.assertFalse((self.base / 'concurrent.zip').exists())

    def test_restore_refuses_a_non_empty_destination(self):
        d = self.dest('occupied'); d.mkdir(parents=True); (d / 'x').write_text('keep')
        with self.assertRaises(FileExistsError):
            restore(self.archive, d)
        self.assertEqual((d / 'x').read_text(), 'keep')

    def test_expected_head_pins_the_restore(self):
        with self.assertRaisesRegex(ValueError, 'expected head'):
            restore(self.archive, self.dest('pinned-wrong'), expected_head='0' * 64)
        self.assertFalse(self.dest('pinned-wrong').exists())
        restore(self.archive, self.dest('pinned-right'), expected_head=self.record['event_head'])

    def assert_refused(self, name, change, pattern):
        bad = self.base / f'{name}.zip'
        rewrite(self.archive, bad, change)
        with self.assertRaisesRegex(ValueError, pattern):
            restore(bad, self.dest(name))
        self.assertFalse(self.dest(name).exists())
        self.assertEqual([p for p in (self.base / 'restores').iterdir() if p.name.startswith(f'.{name}.')]
                         if (self.base / 'restores').exists() else [], [])

    def test_tampered_member_refused(self):
        self.assert_refused('tampered', lambda n, d: d + b' ' if n == 'resolved_config.json' else d,
                            'hash differs from the manifest')

    def test_extra_member_refused(self):
        def add(n, d):
            return d
        bad = self.base / 'extra.zip'
        rewrite(self.archive, bad, add)
        with zipfile.ZipFile(bad, 'a') as z:
            z.writestr('extra.txt', b'x')
        with self.assertRaisesRegex(ValueError, 'differ from the backup manifest'):
            restore(bad, self.dest('extra'))

    def test_missing_object_refused(self):
        with zipfile.ZipFile(self.archive) as z:
            manifest = json.loads(z.read('MANIFEST.json'))
        victim = next(n for n in manifest['files'] if n.startswith('objects/sha256/'))
        manifest['files'].pop(victim)

        def drop(n, d):
            if n == victim:
                return None
            return canonical(manifest) if n == 'MANIFEST.json' else d
        bad = self.base / 'missing.zip'
        rewrite(self.archive, bad, drop)
        with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
            restore(bad, self.dest('missing'))
        self.assertFalse(self.dest('missing').exists())

    def test_consistently_rewritten_history_is_caught_by_the_pinned_head(self):
        # An attacker who rewrites events.jsonl must recompute the chain and the manifest;
        # local hashes then agree, so only a head recorded elsewhere catches it.
        with zipfile.ZipFile(self.archive) as z:
            manifest = json.loads(z.read('MANIFEST.json'))
            lines = z.read('events.jsonl').split(b'\n')[:-1]
        short = b'\n'.join(lines[:-1]) + b'\n'          # drop the last event: still a valid chain
        import hashlib
        manifest['files']['events.jsonl'] = hashlib.sha256(short).hexdigest()
        last = json.loads(lines[-2])
        manifest['event_head'], manifest['events'] = last['hash'], last['event']['seq']

        def change(n, d):
            return short if n == 'events.jsonl' else (canonical(manifest) if n == 'MANIFEST.json' else d)
        bad = self.base / 'rewritten.zip'
        rewrite(self.archive, bad, change)
        restore(bad, self.dest('rewritten-unpinned'))       # locally consistent
        with self.assertRaisesRegex(ValueError, 'expected head'):
            restore(bad, self.dest('rewritten-pinned'), expected_head=self.record['event_head'])

    def test_unsafe_member_names_refused(self):
        for i, evil in enumerate(('../escape', '/abs/path', 'a/../../b', 'objects\\x')):
            bad = self.base / f'evil{i}.zip'
            rewrite(self.archive, bad, lambda n, d: d)
            with zipfile.ZipFile(bad, 'a') as z:
                z.writestr(evil, b'x')
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                restore(bad, self.dest(f'evil{i}'))
        self.assertFalse((self.base / 'escape').exists())

    def test_symlink_member_refused(self):
        bad = self.base / 'symlink.zip'
        rewrite(self.archive, bad, lambda n, d: d)
        with zipfile.ZipFile(bad, 'a') as z:
            info = zipfile.ZipInfo('link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, b'/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'not a regular file'):
            restore(bad, self.dest('symlink'))

    def test_derived_database_in_backup_refused(self):
        with zipfile.ZipFile(self.archive) as z:
            manifest = json.loads(z.read('MANIFEST.json'))
        import hashlib
        db = (self.campaign / 'campaign.sqlite3').read_bytes()
        manifest['files']['campaign.sqlite3'] = hashlib.sha256(db).hexdigest()
        bad = self.base / 'with-db.zip'
        rewrite(self.archive, bad, lambda n, d: canonical(manifest) if n == 'MANIFEST.json' else d)
        with zipfile.ZipFile(bad, 'a') as z:
            z.writestr('campaign.sqlite3', db)
        with self.assertRaisesRegex(ValueError, 'derived'):
            restore(bad, self.dest('with-db'))

    def test_cli_round_trip(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        out = self.base / 'cli-backup.zip'
        subprocess.run([sys.executable, '-m', 'genesis', 'store', 'backup', str(self.campaign), '--out', str(out)],
                       env=env, check=True, capture_output=True)
        proc = subprocess.run([sys.executable, '-m', 'genesis', 'store', 'restore', str(self.dest('cli')), '--from',
                               str(out), '--expected-head', self.record['event_head']], env=env, capture_output=True,
                              text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['event_head'], self.record['event_head'])


if __name__ == '__main__':
    unittest.main()
