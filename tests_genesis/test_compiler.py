"""The Problem Compiler (Genesis Ω engine 1): every form is exact where it claims to be, checked by brute force on
small problems; families round-trip through compile, decode and their own verifier; every back-end reaches the
brute-force optimum on small instances; repair makes answers feasible."""
from itertools import product
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.compiler import backends as BK  # noqa: E402
from genesis.compiler import bqp as Q  # noqa: E402
from genesis.compiler import families as FM  # noqa: E402


def random_bqp(rng, n, hard=True):
    lin = [[i, rng.randint(-3, 3)] for i in range(n)]
    quad = sorted([[i, j, rng.randint(-3, 3)] for i in range(n) for j in range(i + 1, n) if rng.random() < 0.4])
    b = {'n': n, 'constant': rng.randint(-2, 2), 'linear': [x for x in lin if x[1]],
         'quadratic': [x for x in quad if x[2]], 'hard': {}}
    if hard:
        b['hard'] = {'exclusive': [[0, 1]], 'cover': [[2, 3]], 'one': [[4, 5, 6]], 'atmostone': [[1, 5, 7]]}
    return b


def brute(b):
    best = None
    for x in product((0, 1), repeat=b['n']):
        f, bad = Q.evaluate(b, x)
        if not bad and (best is None or f < best):
            best = f
    return best


class Forms(unittest.TestCase):
    def test_check(self):
        rng = random.Random(0)
        self.assertIsNone(Q.check(random_bqp(rng, 8)))
        bad = random_bqp(rng, 8)
        bad['quadratic'].append([3, 2, 1])
        self.assertIsNotNone(Q.check(bad))

    def test_penalised_is_exact_on_feasible_points_and_optimal_with_a_large_penalty(self):
        rng = random.Random(1)
        for _ in range(20):
            b = random_bqp(rng, 8)
            big = 1 + sum(abs(a) for _, a in b['linear']) + sum(abs(c) for *_, c in b['quadratic'])
            q = Q.penalised(b, big)
            for x in product((0, 1), repeat=8):
                f, bad = Q.evaluate(b, x)
                g, _ = Q.evaluate(q, x)
                if not bad:
                    self.assertEqual(f, g)
                else:
                    self.assertGreaterEqual(g, f + big * 1 - 0)        # at least one violation's penalty
            self.assertEqual(min(Q.evaluate(q, x)[0] for x in product((0, 1), repeat=8)), brute(b))

    def test_maxcut_reduction_is_exact(self):
        rng = random.Random(2)
        for _ in range(20):
            b = random_bqp(rng, 6, hard=False)
            n1, E = Q.to_maxcut(b)
            consts = set()
            for side in product((0, 1), repeat=n1):
                cut = sum(w for u, v, w in E if side[u] != side[v])
                f = Q.evaluate(b, Q.from_cut(side, b['n']))[0]
                consts.add(4 * f + 2 * cut)                            # 4 f = K - 2 cut for one constant K
            self.assertEqual(len(consts), 1)

    def test_milp_model_is_exact(self):
        rng = random.Random(3)
        for _ in range(10):
            b = random_bqp(rng, 8)
            c, const, rows, nv = Q.to_milp(b)
            for x in product((0, 1), repeat=8):
                y = list(x) + [x[i] * x[j] for i, j, _ in b['quadratic']]
                val = const + sum(ci * yi for ci, yi in zip(c, y))
                ok = all((l is None or sum(a * y[k] for k, a in co.items()) >= l) and
                         (h is None or sum(a * y[k] for k, a in co.items()) <= h) for co, l, h in rows)
                f, bad = Q.evaluate(b, x)
                self.assertEqual(ok, bad == 0)
                if ok:
                    self.assertEqual(val, f)

    def test_wcnf_is_exact(self):
        rng = random.Random(4)
        for _ in range(10):
            b = random_bqp(rng, 8)
            hard, soft, nv, off = Q.to_wcnf(b)
            for x in product((0, 1), repeat=8):
                f, bad = Q.evaluate(b, x)
                best = None
                for aux in product((0, 1), repeat=nv - 8):
                    a = list(x) + list(aux)
                    sat = lambda cl: any((a[abs(l) - 1] == 1) == (l > 0) for l in cl)  # noqa: E731
                    if all(sat(cl) for cl in hard):
                        cost = sum(w for w, cl in soft if not sat(cl))
                        best = cost if best is None else min(best, cost)
                self.assertEqual(best is not None, bad == 0)
                if best is not None:
                    self.assertEqual(best + off, f)

    def test_repair_makes_feasible(self):
        rng = random.Random(5)
        for fam, params in (('mis', {'n': 40, 'd': 4}), ('coloring', {'n': 30, 'd': 4, 'k': 3})):
            inst = FM.generate(fam, 1, params)
            b = FM.compile(fam, inst)
            for _ in range(10):
                x = [rng.randint(0, 1) for _ in range(b['n'])]
                self.assertEqual(Q.evaluate(b, Q.repair(b, x))[1], 0)


class Families(unittest.TestCase):
    CASES = (('mis', {'n': 12, 'd': 3}), ('coloring', {'n': 6, 'd': 3, 'k': 3}), ('max2sat', {'n': 10, 'm': 30}),
             ('maxcut', {'n': 12, 'd': 3}))

    def test_round_trip_matches_brute_force(self):
        for fam, params in self.CASES:
            inst = FM.generate(fam, 7, params)
            self.assertEqual(inst, FM.generate(fam, 7, params))
            b = FM.compile(fam, inst)
            self.assertIsNone(Q.check(b))
            sign = 1 if FM.SENSE[fam] == 'max' else -1
            consts, scores = set(), []
            for x in product((0, 1), repeat=b['n']):
                f, bad = Q.evaluate(b, x)
                if bad:
                    continue
                ok, score, _ = FM.verify(fam, inst, FM.decode(fam, inst, x))
                self.assertTrue(ok, fam)
                consts.add(f + sign * score)          # the BQP minimises minus the score (or the score) + a constant
                scores.append(score)
            self.assertEqual(len(consts), 1, fam)
            self.assertTrue(scores)

    def test_verifier_rejects_bad_answers(self):
        inst = FM.generate('mis', 1, {'n': 10, 'd': 3})
        u, v = inst['edges'][0]
        self.assertFalse(FM.verify('mis', inst, {'vertices': [u, v]})[0])
        self.assertFalse(FM.verify('coloring', FM.generate('coloring', 1, {'n': 5, 'd': 2, 'k': 2}),
                                   {'colours': [0, 1, 2, 0, 1]})[0])
        self.assertFalse(FM.verify('max2sat', FM.generate('max2sat', 1, {'n': 4, 'm': 5}),
                                   {'assignment': [0, 1, 2, 0]})[0])
        self.assertFalse(FM.verify('maxcut', inst, {})[0])


class Backends(unittest.TestCase):
    def test_every_backend_reaches_the_optimum_on_small_instances(self):
        for fam, params in (('mis', {'n': 14, 'd': 3}), ('max2sat', {'n': 12, 'm': 40}),
                            ('coloring', {'n': 6, 'd': 3, 'k': 3}), ('maxcut', {'n': 14, 'd': 3})):
            inst = FM.generate(fam, 3, params)
            b = FM.compile(fam, inst)
            opt = brute(b)
            for be in BK.BACKENDS:
                kw = {'native': FM.wcnf(fam, inst)} if be == 'maxsat' else {}
                x, info = BK.run(be, b, 1.0, 1, **kw)
                f, bad = Q.evaluate(b, x)
                ok, score, why = FM.verify(fam, inst, FM.decode(fam, inst, x))
                self.assertTrue(ok, (fam, be, why, info))
                self.assertEqual((bad, f), (0, opt), (fam, be, info))


if __name__ == '__main__':
    unittest.main()
