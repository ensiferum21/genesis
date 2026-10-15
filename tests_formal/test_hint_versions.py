"""B20_R25: versioned ground-hint generators for the Lean replay of E proofs (fof_lean)."""
import json
from pathlib import Path
import unittest

from genesis.fol import parse
from genesis.formal_research import fof_lean as F

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'hint_ab_b20r25'

# A step from a Wolfram-axiom lemma chain (B21 side branch):
# c_0_56 = rw(rw(rw(rw(spm(c_0_51, c_0_52), c_0_53), c_0_44), c_0_54), c_0_44), c_0_44 commutativity.
PARENTS = ['![X1,X2,X3]: s(s(s(X1,X2),X3),s(X1,s(s(X1,X2),s(X3,s(X1,X2))))) = s(s(X1,X2),s(X3,s(X1,X2)))',
           '![X1,X2,X3]: s(s(s(X1,s(X1,X1)),X2),s(X3,X2)) = X2',
           '![X1,X2,X3]: s(s(X1,X2),s(s(X3,s(X3,X3)),X2)) = X2',
           '![X1,X2]: s(X1,X2) = s(X2,X1)',
           '![X1,X2]: s(X1,s(X2,s(X1,X2))) = s(X1,X1)']
CONCLUSION = '![X1,X2]: s(X1,s(X2,X2)) = s(X1,s(X2,X1))'


def shape(t):
    return F._shape(parse(t), 'fof')


class Versions(unittest.TestCase):
    def test_default_and_unknown(self):
        self.assertEqual(F.HINTS, 'v2')
        self.assertEqual(F.HINT_VERSIONS, ('v1', 'v2'))
        with self.assertRaises(ValueError):
            F.ground_hints([shape(PARENTS[3])], shape(CONCLUSION), [], version='v9')

    def test_v2_finds_the_hints_v1_misses(self):
        parents, mine = [shape(p) for p in PARENTS], shape(CONCLUSION)
        self.assertIsNone(F.ground_hints(parents, mine, [], version='v1'))
        hints = F.ground_hints(parents, mine, [], version='v2')
        self.assertTrue(hints)
        self.assertIn(3, {i for i, _ in hints})                   # a commutativity instance is among them

    def test_v2_hints_are_refuting_instances(self):
        parents, mine = [shape(p) for p in PARENTS], shape(CONCLUSION)
        hints = F.ground_hints(parents, mine, [], version='v2')
        sk = {v: ('fn', '#' + v, ()) for v in mine[0]}
        neg = [[(not pos, F._subst(a, sk), F._subst(b, sk))] for pos, a, b in mine[1][0]]
        inst = []
        for i, args in hints:
            m = dict(zip(parents[i][0], args))
            inst += [[(q, F._subst(a, m), F._subst(b, m)) for q, a, b in c] for c in parents[i][1]]
        self.assertTrue(F._unsat(neg + inst))
        self.assertFalse(F._unsat(neg))

    def test_commutative_matching_records_swaps(self):
        s = lambda a, b: ('fn', 's', (a, b))
        X, Y, a, b = ('var', 'X'), ('var', 'Y'), ('fn', 'a', ()), ('fn', 'b', ())
        comm = {'s': (0, 'X1', 'X2')}
        m, swaps = next(F._match_c(s(X, s(Y, Y)), s(s(b, b), a), {}, comm))
        self.assertEqual(m, {'X': a, 'Y': b})
        self.assertEqual(swaps, (s(s(b, b), a),))
        self.assertIsNone(next(F._match_c(s(X, X), s(a, b), {}, comm), None))
        self.assertEqual(F._commutative([shape(PARENTS[3])]), {'s': (0, 'X1', 'X2')})

    def test_rules_are_size_decreasing(self):
        rules = F._rules([shape(p) for p in PARENTS])
        self.assertTrue(rules)
        self.assertTrue(all(F._size(l) > F._size(r) for _, l, r in rules))
        self.assertNotIn(3, {i for i, _, _ in rules})              # commutativity is not a rule


@unittest.skipUnless((EVIDENCE / 'ab.json').exists(), 'B20_R25 hint A/B evidence not generated')
class Evidence(unittest.TestCase):
    def test_recorded(self):
        ab = json.loads((EVIDENCE / 'ab.json').read_text())
        rows = json.loads((EVIDENCE / 'rows.json').read_text())
        ok = lambda r, v: r[v]['status'] == 'THEOREM_CHECKED'
        for system, s in ab['by_system'].items():
            rs = [r for r in rows if r['system'] == system]
            self.assertEqual(s['attempted'], len(rs))
            self.assertEqual(s['v1_checked'], sum(ok(r, 'v1') for r in rs))
            self.assertEqual(s['v2_checked'], sum(ok(r, 'v2') for r in rs))
        self.assertEqual(ab['v2_regressions'], [r['target'] for r in rows if ok(r, 'v1') and not ok(r, 'v2')])
        for r in rows:
            self.assertEqual((r['v1']['hints'], r['v2']['hints']), ('v1', 'v2'))


if __name__ == '__main__':
    unittest.main()
