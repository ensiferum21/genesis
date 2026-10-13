"""CRPD-2b: the formal workspace pin history is a hash chain ending at the current pins."""
import json
from pathlib import Path
import tempfile
import unittest

from genesis.common import canonical
from genesis.formal_research import workspace as W


class PinHistory(unittest.TestCase):
    def test_repository_history_is_consistent(self):
        self.assertEqual(W.history_problems(), [])
        entries = W.history()
        self.assertEqual([e['seq'] for _, e in entries], list(range(len(entries))))
        self.assertIn('CRPD-2b', entries[-1][1]['reason'])
        self.assertEqual(entries[0][1]['pins']['import_roots'], ['Mathlib.Data.Finset.Powerset'])
        self.assertEqual(entries[0][1]['build']['source_identity'],
                         'a3a7569b6d7636a844c87c2b72ef2170eda0f712ff8d9a1b0f15b069e301c7ef')   # the B20 pin

    def tampered(self, lines):
        d = tempfile.mkdtemp()
        p = Path(d) / 'history.jsonl'
        p.write_bytes(b'\n'.join(lines) + b'\n')
        return W.history_problems(path=p)

    def test_tampering_is_detected(self):
        raw = [r for r, _ in W.history()]
        self.assertTrue(self.tampered(raw[:1]))                      # the revision left unrecorded
        e1 = json.loads(raw[1])
        e1['reason'] = 'quietly changed'
        self.assertTrue(any('chained' in p or 'last recorded' in p for p in self.tampered([raw[0], canonical(e1)]))
                        or self.tampered([canonical(json.loads(raw[0])) + b' ', raw[1]]))
        e0 = json.loads(raw[0])
        e0['pins']['import_roots'] = ['Mathlib']
        self.assertTrue(any('digest' in p for p in self.tampered([canonical(e0), raw[1]])))
        e2 = json.loads(raw[1])
        e2['build']['source_identity'] = '0' * 64
        self.assertTrue(any('source identity' in p for p in self.tampered([raw[0], canonical(e2)])))
        self.assertTrue(any('not chained' in p for p in self.tampered([raw[1], raw[0]])))


if __name__ == '__main__':
    unittest.main()
