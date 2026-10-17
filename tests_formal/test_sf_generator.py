"""B20_R55: the sum-free pattern package replays from its sources. Its patterns are the generator's, the base
lemmas and every usable bound are Lean-CHECKED, every obligation survived the screen, the statements are the
generator's own texts, and the trusted definitions are the generator's SFDefs. Needs the formal workspace; the
formal suite accepts no skips."""
import copy
import json
from pathlib import Path
import unittest

from genesis.formal_research import loop as L
from genesis.formal_research import theory_package as TP
from genesis.invention import cuts_sf as SF

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'sf_generator_b20r55'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.summary = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.patterns = SF.generate()

    def test_package_replays(self):
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        self.assertEqual(TP.replay(self.pkg)['verdict'], 'REPLAYED')
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_patterns_statuses_and_definitions(self):
        s = self.summary
        self.assertEqual([p['id'] for p in s['patterns']], [p['id'] for p in self.patterns])
        self.assertTrue(s['base_checked'])
        self.assertEqual(len(s['usable']), 17)
        self.assertTrue(all(v['result'] == 'NO_COUNTEREXAMPLE' for v in s['screen'].values()))
        status = {st['id']: st['status'] for st in self.pkg['statements']}
        self.assertEqual(sorted(s['usable']), sorted(p['id'] for p in self.patterns
                                                     if status.get('sf_' + p['id']) == 'CHECKED'))
        self.assertTrue(all(v == 'CHECKED' for v in status.values()))
        texts = {c['id']: L.statement(c) for c in SF.conjectures(self.patterns)}
        for st in self.pkg['statements']:
            self.assertEqual(st['lean'], texts[st['id']], st['id'])
        mods = {m['name']: m['source'] for m in self.pkg['modules']}
        self.assertEqual(mods['SFDefs'], SF.SOURCE)

    def test_every_kept_pattern_tightens_the_schur_lp(self):
        for p in self.summary['patterns']:
            self.assertGreater(p['lp_schur_rows'], p['ex'] + 1e-6, p['id'])
            self.assertGreater(p['lp_with_earlier'], p['ex'] + 1e-6, p['id'])


if __name__ == '__main__':
    unittest.main()
