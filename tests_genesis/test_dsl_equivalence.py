"""The incremental interpreter must be output-identical to the frozen v1 oracle."""
from itertools import combinations
import random
import time
import unittest

from genesis.dsl import solve, motif_index
from genesis.models import GraphTask, SolverProgram
from genesis.graphs import motifs
from tests_genesis.reference.dsl_v1_reference import solve as solve_v1


def random_task(rng, domain):
    n = rng.randint(2, 9)
    p = rng.choice((0.2, 0.45, 0.7, 0.95))
    edges = tuple(e for e in combinations(range(n), 2) if rng.random() < p)
    return GraphTask(task_id='eq', domain=domain, n=n, edges=edges, family='random')


def random_program(rng):
    return SolverProgram(weights=tuple(rng.randint(-8, 8) for _ in range(4)),
                         rounds=rng.choice((1, 2, 4, 8, 32)),
                         exchange=rng.random() < 0.5, componentwise=rng.random() < 0.5)


class IncrementalInterpreterEquivalence(unittest.TestCase):
    def test_random_hosts_programs_seeds_and_budgets(self):
        rng = random.Random(20261010)
        checked = 0
        for _ in range(600):
            domain = rng.choice(('c4_host_v2', 'triangle_free_host_v1'))
            task = random_task(rng, domain)
            program = random_program(rng)
            budget = rng.choice((1, 3, 7, 20, 60, 500, 5000))
            seed = rng.randrange(1 << 30)
            self.assertEqual(solve(task, program, budget, seed), solve_v1(task, program, budget, seed),
                             (task, program, budget, seed))
            checked += 1
        self.assertEqual(checked, 600)

    def test_complete_hosts(self):
        for domain in ('c4_host_v2', 'triangle_free_host_v1'):
            for n in range(1, 9):
                task = GraphTask(task_id=f'K{n}', domain=domain, n=n,
                                 edges=tuple(combinations(range(n), 2)), family='complete')
                for program in (SolverProgram(rounds=4), SolverProgram(rounds=4, exchange=True),
                                SolverProgram(weights=(0, 0, 0, 1), rounds=4, exchange=True)):
                    for seed in range(3):
                        self.assertEqual(solve(task, program, 5000, seed), solve_v1(task, program, 5000, seed))

    def test_index_partitions_every_motif_by_its_edges(self):
        task = GraphTask(task_id='K6', n=6, edges=tuple(combinations(range(6), 2)), family='complete')
        cycles, by_edge = motif_index(task)
        self.assertEqual(cycles, motifs(task))
        for i, bucket in enumerate(by_edge):
            self.assertEqual(sorted(bucket), sorted(c for c in cycles if c >> i & 1))
        # Each C4 has four edges, so it appears in exactly four buckets.
        self.assertEqual(sum(len(b) for b in by_edge), 4 * len(cycles))

    def test_larger_complete_host_is_now_tractable(self):
        task = GraphTask(task_id='K24', n=24, edges=tuple(combinations(range(24), 2)), family='complete')
        start = time.process_time()
        result = solve(task, SolverProgram(rounds=4), 100000, 0)
        self.assertLess(time.process_time() - start, 30)
        self.assertGreater(result['value'], 0)


if __name__ == '__main__':
    unittest.main()
