"""Representation synthesis as a process (directive items 9 and 11; fixtures): a level-2 process improves a weak
synthesiser on training relations; the promotion gate admits the descendant only for more verified gadgets on
unfamiliar relations at matched fuel, and refuses an unchanged one; a level-3 process improves the improver; one fuel
budget bounds every level."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import process as P  # noqa: E402
from genesis.representation import processes as RP  # noqa: E402
from genesis.representation import relations as R  # noqa: E402

TRAIN = {'relations': [r.to_json() for r in (R.clause([True, True, True]), R.parity(3, 1), R.and_gate(3),
                                              R.exactly(3, 1), R.nae(3), R.clause([True, False]))]}
UNFAMILIAR = {'relations': [r.to_json() for r in (R.or_gate(3), R.parity(3, 0), R.at_least(3, 2),
                                                   R.clause([False, False, True]), R.at_most(3, 1))]}


class Processes(unittest.TestCase):
    def test_level2_improves_and_the_gate_verifies_on_unfamiliar_relations(self):
        weak = RP.synthesizer(max_ancillas=0, bound=1)
        lvl2 = RP.improver(2, variants=6, step=2, subtask=TRAIN)
        best, y = P.step(lvl2, weak, P.Fuel(400), RP.measure, random.Random(3))
        y0 = RP.measure(weak, TRAIN, P.Fuel(100))
        self.assertGreater(y, y0)
        self.assertTrue(best['lineage'])
        admit, yc, yi = RP.promotion_gate(best, weak, UNFAMILIAR)
        self.assertTrue(admit, (yc, yi))
        self.assertEqual(RP.promotion_gate(weak, weak, UNFAMILIAR)[0], False)

    def test_level3_improves_the_improver_under_one_budget(self):
        weak = RP.synthesizer(max_ancillas=0, bound=1)
        lvl2 = RP.improver(2, variants=1, step=1, target=weak, subtask=TRAIN)
        lvl3 = RP.improver(3, variants=2, step=1)
        best2, y = P.step(lvl3, lvl2, P.Fuel(2000), RP.measure, random.Random(5))
        self.assertEqual(best2['level'], 2)
        with self.assertRaises(P.OutOfFuel):
            P.step(lvl3, lvl2, P.Fuel(5), RP.measure, random.Random(5))

    def test_only_synthesisers_are_measured(self):
        with self.assertRaises(ValueError):
            RP.measure(RP.improver(2), TRAIN, P.Fuel(10))


if __name__ == '__main__':
    unittest.main()
