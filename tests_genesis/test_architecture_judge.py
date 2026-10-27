"""ARA-1, the Limitation Zoo and the judge harness (kernel side; `docs/OMEGA_ARCHITECTURE_INVENTION.md` §7, §12):
sealed draws disjoint from dev; the view exposes no key; every incumbent well formed; the planted remedies help where
something is planted and nothing helps on NULL and DECOY; the judge's four checks each refuse what they should, its
verdict carries no sealed number, and its digest is pinned."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import graph as G  # noqa: E402
from genesis.architecture import judge as J  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

class Zoo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.envs = {c: Z.Environment(31, 77, c) for c in Z.CLASSES}

    def test_sealed_draws_are_disjoint_from_dev(self):
        env = self.envs['GLOBAL_ONLY']
        key = lambda g: (g['n'], tuple(map(tuple, g['edges'])))
        dev = {key(g) for s in ('dev_a', 'dev_b') for g in env.graphs[s]}
        sealed = {key(g) for s in ('confirm', 'sealed') for g in env.graphs[s]}
        self.assertFalse(dev & sealed)
        other = Z.Environment(31, 78, 'GLOBAL_ONLY')                        # another sealed seed: same dev, new sealed
        self.assertEqual([key(g) for g in other.graphs['dev_a']], [key(g) for g in env.graphs['dev_a']])
        self.assertNotEqual([key(g) for g in other.graphs['sealed']], [key(g) for g in env.graphs['sealed']])

    def test_the_view_exposes_no_key(self):
        v = self.envs['SENSE_BLIND'].view()
        public = {a for a in dir(v) if not a.startswith('_')}
        self.assertEqual(public, {'incumbent', 'K', 'budget', 'graphs', 'size', 'evaluate', 'units'})
        for split in ('confirm', 'sealed'):
            with self.assertRaises(KeyError):
                v.graphs(split)
            with self.assertRaises(KeyError):
                v.evaluate(split, 0, 0, 0)
        with self.assertRaises(AttributeError):
            v.cls = 'x'                                                     # slots: nothing can be attached
        n = v.units
        v.evaluate('dev_a', 0, 1, 0)
        self.assertEqual(v.units, n + 1)

    def test_every_incumbent_is_well_formed_and_defects_cost(self):
        for c, env in self.envs.items():
            self.assertEqual(G.check(env.incumbent), [], c)
        for c in Z.DEFECTS:
            env = self.envs[c]
            inc = G.execute(env.incumbent, env.view(), seed=0)
            rem = G.execute(env.remedy(), env.view(), seed=0)
            vi = env.value('sealed', G.choose(inc['policy'], env.graphs['sealed']))
            vr = env.value('sealed', G.choose(rem['policy'], env.graphs['sealed']))
            self.assertGreater(vr, vi + 0.1 * env.delta, c)

    def test_controls_have_nothing_to_gain_on_sealed_tasks(self):
        for c in ('NULL', 'DECOY'):
            env = self.envs[c]
            self.assertEqual(env.oracle('sealed'), 0.0)
        env = self.envs['DECOY']                                             # the decoy is real on dev only
        self.assertGreater(env.oracle('dev_a'), 0.0)
        env = self.envs['NO_HEADROOM']
        inc = G.execute(env.incumbent, env.view(), seed=0)
        v = env.value('sealed', G.choose(inc['policy'], env.graphs['sealed']))
        self.assertGreater(v, 0.9 * env.oracle('sealed'))

    def test_evaluation_is_deterministic_with_shared_and_independent_noise(self):
        env = self.envs['EVAL_NOISY']
        self.assertEqual(env.draw('dev_a', 3, 1, 5), env.draw('dev_a', 3, 1, 5))
        a = env.draw('dev_a', 3, 0, 5) - env.draw('dev_a', 3, 1, 5)
        b = env.draw('dev_a', 3, 0, 6) - env.draw('dev_a', 3, 1, 6)
        self.assertNotEqual(a, b)


class Judge(unittest.TestCase):
    def setUp(self):
        self.h = J.Harness(sealed_seed=5)
        self.view = self.h.open(0, 'GLOBAL_ONLY')
        self.env = self.h._env(0)
        self.remedy = self.env.remedy()
        run = G.execute(self.remedy, self.env.view(), seed=2)
        self.claim = {'policy': run['policy'], 'charges': run['charges'], 'seed': 2}

    def test_a_real_gain_is_promoted_and_the_verdict_has_no_numbers(self):
        v = self.h.submit(0, 'oracle_key', self.remedy, self.claim, 10.0, 100.0)
        self.assertEqual(v, {'promoted': True, 'failed': None})
        rec = self.h.ledger()[-1]
        self.assertGreaterEqual(rec['gain'], J.MATERIAL)
        self.assertEqual(rec['class'], 'STRUCTURAL')

    def test_each_check_refuses(self):
        bad = copy.deepcopy(self.remedy)
        bad['nodes']['out']['params'] = {'x': 1}
        self.assertEqual(self.h.submit(0, 'a', bad, self.claim, 1, 100)['failed'], 'correctness')
        wrong = dict(self.claim, charges={'search': 1.0})
        self.assertEqual(self.h.submit(0, 'a', self.remedy, wrong, 1, 100)['failed'], 'reproducibility')
        self.assertEqual(self.h.submit(0, 'a', self.remedy, self.claim, 101, 100)['failed'], 'budget')
        inc = self.env.incumbent
        run = G.execute(inc, self.env.view(), seed=2)
        same = {'policy': run['policy'], 'charges': run['charges'], 'seed': 2}
        self.assertEqual(self.h.submit(0, 'a', inc, same, 1, 100)['failed'], 'sealed')

    def test_the_key_and_the_oracle_arm_are_for_the_study(self):
        self.assertEqual(self.h.key(0), {'class': 'GLOBAL_ONLY', 'location': 'expressiveness'})
        self.assertGreater(self.h.oracle_key(0), J.MATERIAL)

    def test_the_judge_is_pinned(self):
        got = hashlib.sha256((ROOT / 'src' / 'genesis' / 'architecture' / 'judge.py').read_bytes()).hexdigest()
        self.assertEqual(got, PINNED)


PINNED = 'a065a095ede61db8803610f2f967d155d845536d7116303739194658081b9003'     # judge.py; a change is a human-gated amendment

if __name__ == '__main__':
    unittest.main()
