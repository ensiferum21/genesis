"""G2's forecast-calibration rules (`frontier/calibrate.py`; `docs/OMEGA_FOUNDRY.md` §3, B20_R170): the grammar and its
canonical forms; the identity rule leaves the engine unchanged; each update converges on stationary residuals to the
nominal coverage; the shift corrects a bias; hindcast origins; state round trips; the policy hook resolves forecasts
deterministically in an engine run on a planted world of a seed no study uses."""
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import calibrate as CAL  # noqa: E402


def stream(n, scale=1.0, bias=0.0, seed=0):
    """Raw forecasts with half-width 1 around 0, and truths N(bias, (scale / 1.645)^2): a forecaster whose nominal 90%
    interval is `scale` times too narrow (and biased by `bias`)."""
    rng = random.Random(seed)
    for _ in range(n):
        yield {'lo': -1.0, 'mid': 0.0, 'hi': 1.0}, rng.gauss(bias, scale / 1.645)


def coverage(cal, n=4000, scale=2.0, bias=0.0, seed=1, frac=0.6):
    hits = 0
    for fc, truth in stream(n, scale, bias, seed):
        adj = cal.adjust(fc, frac)
        hits += adj['lo'] <= truth <= adj['hi']
    return hits / n


class Grammar(unittest.TestCase):
    def test_grid_and_validation(self):
        self.assertEqual(CAL.rule_of({}), CAL.DEFAULT)
        with self.assertRaises(ValueError):
            CAL.rule_of({'cal_signal': 'oracle'})
        n = 1
        for v in CAL.GRID.values():
            n *= len(v)
        self.assertEqual(n, 144)
        distinct = set()
        import itertools
        keys = sorted(CAL.GRID)
        for combo in itertools.product(*(CAL.GRID[k] for k in keys)):
            distinct.add(tuple(sorted(CAL.canonical(dict(zip(keys, combo))).items())))
        self.assertEqual(len(distinct), 81)       # the identity and 2 signals x (16 scale + 16 both + 8 shift)
        self.assertEqual(CAL.canonical({'cal_signal': 'none', 'cal_form': 'shift'}), CAL.DEFAULT)

    def test_identity_changes_nothing(self):
        c = CAL.Calibrator({})
        fc = {'lo': 0.1, 'mid': 0.2, 'hi': 0.4, 'n': 9}
        self.assertIs(c.adjust(fc, 0.5), fc)
        c.resolve(fc, 0.5, 9.0)
        self.assertEqual((c.state, c.resolved), ({}, 0))

    def test_open_intervals_pass_through(self):
        c = CAL.Calibrator({'cal_signal': 'hindcast'})
        fc = {'lo': -math.inf, 'mid': 0.0, 'hi': math.inf}
        self.assertIs(c.adjust(fc, 0.5), fc)
        c.resolve(fc, 0.5, 1.0)
        self.assertEqual(c.resolved, 0)


class Updates(unittest.TestCase):
    def learn(self, rule, n=3000, scale=2.0, bias=0.0):
        c = CAL.Calibrator(dict(rule, cal_signal='hindcast'))
        for fc, truth in stream(n, scale, bias, seed=7):
            c.resolve(fc, 0.6, truth)
        return c

    def test_aci_scale_reaches_nominal_coverage(self):
        fixed = CAL.Calibrator({})
        self.assertLess(coverage(fixed), 0.65)                      # the raw interval is twice too narrow
        for rate in CAL.GRID['cal_rate']:
            c = self.learn({'cal_form': 'scale', 'cal_update': 'aci', 'cal_rate': rate}, n=6000)
            self.assertAlmostEqual(coverage(c), 0.90, delta=0.04, msg=rate)

    def test_quantile_scale_is_the_conformal_quantile(self):
        c = self.learn({'cal_form': 'scale', 'cal_update': 'quantile', 'cal_rate': 0.01})
        st = c.state['0']
        self.assertEqual(len(st['q']), 200)
        import numpy as np
        q = np.array(st['q'])
        self.assertAlmostEqual(st['s_hi'], float(np.quantile(q[:, 0] / q[:, 1], 0.95)), places=12)
        self.assertAlmostEqual(coverage(c), 0.90, delta=0.05)

    def test_shift_removes_a_bias(self):
        biased = CAL.Calibrator({})
        self.assertLess(coverage(biased, scale=1.0, bias=0.8), 0.80)
        for upd in ('aci', 'quantile'):
            c = self.learn({'cal_form': 'both', 'cal_update': upd, 'cal_rate': 0.05}, scale=1.0, bias=0.8)
            self.assertAlmostEqual(c.state['0']['d'], 0.8, delta=0.25, msg=upd)
            self.assertAlmostEqual(coverage(c, scale=1.0, bias=0.8), 0.90, delta=0.06, msg=upd)

    def test_upper_side_only_and_bands(self):
        c = self.learn({'cal_form': 'scale', 'cal_sides': 'hi', 'cal_update': 'aci'})
        self.assertEqual(c.state['0']['s_lo'], 1.0)
        self.assertGreater(c.state['0']['s_hi'], 1.5)
        b = CAL.Calibrator({'cal_signal': 'resolved', 'cal_cond': 'frac'})
        for frac in (0.1, 0.6, 0.9):
            b.resolve({'lo': -1.0, 'mid': 0.0, 'hi': 1.0}, frac, 5.0)
        self.assertEqual(sorted(b.state), ['0', '1', '2'])

    def test_bounds(self):
        c = self.learn({'cal_form': 'scale', 'cal_update': 'aci', 'cal_rate': 0.05}, n=20000, scale=40.0)
        self.assertLessEqual(c.state['0']['s_hi'], CAL.S_MAX)

    def test_round_trip(self):
        c = self.learn({'cal_form': 'both', 'cal_update': 'quantile'}, n=50)
        d = CAL.Calibrator(c.rule)
        d.load(c.to_json())
        fc = {'lo': -1.0, 'mid': 0.0, 'hi': 1.0}
        self.assertEqual(c.adjust(fc, 0.6), d.adjust(fc, 0.6))
        with self.assertRaises(ValueError):
            CAL.Calibrator({'cal_signal': 'resolved'}).load(c.to_json())

    def test_hindcast_origin(self):
        self.assertIsNone(CAL.hindcast_origin([10, 20, 30, 40], 0.5))
        ts = [10 * i for i in range(1, 21)]
        j = CAL.hindcast_origin(ts, 0.5)
        self.assertEqual(ts[j], 100)
        self.assertIsNone(CAL.hindcast_origin(ts, 0.1))           # fewer than 4 points before the origin
        self.assertIsNone(CAL.hindcast_origin(ts, 1.0))           # nothing left to forecast


class InTheEngine(unittest.TestCase):
    def run_engine(self, rule, seed=887001, budget=8000):
        from genesis.frontier.engine import Frontier
        from genesis.frontier.manifest import Manifest
        from genesis.frontier.world import PlantedWorld
        w = PlantedWorld(seed, problems=3, horizon=budget, sigma=0.02)
        e = Frontier(Manifest(w, w.verify, budget, quantum=10, description={'test': 'G2'}), 'frontier', seed=3,
                     abstraction=False, branch_out=False, policy_params=rule)
        e.run()
        return e

    def test_identity_rule_is_the_defaults(self):
        a = self.run_engine({})
        b = self.run_engine(dict(CAL.DEFAULT))
        self.assertEqual(a.events, b.events)
        self.assertNotIn('calib', a.policy.to_json())

    def test_rules_resolve_and_replay(self):
        for sig in ('resolved', 'hindcast'):
            rule = {'cal_signal': sig, 'cal_form': 'both', 'cal_update': 'aci'}
            a, b = self.run_engine(rule), self.run_engine(rule)
            self.assertGreater(a.policy.calib.resolved, 0, sig)
            self.assertEqual(a.events, b.events, sig)
            self.assertEqual(a.policy.calib.state, b.policy.calib.state, sig)
            self.assertTrue(a.policy._fc_used)

    def test_save_and_resume(self):
        import tempfile
        from genesis.frontier.engine import Frontier
        from genesis.frontier.manifest import Manifest
        from genesis.frontier.world import PlantedWorld
        rule = {'cal_signal': 'resolved', 'cal_form': 'scale', 'cal_update': 'quantile'}
        whole = self.run_engine(rule)
        w = PlantedWorld(887001, problems=3, horizon=8000, sigma=0.02)
        m = Manifest(w, w.verify, 8000, quantum=10, description={'test': 'G2'})
        e = Frontier(m, 'frontier', seed=3, abstraction=False, branch_out=False, policy_params=rule)
        e.run(max_steps=120)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.json'
            e.save(p)
            e2 = Frontier.load(p, Manifest(w, w.verify, 8000, quantum=10, description={'test': 'G2'}),
                               policy_params=rule)
        self.assertEqual(e2.policy.calib.to_json(), e.policy.calib.to_json())
        e2.run()
        self.assertEqual(e2.total(), whole.total())


if __name__ == '__main__':
    unittest.main()
