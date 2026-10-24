"""B20_R126: the self-improvement machinery. Engines are mcx2 programs: random ones, mutations (by the process's
weights) and crossovers are always valid; the search with the ORIGINAL process is exactly the feedback contract's
search; processes are data, refused outside their space, mutated and crossed validly; feedback's constants are
restored after every search; the MAP-Elites algorithm, the calibration effort and seeded starts (the amendment).
"""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import feedback as FB  # noqa: E402
from genesis.autonomy import selfimprove as SI  # noqa: E402
from genesis.candidate_kinds import mcx2 as K  # noqa: E402


def toy_evaluate(cfg, split):
    """A cheap stand-in for running engines: more I statements and more levels score higher, plus split noise."""
    r = random.Random(SI.key(cfg) + split)
    st = K.statements(cfg['prog'])
    return sum(op == 'I' for op, _ in st) * 0.1 + cfg['levels'] * 0.05 + r.gauss(0, 0.02)


class Engines(unittest.TestCase):
    def test_random_mutate_crossover_are_valid(self):
        rng = random.Random(1)
        cfgs = [SI.random_engine(rng) for _ in range(200)]
        self.assertTrue(all(K.check_config(c) is None for c in cfgs))
        self.assertGreater(len({SI.key(c) for c in cfgs}), 190)
        for c in cfgs[:100]:
            m = SI.mutate(c, rng)
            self.assertIsNone(K.check_config(m))
            self.assertNotEqual(m, c)
            x = SI.crossover(c, cfgs[-1], rng)
            self.assertIsNone(K.check_config(x))
        self.assertIsNone(K.check_config(SI.mutate(K.DEFAULT, rng)))

    def test_weights_choose_the_mutation(self):
        rng = random.Random(2)
        only_option = {m: (1.0 if m == 'option' else 0.0) for m in SI.MUTATIONS}
        for _ in range(30):
            m = SI.mutate(K.DEFAULT, rng, only_option)
            self.assertEqual(m['prog'], K.DEFAULT['prog'])
            self.assertEqual(sum(m[k] != K.DEFAULT[k] for k in K.SPACE), 1)
        only_delete = {m: (1.0 if m == 'delete' else 0.0) for m in SI.MUTATIONS}
        m = SI.mutate(K.DEFAULT, rng, only_delete)
        self.assertEqual(SI.size(m), SI.size(K.DEFAULT) - 1)


class Search(unittest.TestCase):
    def test_original_process_is_the_contract_search(self):
        ops = SI.engine_ops()
        a = SI.search(SI.ORIGINAL, ops, toy_evaluate, 200, 7)
        b = FB.steady_state_search(ops, toy_evaluate, 200, 7, contract=True, calibrate='BC')
        self.assertEqual(SI.key(a), SI.key(b))
        self.assertEqual((FB.POP, FB.CHILDREN, FB.LEADERS, FB.TOURNAMENT, FB.P_CROSS), (16, 8, 2, 3, 0.25))

    def test_another_process_changes_the_search_and_constants_are_restored(self):
        ops = SI.engine_ops()
        proc = dict(SI.ORIGINAL, pop=8, children=4, tournament=2)
        a = SI.search(proc, ops, toy_evaluate, 200, 7)
        b = SI.search(SI.ORIGINAL, ops, toy_evaluate, 200, 7)
        self.assertNotEqual(SI.key(a), SI.key(b))
        self.assertEqual((FB.POP, FB.CHILDREN, FB.TOURNAMENT), (16, 8, 3))
        with self.assertRaises(ValueError):
            SI.search(dict(SI.ORIGINAL, pop=5), ops, toy_evaluate, 50, 1)
        self.assertEqual(FB.POP, 16)


class Amendment(unittest.TestCase):
    def test_map_elites_under_the_contract(self):
        proc = dict(SI.ORIGINAL, algorithm='map-elites', calib_extra=4, pop=8)
        eng, rep = SI.search(proc, SI.engine_ops(), toy_evaluate, 150, 3)
        self.assertIsNone(K.check_config(eng))
        self.assertGreater(rep['cells'], 3)
        self.assertLessEqual(rep['evaluations'], 150)
        self.assertIn('releases', rep['judge'])
        again, _ = SI.search(proc, SI.engine_ops(), toy_evaluate, 150, 3)
        self.assertEqual(SI.key(eng), SI.key(again))                    # deterministic given the seed

    def test_descriptor(self):
        self.assertEqual(SI.descriptor(K.DEFAULT), (2, True, True, True, False, False))
        self.assertEqual(SI.descriptor(dict(K.DEFAULT, prog='b1 S10 M R', levels=1)), (0, False, False, False, True, True))

    def test_calibration_effort_is_charged(self):
        small = SI.search(dict(SI.ORIGINAL, calib_extra=4), SI.engine_ops(), toy_evaluate, 120, 5)[1]
        big = SI.search(SI.ORIGINAL, SI.engine_ops(), toy_evaluate, 120, 5)[1]
        self.assertGreater(small['generations'], big['generations'])    # fewer calibration runs, more search
        self.assertEqual(FB.CALIBRATION_EXTRA, 16)

    def test_seeded_start(self):
        rng = random.Random(4)
        seeds = [K.DEFAULT, SI.random_engine(rng)]
        ops = SI.seeded_ops(SI.engine_ops(), seeds)
        self.assertEqual([ops['random'](rng) for _ in range(2)], seeds)
        self.assertIsNone(K.check_config(ops['random'](rng)))
        eng, rep = SI.search(SI.ORIGINAL, SI.seeded_ops(SI.engine_ops(), [K.DEFAULT]), toy_evaluate, 120, 6)
        self.assertIsNone(K.check_config(eng))


class LearningFromFailure(unittest.TestCase):
    def test_macros_are_the_recurring_runs(self):
        engines = [dict(K.DEFAULT, prog='B100 X I S2000 C'), dict(K.DEFAULT, prog='b5 X I M'),
                   dict(K.DEFAULT, prog='B7 X I'), dict(K.DEFAULT, prog='R B1')]
        lib = SI.learn_macros(engines, k=3)
        self.assertEqual(lib[0], [('X', None), ('I', None)])
        self.assertTrue(all(len(m) >= 2 for m in lib))
        self.assertEqual(SI.learn_macros([dict(K.DEFAULT, prog='B1')]), [])

    def test_macro_mutation_inserts_a_learned_block(self):
        rng = random.Random(9)
        lib = [[('X', None), ('I', None), ('C', None)]]
        only = {m: 0.0 for m in SI.MUTATIONS}
        used = []
        c = SI.mutate(dict(K.DEFAULT, prog='b1'), rng, dict(only, macro=1.0), lib, used)
        self.assertEqual(used, ['macro'])
        self.assertIn('X I C', c['prog'])
        self.assertIsNone(K.check_config(c))

    def test_adaptive_selection_learns_from_failure(self):
        ad = SI.Adaptive(SI.ORIGINAL['weights'])

        def evaluate(cfg, split):                # shorter is better: deleting never fails, inserting always does
            return -SI.size(cfg)
        ev = ad.evaluate(evaluate)
        rng = random.Random(1)
        ops = ad.ops()
        p = dict(K.DEFAULT, prog='B1 X I C M H R')
        ev(p, 'A')
        for _ in range(200):
            c = ops['mutate'](p, rng)
            ev(c, 'A')
        w = ad.weights()
        self.assertGreater(w['delete'], w['insert'])        # deleting shortens: never worse here
        self.assertGreater(w['delete'], w['duplicate'])
        self.assertEqual(sum(a for _, a in ad.stats.values()), 200)

    def test_adapt_runs_under_the_contract(self):
        eng, rep = SI.search(dict(SI.ORIGINAL, adapt=True, calib_extra=4), SI.engine_ops(), toy_evaluate, 150, 8)
        self.assertIsNone(K.check_config(eng))
        lib = SI.learn_macros([K.DEFAULT, dict(K.DEFAULT, prog='b2 X I')])
        eng, rep = SI.search(dict(SI.ORIGINAL, adapt=True, algorithm='map-elites', calib_extra=4),
                             SI.engine_ops(library=lib), toy_evaluate, 150, 8)
        self.assertIsNone(K.check_config(eng))


class Processes(unittest.TestCase):
    def test_processes_are_data(self):
        self.assertIsNone(SI.check_process(SI.ORIGINAL))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, pop=7)))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, tournament=6, pop=4)))
        self.assertIsNotNone(SI.check_process({k: v for k, v in SI.ORIGINAL.items() if k != 'p_cross'}))
        bad = dict(SI.ORIGINAL, weights=dict(SI.ORIGINAL['weights'], arg=3.0))
        self.assertIsNotNone(SI.check_process(bad))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, algorithm='annealing')))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, calib_extra=0)))
        self.assertEqual((SI.ORIGINAL['algorithm'], SI.ORIGINAL['calib_extra'], SI.ORIGINAL['adapt']),
                         ('steady', 16, False))
        rng = random.Random(3)
        for _ in range(100):
            p = SI.random_process(rng)
            self.assertIsNone(SI.check_process(p))
            q = SI.mutate_process(p, rng)
            self.assertIsNone(SI.check_process(q))
            self.assertNotEqual(q, p)
            self.assertIsNone(SI.check_process(SI.crossover_process(p, SI.ORIGINAL, rng)))


if __name__ == '__main__':
    unittest.main()
