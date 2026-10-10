"""SAT/DRAT certificates: encoding correctness, agreement with exact solvers, and tamper resistance."""
from itertools import combinations
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

from genesis.graphs import certified_optimum, check_witness, motifs
from genesis.models import GraphTask
from genesis.verification import sat
from genesis.verification.tools import available, tool, ToolUnavailable

READY = available('cadical') and available('drat-trim')


def random_task(rng, n, p, domain):
    edges = tuple(e for e in combinations(range(n), 2) if rng.random() < p)
    return GraphTask(task_id='t', domain=domain, n=n, edges=edges, family='random')


def brute_force_max(task):
    cycles = motifs(task); m = len(task.edges); best = 0
    for mask in range(1 << m):
        if mask.bit_count() > best and not any(mask & c == c for c in cycles):
            best = mask.bit_count()
    return best


@unittest.skipUnless(READY, 'pinned CaDiCaL/drat-trim not installed')
class Encoding(unittest.TestCase):
    def test_cnf_satisfiable_exactly_when_a_large_enough_valid_subgraph_exists(self):
        rng = random.Random(11)
        checked = 0
        for _ in range(40):
            domain = rng.choice(('c4_host_v2', 'triangle_free_host_v1'))
            task = random_task(rng, rng.randint(4, 7), rng.choice((0.4, 0.6, 0.8)), domain)
            if not 1 <= len(task.edges) <= 13:
                continue
            best = brute_force_max(task)
            for k in range(1, len(task.edges) + 1):
                status = sat.solve(sat.encode(task, k), seconds=20)['status']
                self.assertEqual(status, 'SAT' if k <= best else 'UNSAT', (task, k, best))
                checked += 1
        self.assertGreater(checked, 100)

    def test_models_decode_to_valid_witnesses(self):
        task = random_task(random.Random(3), 9, 0.6, 'c4_host_v2')
        record = sat.solve(sat.encode(task, 5), seconds=20)
        self.assertEqual(record['status'], 'SAT')
        self.assertGreaterEqual(check_witness(task, sat.witness_from_model(task, record['model']))['value'], 5)


@unittest.skipUnless(READY, 'pinned CaDiCaL/drat-trim not installed')
class AgreementWithExactSolvers(unittest.TestCase):
    def test_certified_optimum_matches_dual_exhaustive_solvers(self):
        rng = random.Random(20261010)
        for i in range(30):
            domain = ('c4_host_v2', 'triangle_free_host_v1')[i % 2]
            task = random_task(rng, rng.randint(5, 9), rng.choice((0.35, 0.5, 0.65)), domain)
            if not 3 <= len(task.edges) <= 22:
                continue
            exact = certified_optimum(task)['value']
            bounds = sat.certified_bounds(task, seconds=60)
            self.assertEqual(bounds['status'], 'OPTIMALITY_CHECKED', bounds)
            self.assertEqual((bounds['lower'], bounds['upper']), (exact, exact), task)

    def test_beyond_exhaustive_range(self):
        rng = random.Random(5)
        task = random_task(rng, 16, 0.35, 'c4_host_v2')
        self.assertGreater(len(task.edges), 24)
        bounds = sat.certified_bounds(task, seconds=120)
        self.assertEqual(bounds['status'], 'OPTIMALITY_CHECKED')
        self.assertEqual(check_witness(task, bounds['witness'])['value'], bounds['upper'])


@unittest.skipUnless(READY, 'pinned CaDiCaL/drat-trim not installed')
class Tampering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = random.Random(9)
        cls.task = random_task(rng, 12, 0.45, 'c4_host_v2')
        bounds = sat.certified_bounds(cls.task, seconds=120)
        assert bounds['status'] == 'OPTIMALITY_CHECKED' and bounds['upper_certificate']['method'] == 'SAT_DRAT'
        cls.cert, cls.proof = bounds['upper_certificate'], bounds['proof']

    def test_replay_of_the_genuine_certificate_is_valid(self):
        self.assertEqual(sat.verify_upper_certificate(self.task, self.cert, self.proof), 'VALID')

    def test_corrupted_or_truncated_proof_is_not_valid(self):
        lines = self.proof.decode().splitlines()
        self.assertGreater(len(lines), 2)
        truncated = ('\n'.join(lines[: len(lines) // 3]) + '\n').encode()
        cnf = sat.encode(self.task, self.cert['upper'] + 1)
        self.assertNotEqual(sat.check_proof(cnf, truncated)[0], 'VALID')
        # Also rejected at the certificate level (proof hash binding).
        self.assertEqual(sat.verify_upper_certificate(self.task, self.cert, truncated), 'REJECTED')

    def test_certificate_cannot_be_reused_for_a_stronger_claim(self):
        stronger = dict(self.cert, upper=self.cert['upper'] - 1)
        self.assertEqual(sat.verify_upper_certificate(self.task, stronger, self.proof), 'REJECTED')

    def test_certificate_cannot_be_moved_to_another_host(self):
        other = GraphTask(task_id='o', n=self.task.n, edges=self.task.edges[:-1], family='random')
        self.assertEqual(sat.verify_upper_certificate(other, self.cert, self.proof), 'REJECTED')

    def test_unverifiable_formula_fails_closed(self):
        # An empty proof for a satisfiable formula must not verify.
        cnf = sat.encode(self.task, self.cert['upper'])
        self.assertNotEqual(sat.check_proof(cnf, b'')[0], 'VALID')

    def test_bogus_solver_model_is_never_trusted(self):
        fake = {'status': 'SAT', 'model': set(range(1, len(self.task.edges) + 1)), 'proof': None,
                'solver': 'fake', 'seconds': 0.0, 'exit_code': 10}
        with mock.patch.object(sat, 'solve', return_value=fake):
            with self.assertRaises(ValueError):  # dual predicates reject the forbidden motifs
                sat.certified_bounds(self.task, seconds=10)


class Pins(unittest.TestCase):
    def test_binary_hash_mismatch_refuses_the_tool(self):
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / 'cadical' / 'build'; fake.mkdir(parents=True)
            (fake / 'cadical').write_bytes(b'#!/bin/sh\nexit 20\n'); (fake / 'cadical').chmod(0o755)
            with mock.patch.dict(os.environ, {'GENESIS_TOOLCHAIN': d}):
                with self.assertRaisesRegex(ToolUnavailable, 'differs from pin'):
                    tool('cadical')


if __name__ == '__main__':
    unittest.main()
