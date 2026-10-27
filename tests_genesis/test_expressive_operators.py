"""B20_R153: the inventor's search operators over Λ0 and Λ1 (`genesis.expressive.operators`).

Every genome an operator returns is valid in its language at its bound: in 'L0' an mcx2 program (the kind mcx2
accepts it as it is) with no construct of Λ1; in 'L1' a canonical program that expands to a valid mcx3 program.
'L1' reaches every construct and, with a library, calls; every kind of mutation applies; the operators are
deterministic given the seed; and the protected search (`autonomy.feedback.steady_state_search`) and selfimprove's
process search run with them unchanged."""
import collections
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import feedback as FB  # noqa: E402
from genesis.autonomy import selfimprove as SI  # noqa: E402
from genesis.candidate_kinds import mcx2 as K2  # noqa: E402
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import lambda1 as L  # noqa: E402
from genesis.expressive import operators as O  # noqa: E402

LIB = L.EMPTY.extend('kick', 'R B$1').extend('stallfix', 'S$1 [ C kick($2) ]').extend('late', '?f>$1')


def fuzz(lang, library=L.EMPTY, steps=1500, seed=1, bound=O.BOUND):
    rng = random.Random(seed)
    used, out = [], []
    pop = [O.random_engine(rng, lang, library, bound) for _ in range(20)]
    out += pop
    for _ in range(steps):
        a = rng.choice(pop)
        c = (O.mutate(a, rng, lang, library, used=used, bound=bound) if rng.random() < 0.8
             else O.crossover(a, rng.choice(pop), rng, lang, library, bound))
        pop[rng.randrange(len(pop))] = c
        out.append(c)
    return out, used


class Operators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.l0, cls.used0 = fuzz('L0')
        cls.l1, cls.used1 = fuzz('L1')
        cls.lib, cls.usedlib = fuzz('L1', LIB)

    def test_l0_writes_mcx2_programs_only(self):
        for g in self.l0:
            self.assertIsNone(K2.check_config(g), g['prog'])
            self.assertTrue(K.is_lambda0(K.parse(g['prog'])), g['prog'])
            self.assertFalse(set(g['prog']) & set('@[]*?'), g['prog'])
            self.assertLessEqual(O.size(g), O.BOUND)

    def test_l1_writes_valid_canonical_programs(self):
        for lib, gs in ((L.EMPTY, self.l1), (LIB, self.lib)):
            for g in gs:
                p = L.surface(g['prog'], lib)
                self.assertEqual(K.render(p), g['prog'])
                self.assertIsNone(K.check_config(L.config(g, lib)))
                self.assertLessEqual(O.size(g, lib), O.BOUND)

    def test_l1_reaches_every_construct(self):
        text = ' '.join(g['prog'] for g in self.l1)
        for mark in ('@c', '@h', '@a', '[', '*', '?f', '?d', '?s', '?t', 'S', 'P'):
            self.assertIn(mark, text, mark)
        calls = collections.Counter(x[1] for g in self.lib for x in K.walk(K.parse(g['prog'], calls=True))
                                    if x[0] == 'call')
        self.assertEqual(set(calls), set(LIB.names()))

    def test_every_kind_of_mutation_applies(self):
        self.assertEqual(set(self.used0), set(O.L0_KINDS))
        self.assertEqual(set(self.used1), set(O.L1_KINDS))
        self.assertEqual(set(self.usedlib), set(O.L1_KINDS) | {'call'})
        self.assertEqual(O.kinds('L0'), O.L0_KINDS)
        self.assertEqual(O.kinds('L1', LIB)[-1], 'call')
        with self.assertRaises(ValueError):
            O.kinds('L2')

    def test_deterministic_and_bounded(self):
        a, _ = fuzz('L1', LIB, steps=300, seed=9)
        b, _ = fuzz('L1', LIB, steps=300, seed=9)
        self.assertEqual(a, b)
        small, _ = fuzz('L1', steps=400, seed=4, bound=6)
        self.assertTrue(all(O.size(g) <= 6 for g in small))

    def test_the_searches_run_with_them_unchanged(self):
        def evaluate(p, split):                               # a deterministic stand-in for running engines
            prog = K.parse(L.config(p, LIB)['prog'])
            return sum(1 for x in K.walk(prog) if x[0] == 'op' and x[1] == 'D') - 0.01 * K.size(prog) + (
                0.001 * (split == 'B'))
        ops = O.ops('L1', LIB)
        winner, report = FB.steady_state_search(ops, evaluate, 120, seed=3)
        self.assertIsNone(K.check_config(L.config(winner, LIB)))
        self.assertGreater(report['distinct_programs'], 20)
        w2, _ = FB.steady_state_search(O.ops('L1', LIB), evaluate, 120, seed=3)
        self.assertEqual(winner, w2)
        w0, _ = SI.search(SI.ORIGINAL, O.ops('L0'), evaluate, 120, seed=3, contract=False, calibrate='AB')
        self.assertIsNone(K2.check_config(w0))


if __name__ == '__main__':
    unittest.main()
