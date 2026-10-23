"""B20_R115: language v2 and the search in it (design). The new statements keep every edge set triangle-free and a
subset of the host; B20_R78's programs are still valid and mean the same; generation, mutation and crossover stay
in the language; the library extends B20_R111's with two memetic templates; the signature and novelty rule; the
registered output."""
import json
from pathlib import Path
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r115_language_v2 as M  # noqa: E402
from genesis.candidate_kinds import solver_program as KP  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.invention import solver_programs as SP  # noqa: E402
from genesis.invention import solver_programs_v2 as V2  # noqa: E402

LIC = KP.licensed_reps('triangle_free_host_v1')
REPS = {r['id']: r for r in R.proposals()}


def host(seed, n=40, p=0.3):
    rng = random.Random(seed)
    return n, [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]


def triangle_free(n, S):
    adj = [set() for _ in range(n)]
    for u, v in S:
        adj[u].add(v)
        adj[v].add(u)
    return all(not (adj[u] & adj[v]) for u, v in S)


class Language(unittest.TestCase):
    def test_v1_programs_are_v2_programs_and_run_the_same(self):
        rng = random.Random(1)
        n, E = host(1)
        for _ in range(5):
            p = SP.random_program(rng, LIC)
            self.assertEqual(V2.problems(p, LIC), [])
            self.assertEqual(SP.size(p), V2.size(p))
        self.assertEqual(V2.problems({'rep': 'cross_2', 'body': [['agree', 1]]}, LIC)[0][:13], 'bad arguments')

    def test_pool_moves_keep_edge_sets_valid(self):
        for seed in range(4):
            n, E = host(seed)
            for rec in ('agree', 'cluster'):
                p = {'rep': 'cross_2', 'body': [['init'], ['descent'], ['elite'], [rec], ['sweep', 'drop', 'sideways'],
                                                ['elite']]}
                S = V2.run(p, REPS['cross_2'], n, E, 0.2, seed)
                self.assertTrue(set(S) <= set(E) and triangle_free(n, S) and len(S) > 0, (seed, rec))

    def test_machine_pool(self):
        n, E = host(7)
        m = V2.Machine(n, E, REPS['cross_2'], random.Random(7))
        for _ in range(12):
            m.init()
            m.elite()
        self.assertLessEqual(len(m.pool), V2.POOL_K)
        self.assertEqual(len(set(m.pool)), len(m.pool))
        m.agree()
        common = frozenset.intersection(*m.pool)
        self.assertTrue(common <= m._current())
        m.cluster()
        S = [E[i] for i in m._current()]
        self.assertTrue(triangle_free(n, S))

    def test_generation_stays_in_the_language(self):
        rng = random.Random(3)
        for _ in range(100):
            p = V2.random_program(rng, LIC)
            q = V2.mutate(p, rng, LIC)
            self.assertEqual(V2.problems(q, LIC), [])
            self.assertEqual(V2.problems(V2.crossover(p, q, rng, LIC), LIC), [])


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r115_language_v2.py':
                self.assertIsNone(re.search(rf'\b{M.HOST_SEED}\b', path.read_text()), path.name)

    def test_library(self):
        self.assertEqual(list(M.LIBRARY), [f'T{i}' for i in range(1, 11)])
        self.assertEqual(sum(len(v) for v in M.LIBRARY.values()), 84)
        for vs in M.LIBRARY.values():
            for n, p in vs:
                self.assertEqual(V2.problems(p, LIC), [], n)
        self.assertEqual(len(set(M.TEMPLATE_SIGNATURES.values())), 10)

    def test_novelty_rule_covers_the_memetic_templates(self):
        textbook = {'rep': 'ordered_2', 'body': [['init'], ['descent'], ['elite'], ['cluster']]}
        self.assertEqual(M.core_label(M.signature(textbook))[0], 'KNOWN_CORE')       # reduced T10
        new = {'rep': 'cross_2', 'body': [['loop', [['relabel', 'random', 'anneal', 1000], ['elite'], ['agree']]]]}
        self.assertEqual(M.core_label(M.signature(new))[0], 'NOVEL_CORE')
        self.assertTrue(M.uses_pool(new) and not M.uses_pool(M.LIBRARY['T4'][0][1]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
