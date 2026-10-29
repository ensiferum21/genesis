"""G4's state features for the Frontier's own allocator (`frontier/statefeat.py`; `docs/OMEGA_FOUNDRY.md` §3,
B20_R172): the primitives; the feature language; the defaults and decision logging leave runs unchanged; replays are
pure and charged; the proposal recovers a planted distinction and proposes nothing on noise; a feature in the policy
changes decisions deterministically. Planted worlds of seeds no study uses (887xxx)."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import statefeat as SF  # noqa: E402


def engine(params=None, seed=887011, budget=6000):
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    from genesis.frontier.world import PlantedWorld
    w = PlantedWorld(seed, problems=3, horizon=budget, sigma=0.02)
    e = Frontier(Manifest(w, w.verify, budget, quantum=10, description={'test': 'G4'}), 'frontier', seed=5,
                 abstraction=False, branch_out=False, policy_params=params)
    e.run()
    return e, w


class Primitives(unittest.TestCase):
    def test_values(self):
        br = {'t': 100.0, 'ts': [10.0 * i for i in range(1, 11)], 'ys': [0.0, 0.1, 0.2, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]}
        fc = {'lo': 0.2, 'mid': 0.35, 'hi': 0.5}
        p = SF.primitives(br, fc, 0.25, 0.25, 0.0, 0.0, 0.25, 200.0)
        self.assertAlmostEqual(p['level'], 0.3)
        self.assertAlmostEqual(p['head'], 0.05)
        self.assertAlmostEqual(p['width'], 0.3)
        self.assertEqual(p['since'], 60.0)                     # the running maximum last rose at t = 40
        self.assertEqual(p['slope4'], 0.0)
        self.assertGreater(p['slope16'], 0.0)
        self.assertEqual(p['frac'], 0.5)
        self.assertEqual(set(p), set(SF.PRIMS))

    def test_language(self):
        lang = SF.language()
        self.assertEqual(len(lang), 17 + 17 * 16 * 2 + 17 * 16 // 2)
        self.assertTrue(all(SF.check(x) for x in lang))
        self.assertFalse(SF.check(['+', 'gain', 'lp']))
        self.assertFalse(SF.check(['-', 'gain', ['-', 'lp', 'con']]))
        with self.assertRaises(ValueError):
            SF.evaluate('oracle', {})
        self.assertEqual(SF.evaluate(['/', 'gain', 'lp'], {'gain': 1.0, 'lp': 0.0}), 0.0)


class InTheEngine(unittest.TestCase):
    def test_defaults_and_logging_change_nothing(self):
        a, _ = engine()
        b, _ = engine({'state_feature': None, 'log_decisions': False})
        c, _ = engine({'log_decisions': True})
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.events, c.events)
        self.assertEqual(a.policy.decisions, [])
        self.assertGreater(len(c.policy.decisions), 10)
        self.assertTrue(all(len(d['top']) == 2 for d in c.policy.decisions))

    def test_replays_are_pure_and_charged(self):
        e, w = engine({'log_decisions': True})
        dec = e.policy.decisions[len(e.policy.decisions) // 2]
        br = dec['top'][0]['branch']
        g1, c1 = SF.replay_gain(w, br, 8, 10)
        g2, c2 = SF.replay_gain(w, br, 8, 10)
        self.assertEqual((g1, c1), (g2, c2))
        self.assertEqual(c1, 80)
        pairs, used = SF.counterexamples(w, e.policy.decisions, 5, 10, max_pairs=12)
        self.assertEqual(len(pairs), 12)
        self.assertEqual(used, 12 * 2 * 5 * 10)

    def test_a_feature_changes_decisions_deterministically(self):
        f = {'expr': 'n', 'weight': -0.01}           # fewer points first: large enough to matter
        a, _ = engine({'state_feature': f})
        b, _ = engine({'state_feature': f})
        c, _ = engine()
        self.assertEqual(a.events, b.events)
        self.assertNotEqual(a.events, c.events)
        with self.assertRaises(ValueError):
            engine({'state_feature': {'expr': 'oracle', 'weight': 1.0}})


class Proposal(unittest.TestCase):
    def synthetic(self, n, planted, seed=0):
        rng = random.Random(seed)
        pairs = []
        for i in range(n):
            pa = {k: rng.random() for k in SF.PRIMS}
            pb = {k: rng.random() for k in SF.PRIMS}
            pa['index'], pb['index'] = 1.0 + 0.01 * rng.random(), 1.0 + 0.01 * rng.random()   # the index looks alike
            if planted:
                ga, gb = -pa['since'], -pb['since']            # a branch that stalled longer gains less
            else:
                ga, gb = rng.random(), rng.random()
            pairs.append({'a': pa, 'b': pb, 'gain_a': ga, 'gain_b': gb, 'step': i})
        return pairs

    def test_recovers_a_planted_distinction(self):
        pairs = self.synthetic(200, planted=True)
        r = SF.propose(pairs)
        self.assertIsNotNone(r)
        self.assertIn('since', r['expr'] if isinstance(r['expr'], list) else [r['expr']])
        self.assertGreater(r['held_out'], 0.9)
        self.assertLess(r['baseline'], 0.6)
        self.assertLess(r['weight'], 0)                        # longer stalls rank lower
        self.assertGreater(SF.agreement(pairs, r['expr'], r['weight']), 0.9)

    def test_proposes_nothing_on_noise(self):
        found = sum(SF.propose(self.synthetic(200, planted=False, seed=s)) is not None for s in range(5))
        self.assertLessEqual(found, 1)

    def test_on_engine_decisions(self):
        e, w = engine({'log_decisions': True}, budget=8000)
        pairs, used = SF.counterexamples(w, e.policy.decisions, 10, 10, max_pairs=120)
        self.assertGreater(used, 0)
        r = SF.propose(pairs)
        if r is not None:
            self.assertTrue(SF.check(r['expr']))
            self.assertGreaterEqual(r['held_out'], r['baseline'] + SF.MIN_GAIN)


if __name__ == '__main__':
    unittest.main()
