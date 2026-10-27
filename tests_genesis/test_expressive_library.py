"""X2 (B20_R154): library learning over Λ1 (`genesis.expressive.library`).

Fragments respect the guard rules (a run governed by a guard, or ending in one, is not a fragment; a single guard
is); anti-unification keeps what is equal, makes what differs a parameter, and shares a parameter between positions
that always agree; rewriting never changes what a program means (checked here on random corpora, as the learner
itself checks); the learner chooses by compression, is deterministic, excludes what it is told to, names in order,
and lets a later generation's statement call an earlier one."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import lambda1 as L1  # noqa: E402
from genesis.expressive import library as LL  # noqa: E402
from genesis.expressive import operators as O  # noqa: E402


def meaning(text, lib=L1.EMPTY):
    return K.render(L1.expand(L1.surface(text, lib), lib))


def random_corpus(rng, n=12, parents=4):
    base = [O.random_engine(rng, 'L1') for _ in range(parents)]
    out = []
    for _ in range(n):
        g = rng.choice(base)
        for _ in range(rng.randint(0, 3)):
            g = O.mutate(g, rng, 'L1')
        out.append(g['prog'])
    return out


class Fragments(unittest.TestCase):
    def test_runs_respect_guards(self):
        p = K.parse('b1 S5 X I ?f>3 M D')
        frags = {K.render(f) for f in LL.fragments(p, frozenset())}
        self.assertIn('S5 X', frags)                      # a guard with what it governs
        self.assertIn('S5', frags)                        # a single guard: a named condition
        self.assertNotIn('X I', frags)                    # governed by S5: a call would put both under it
        self.assertNotIn('I ?f>3', frags)                 # ends in a guard
        self.assertIn('I ?f>3 M', frags)
        self.assertNotIn('M D', frags)                    # M is governed by ?f>3
        self.assertIn('D', frags)
        nested = {K.render(f) for f in LL.fragments(K.parse('b1 *3 [ X I ] P2 [ D L ]'), frozenset())}
        self.assertTrue({'X I', '[ X I ]', 'D L'} <= nested)

    def test_anti_unification(self):
        body, params = LL.anti_unify([[100, 5, 7], [200, 5, 14], [300, 5, 21]])
        self.assertEqual((body, len(params)), (['$1', 5, '$2'], 2))
        body, params = LL.anti_unify([[100, 100, 3], [200, 200, 3]])
        self.assertEqual(body, ['$1', '$1', 3])           # positions that always agree share a parameter
        s, v = LL.skeleton(K.parse('B100 S20 *3 [ X@h ?d<40 ]'))
        self.assertEqual(v, [100, 20, 3, 40])
        self.assertEqual(LL._fill(s, v), K.parse('B100 S20 *3 [ X@h ?d<40 ]'))


class Learning(unittest.TestCase):
    def test_a_recurring_fragment_is_learned_with_its_parameter(self):
        corpus = ['B100 X I S2000 C', 'b5 X I S300 C D', 'B20 X I S2000 C L', 'b3 R B7 X I S50 C']
        lib, texts, steps = LL.learn(corpus, k=3)
        self.assertEqual((steps[0]['name'], steps[0]['body'], steps[0]['params']), ('g1a', 'X I S$1 C', 1))
        self.assertGreater(steps[0]['compression_bits'], 0)
        self.assertEqual(texts[0], 'B100 g1a(2000)')
        for a, b in zip(corpus, texts):
            self.assertEqual(meaning(a), meaning(b, lib))
        self.assertEqual(lib.get('g1a')['provenance']['programs'], [0, 1, 2, 3])
        self.assertEqual(L1.Library.from_json(lib.to_json()).version, lib.version)

    def test_meaning_is_preserved_on_random_corpora(self):
        rng = random.Random(1)
        learned = 0
        for _ in range(25):
            corpus = random_corpus(rng)
            lib, texts, steps = LL.learn(corpus, k=3)
            learned += len(steps)
            for a, b in zip(corpus, texts):
                self.assertEqual(meaning(a), meaning(b, lib), (a, b))
            self.assertTrue(all(s['compression_bits'] > 0 for s in steps))
        self.assertGreater(learned, 5)

    def test_deterministic_exclude_and_names(self):
        corpus = ['b1 R B5 D L X', 'B9 R B7 D L', 'b3 I R B9 D L M', 'B2 R B4 D L', 'b4 R B3 D L I', 'B6 X R B8 D L',
                  'b7 R B2 D L C', 'B1 R B6 D L']
        self.assertEqual(LL.learn(corpus, k=2)[2], LL.learn(corpus, k=2)[2])
        best = LL.learn(corpus, k=1)[2][0]['body']
        lib, _, steps = LL.learn(corpus, k=1, exclude={best}, first=2, generation=4)
        self.assertTrue(steps)
        self.assertNotEqual(steps[0]['body'], best)
        self.assertEqual(steps[0]['name'], 'g4c')
        self.assertEqual(LL.learn(['B1 X', 'b2 I'], k=2)[2], [])        # nothing recurs: nothing learned

    def test_a_later_statement_can_call_an_earlier_one(self):
        lib1 = L1.EMPTY.extend('g1a', 'R B$1')
        corpus = ['b1 g1a(5) D L X', 'B9 g1a(7) D L', 'b3 I g1a(9) D L M', 'B2 g1a(4) D L', 'b4 g1a(3) D L I',
                  'B6 X g1a(8) D L', 'b7 g1a(2) D L C', 'B1 g1a(6) D L']           # enough uses to pay for a name
        lib2, texts, steps = LL.learn(corpus, lib1, k=1, generation=2)
        self.assertTrue(steps)
        self.assertIn('g1a', steps[0]['body'])
        self.assertEqual(lib2.parent, lib1.version)
        for a, b in zip(corpus, texts):
            self.assertEqual(meaning(a, lib1), meaning(b, lib2))


if __name__ == '__main__':
    unittest.main()
