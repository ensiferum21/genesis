"""ARA-1, the limitation scientist and the cycle (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §4, §8, §9, §15): the ladder
localises planted search and expressiveness limitations and says NONE where nothing is attainable; the cycle
modifies when the dev gain qualifies, solves (keeps the incumbent) when nothing does, stays within its budget,
always ends in the reattempt, and is judged; the blind control uses the same generator without the ladder; the
tuning-only control changes nothing but TUNING-class choices. These are fixture tests of the mechanism on single
generated environments, not results (`B20_R141` is the study)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import ara as A  # noqa: E402
from genesis.architecture import diagnose as D  # noqa: E402
from genesis.architecture import graph as G  # noqa: E402
from genesis.architecture import judge as J  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

ENV_SEED = 1234      # fixture environments (development only; B20_R141 uses its own preregistered seeds)


class Ladder(unittest.TestCase):
    def test_localisation_on_fixtures(self):
        for cls, want in (('SEARCH_WEAK', 'search'), ('GLOBAL_ONLY', 'expressiveness'), ('NULL', 'NONE'),
                          ('NO_HEADROOM', 'NONE')):
            v = Z.Environment(ENV_SEED, 99, cls).view()
            L = D.ladder(v, v.incumbent, seed=0)
            self.assertEqual(L['diagnosis'], want, cls)
            if want == 'NONE':
                self.assertEqual(L['located'], [])
            else:
                self.assertIn(want, L['significant'])

    def test_no_attainable_range_means_nothing_is_material(self):
        v = Z.Environment(ENV_SEED, 99, 'NULL').view()
        L = D.ladder(v, v.incumbent, seed=0)
        self.assertTrue(L['range_lo'] <= 0 or L['diagnosis'] == 'NONE')

    def test_the_ladder_is_deterministic_and_draws_each_cell_once(self):
        a = Z.Environment(ENV_SEED, 99, 'SEARCH_WEAK').view()
        b = Z.Environment(ENV_SEED, 99, 'SEARCH_WEAK').view()
        La, Lb = D.ladder(a, a.incumbent, seed=0), D.ladder(b, b.incumbent, seed=0)
        self.assertEqual(La['terms'], Lb['terms'])
        n = a.size('dev_a') + a.size('dev_b')
        self.assertEqual(a.units, n * a.K * D.EXACT_REPEATS)    # the incumbent's own run reused the lab's draws

    def test_the_battery_holds_every_primitive_aggregate(self):
        b = D.battery(0)
        for p in ('deg', 'clust', 'tri', 'core'):
            self.assertIn(['mean_n', p], b)
        self.assertEqual(len(b), len({repr(x) for x in b}))


class Cycle(unittest.TestCase):
    def run_cycle(self, cls, **kw):
        h = J.Harness(sealed_seed=8)
        view = h.open(0, cls)
        budget = 4 * view.budget
        tr = A.cycle(view, seed=1, budget=budget,
                     submit=lambda v, c, u: h.submit(0, 'ara', v, c, u, budget), **kw)
        return h, view, tr, budget

    def test_modify_when_a_variant_qualifies(self):
        h, view, tr, budget = self.run_cycle('GLOBAL_ONLY')
        self.assertEqual(tr['arm'], 'modify')
        self.assertEqual(tr['submitted']['class'], 'STRUCTURAL')
        self.assertTrue(tr['verdict']['promoted'])
        self.assertLessEqual(tr['units']['spent'], budget)
        self.assertFalse(tr['final']['is_incumbent'])
        self.assertEqual(tr['final']['ag']['nodes']['out'], view.incumbent['nodes']['out'])    # the reattempt
        rec = h.ledger()[-1]
        self.assertTrue(rec['promoted'] and rec['arm'] == 'ara')

    def test_solve_when_nothing_qualifies(self):
        h, view, tr, budget = self.run_cycle('NULL')
        self.assertEqual(tr['arm'], 'solve')
        self.assertIsNone(tr['submitted'])
        self.assertTrue(tr['final']['is_incumbent'])
        self.assertEqual(h.ledger(), [])

    def test_a_tiny_budget_stops_the_cycle(self):
        h = J.Harness(sealed_seed=8)
        view = h.open(0, 'GLOBAL_ONLY')
        tr = A.cycle(view, seed=1, budget=view.units + 1500.0, submit=None)
        self.assertIn(tr['arm'], ('stop', 'solve', 'modify'))
        self.assertLessEqual(len([v for v in tr['variants'] if 'dev_value' in v]), A.MAX_VARIANTS)

    def test_the_blind_control_uses_the_generator_without_the_ladder(self):
        h, view, tr, budget = self.run_cycle('GLOBAL_ONLY', diagnose=False)
        self.assertIsNone(tr['diagnosis'])
        self.assertTrue(all(v['rewrite']['op'] in A.R.OPERATORS for v in tr['variants']))

    def test_tuning_only_changes_only_tuning(self):
        h = J.Harness(sealed_seed=8)
        view = h.open(0, 'SEARCH_WEAK')
        cands = A.tune_candidates(view.incumbent, 0)
        self.assertTrue(cands)
        self.assertTrue(all(G.classify(view.incumbent, c) == 'TUNING' for c in cands))
        budget = 4 * view.budget
        tr = A.tune_only(view, seed=1, budget=budget, submit=lambda v, c, u: h.submit(0, 'tuning', v, c, u, budget))
        self.assertEqual(tr['arm'], 'tuning')
        self.assertLessEqual(tr['units']['spent'], budget)
        self.assertIn(G.classify(view.incumbent, tr['final']['ag']), ('TUNING', 'NONE'))


if __name__ == '__main__':
    unittest.main()
