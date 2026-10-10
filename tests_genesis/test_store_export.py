"""Incremental event export keeps append-only, corruption-detecting semantics."""
from pathlib import Path
import tempfile
import time
import unittest

from genesis.store import Store


class IncrementalExport(unittest.TestCase):
    def test_export_matches_journal_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(d) as s:
                for i in range(30):
                    s.finish(s.start('t', {'i': i}), {'status': 'SUCCESS'})
            size = (Path(d) / 'events.jsonl').stat().st_size
            with Store(d) as s:
                self.assertEqual(s.verify()['events'], 60)
                s.event('NOTE', {'x': 1})
            self.assertGreater((Path(d) / 'events.jsonl').stat().st_size, size)
            lines = (Path(d) / 'events.jsonl').read_bytes().splitlines()
            self.assertEqual(len(lines), 61)

    def test_resized_export_is_detected_on_next_commit(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(d) as s:
                s.event('A', {'x': 1})
                path = Path(d) / 'events.jsonl'
                path.write_bytes(path.read_bytes().replace(b'"A"', b'"AB"'))
                with self.assertRaises(RuntimeError):
                    s.event('C', {'x': 2})

    def test_same_size_tampering_is_detected_by_verify_and_on_reopen(self):
        # Per-commit checks are O(new events); full prefix checks run in verify(),
        # on open, and before snapshots/exports.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'events.jsonl'
            with Store(d) as s:
                s.event('A', {'x': 1})
                path.write_bytes(path.read_bytes().replace(b'"A"', b'"B"'))
                with self.assertRaises(RuntimeError):
                    s.verify()
            with self.assertRaises(RuntimeError):
                Store(d)

    def test_truncated_export_is_restored_by_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(d) as s:
                for i in range(5):
                    s.event('A', {'i': i})
            path = Path(d) / 'events.jsonl'
            full = path.read_bytes()
            path.write_bytes(full[:len(full) - 7])  # partial final line, e.g. crash mid-write
            with Store(d):
                pass
            self.assertEqual(path.read_bytes(), full)

    def test_write_cost_does_not_grow_with_history(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(d) as s:
                times = []
                for k in range(3):
                    start = time.monotonic()
                    for i in range(150):
                        s.event('A', {'k': k, 'i': i})
                    times.append(time.monotonic() - start)
            self.assertLess(times[-1], 3 * times[0] + 0.5)


if __name__ == '__main__':
    unittest.main()
