"""CRPD-2b: the Lean-checked C4 pair-count bound and its use as the PAIR_COUNT_LEAN upper method.

Requires the revised formal workspace (formal suite: no skips). Also the W23 Lean-kernel route.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from genesis.common import canonical
from genesis.formal_research import theory_package as TP
from genesis.graphs import exact_producer
from genesis.invention import pair_count as PC
from genesis.invention import soundness as SM
from genesis.models import GraphTask
from genesis.verification import certificates as CB
from genesis.verification import reliability as RL

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'pair_count_b20r'


def complete(n, domain='c4_host_v2'):
    return GraphTask(task_id=f'pc-k{n}', domain=domain, n=n, edges=tuple((u, v) for u in range(n) for v in range(u + 1, n)),
                     family='complete')


class CommittedPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads((EVIDENCE / 'package.json').read_text())

    def test_both_statements_checked_with_allowed_axioms(self):
        st = {s['id']: s['status'] for s in self.package['statements']}
        self.assertEqual(st, {'pair_count_c4': 'CHECKED', 'c4_quadratic_bound': 'CHECKED'})
        self.assertLessEqual(set(self.package['assumptions']['axioms_used']), {'propext', 'Classical.choice', 'Quot.sound'})
        self.assertEqual(PC.package_problems(self.package), [])
        self.assertIn('builder-written', ' '.join(self.package['assumptions']['conventions']))

    def test_replays_from_sources(self):
        self.assertEqual(PC.replay_verdict(self.package), 'REPLAYED')

    def test_weakened_or_foreign_statement_is_refused(self):
        bad = copy.deepcopy(self.package)
        for m in bad['modules']:
            if m['name'] == PC.CONJ_NAME:
                m['source'] = m['source'].replace('4 * S.card ^ 2 ≤', '2 * S.card ^ 2 ≤')
        self.assertTrue(PC.package_problems(bad))
        self.assertNotEqual(TP.replay(bad)['verdict'], 'REPLAYED')
        other = copy.deepcopy(self.package)
        for s in other['statements']:
            if s['id'] == PC.STATEMENT_ID:
                s['status'] = 'UNRESOLVED'
        self.assertTrue(PC.package_problems(other))


class Certificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads((EVIDENCE / 'package.json').read_text())
        cls.summary = json.loads((EVIDENCE / 'certificates.json').read_text())

    def objects(self):
        return lambda k: (EVIDENCE / 'bundles' / 'objects' / k).read_bytes()

    def test_committed_bundles_replay(self):
        want = {'complete-k3': 'OPTIMALITY_CHECKED', 'complete-k4': 'OPTIMALITY_CHECKED',
                'complete-k5': 'OPTIMALITY_CHECKED'}
        for row in self.summary['certificates']:
            b = json.loads((EVIDENCE / 'bundles' / 'bundles' / f'{row["bundle_sha256"]}.json').read_text())
            self.assertEqual(CB.custody_problems(b, lambda h: (EVIDENCE / 'bundles' / 'objects' / h).exists()), [])
            r = CB.replay(b, self.objects())
            self.assertEqual(r['status'], want.get(row['task_id'], 'BOUNDS_CHECKED'), row['task_id'])
            lo, up = SM.certificate_bound_modes(b, r)
            self.assertEqual(up['established'], 'BOUND')
            self.assertEqual(not SM.optimum_problems(lo, up), row['task_id'] in want)
            if 'sat_cross_check' in row:                       # the bound is not tight there; SAT agrees with the witness
                self.assertEqual(row['sat_cross_check']['upper'], row['exact_optimum'])

    def build(self, task, package=None):
        ex = exact_producer(task)
        return CB.build_v2(task, witness=ex['selected'], lower=ex['value'],
                           upper={'method': 'PAIR_COUNT_LEAN', 'package': package or self.package})

    def test_tampering_and_revocation(self):
        bundle, blobs = self.build(complete(5))
        get = lambda k: blobs[k]
        self.assertEqual(CB.replay(bundle, get)['status'], 'OPTIMALITY_CHECKED')
        b2 = copy.deepcopy(bundle)
        b2['upper']['value'] = 5                    # a stronger bound than the theorem gives
        b2['gap'] = -1
        self.assertEqual(CB.replay(b2, get)['upper'], 'REJECTED')
        self.assertEqual(CB.replay(bundle, lambda k: (_ for _ in ()).throw(FileNotFoundError(k)))['upper'], 'REJECTED')
        self.assertIn('pair-count theory package object missing or altered',
                      CB.custody_problems(bundle, lambda h: False))
        dead = [PC.checker_identity()]
        self.assertEqual(CB.replay(bundle, get, revoked_checkers=dead)['upper'], 'REJECTED')
        self.assertTrue(CB.custody_problems(bundle, lambda h: True, revoked_checkers=dead))
        swapped = dict(blobs)
        bad = copy.deepcopy(self.package)
        for s in bad['statements']:
            if s['id'] == PC.STATEMENT_ID:
                s['lean'] = 'True'
        swapped[bundle['upper']['package_sha256']] = canonical(bad)
        self.assertEqual(CB.replay(bundle, lambda k: swapped[k])['upper'], 'REJECTED')

    def test_scope_is_c4_hosts_only(self):
        with self.assertRaisesRegex(ValueError, 'c4_host_v2 hosts only'):
            self.build(complete(5, 'triangle_free_host_v1'))
        bad = copy.deepcopy(self.package)
        bad['statements'] = [s for s in bad['statements'] if s['id'] != PC.STATEMENT_ID]
        with self.assertRaises(ValueError):
            self.build(complete(4), bad)


class LeanKernelRoute(unittest.TestCase):
    """W23: the Lean kernel decides the repository's own predicate; it is diverse from the Python ones."""

    TASK = GraphTask(task_id='rl-lean', domain='c4_host_v2', n=5,
                     edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 4), (3, 4)), family='fixture')

    def test_agreement_with_a_diverse_route(self):
        for edges, want in ((((0, 1), (0, 2), (1, 2), (2, 4)), True), (((0, 2), (0, 3), (1, 2), (1, 3)), False)):
            c = RL.check_witness_routes(self.TASK, edges, lean=True)
            self.assertEqual((c['verdict'], c['answer']), ('AGREE', want), c['outcomes'])
            self.assertIn(('explicit-motifs-v1', 'lean-kernel-decide-v1'), [tuple(p) for p in c['diverse_pairs']])

    def test_triangle_domain(self):
        t = GraphTask(task_id='rl-lean-tf', domain='triangle_free_host_v1', n=4,
                      edges=((0, 1), (0, 2), (1, 2), (2, 3)), family='fixture')
        self.assertEqual(RL.check_witness_routes(t, ((0, 1), (0, 2), (1, 2)))['answer'], False)
        self.assertEqual(RL.check_witness_routes(t, ((0, 1), (1, 2), (2, 3)))['answer'], True)

    def test_large_inputs_are_unsupported_not_guessed(self):
        n = RL.LEAN_DECIDE_MAX_VERTICES + 2
        t = GraphTask(task_id='rl-big', domain='c4_host_v2', n=n, edges=tuple((u, u + 1) for u in range(n - 1)),
                      family='path')
        c = RL.check_witness_routes(t, t.edges)
        self.assertEqual(c['outcomes']['lean-kernel-decide-v1']['status'], 'UNSUPPORTED')
        self.assertEqual(c['verdict'], 'CORRELATED')


if __name__ == '__main__':
    unittest.main()
