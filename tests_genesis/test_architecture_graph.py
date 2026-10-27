"""ARA-1, the Architecture Graph (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §2.2, §2.3): type correctness, the closed
kernel, budget conservation, determinism, bounded execution, per-node charges and the diff classifier."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import graph as G  # noqa: E402
from genesis.architecture import model as M  # noqa: E402
from genesis.architecture import policies as PO  # noqa: E402


def fixture(**kw):
    return M._fixture_ag(**kw)


class Invariants(unittest.TestCase):
    def test_a_well_formed_graph_checks(self):
        self.assertEqual(G.check(fixture()), [])
        self.assertEqual(len(G.ag_id(fixture())), 64)

    def test_type_errors_are_refused_before_running(self):
        ag = fixture()
        bad = copy.deepcopy(ag)
        bad['edges'].append(['pol', 'feat', 'senses'])            # a Family is not a Column
        self.assertTrue(any('is not Column' in p for p in G.check(bad)))
        bad = copy.deepcopy(ag)
        bad['nodes']['pol']['op'] = 'neural_net'
        self.assertTrue(any('unknown operator' in p for p in G.check(bad)))
        bad = copy.deepcopy(ag)
        bad['edges'] = [e for e in bad['edges'] if e[2] != 'scheme']
        self.assertTrue(any('exactly one input' in p for p in G.check(bad)))
        bad = copy.deepcopy(ag)
        bad['nodes']['s1']['params']['expr'] = ['mean_n', 'no_such_primitive']
        self.assertTrue(G.check(bad))
        bad = copy.deepcopy(ag)
        bad['nodes']['pol']['searched'] = ['n_cuts', 'everything']
        self.assertTrue(any('cannot be searched' in p for p in G.check(bad)))
        with self.assertRaises(ValueError):
            G.execute(bad, M.FixtureView())

    def test_a_cycle_is_refused(self):
        ag = fixture()
        ag['nodes']['f1'] = G.node('Sense', 'fuse', {'op': 'sub_s', 'scale': 1.0})
        ag['edges'] += [['f1', 'f1', 'a'], ['s1', 'f1', 'b']]
        self.assertTrue(any('cycle' in p or 'takes exactly one' in p for p in G.check(ag)))

    def test_the_kernel_is_closed(self):
        ag = fixture()
        for mutate in (lambda a: a['nodes']['out']['params'].update({'x': 1}),
                       lambda a: a['nodes']['out'].update({'kernel': False}),
                       lambda a: a.update({'edges': [e for e in a['edges'] if e[1] != 'out']}),
                       lambda a: a['nodes'].update({'judge': G.node('Output', 'reattempt', kernel=True)}),
                       lambda a: a['edges'].append(['search', 'out', 'policy'])):
            new = copy.deepcopy(ag)
            mutate(new)
            self.assertIsNotNone(G.admissible(ag, new))
            self.assertTrue(G.kernel_violations(ag, new) or G.check(new))

    def test_budget_conservation(self):
        ag = fixture()
        more = copy.deepcopy(ag)
        more['budget']['total'] += 1
        self.assertIn('budget', G.admissible(ag, more))
        less = copy.deepcopy(ag)
        less['budget']['total'] -= 1
        self.assertIsNone(G.admissible(ag, less))

    def test_determinism(self):
        a = G.execute(fixture(search='restarts'), M.FixtureView(), seed=3)
        b = G.execute(fixture(search='restarts'), M.FixtureView(), seed=3)
        self.assertEqual(a, b)
        self.assertEqual(a['id'], G.ag_id(fixture(search='restarts')))

    def test_charges_are_per_node_and_total(self):
        view = M.FixtureView()
        r = G.execute(fixture(), view)
        self.assertEqual(set(r['charges']), {'s1', 's2', 'search'})
        self.assertAlmostEqual(r['units'], sum(r['charges'].values()))
        self.assertEqual(r['charges']['search'], view.units)              # paired, one repeat: n x K draws
        self.assertEqual(view.units, view.size('dev_a') * view.K)

    def test_bounded_execution(self):
        with self.assertRaises(G.BudgetExceeded):
            G.execute(fixture(), M.FixtureView(), depth=G.MAX_NEST + 1)
        tight = fixture(evaluator='independent')
        tight['budget'] = {'total': 20.0, 'split': {'search': 0.5}}
        view = M.FixtureView()
        r = G.execute(tight, view)                                          # the search stops at its share
        self.assertLessEqual(r['charges']['search'], 10.0)
        starved = fixture()
        starved['budget'] = {'total': 1.0, 'split': {'search': 0.99}}
        with self.assertRaises(G.BudgetExceeded):                          # the senses exceed their pool
            G.execute(starved, M.FixtureView())

    def test_a_fitted_policy_applies_to_new_graphs(self):
        r = G.execute(fixture(), M.FixtureView())
        from genesis.architecture import rewrite as R
        ch = G.choose(r['policy'], R.probes()[:3])
        self.assertEqual(len(ch), 3)
        self.assertTrue(all(c in range(3) for c in ch))


class Classifier(unittest.TestCase):
    def test_classes(self):
        ag = fixture()
        self.assertEqual(G.classify(ag, copy.deepcopy(ag)), 'NONE')
        t = copy.deepcopy(ag)
        t['nodes']['ev']['params']['repeats'] = 4
        self.assertEqual(G.classify(ag, t), 'TUNING')
        t = copy.deepcopy(ag)
        t['nodes']['pol']['searched'] = ['n_cuts']
        self.assertEqual(G.classify(ag, t), 'TUNING')
        t = copy.deepcopy(ag)
        t['budget']['split'] = {'search': 0.8}
        self.assertEqual(G.classify(ag, t), 'TUNING')
        s = copy.deepcopy(ag)
        s['nodes']['search']['op'] = 'restarts'
        self.assertEqual(G.classify(ag, s), 'STRUCTURAL')
        s = copy.deepcopy(ag)
        s['nodes']['s3'] = G.node('Sense', 'expr', {'expr': ['mean_n', 'clust']})
        s['edges'].append(['s3', 'feat', 'senses'])
        self.assertEqual(G.classify(ag, s), 'STRUCTURAL')
        lib = copy.deepcopy(G.LIB)
        lib['Policy']['ensemble'] = {'in': {}, 'out': 'Family', 'params': ()}
        lang = G.make(ag['nodes'], ag['edges'], ag['budget']['total'], ag['budget']['split'], lib=lib)
        self.assertEqual(G.classify(ag, lang), 'LANGUAGE')


class Evaluation(unittest.TestCase):
    def test_paired_cancels_shared_noise_and_independent_does_not(self):
        class Noisy:
            K = 2

            def size(self, split):
                return 4

            def evaluate(self, split, i, c, r):
                return 10.0 * (r % 3) + (1.0 if c == 1 else 0.0)            # a large shared term per repeat
        m = PO.Meter()
        p = PO.Evaluation(Noisy(), 'dev_a', {'op': 'paired', 'repeats': 3}, m, 'n')
        self.assertGreater(p.value([1, 1, 1, 1]), p.value([0, 0, 0, 0]))
        self.assertEqual(p.value([1, 1, 1, 1]) - p.value([0, 0, 0, 0]), 1.0)
        q = PO.Evaluation(Noisy(), 'dev_a', {'op': 'independent', 'repeats': 1}, PO.Meter(), 'n')
        diffs = {round(q.value([1] * 4) - q.value([0] * 4), 6) for _ in range(3)}
        self.assertGreater(len(diffs), 1)                                  # the shared term does not cancel

    def test_shared_draws_save_units_never_charges(self):
        view = M.FixtureView()
        draws = {}
        a = G.execute(fixture(), view, draws=draws)
        used = view.units
        b = G.execute(fixture(), view, draws=draws)
        self.assertEqual(view.units, used)                                 # nothing drawn twice
        self.assertEqual(a['charges'], b['charges'])                       # but each execution is charged in full


if __name__ == '__main__':
    unittest.main()
