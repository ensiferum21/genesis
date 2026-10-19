"""B20_R71: `represent-search-v1`, the system's representation-and-repair engine with a closed choice of move rule
(the frozen engine's descent, tau-extremal optimization or simulated annealing). Licensing, closed parameters, faithfulness of the
descent rule to the frozen engine's semantics, the repair, and a metered runc run."""
from itertools import combinations
import random
import unittest

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import represent_search as RS
from genesis.graphs import check_witness
from genesis.invention import representations as R
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
SOUND = ('cross_2', 'adjacent_2', 'adjacent_3', 'ordered_2')


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Parameters(unittest.TestCase):
    def test_only_licensed_representations_and_closed_fields(self):
        for rep in SOUND:
            for move in RS.MOVES:
                self.assertIsNone(RS.check_parameters(TF, {'representation': rep, 'move': move, 'cpu_seconds': 0.5}))
        for rep in ('cross_3', 'inside_2', 'ordered_3', 'nonexistent'):           # unsound or unknown on TF
            self.assertIsNotNone(RS.check_parameters(TF, {'representation': rep, 'move': 'eo', 'cpu_seconds': 0.5}))
        for bad in ({'representation': 'cross_2', 'move': 'tabu', 'cpu_seconds': 0.5},
                    {'representation': 'cross_2', 'move': 'eo', 'cpu_seconds': 0},
                    {'representation': 'cross_2', 'move': 'eo', 'cpu_seconds': True},
                    {'representation': 'cross_2', 'move': 'eo'},
                    {'representation': 'cross_2', 'move': 'eo', 'cpu_seconds': 0.5, 'seed': 1}):
            self.assertIsNotNone(RS.check_parameters(TF, bad), bad)
        self.assertIsNotNone(RS.check_parameters('c4_host_v2', {'representation': 'cross_2', 'move': 'eo',
                                                                 'cpu_seconds': 0.5}))

    def test_identity_includes_the_representation_engine(self):
        ident = C2.implementation_identity('represent-search-v1')
        for f in RS.FILES:
            self.assertIn(f, ident)


class Semantics(unittest.TestCase):
    def test_kept_counts_match_the_frozen_decoder(self):
        rng = random.Random(4)
        E = sorted({tuple(sorted(rng.sample(range(12), 2))) for _ in range(40)})
        for rep in R.proposals():
            c = [rng.randrange(rep['k']) for _ in range(12)]
            inc = RS._graph(12, E, rep['_py'])
            mine = sum(RS._keeps(rep['_py'], c, v, w, low) for v in range(12) for w, low in inc[v]) // 2
            self.assertEqual(mine, len(R.decode(rep, dict(enumerate(c)), E)), rep['id'])

    def test_descent_ends_at_a_local_optimum(self):
        rng = random.Random(9)
        E = sorted({tuple(sorted(rng.sample(range(20), 2))) for _ in range(90)})
        rep = next(r for r in R.proposals() if r['id'] == 'adjacent_3')
        inc = RS._graph(20, E, rep['_py'])
        c = RS._descent(20, 3, rep['_py'], inc, random.Random(1), float('inf'))
        for v in range(20):
            cur = sum(RS._keeps(rep['_py'], c, v, w, low) for w, low in inc[v])
            for alt in range(3):
                d = c[:]
                d[v] = alt
                self.assertLessEqual(sum(RS._keeps(rep['_py'], d, v, w, low) for w, low in inc[v]), cur)

    def test_known_optima_and_valid_witnesses(self):
        k10 = list(combinations(range(10), 2))
        for rep in SOUND:
            for move in RS.MOVES:
                out = RS.solve(CandidateGraph(domain=TF, n=10, edges=tuple(k10)),
                               {'representation': rep, 'move': move, 'cpu_seconds': 0.15}, 2, 5)
                self.assertEqual(out['value'], 25, (rep, move))
                self.assertEqual(check_witness(task(10, k10), [tuple(e) for e in out['selected']])['value'], 25)


class Sandbox(unittest.TestCase):
    def test_runs_in_the_sandbox_with_checked_witnesses(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20267101, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        for move in RS.MOVES:
            d = C2.build_descriptor('represent-search-v1', TF, {'representation': 'cross_2', 'move': move,
                                                                'cpu_seconds': 0.5}, **PROFILE)
            r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
            self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), (move, r))
            self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])


if __name__ == '__main__':
    unittest.main()
