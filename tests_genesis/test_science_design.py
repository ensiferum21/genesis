"""B20_R129 (Genesis Ω, P1): the domain-independent experimental scientist and Genesis's acquisition language.
Bayes updates, information gain and decision improvement against hand computation; the lookahead; the acquisitions'
choices; the language's checks, interpreter and search operators; and that the decision layer imports no domain."""
import json
import math
from pathlib import Path
import random
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.science import acquire as Q  # noqa: E402
from genesis.science import design as D  # noqa: E402


class Toy(D.Domain):
    """Two binary questions. Experiment 'a' reveals q1 exactly; 'b' says nothing; 'c' and 'd' each half-reveal q2
    (q2 = XOR of two hidden bits; each experiment shows one bit), so only both together answer q2."""
    focus = 'yes'

    def __init__(self, truth=('yes', 'no')):
        self.truth = truth

    def questions(self):
        return ['q1', 'q2']

    def hypotheses(self):
        return ('yes', 'no')

    def outcomes(self):
        return ('0', '1')

    def prior(self, q):
        return [0.5, 0.5]

    def experiments(self):
        return ['a', 'b', 'c', 'd']

    def touches(self, e):
        return {'a': ['q1'], 'b': ['q1'], 'c': ['q2'], 'd': ['q2']}[e]

    def predict(self, q, e):
        if e == 'a':
            return [[1.0, 0.0], [0.0, 1.0]]
        if e == 'b':
            return [[0.5, 0.5], [0.5, 0.5]]
        if e == 'c':
            return [[0.5, 0.5], [0.5, 0.5]]
        return [[0.5, 0.5], [0.5, 0.5]]

    def execute(self, e):
        q = self.touches(e)[0]
        return {q: '0' if (e == 'a' and self.truth[0] == 'yes') else '1'}


class XorDomain(Toy):
    """q2's hypotheses are the four bit pairs; 'c' shows bit 1, 'd' bit 2; the decision of interest is the pair."""

    def hypotheses(self):
        return ('00', '01', '10', '11')

    def prior(self, q):
        return [0.25] * 4

    def predict(self, q, e):
        bit = 0 if e == 'c' else 1
        return [[1.0 if h[bit] == o else 0.0 for o in '01'] for h in self.hypotheses()]

    focus = '11'


class Information(unittest.TestCase):
    def test_entropy_and_values_match_hand_computation(self):
        p = np.array([0.5, 0.5])
        f = D.features(p, np.array([[1.0, 0.0], [0.0, 1.0]]), 0, 0)
        self.assertAlmostEqual(f['eig'], math.log(2))
        self.assertAlmostEqual(f['dec'], 0.5)                      # 0.5 -> 1.0
        self.assertAlmostEqual(f['decf'], 0.5)
        f = D.features(p, np.array([[0.5, 0.5], [0.5, 0.5]]), 0, 0)
        self.assertAlmostEqual(f['eig'], 0.0)
        self.assertAlmostEqual(f['dec'], 0.0)
        self.assertAlmostEqual(f['ent'], 1.0)
        # a noisy test: P(o=0 | yes) = 0.8, P(o=0 | no) = 0.3, prior 0.5
        L = np.array([[0.8, 0.2], [0.3, 0.7]])
        f = D.features(p, L, 0, 0)
        po = [0.55, 0.45]
        post = [[0.8 * 0.5 / 0.55, 0.3 * 0.5 / 0.55], [0.2 * 0.5 / 0.45, 0.7 * 0.5 / 0.45]]
        H = lambda x: -sum(v * math.log(v) for v in x if v > 0)  # noqa: E731
        self.assertAlmostEqual(f['eig'], H([0.5, 0.5]) - po[0] * H(post[0]) - po[1] * H(post[1]))
        self.assertAlmostEqual(f['dec'], 0.4 + 0.35 - 0.5)

    def test_lookahead_values_two_experiments_together(self):
        d = XorDomain()
        b = D.Beliefs(d)
        r = D.Run(d, b)
        c = b.feature('q2', (), 'c', ('d',))
        self.assertAlmostEqual(c['eig'], math.log(2))              # one bit
        self.assertAlmostEqual(c['eigall'], math.log(4))           # both bits
        self.assertAlmostEqual(c['decfall'] - c['decf'], 0.25)     # "is it 11?" answered only by both
        self.assertEqual(c['left'], 2.0)
        self.assertEqual(r.by_q['q2'], ['c', 'd'])

    def test_bayes_update_and_decisions(self):
        d = Toy(truth=('no', 'no'))
        r = D.Run(d)
        self.assertEqual(r.decisions(), {'q1': 'yes', 'q2': 'yes'})          # ties to the first hypothesis
        r.do('a')
        self.assertTrue(np.allclose(r.posterior('q1'), [0.0, 1.0]))
        self.assertEqual(r.decisions()['q1'], 'no')
        r.do('b')
        self.assertTrue(np.allclose(r.posterior('q1'), [0.0, 1.0]))
        self.assertAlmostEqual(r.total_entropy(), math.log(2))                 # q2 untouched

    def test_impossible_outcome_is_ignored(self):
        d = Toy(truth=('yes', 'no'))
        b = D.Beliefs(d)
        p = b.posterior('q1', (('a', '0'),))
        self.assertTrue(np.allclose(b.posterior('q1', (('a', '0'), ('a', '1'))), p))

    def test_history_is_order_free(self):
        d = XorDomain()
        r1, r2 = D.Run(d), D.Run(d)
        r1.do('c'), r1.do('d')
        r2.do('d'), r2.do('c')
        self.assertEqual(r1.hist, r2.hist)
        self.assertTrue(np.allclose(r1.posterior('q2'), r2.posterior('q2')))


class Acquisitions(unittest.TestCase):
    def test_choices(self):
        d = Toy()
        rng = np.random.default_rng(0)
        self.assertEqual(D.choose(D.Run(d), {'kind': 'eig'}, rng), 'a')
        self.assertEqual(D.choose(D.Run(d), {'kind': 'dec'}, rng), 'a')
        self.assertEqual(D.choose(D.Run(d), {'kind': 'hybrid', 'lam': 2.0}, rng), 'a')
        self.assertEqual(D.choose(D.Run(d), {'kind': 'order', 'order': ['c', 'a', 'b', 'd']}, rng), 'c')
        r = D.Run(d)
        r.do('a')
        self.assertEqual(D.choose(r, {'kind': 'eig'}, rng), 'b')          # all zero now: ties to the earliest
        self.assertIn(D.choose(D.Run(d), {'kind': 'random'}, np.random.default_rng(1)), d.experiments())
        r = D.Run(d)
        for e in d.experiments():
            r.do(e)
        self.assertIsNone(D.choose(r, {'kind': 'eig'}, rng))
        with self.assertRaises(ValueError):
            D.choose(D.Run(d), {'kind': 'nonsense'}, rng)

    def test_static_eig_ignores_results(self):
        class Redundant(Toy):
            """x and y both answer q1 exactly; z is a noisy test of q2."""
            def experiments(self):
                return ['x', 'y', 'z']

            def touches(self, e):
                return ['q2'] if e == 'z' else ['q1']

            def predict(self, q, e):
                return [[0.8, 0.2], [0.3, 0.7]] if e == 'z' else [[1.0, 0.0], [0.0, 1.0]]

            def execute(self, e):
                return {self.touches(e)[0]: '0'}
        d = Redundant()
        r = D.Run(d)
        r.do('x')
        self.assertEqual(D.choose(r, {'kind': 'eig'}, None), 'z')           # q1 is answered: y is now worthless
        self.assertEqual(D.choose(r, {'kind': 'static_eig'}, None), 'y')    # the prior's ranking, never updated

    def test_program_matches_builtin(self):
        for acq, prog in (({'kind': 'eig'}, Q.EIG), ({'kind': 'dec'}, Q.DEC),
                          ({'kind': 'hybrid', 'lam': 4.0}, Q.hybrid(4.0))):
            for truth in (('yes', 'no'), ('no', 'yes')):
                a = D.run(Toy(truth), acq, 4)[0].done
                b = D.run(Toy(truth), {'kind': 'program', 'program': prog}, 4)[0].done
                self.assertEqual(a, b)

    def test_run_trail_and_stop(self):
        r, trail = D.run(Toy(), {'kind': 'eig'}, 4)
        self.assertEqual(len(trail), 5)
        self.assertEqual(sorted(r.done), ['a', 'b', 'c', 'd'])
        r, trail = D.run(Toy(), {'kind': 'eig'}, 4, stop=lambda k, dec: k == 1)
        self.assertEqual((len(trail), r.done), (2, ['a']))
        r, trail = D.run(Toy(), {'kind': 'eig'}, 4, stop=lambda k, dec: True)
        self.assertEqual((len(trail), r.done), (1, []))

    def test_decision_layer_imports_no_domain(self):
        for name in ('design.py', 'acquire.py'):
            text = (ROOT / 'src' / 'genesis' / 'science' / name).read_text()
            for dom in ('causal', 'maxcut', 'gset', 'candidate_kinds'):
                self.assertNotIn(f'import {dom}', text)
                self.assertNotIn(f'from ..{dom}', text)


class Language(unittest.TestCase):
    def test_check(self):
        self.assertIsNone(Q.check(Q.EIG))
        self.assertIsNone(Q.check(Q.hybrid(0.25)))
        for bad in ({'agg': 'sum'}, {'agg': 'mean', 'expr': 'eig'}, {'agg': 'sum', 'expr': 'nope'},
                    {'agg': 'sum', 'expr': 3.0}, {'agg': 'sum', 'expr': ['/', 'eig', 'dec']},
                    {'agg': 'sum', 'expr': ['+', 'eig']}, {'agg': 'sum', 'expr': '__import__'},
                    {'agg': 'sum', 'expr': ['+'] + [['+', ['+', ['+', ['+', 'eig', 'eig'], 'eig'], 'eig'], 'eig']] * 2}):
            self.assertIsNotNone(Q.check(bad), bad)

    def test_interpreter(self):
        pairs = [(0, {f: 1.0 for f in D.FEATURES}), (0, dict({f: 1.0 for f in D.FEATURES}, eig=3.0)),
                 (2, {f: 2.0 for f in D.FEATURES})]
        self.assertEqual(list(Q.scores({'agg': 'sum', 'expr': 'eig'}, 3, pairs)), [4.0, 0.0, 2.0])
        self.assertEqual(list(Q.scores({'agg': 'max', 'expr': 'eig'}, 3, pairs)), [3.0, 0.0, 2.0])
        self.assertEqual(list(Q.scores({'agg': 'sum', 'expr': ['-', 'one', ['inv1', 'dec']]}, 3, pairs)),
                         [1.0, 0.0, 2 - 1 / 3])
        self.assertEqual(Q.text(Q.hybrid(2.0)), 'sum (eig + (2.0 * dec))')

    def test_operators_always_give_programs(self):
        rng = random.Random(5)
        ops = Q.ops([Q.EIG, Q.DEC])
        self.assertEqual(ops['random'](rng), Q.EIG)
        self.assertEqual(ops['random'](rng), Q.DEC)
        progs = [ops['random'](rng) for _ in range(200)]
        for _ in range(2000):
            a, b = rng.choice(progs), rng.choice(progs)
            for c in (ops['mutate'](a, rng), ops['crossover'](a, b, rng)):
                self.assertIsNone(Q.check(c), c)
                self.assertEqual(json.loads(json.dumps(c)), c)
                self.assertGreaterEqual(ops['size'](c), 1)
        with self.assertRaises(ValueError):
            Q.ops([{'agg': 'sum', 'expr': 'nope'}])

    def test_same_program_same_choices(self):
        rng = random.Random(9)
        for _ in range(50):
            prog = Q.random_program(rng)
            a = D.run(XorDomain(), {'kind': 'program', 'program': prog}, 4)[0].done
            b = D.run(XorDomain(), {'kind': 'program', 'program': json.loads(json.dumps(prog))}, 4)[0].done
            self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
