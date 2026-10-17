"""B20_R55: the sum-free pattern generator (`invention/cuts_sf.py`), checked without Lean.

* the domain: Schur triples and sum-freeness agree with brute force; ex(P) by MILP equals brute force on every
  candidate up to 7;
* copies are injective and send every Schur triple of the pattern to one of the host's (brute force on small hosts);
* the kept rule: every kept pattern's LP exceeds ex under the Schur rows and under the earlier patterns;
* every kept pattern has an integer rounding certificate that checks exactly (cover, rounding, value);
* the obligations' Python models are sound on exhaustive small instances, and their Lean texts are well formed.
"""
from fractions import Fraction
import itertools
import unittest

from genesis.formal_research import loop as L
from genesis.invention import cuts_sf as SF


def brute_ex(P):
    for k in range(len(P), -1, -1):
        for sub in itertools.combinations(P, k):
            if SF.sumfree(sub):
                return k


class Domain(unittest.TestCase):
    def test_schur_triples_and_sumfree(self):
        self.assertEqual(SF.schur_triples([1, 2, 3, 4]), [(1, 1, 2), (1, 2, 3), (1, 3, 4), (2, 2, 4)])
        self.assertTrue(SF.sumfree([3, 4, 5]))
        self.assertFalse(SF.sumfree([2, 4]))
        self.assertFalse(SF.sumfree([1, 2, 3]))
        self.assertTrue(SF.sumfree([1, 3, 5, 7]))
        self.assertTrue(SF.sumfree([]))

    def test_ex_milp_equals_brute_force(self):
        n = 0
        for P in SF.candidates(7):
            ex, wit = SF.ex_milp(list(P))
            self.assertEqual(ex, brute_ex(list(P)), P)
            self.assertTrue(SF.sumfree(wit) and set(wit) <= set(P))
            n += 1
        self.assertGreater(n, 50)

    def test_copies(self):
        host = [1, 2, 3, 4, 5, 6, 7, 9, 10, 12]
        for P in ([1, 2, 3, 4], [1, 2, 4, 5], [1, 2, 5, 6, 7]):
            T = SF._index_triples(P)
            found = {frozenset(c) for c in SF.copies(P, host)}
            brute = set()
            for phi in itertools.permutations(host, len(P)):
                if all(phi[a] + phi[b] == phi[c] for a, b, c in T):
                    brute.add(frozenset(phi))
            self.assertEqual(found, brute, P)
            for c in SF.copies(P, host):
                self.assertEqual(len(set(c)), len(P))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = {}
        cls.patterns = SF.generate(stats=cls.stats)

    def test_counts_and_kept_rule(self):
        self.assertEqual(len(self.patterns), 17)
        self.assertEqual(self.patterns[0]['elements'], [1, 2, 3, 4])
        for i, p in enumerate(self.patterns):
            self.assertEqual(p['ex'], brute_ex(p['elements']))
            self.assertGreater(p['lp_schur_rows'], p['ex'] + 1e-6)
            self.assertGreater(SF.relaxation_lp(p['elements'], self.patterns[:i]), p['ex'] + 1e-6)

    def test_every_pattern_has_an_exact_certificate(self):
        for i, p in enumerate(self.patterns):
            cert = SF.proof_certificate(p, self.patterns[:i])
            self.assertIsNotNone(cert, p['id'])
            D, K = cert['D'], cert['K']
            cover = {x: cert['slack'].get(x, 0) for x in p['elements']}
            total = sum(cert['slack'].values())
            for kind, qid, vals, mult, rhs in cert['rows']:
                if kind == 'schur':
                    a, b, c = vals
                    self.assertEqual((a + b, rhs), (c, 2))
                elif kind == 'double':
                    a, c = vals
                    self.assertEqual((2 * a, rhs), (c, 1))
                else:
                    q = next(q for q in self.patterns if q['id'] == qid)
                    self.assertEqual(rhs, q['ex'])
                    for x, y, z in SF._index_triples(q['elements']):
                        self.assertEqual(vals[x] + vals[y], vals[z])
                for v in set(vals) if kind != 'pattern' else vals:
                    cover[v] += mult
                total += mult * rhs
            self.assertTrue(all(c >= D for c in cover.values()), p['id'])
            self.assertEqual(total, K)
            self.assertEqual(K // D, p['ex'])
            self.assertLess(Fraction(K, D), p['ex'] + 1)


class Obligations(unittest.TestCase):
    def test_models_are_sound_on_small_instances(self):
        pats = SF.generate()[:3]
        conjs = {c['id']: c for c in SF.conjectures(pats)}
        U = range(1, 9)
        sets = [frozenset(s) for k in range(0, 5) for s in itertools.combinations(U, k) if SF.sumfree(s)]
        for S in sets:
            for a, b in itertools.product(range(0, 9), repeat=2):
                v = {'S': S, 'a': a, 'b': b, 'c': a + b, 'x': a}
                self.assertTrue(conjs['sf_bridge']['model'](v))
                self.assertTrue(conjs['sf_ind_le_one']['model'](v))
                self.assertTrue(conjs['sf_bridge_double']['model']({'S': S, 'a': a, 'c': 2 * a}))
            for p in pats:
                for c in range(1, 3):
                    v = {'S': S, **{f'v{i}': c * x for i, x in enumerate(p['elements'])}}
                    self.assertTrue(conjs[f'sf_{p["id"]}']['model'](v))

    def test_statements(self):
        p = SF.generate()[0]
        c = SF.conjectures([p])[3]
        self.assertEqual(L.statement(c), '∀ (S : Finset ℕ) (hS : SF.SumFree S) (v0 : ℕ) (v1 : ℕ) (v2 : ℕ) (v3 : ℕ) '
                                         '(r0 : v0 + v0 = v1) (r1 : v0 + v1 = v2) (r2 : v0 + v2 = v3) '
                                         '(r3 : v1 + v1 = v3), SF.ind S v0 + SF.ind S v1 + SF.ind S v2 + '
                                         'SF.ind S v3 ≤ 2')
        self.assertIn('def SumFree (S : Finset ℕ) : Prop := ∀ a ∈ S, ∀ b ∈ S, a + b ∉ S', SF.SOURCE)


if __name__ == '__main__':
    unittest.main()
