"""B20_R153: Λ1's front end (`genesis.expressive.lambda1`): named statements with parameters, versioned libraries,
expansion to the kind's programs, and the two description-length measures.

A library is immutable and versioned (a new definition gives a new version naming its parent; the JSON form rebuilds
to the same version); a definition is refused unless its parameters are $1..$k, each used, its calls name earlier
definitions, and its trial expansion is a valid program; a parameter used in several places takes the intersection
of their ranges. A call is one item (a guard before it governs the whole statement); a one-item body is that item,
so that a named statement can be a guard, and the canonical form of a program with calls treats such a call as a
guard. `length` counts items; `bits` is a prefix code that grows with every item; `config` gives the kind a program
without calls."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import lambda1 as L  # noqa: E402


def lib3():
    return L.EMPTY.extend('kick', 'R B$1').extend('stallfix', 'S$1 [ C kick($2) ]').extend('late', '?f>$1')


class Library(unittest.TestCase):
    def test_versions_and_parents(self):
        a = L.EMPTY.extend('kick', 'R B$1')
        b = a.extend('late', '?f>$1')
        self.assertEqual(b.parent, a.version)
        self.assertEqual(a.parent, L.EMPTY.version)
        self.assertNotEqual(a.version, b.version)
        self.assertEqual(L.EMPTY.extend('kick', 'R B$1').version, a.version)          # deterministic
        self.assertNotEqual(L.EMPTY.extend('kick', 'R B$1 X').version, a.version)
        self.assertEqual(b.names(), ['kick', 'late'])
        self.assertEqual(len(L.EMPTY), 0)
        self.assertEqual(L.Library.from_json(b.to_json()).version, b.version)
        bad = b.to_json()
        bad['defs'][0]['body'] = 'R B$1 I'
        with self.assertRaises(ValueError):
            L.Library.from_json(bad)

    def test_definitions_are_checked(self):
        lib = lib3()
        for name, body in (('Kick2', 'R B$1'), ('k', 'R B$1'), ('kick', 'R'), ('two', 'B$1 S$3'),
                           ('rec', 'rec(2) B1'), ('fwd', 'later(3) B1'), ('bad', 'B$1 X3'), ('rg', '*$1 late($2)'),
                           ('lit', 'B0'), ('rep', '*$1 late($2) B1')):
            with self.assertRaises(ValueError, msg=(name, body)):
                lib.extend(name, body)
        d = lib.extend('mixed', '*$1 B$1 ?f<$1').get('mixed')
        self.assertEqual((d['params'], d['ranges']), (1, [(1, 1000)]))           # the intersection of the ranges
        self.assertEqual(lib.get('stallfix')['ranges'], [(1, 10 ** 7), (1, 100000)])
        self.assertEqual(lib.guard_calls(), frozenset({'late'}))
        self.assertEqual(lib.extend('later', 'late($1)').guard_calls(), frozenset({'late', 'later'}))
        self.assertEqual(lib.extend('noparam', 'X I').get('noparam')['params'], 0)


class Expansion(unittest.TestCase):
    def setUp(self):
        self.lib = lib3()

    def ex(self, text):
        return K.render(L.expand(L.surface(text, self.lib), self.lib))

    def test_a_call_is_one_item(self):
        self.assertEqual(self.ex('b1 S5 kick(3) X'), 'b1 S5 [ R B3 ] X')
        self.assertEqual(self.ex('b1 kick(3) X'), 'b1 R B3 X')                    # unguarded: spliced
        self.assertEqual(self.ex('b1 *2 kick(3)'), 'b1 *2 [ R B3 ]')
        self.assertEqual(self.ex('B10 stallfix(2000,5) X'), 'B10 S2000 [ C R B5 ] X')
        self.assertEqual(self.ex('late(500) X b1'), '?f>500 X b1')                 # a named condition
        self.assertEqual(self.ex('b1 late(900) [ M H ]'), 'b1 ?f>900 [ M H ]')
        self.assertEqual(self.ex('b1 [ X late(3) ] I'), 'b1 [ X ?f>3 ] I')
        self.assertEqual(K.render(L.expand(L.surface('noparam b1', self.lib.extend('noparam', 'X I')),
                                           self.lib.extend('noparam', 'X I'))), 'X I b1')

    def test_refusals(self):
        for bad in ('kick', 'kick(0)', 'kick(1,2)', 'nope(3)', '*2 late(5) b1', 'late(1001) b1', 'kick(100001)',
                    'late(5)'):
            with self.assertRaises(ValueError, msg=bad):
                self.ex(bad)

    def test_the_canonical_form_of_calls_keeps_their_meaning(self):
        for text in ('b3 late(900) [ M H ]', 'b1 [ X late(3) ] I', 'S5 [ late(3) ] b1'):
            self.assertEqual(K.render(L.surface(text, self.lib)), text)
        self.assertEqual(K.render(L.surface('b1 kick(2) [ M H ]', self.lib)), 'b1 kick(2) M H')
        self.assertEqual(K.render(K.canonical(K.parse('b3 foo [ M H ] [ X ]', calls=True))), 'b3 foo [ M H ] X')

    def test_config(self):
        c = L.config(dict(K.DEFAULT, prog='B10 stallfix(2000,5) late(500) kick(3) X'), self.lib)
        self.assertEqual(c['prog'], 'B10 S2000 [ C R B5 ] ?f>500 [ R B3 ] X')
        self.assertIsNone(K.check_config(c))
        self.assertEqual(L.config(K.DEFAULT), K.DEFAULT)
        with self.assertRaises(ValueError):
            L.config(dict(K.DEFAULT, prog='b1 kick(3)'))                          # not in the empty library


class Length(unittest.TestCase):
    def test_length_counts_items(self):
        lib = lib3()
        self.assertEqual(L.length(K.parse('B100 X I S2000 C')), 5)
        self.assertEqual(L.length(K.parse('b1 [ X I ] *2 D')), 6)
        p = L.surface('B10 stallfix(2000,5) X', lib)
        self.assertEqual(L.length(p), 3)
        self.assertEqual(L.length(L.expand(p, lib)), 7)                            # a call is shorter than its body

    def test_bits_is_a_code_that_grows(self):
        lib = lib3()
        base = K.parse('B100 X I S2000 C')
        self.assertGreater(L.bits(base), 0)
        for extra in (' X', ' B5', ' ?f>500 M', ' *3 D', ' [ X I ]', ' L@h'):
            self.assertGreater(L.bits(K.parse('B100 X I S2000 C' + extra)), L.bits(base), extra)
        self.assertGreater(L.bits(K.parse('B1000 X')), L.bits(K.parse('B10 X')))
        self.assertGreater(L.bits(base, lib), L.bits(base))                        # a larger alphabet
        p = L.surface('B10 stallfix(2000,5) stallfix(2000,5) X', lib)
        self.assertLess(L.bits(p, lib), L.bits(L.expand(p, lib)))
        self.assertGreater(L.library_bits(lib), L.library_bits(L.EMPTY.extend('kick', 'R B$1')))
        self.assertEqual(L.library_bits(L.EMPTY), 0)


if __name__ == '__main__':
    unittest.main()
