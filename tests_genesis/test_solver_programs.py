"""B20_R78: the solver language, its interpreter, the `solver-program-v1` kind and the program search. The grammar
refuses what is outside it; every program's result is triangle-free; moves and undo behave; random programs, mutants
and crossovers stay in the language; the search starts from random programs only and returns a valid one; the kind
is registered, bound to its files, closed, and runs in the sandbox with a checked witness."""
from itertools import combinations
import json
import random
import time
import unittest

from genesis import candidates_v2 as C2
from genesis.candidate_kinds import kinds as K
from genesis.candidate_kinds import represent_search as RS
from genesis.candidate_kinds import solver_program as KP
from genesis.graphs import check_witness
from genesis.invention import representations as R
from genesis.invention import solver_programs as SP
from genesis.invention import solver_search as SS
from genesis.models import CandidateGraph, GraphTask

TF = 'triangle_free_host_v1'
KIND = 'solver-program-v1'
PROFILE = {'cpu_seconds': 2, 'memory_mib': 2048, 'wall_seconds': 10, 'queries': 1000}
REP = {r['id']: r for r in R.proposals()}
REPS = KP.licensed_reps(TF)
# Hand-written programs: only to show what the language can express. None is given to the search.
ENGINE_B18 = {'rep': 'cross_2', 'body': [['init'], ['descent']]}
SWAP_ILS = {'rep': 'cross_2', 'body': [['split', 0.75, [['loop', [['init'], ['descent']]]],
                                        [['best'], ['loop', [['edges', 'force', 'always', 1],
                                                             ['sweep', 'drop', 'improve']]]]]]}


def task(n, edges, tid='t'):
    return GraphTask(task_id=tid, domain=TF, n=n, edges=tuple(sorted(edges)), family='fixture', split='DEV')


def random_host(rng, n, m):
    return sorted({tuple(sorted(rng.sample(range(n), 2))) for _ in range(m)})


class Grammar(unittest.TestCase):
    def test_licensed_representations_are_b18_s(self):
        self.assertEqual(REPS, {r['id'] for r in R.proposals() if RS.licensed(r['id'], TF) in ('SUFF', 'EQ')})
        self.assertEqual(REPS, {'cross_2', 'ordered_2', 'adjacent_2', 'adjacent_3'})

    def test_valid_programs(self):
        for p in (ENGINE_B18, SWAP_ILS, {'rep': 'adjacent_3', 'body': [['relabel', 'best', 'anneal', 10]]},
                  {'rep': 'ordered_2', 'body': [['repeat', 3, [['edges', 'drop', 'sideways', 100]]], ['best']]}):
            self.assertEqual(SP.problems(p, REPS), [], p)

    def test_refusals(self):
        bad = [
            {'rep': 'cross_3', 'body': [['init']]},                                  # not licensed
            {'rep': 'cross_2', 'body': []},                                          # empty block
            {'rep': 'cross_2', 'body': [['init']] * 7},                              # block too long
            {'rep': 'cross_2', 'body': [['exec', 'print(1)']]},                      # unknown statement
            {'rep': 'cross_2', 'body': [['edges', 'drop', 'improve', 5]]},           # N not in the set
            {'rep': 'cross_2', 'body': [['edges', 'drop', 'improve', True]]},        # a bool is not an N
            {'rep': 'cross_2', 'body': [['repeat', 3.0, [['init']]]]},               # stall must be an int
            {'rep': 'cross_2', 'body': [['split', 1, [['init']], [['init']]]]},      # frac must be a listed float
            {'rep': 'cross_2', 'body': [['loop', [['loop', [['loop', [['loop', [['init']]]]]]]]]]},  # too deep
            {'rep': 'cross_2', 'body': [['init']], 'code': 'x'},                     # extra field
            ['init'],
        ]
        for p in bad:
            self.assertNotEqual(SP.problems(p, REPS), [], p)
        big = {'rep': 'cross_2', 'body': [['loop', [['loop', [['init']] * 6]] * 6]]}
        self.assertIn(f'more than {SP.MAX_NODES} statements', SP.problems(big, REPS))

    def test_generation_mutation_and_crossover_stay_in_the_language(self):
        rng = random.Random(3)
        progs = [SP.random_program(rng, REPS) for _ in range(3000)]       # 1 in ~300 drafts exceeds MAX_NODES
        for p in progs:
            self.assertEqual(SP.problems(p, REPS), [], p)
        self.assertGreater(max(SP.size(p) for p in progs), 20)             # large programs are still drawn
        for i in range(600):
            a, b = rng.choice(progs), rng.choice(progs)
            for child in (SP.mutate(a, rng, REPS), SP.crossover(a, b, rng, REPS)):
                self.assertEqual(SP.problems(child, REPS), [], child)


class Interpreter(unittest.TestCase):
    def test_every_result_is_triangle_free_and_the_budget_holds(self):
        rng = random.Random(8)
        for i in range(40):
            n = rng.randint(6, 24)
            E = random_host(rng, n, rng.randint(n, 4 * n))
            p = SP.random_program(rng, REPS)
            t0 = time.process_time()
            best = SP.run(p, REP[p['rep']], n, E, 0.05, i)
            self.assertLess(time.process_time() - t0, 0.05 + 0.25, p)
            self.assertEqual(check_witness(task(n, E), best)['value'], len(best), p)

    def test_known_optima(self):
        k10 = list(combinations(range(10), 2))
        c5 = [(0, 1), (0, 4), (1, 2), (2, 3), (3, 4)]
        for p in (ENGINE_B18, SWAP_ILS):
            self.assertEqual(len(SP.run(p, REP['cross_2'], 10, k10, 0.2, 1)), 25)
            self.assertEqual(len(SP.run(p, REP['cross_2'], 5, c5, 0.05, 1)), 5)

    def test_drop_with_improve_is_a_one_two_swap_and_undo_restores(self):
        E = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3)]                # K4 minus {2, 3}
        m = SP.Machine(4, E, REP['cross_2'], random.Random(0))
        m._set_edges([(0, 1), (1, 2), (0, 3)])                       # maximal, 3 edges; the optimum has 4
        m.sweep('drop', 'improve', float('inf'), lambda: 1.0)
        self.assertEqual(sorted(m.best or [E[i] for i in range(5) if m.inS[i]]), [(0, 2), (0, 3), (1, 2), (1, 3)])
        m._set_edges([(0, 1), (1, 2), (0, 3)])
        before = (list(m.N), bytes(m.inS), m.size)
        m.log = []
        m._move('force', m.eid[(0, 2)])
        m._undo()
        self.assertEqual((list(m.N), bytes(m.inS), m.size), before)

    def test_force_keeps_the_set_triangle_free(self):
        rng = random.Random(5)
        E = random_host(rng, 18, 80)
        m = SP.Machine(18, E, REP['cross_2'], random.Random(2))
        m.init()
        for _ in range(300):
            m.edges('force', 'always', 1, float('inf'), lambda: 1.0)
            m.sweep('drop', 'sideways', float('inf'), lambda: 1.0)
            cur = [E[i] for i in range(len(E)) if m.inS[i]]
            self.assertEqual(check_witness(task(18, E), cur)['value'], m.size)


class Search(unittest.TestCase):
    def test_the_search_starts_from_random_programs_and_returns_a_valid_one(self):
        from unittest import mock
        rng = random.Random(4)
        hosts = [task(14, random_host(rng, 14, 45), f'h{i}') for i in range(3)]
        made = []
        real = SP.random_program

        def spy(r, reps):
            p = real(r, reps)
            made.append(json.dumps(p, sort_keys=True))
            return p
        hist = []
        with mock.patch.object(SS, 'BUDGET', 0.02), mock.patch.object(SS, 'FINAL_BUDGETS', (0.02,)), \
                mock.patch.object(SP, 'random_program', spy):
            best, rep = SS.search(hosts, REPS, REP, 3.0, 1, log=lambda m: None, history=hist)
        self.assertEqual(SP.problems(best, REPS), [])
        first = [json.dumps(h['program'], sort_keys=True) for h in hist[:SS.POP]]
        self.assertTrue(set(first) <= set(made))                    # the initial population is random programs
        self.assertNotIn(json.dumps(SWAP_ILS, sort_keys=True), first)
        self.assertGreaterEqual(rep['evaluations'], SS.POP)
        self.assertEqual(len(rep['finalists']), min(SS.FINALISTS, len(rep['population'])))
        a = SS.anatomy(SWAP_ILS)
        self.assertTrue(a['swap_like'] and a['kick'] and a['cut_search'] and a['phases'])
        self.assertFalse(SS.anatomy(ENGINE_B18)['swap_like'])


class Kind(unittest.TestCase):
    def test_registered_bound_and_closed(self):
        self.assertIn(KIND, C2.KINDS)
        ident = C2.implementation_identity(KIND)
        self.assertEqual(list(ident)[3], 'candidate_kinds/solver_program.py')
        self.assertIn('invention/solver_programs.py', ident)
        self.assertNotIn('candidate_kinds/kinds.py', ident)
        for other in K.KINDS:
            if other not in (KIND, 'solver-library-v1'):          # B20_R82's library kind builds on this language
                self.assertNotIn('invention/solver_programs.py', C2.implementation_identity(other), other)
        self.assertIsNone(KP.check_parameters(TF, {'program': SWAP_ILS, 'cpu_seconds': 0.5}))
        for bad in ({'program': SWAP_ILS}, {'program': SWAP_ILS, 'cpu_seconds': 0},
                    {'program': {'rep': 'cross_3', 'body': [['init']]}, 'cpu_seconds': 1},
                    {'program': {'rep': 'cross_2', 'body': [['exec']]}, 'cpu_seconds': 1},
                    {'program': SWAP_ILS, 'cpu_seconds': 1, 'seed': 3}):
            self.assertIsNotNone(KP.check_parameters(TF, bad), bad)
        self.assertIsNotNone(KP.check_parameters('c4_host_v2', {'program': SWAP_ILS, 'cpu_seconds': 1}))

    def test_runs_in_the_sandbox_with_a_checked_witness(self):
        from genesis.domains import ADAPTERS
        t = ADAPTERS[TF].generate(20267801, 1, 'DEV', 'planted_cluster', {'n': 30, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        d = C2.build_descriptor(KIND, TF, {'program': SWAP_ILS, 'cpu_seconds': 0.5}, **PROFILE)
        r = C2.run(t, d, seed=3, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(check_witness(t, [tuple(e) for e in r['result']['selected']])['value'], r['result']['value'])
        self.assertGreaterEqual(r['cpu_ns'], int(0.5e9))
        out = KP.solve(CandidateGraph(domain=TF, n=t.n, edges=t.edges), {'program': ENGINE_B18, 'cpu_seconds': 0.1}, 2, 1)
        self.assertEqual(check_witness(t, [tuple(e) for e in out['selected']])['value'], out['value'])


if __name__ == '__main__':
    unittest.main()
