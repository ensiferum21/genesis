"""B20_R17 (s15.3, W10): the generated relational decoders' package replays from its sources, and the
recorded evidence keeps its contract (the only NEW decoder is checked; the utility verdict is the
preregistered one). Needs the formal workspace and the sandbox; the formal suite accepts no skips."""
import copy
import json
from pathlib import Path
import unittest

from genesis.formal_research import theory_package as TP
from genesis.invention import relations as RL

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'relation_invention_b20r17'


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = json.loads((EVIDENCE / 'package.json').read_text())
        cls.a = json.loads((EVIDENCE / 'part_a.json').read_text())
        cls.b = json.loads((EVIDENCE / 'part_b.json').read_text())

    def test_generator_record_matches_the_code(self):
        gen = RL.generate()
        self.assertEqual([(g['k'], g['relation'], g['equals_menu']) for g in gen],
                         [(r['k'], r['relation'], r['equals_menu']) for r in self.a['generated']])
        self.assertEqual(self.a['new_checked'], ['rel3_011220'])
        self.assertTrue(all(r['obligations'] == {'image': 'CHECKED', 'sound_tf': 'CHECKED'} for r in self.a['generated']))

    def test_package_is_intact_and_replays(self):
        self.assertEqual(TP.integrity_problems(self.pkg), [])
        r = TP.replay(self.pkg)
        self.assertEqual(r['verdict'], 'REPLAYED', r.get('differences'))
        tampered = copy.deepcopy(self.pkg)
        tampered['statements'][0]['status'] = 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')

    def test_utility_verdict_follows_from_the_rows(self):
        rows = json.loads((EVIDENCE / 'part_b_rows.json').read_text())
        self.assertEqual(len(rows), 32)
        for other, c in self.b['comparisons'].items():
            diffs = [r['values']['new'] - r['values'][other] for r in rows]
            self.assertEqual(c['wins_ties_losses'], [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs),
                                                     sum(d < 0 for d in diffs)])
            self.assertEqual(c['passes'], c['mean'] >= 0.5 and c['interval_90'][0] > 0)
        self.assertEqual(self.b['verdict'], 'NO_UTILITY_AFTER_COST')


if __name__ == '__main__':
    unittest.main()
