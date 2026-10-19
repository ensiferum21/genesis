"""B20_R82: solver programs with a library of earlier generations' programs, the library search and the
`solver-library-v1` kind. The grammar (macros only to earlier entries, no cycles), the interpreter (macros run their
body, also inside control statements), generation and mutation stay in the language, an empty library is B20_R78's
language exactly, the search returns a valid program with the same library, and the kind runs in the sandbox."""
from itertools import combinations
import json
import random
import unittest
from unittest import mock

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import kinds as K
from genesis.candidate_kinds import solver_library_program as KL
from genesis.candidate_kinds import solver_program as KP
from genesis.graphs import check_witness
from genesis.invention import library_search as LS
from genesis.invention import representations as R
from genesis.invention import solver_library as SL
from genesis.invention import solver_programs as SP
from genesis.invention import solver_search as SS
from genesis.models import GraphTask

TF = 'triangle_free_host_v1'
KIND = 'solver-library-v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
REP = {r['id']: r for r in R.proposals()}
REPS = KP.licensed_reps(TF)
LIB = [[['init'], ['descent']], [['macro', 0], ['sweep', 'drop', 'improve']]]


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


class Grammar(unittest.TestCase):
    def test_valid(self):
        for p in ({'rep': 'cross_2', 'body': [['macro', 1]], 'library': LIB},
                  {'rep': 'cross_2', 'body': [['loop', [['macro', 0], ['edges', 'force', 'always', 1]]]], 'library': LIB},
                  {'rep': 'adjacent_3', 'body': [['init'], ['descent']], 'library': []}):
            self.assertEqual(SL.problems(p, REPS), [], p)

    def test_refusals(self):
        bad = [{'rep': 'cross_2', 'body': [['macro', 2]], 'library': LIB},            # no entry 2
               {'rep': 'cross_2', 'body': [['macro', 0]], 'library': [[['macro', 0]]]},  # an entry calling itself
               {'rep': 'cross_2', 'body': [['init']], 'library': [[['macro', 1]], [['init']]]},  # calling a later one
               {'rep': 'cross_2', 'body': [['macro', True]], 'library': LIB},
               {'rep': 'cross_2', 'body': [['macro', 0]]},                             # no library field
               {'rep': 'cross_3', 'body': [['macro', 0]], 'library': LIB},             # unlicensed representation
               {'rep': 'cross_2', 'body': [['edges', 'drop', 'improve', 7]], 'library': []},
               {'rep': 'cross_2', 'body': [['loop', [['loop', [['loop', [['loop', [['macro', 0]]]]]]]]]], 'library': LIB},
               {'rep': 'cross_2', 'body': [['init']], 'library': [[['init']]] * 9}]
        for p in bad:
            self.assertNotEqual(SL.problems(p, REPS), [], p)

    def test_an_empty_library_is_b20r78_s_language(self):
        rng = random.Random(6)
        for _ in range(300):
            p = SP.random_program(rng, REPS)
            self.assertEqual(SL.problems(dict(p, library=[]), REPS), [], p)
            self.assertEqual(SL.size(dict(p, library=[])), SP.size(p))
        broken = {'rep': 'cross_2', 'body': [['sweep', 'drop', 'improve', 3]]}
        self.assertNotEqual(SP.problems(broken, REPS), [])
        self.assertNotEqual(SL.problems(dict(broken, library=[]), REPS), [])
        p = SL.random_program(rng, REPS, [])
        self.assertFalse(any(s[0] == 'macro' for b, _ in SL._blocks(p) for s in b))

    def test_generation_mutation_crossover_stay_in_the_language(self):
        rng = random.Random(9)
        progs = [SL.random_program(rng, REPS, LIB) for _ in range(200)]
        self.assertTrue(any(s[0] == 'macro' for p in progs for b, _ in SL._blocks(p) for s in b))
        for p in progs:
            self.assertEqual(SL.problems(p, REPS), [], p)
        for _ in range(400):
            a, b = rng.choice(progs), rng.choice(progs)
            for child in (SL.mutate(a, rng, REPS), SL.crossover(a, b, rng, REPS)):
                self.assertEqual(SL.problems(child, REPS), [], child)
                self.assertEqual(child['library'], LIB)


class Interpreter(unittest.TestCase):
    def test_macros_run_their_bodies_also_inside_control(self):
        calls = []
        real = SP.Machine.descent

        def spy(self, deadline):
            calls.append(1)
            return real(self, deadline)
        k10 = list(combinations(range(10), 2))
        with mock.patch.object(SP.Machine, 'descent', spy):
            for body in ([['macro', 0]], [['split', 0.5, [['loop', [['macro', 1]]]], [['best']]]]):
                calls.clear()
                best = SL.run({'rep': 'cross_2', 'body': body, 'library': LIB}, REP['cross_2'], 10, k10, 0.1, 1)
                self.assertGreater(len(calls), 0, body)
                self.assertEqual(len(best), 25)

    def test_results_are_triangle_free(self):
        rng = random.Random(3)
        for i in range(30):
            n = rng.randint(6, 20)
            E = sorted({tuple(sorted(rng.sample(range(n), 2))) for _ in range(rng.randint(n, 3 * n))})
            p = SL.random_program(rng, REPS, LIB)
            best = SL.run(p, REP[p['rep']], n, E, 0.04, i)
            self.assertEqual(check_witness(task(n, E), best)['value'], len(best), p)


class Search(unittest.TestCase):
    def test_returns_a_valid_program_with_the_same_library(self):
        rng = random.Random(1)
        hosts = [task(14, sorted({tuple(sorted(rng.sample(range(14), 2))) for _ in range(45)}), f'h{i}')
                 for i in range(2)]
        for lib in (LIB, []):
            with mock.patch.object(SS, 'BUDGET', 0.02), mock.patch.object(SS, 'FINAL_BUDGETS', (0.02,)):
                best, rep = LS.search(hosts, REPS, REP, lib, 2.0, 5, log=lambda m: None)
            self.assertEqual(SL.problems(best, REPS), [])
            self.assertEqual(best['library'], lib)
            self.assertGreaterEqual(rep['evaluations'], SS.POP)
            if not lib:
                self.assertEqual(rep['macro_use_in_final_population'], 0)

    def test_library_entry(self):
        p = {'rep': 'ordered_2', 'body': [['init'], ['descent']]}
        self.assertEqual(SL.as_library_entry(p), [['init'], ['descent']])


class Kind(unittest.TestCase):
    def test_registered_bound_closed_and_sandboxed(self):
        from genesis.domains import ADAPTERS
        self.assertIn(KIND, C2.KINDS)
        ident = C2.implementation_identity(KIND)
        self.assertEqual(list(ident)[3], 'candidate_kinds/solver_library_program.py')
        self.assertIn('invention/solver_library.py', ident)
        for other in K.KINDS:
            if other != KIND:
                self.assertNotIn('invention/solver_library.py', C2.implementation_identity(other), other)
        prog = {'rep': 'cross_2', 'body': [['loop', [['macro', 1]]]], 'library': LIB}
        self.assertIsNone(KL.check_parameters(TF, {'program': prog, 'cpu_seconds': 0.5}))
        self.assertIsNotNone(KL.check_parameters(TF, {'program': dict(prog, body=[['macro', 5]]), 'cpu_seconds': 0.5}))
        self.assertIsNotNone(KL.check_parameters(TF, {'program': prog, 'cpu_seconds': 0.5, 'x': 1}))
        t = ADAPTERS[TF].generate(20268201, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor(KIND, TF, {'program': prog, 'cpu_seconds': 0.5}, **PROFILE)
        r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])


if __name__ == '__main__':
    unittest.main()
