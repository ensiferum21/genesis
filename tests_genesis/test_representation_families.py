"""The representation language, stage C (fixtures): families given only as predicates; Genesis synthesises every
gadget their relations need (no hand-written reduction), and the compiled problem is exact for Max-CSP by brute force
against the family's own checker; the natural MaxSAT encodings count violations as documented."""
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.representation import compile as C  # noqa: E402
from genesis.representation import families as F  # noqa: E402
from genesis.representation import gadgets as GD  # noqa: E402
from genesis.representation import library as LB  # noqa: E402


class Families(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib = LB.EMPTY
        for fam, rel in F.BASE.items():
            g, rep = GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=True)
            lib = LB.register(lib, rel, g, {'synthesizer': 'milp', 'for': fam, 'tried': rep['tried']})
        cls.lib = lib

    def test_no_hand_written_reduction_and_exact(self):
        for fam in F.FAMILIES:
            for seed in range(3):
                inst = F.generate(fam, seed, {'n': 6, 'm': 7})
                p = F.spec(inst)
                self.assertEqual(C.missing(p, LB.EMPTY, 'max_csp')[0].id(), F.BASE[fam].id())
                bqp, info = C.compile(p, self.lib, 'max_csp')
                v, z = C.brute_force(bqp)
                best = max(F.check(inst, x)[1] for x in product((0, 1), repeat=inst['n']))
                self.assertEqual(len(inst['constraints']) - v, best, (fam, seed))
                self.assertEqual(F.check(inst, C.decode(z, info)), (True, best))

    def test_natural_encodings(self):
        for fam in F.FAMILIES:
            inst = F.generate(fam, 9, {'n': 5, 'm': 6})
            w = F.wcnf(inst)
            for x in product((0, 1), repeat=inst['n']):
                cost = sum(wt for wt, cl in w['soft'] if not any((x[abs(l) - 1] == 1) == (l > 0) for l in cl))
                viol = len(inst['constraints']) - F.check(inst, x)[1]
                if fam == 'one_in_three':
                    self.assertGreaterEqual(cost, viol)
                    self.assertEqual(cost == 0, viol == 0)
                else:
                    self.assertEqual(cost, viol)

    def test_checker_refuses_malformed(self):
        inst = F.generate('nae3', 1, {'n': 4, 'm': 3})
        self.assertEqual(F.check(inst, [0, 1, 2, 0]), (False, None))
        with self.assertRaises(ValueError):
            F.generate('sat5', 1, {'n': 4, 'm': 3})


if __name__ == '__main__':
    unittest.main()
