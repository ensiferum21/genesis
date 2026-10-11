"""B15 / W04: toolchain pins change only through a hash-chained, known-answer-gated revision."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from genesis import deployment as D
from genesis.kernel.anchors import pinned_tool_anchors

ROOT = Path(__file__).resolve().parents[1]


def copy_entries():
    return [(raw, json.loads(raw)) for raw, _ in D.read_history()]


def rechain(entries):
    """Recompute prev/pins hashes after editing entries (what a careful forger would do)."""
    out, prev = [], None
    for i, (_, e) in enumerate(entries, 1):
        e = dict(e, seq=i, prev=prev, pins_sha256=hashlib.sha256(D._canon(e['pins'])).hexdigest())
        raw = D._canon(e)
        out.append((raw, e)); prev = hashlib.sha256(raw).hexdigest()
    return out


class History(unittest.TestCase):
    def setUp(self):
        self.pins = json.loads(D.PINS_PATH.read_text())
        self.entries = copy_entries()

    def test_committed_pins_are_the_last_revision(self):
        self.assertEqual(D.check_pins_history(), [])
        self.assertGreaterEqual(len(self.entries), 2)

    def test_hand_edited_pins_are_refused(self):
        edited = json.loads(json.dumps(self.pins))
        edited['drat-trim']['binary_sha256'] = '0' * 64
        problems = D.check_pins_history(edited, self.entries)
        self.assertTrue(any('differs from the last recorded revision' in p for p in problems), problems)

    def test_binary_change_without_known_answers_is_refused(self):
        new = json.loads(json.dumps(self.pins)); new['cadical']['binary_sha256'] = '1' * 64
        raw, entry = D.history_entry(self.entries, new, reason='swap', known_answers=None)
        problems = D.check_pins_history(new, self.entries + [(raw, entry)])
        self.assertTrue(any('without passing known answers' in p for p in problems), problems)

    def test_known_answers_must_have_run_the_new_binary(self):
        new = json.loads(json.dumps(self.pins)); new['cadical']['binary_sha256'] = '1' * 64
        ka = {'ok': True, 'binaries': {'cadical': self.pins['cadical']['binary_sha256']}}
        raw, entry = D.history_entry(self.entries, new, reason='swap', known_answers=ka)
        problems = D.check_pins_history(new, self.entries + [(raw, entry)])
        self.assertTrue(any('did not run the new cadical binary' in p for p in problems), problems)
        ka_failed = {'ok': False, 'binaries': {'cadical': '1' * 64}}
        raw, entry = D.history_entry(self.entries, new, reason='swap', known_answers=ka_failed)
        self.assertTrue(D.check_pins_history(new, self.entries + [(raw, entry)]))

    def test_recorded_changes_and_retired_anchors_must_be_truthful(self):
        i = next(k for k, (_, e) in enumerate(self.entries) if e.get('retired_anchors'))
        target = self.entries[i][1]
        for edit, message in (({'changes': []}, 'changes do not match'),
                              ({'retired_anchors': []}, 'anchors it retires')):
            forged = self.entries[:i] + [(None, dict(target, **edit))] + self.entries[i + 1:]
            problems = D.check_pins_history(self.pins, rechain(forged))
            self.assertTrue(any(message in p for p in problems), (message, problems))

    def test_broken_chain_and_non_canonical_lines_are_refused(self):
        raw, e = self.entries[-1]
        broken = self.entries[:-1] + [(D._canon(dict(e, prev='0' * 64)), dict(e, prev='0' * 64))]
        self.assertTrue(any('breaks the chain' in p for p in D.check_pins_history(self.pins, broken)))
        spaced = json.dumps(e).encode()
        problems = D.check_pins_history(self.pins, self.entries[:-1] + [(spaced, e)])
        self.assertTrue(any('not canonical' in p for p in problems), problems)

    def test_recipe_change_requires_a_revision(self):
        pins = json.loads(json.dumps(self.pins)); pins['built_with']['recipe_sha256'] = '2' * 64
        entries = rechain(self.entries[:-1] + [(None, dict(self.entries[-1][1], pins=pins))])
        problems = D.check_pins_history(pins, entries)
        self.assertTrue(any('build_reproducible.sh changed' in p for p in problems), problems)

    def test_retired_hashes_are_no_longer_anchors(self):
        anchors = pinned_tool_anchors()
        for entry in (e for _, e in self.entries):
            for old in entry.get('retired_anchors') or []:
                self.assertNotIn(old, anchors)
        for name in ('drat-trim', 'lean', 'cadical', 'eprover', 'zstd'):
            self.assertIn(self.pins[name]['binary_sha256'], anchors)


class ReviseCommand(unittest.TestCase):
    """Drive toolchain/revise_pins.py against a private copy of the pin files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        for name in ('PINS.json', 'PINS_HISTORY.jsonl'):
            shutil.copy(ROOT / 'toolchain' / name, d / name)
        self.pins_path, self.hist_path = d / 'PINS.json', d / 'PINS_HISTORY.jsonl'
        sys.path.insert(0, str(ROOT / 'toolchain'))
        import revise_pins
        self.revise = revise_pins
        self.patches = [mock.patch.object(D, 'PINS_PATH', self.pins_path),
                        mock.patch.object(D, 'HISTORY_PATH', self.hist_path)]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def test_refuses_a_binary_change_without_known_answers(self):
        before = (self.pins_path.read_bytes(), self.hist_path.read_bytes())
        with self.assertRaisesRegex(SystemExit, 'known answers'):
            self.revise.main(['--reason', 'swap', '--set', 'cadical.binary_sha256=' + '3' * 64])
        self.assertEqual((self.pins_path.read_bytes(), self.hist_path.read_bytes()), before)

    def test_records_a_metadata_change(self):
        self.assertEqual(self.revise.main(['--reason', 'annotate', '--set', 'cadical.note=reviewed']), 0)
        pins = json.loads(self.pins_path.read_text())
        self.assertEqual(pins['cadical']['note'], 'reviewed')
        self.assertEqual(D.check_pins_history(pins, D.read_history(self.hist_path)), [])
        last = D.read_history(self.hist_path)[-1][1]
        self.assertEqual(last['changes'], [{'tool': 'cadical', 'field': 'note', 'old': None, 'new': 'reviewed'}])

    def test_accepts_a_binary_change_with_matching_known_answers(self):
        ka = Path(self.tmp.name) / 'ka.json'
        ka.write_text(json.dumps({'ok': True, 'binaries': {'cadical': '4' * 64}}))
        self.assertEqual(self.revise.main(['--reason', 'rebuild', '--set', 'cadical.binary_sha256=' + '4' * 64,
                                           '--known-answers', str(ka)]), 0)
        last = D.read_history(self.hist_path)[-1][1]
        self.assertEqual(last['retired_anchors'], [json.loads((ROOT / 'toolchain/PINS.json').read_text())
                                                   ['cadical']['binary_sha256']])

    def test_refuses_to_revise_an_inconsistent_history(self):
        pins = json.loads(self.pins_path.read_text()); pins['zstd']['commit'] = '0' * 40
        self.pins_path.write_text(json.dumps(pins))
        with self.assertRaisesRegex(SystemExit, 'not consistent'):
            self.revise.main(['--reason', 'cover-up', '--set', 'zstd.note=x'])


if __name__ == '__main__':
    unittest.main()
