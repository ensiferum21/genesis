"""CRPD-2: the Lean-checked codegree characterisation of C4-freeness (first EQ abstraction).

The committed package replays from its sources in the pinned workspace with only the
allowed axioms; tampering with the trusted statement is detected; the Python model used
for screening agrees with the C4 model on every edge set over 3 labelled vertices
(loops and both orientations included); the soundness record is EQ and licenses pruning.
Requires the formal workspace (formal suite: no skips).
"""
import copy
from itertools import product
import json
from pathlib import Path
import unittest

from genesis.formal_research import theory_package as TP
from genesis.invention import codegree as CG
from genesis.invention import representations as R
from genesis.invention import soundness as S

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'codegree_b20r'


class Model(unittest.TestCase):
    def test_python_models_agree_exhaustively_on_three_vertices(self):
        pairs = [(u, v) for u in range(3) for v in range(3)]           # 9 ordered pairs, loops included
        for bits in product((0, 1), repeat=len(pairs)):
            S_ = {p for p, b in zip(pairs, bits) if b}
            self.assertEqual(R.c4free(S_), CG.codeg_le_one(S_), sorted(S_))

    def test_loops_do_not_break_the_equivalence(self):
        triangle_with_loop = {(0, 0), (0, 1), (1, 2), (2, 0)}
        self.assertFalse(R.c4free(triangle_with_loop))                 # the closed walk 0-0-1-2... uses the loop
        self.assertFalse(CG.codeg_le_one(triangle_with_loop))


class CommittedPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads((EVIDENCE / 'package.json').read_text())

    def test_statement_checked_with_allowed_axioms_only(self):
        p = self.package
        st = {s['id']: s for s in p['statements']}
        self.assertEqual(st['codeg_iff_c4free']['status'], 'CHECKED')
        self.assertLessEqual(set(p['assumptions']['axioms_used']), {'propext', 'Classical.choice', 'Quot.sound'})
        self.assertEqual(TP.integrity_problems(p), [])
        self.assertIn('builder-written', ' '.join(p['assumptions']['conventions']))

    def test_replays_from_sources(self):
        self.assertEqual(TP.replay(self.package)['verdict'], 'REPLAYED')

    def test_weakened_trusted_statement_is_detected(self):
        bad = copy.deepcopy(self.package)
        for m in bad['modules']:
            if m['name'] == 'CDDefs':
                m['source'] = m['source'].replace('.card ≤ 1', '.card ≤ 2')
        self.assertNotEqual(TP.replay(bad)['verdict'], 'REPLAYED')

    def test_first_eq_abstraction(self):
        rec = CG.soundness_record(self.package)
        self.assertEqual(rec['established'], 'EQ')
        for use in ('lift_positive', 'lift_negative', 'prune'):
            self.assertTrue(S.admit(rec, use))
        committed = json.loads((EVIDENCE / 'soundness.json').read_text())
        self.assertEqual(committed['record_id'], rec['record_id'])


if __name__ == '__main__':
    unittest.main()
