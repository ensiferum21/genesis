"""B20_R46: the C4 pattern package replays from its sources. Its patterns are the generator's, the
base lemmas and every usable bound are Lean-CHECKED, every obligation survived the screen, and the
statements are the generator's own texts. Needs the formal workspace; the formal suite accepts no
skips."""
import copy
import json
from pathlib import Path
import unittest

from genesis.formal_research import loop as L
from genesis.formal_research import theory_package as TP
from genesis.invention import cuts_c4 as C4

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'c4_generator_b20r46'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.summary = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.patterns = C4.generate()

    def test_package_replays(self):
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        self.assertEqual(TP.replay(self.pkg)['verdict'], 'REPLAYED')
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_patterns_and_statuses(self):
        s = self.summary
        self.assertEqual([p['id'] for p in s['patterns']], [p['id'] for p in self.patterns])
        self.assertTrue(s['base_checked'])
        self.assertTrue(all(v['result'] == 'NO_COUNTEREXAMPLE' for v in s['screen'].values()))
        status = {st['id']: st['status'] for st in self.pkg['statements']}
        self.assertEqual(sorted(s['usable']), sorted(p['id'] for p in self.patterns
                                                     if status.get('p4_' + p['id']) == 'CHECKED'))
        texts = {c['id']: L.statement(c) for c in C4.conjectures(self.patterns)}
        for st in self.pkg['statements']:
            self.assertEqual(st['lean'], texts[st['id']], st['id'])

    def test_every_kept_pattern_tightens_the_cycle_lp(self):
        for p in self.summary['patterns']:
            self.assertGreater(p['lp_cycle_rows'], p['ex'] + 1e-6, p['id'])
            self.assertGreater(p['lp_with_earlier'], p['ex'] + 1e-6, p['id'])


if __name__ == '__main__':
    unittest.main()
