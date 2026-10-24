"""Genesis Ω contract §4, §16.3: a new typed primitive is synthesised from recurring structure, registered in a new
immutable library version with its contract, reused by the search and evaluated exactly as its expansion, and rolled
back (a program naming it is refused against the earlier version, never reinterpreted)."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.science import acquire as Q  # noqa: E402
from genesis.science import design as D  # noqa: E402
from genesis.science import library as L  # noqa: E402

SUB = ['*', 'decall', ['sq', 'pf']]
PROGS = [{'agg': 'max', 'expr': SUB}, {'agg': 'sum', 'expr': ['+', SUB, 'eig']},
         {'agg': 'sum', 'expr': ['max', SUB, ['*', 0.5, 'dec']]}, {'agg': 'sum', 'expr': ['+', 'eig', 'dec']}]


def domains(n, seed0):
    from genesis.causal import active3 as A3
    from genesis.causal import sem as S
    out = []
    for s in range(seed0, seed0 + n):
        view, truth = S.instance(s, 8, 2, 0.3, 'gauss', 3, 1500)
        out.append(A3.CausalDomain(A3.prepare(view, truth, 500, s), A3.THEORY))
    return out


class Library(unittest.TestCase):
    def test_synthesise_register_reuse_rollback(self):
        body, count = L.synthesise(PROGS, L.EMPTY)
        self.assertEqual((body, count), (SUB, 2))                 # recurs in two programs as a proper subtree
        v0 = L.EMPTY
        v1 = L.register(v0, 'p1', body, {'from': 'test programs', 'count': count})
        self.assertNotEqual(L.version(v1), L.version(v0))
        self.assertEqual(v1['parent'], L.version(v0))
        self.assertEqual(v1['primitives'][0]['range'], [0.0, 1.0])
        self.assertIn('p1', L.features(v1))
        self.assertEqual(L.synthesise(PROGS, v1)[0] != SUB, True)  # not proposed again
        # reuse: the search operators draw p1 as a leaf; programs with it run as their expansions
        ops = Q.ops(features=L.features(v1))
        rng = random.Random(3)
        drawn = [ops['random'](rng) for _ in range(200)]
        uses = [p for p in drawn if 'p1' in str(p['expr'])]
        self.assertTrue(uses)
        doms = domains(4, 4200)
        prog = {'agg': 'sum', 'expr': ['+', 'p1', 'eig']}
        self.assertIsNone(L.check(prog, v1))
        a = [D.run(d, L.acq(prog, v1), 4)[0].done for d in doms]
        b = [D.run(d, {'kind': 'program', 'program': {'agg': 'sum', 'expr': ['+', SUB, 'eig']}}, 4)[0].done
             for d in doms]
        self.assertEqual(a, b)
        # rollback: against v0 the program is refused
        self.assertIsNotNone(L.check(prog, v0))
        with self.assertRaises(ValueError):
            L.acq(prog, v0)
        # a primitive is one node: a program of 15 nodes written with it is valid though its expansion is larger
        big = {'agg': 'sum', 'expr': ['+', ['+', ['+', 'p1', 'p1'], ['+', 'p1', 'p1']],
                                      ['+', ['+', 'p1', 'p1'], ['+', 'p1', 'p1']]]}
        self.assertIsNone(L.check(big, v1))

    def test_register_refusals(self):
        with self.assertRaises(ValueError):
            L.register(L.EMPTY, 'eig', SUB, {})                   # a feature's name
        v1 = L.register(L.EMPTY, 'p1', SUB, {})
        with self.assertRaises(ValueError):
            L.register(v1, 'p1', ['+', 'eig', 'dec'], {})          # an existing name
        with self.assertRaises(ValueError):
            L.register(v1, 'p2', ['+', 'nothing', 'dec'], {})      # unknown names
        v2 = L.register(v1, 'p2', ['*', 'p1', 2.0], {})            # primitives compose
        self.assertEqual(L.expand_tree('p2', v2), ['*', SUB, 2.0])


if __name__ == '__main__':
    unittest.main()
