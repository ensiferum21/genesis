"""B20_R126: the self-improvement machinery. Engines are mcx2 programs: random ones, mutations (by the process's
weights) and crossovers are always valid; the search with the ORIGINAL process is exactly the feedback contract's
search; processes are data, refused outside their space, mutated and crossed validly; feedback's constants are
restored after every search."""
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


class Processes(unittest.TestCase):
    def test_processes_are_data(self):
        self.assertIsNone(SI.check_process(SI.ORIGINAL))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, pop=7)))
        self.assertIsNotNone(SI.check_process(dict(SI.ORIGINAL, tournament=6, pop=4)))
        self.assertIsNotNone(SI.check_process({k: v for k, v in SI.ORIGINAL.items() if k != 'p_cross'}))
        bad = dict(SI.ORIGINAL, weights=dict(SI.ORIGINAL['weights'], arg=3.0))
        self.assertIsNotNone(SI.check_process(bad))
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
