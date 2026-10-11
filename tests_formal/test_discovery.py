"""B19 / W13–W15: LP dual certificates, active experiment selection, catalysis evidence."""
import copy
import json
from pathlib import Path
import random
import unittest

from genesis import sandbox
from genesis.discovery import active as A
from genesis.discovery import obstruction as O
from genesis.domains import ADAPTERS
from genesis.formal_research import theory_package as TP
from genesis.formal_research import triangle_theory as T
from genesis.formal_research import workspace as W
from genesis.models import GraphTask

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'discovery_b19'


def _ready():
    try:
        W.environment()
        return sandbox.available()
    except Exception:
        return False


READY = _ready()


def host(n, p, seed, domain='triangle_free_host_v1'):
    rng = random.Random(seed)
    edges = tuple((u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p)
    return GraphTask(task_id=f't{seed}', domain=domain, n=n, edges=edges, family='test')


class LPCertificates(unittest.TestCase):
    def test_certificates_are_sound_and_exact(self):
        for seed in range(12):
            t = host(7, 0.6, seed)
            cert, value = O.lp_dual(t)
            check = O.check_certificate(t, cert)
            self.assertEqual(check['verdict'], 'VALID', check)
            self.assertGreaterEqual(check['bound'], T.tf_opt(set(t.edges)))       # soundness against brute force

    def test_c4_certificates(self):
        for seed in range(6):
            t = host(7, 0.6, seed, domain='c4_host_v2')
            cert, _ = O.lp_dual(t)
            check = O.check_certificate(t, cert)
            self.assertEqual(check['verdict'], 'VALID')
            self.assertTrue(all(len(q['edges']) == 4 and q['rhs'] == 3 for q in cert['inequalities']))

    def test_tampered_certificates_are_rejected(self):
        t = host(9, 0.6, 3)
        cert, _ = O.lp_dual(t)
        other = host(9, 0.6, 4)
        self.assertEqual(O.check_certificate(other, cert)['verdict'], 'REJECTED')
        cases = []
        c = copy.deepcopy(cert); c['inequalities'][0]['weight'] = '0'; cases.append(c)
        c = copy.deepcopy(cert); c['inequalities'][0]['rhs'] = 3; cases.append(c)
        c = copy.deepcopy(cert); c['inequalities'][0]['edges'][0] = [0, 99]; cases.append(c)
        c = copy.deepcopy(cert); c['slack'] = []; cases.append(c)
        c = copy.deepcopy(cert); c['bound'] -= 1; cases.append(c)
        c = copy.deepcopy(cert); c['objective'] = '1'; cases.append(c)
        c = copy.deepcopy(cert); c['schema'] = 'x'; cases.append(c)
        for c in cases:
            self.assertEqual(O.check_certificate(t, c)['verdict'], 'REJECTED')
        # a non-motif inequality (three edges that do not form a triangle) is refused
        E = list(t.edges)
        path = [e for e in E if e[0] == E[0][0]][:1] + [e for e in E if e[0] != E[0][0]][:2]
        c = copy.deepcopy(cert); c['inequalities'].append({'edges': [list(e) for e in path], 'rhs': 2, 'weight': '1'})
        self.assertFalse(O._is_motif(t, path))
        self.assertEqual(O.check_certificate(t, c)['verdict'], 'REJECTED')

    def test_joint_certification_claims_optimum_only_on_a_match(self):
        t = host(8, 0.6, 5)
        rec = O.certify(t, [], seconds=5, sat_fallback=False)        # empty witness: lower 0
        self.assertEqual(rec['lower'], 0)
        self.assertEqual(rec['status'], 'BOUNDS_ONLY' if rec['upper'] > 0 else 'OPTIMALITY_CHECKED')
        opt = T.tf_opt(set(t.edges))
        from itertools import combinations
        witness = next(list(c) for c in combinations(t.edges, opt) if T.tf(c))
        rec = O.certify(t, witness, seconds=5, sat_fallback=False)
        self.assertEqual(rec['lower'], opt)
        if rec['upper'] == opt:
            self.assertEqual(rec['status'], 'OPTIMALITY_CHECKED')
            self.assertEqual(rec['upper_evidence']['method'], 'LP_DUAL_EXACT')


class ActiveSelection(unittest.TestCase):
    def pools(self):
        rng = random.Random(0)
        methods = ['a', 'b', 'b_twin', 'c']
        fams = ['f1', 'f2']
        rate = {('a', 'f1'): 0.9, ('b', 'f1'): 0.3, ('c', 'f1'): 0.2, ('a', 'f2'): 0.2, ('b', 'f2'): 0.85,
                ('c', 'f2'): 0.3}
        pools = {}
        for f in fams:
            for m in ('a', 'b', 'c'):
                pools[(m, f)] = [int(rng.random() < rate[(m, f)]) for _ in range(30)]
            pools[('b_twin', f)] = list(pools[('b', f)])
        costs = {(m, f): 1.0 for m in methods for f in fams}
        return pools, costs, methods, fams

    def test_indistinguishable_methods_are_collapsed_and_reported(self):
        pools, costs, methods, fams = self.pools()
        classes = A.equivalence_classes(methods, fams, pools)
        self.assertIn(['b', 'b_twin'], classes)
        out = A.evaluate(pools, costs, methods, fams, budget=24, repetitions=8, draws=60)
        self.assertEqual(out['within_class'][0]['verdict'], 'UNRESOLVED')
        self.assertEqual(set(out['policies']), {'eig', 'round_robin', 'random'})
        self.assertEqual(A.resolve('b', ['b'], classes)['verdict'], 'UNRESOLVED')
        self.assertEqual(A.resolve('a', ['a'], classes)['verdict'], 'RESOLVED')

    def test_policies_spend_equal_budgets(self):
        pools, costs, methods, fams = self.pools()
        for policy in ('eig', 'round_robin', 'random', 'kg', 'top_two'):
            res = A.run_policy(policy, pools, costs, 10, seed=1, methods=methods, families=fams, draws=40)
            self.assertEqual(res['spent'], 10)

    def test_knowledge_gradient_is_exact(self):
        self.assertAlmostEqual(sum(A._betabinom_pmf(h, 8, 2.0, 3.0) for h in range(9)), 1.0, places=12)
        post = A.Posterior(['a', 'b'], ['f'])
        for _ in range(3):
            post.update('a', 'f', True)
        # a leads (mean 0.8); one observation of b cannot overtake it, four can
        self.assertEqual(A.kg_star(post, 'b', 'f', 1.0, horizons=(1,)), 0.0)
        self.assertGreater(A.kg_star(post, 'b', 'f', 1.0), 1e-4)

    def test_calibration_report(self):
        pools, _, methods, fams = self.pools()
        cal = A.calibration(pools, methods, fams)
        self.assertLess(cal['mean_abs_error'], 0.25)


@unittest.skipUnless(READY, 'formal workspace or sandbox unavailable')
class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((EVIDENCE / 'summary.json').read_text())

    def test_obstruction(self):
        ev = json.loads((EVIDENCE / 'obstruction' / 'evaluation.json').read_text())
        s = ev['summary']
        self.assertEqual(s['disagreements'], 0)
        self.assertGreaterEqual(s['joint_certified'], s['reference_certified'])
        self.assertEqual(s['lean_inequalities']['tri_not_all'], 'CHECKED')
        tasks = {}
        adapter = ADAPTERS['triangle_free_host_v1']
        for r in ev['rows']:
            if r['joint']['upper_method'] == 'LP_DUAL_EXACT':
                self.assertEqual(r['joint']['lp_certificate_recheck'], 'VALID')
            if r['joint']['status'] == 'OPTIMALITY_CHECKED':
                self.assertEqual(r['joint']['lower'], r['joint']['upper'])

    def test_active_and_catalysis_recorded(self):
        act = json.loads((EVIDENCE / 'active' / 'evaluation.json').read_text())
        self.assertEqual(act['split'], 'DEV')
        within = act['by_budget']['0.2']['within_class']
        self.assertTrue(any(set(w['class']) == {'rr_adjacent_2', 'rr_cross_2'} for w in within))
        cat = json.loads((EVIDENCE / 'catalysis' / 'solver.json').read_text())
        self.assertIn('interaction', cat['factorial']['all'])
        concept = json.loads((EVIDENCE / 'catalysis' / 'concept.json').read_text())
        self.assertLessEqual(concept['controls']['placebo']['proved'], concept['b18_arms']['concept']['proved'])

    def test_second_active_evaluation_on_fresh_pools(self):
        v1 = json.loads((EVIDENCE / 'active' / 'evaluation.json').read_text())
        v2 = json.loads((EVIDENCE / 'active_v2' / 'evaluation.json').read_text())
        self.assertNotEqual(v1['seed'], v2['seed'])                       # fresh pools, not the first ones
        self.assertEqual(set(v2['policies']), {'eig', 'round_robin', 'random', 'kg', 'top_two'})
        self.assertEqual(set(v1['by_budget']['0.2']['policies']), {'eig', 'round_robin', 'random'})   # kept as run
        for share in ('0.2', '0.4'):
            self.assertTrue(any(set(w['class']) == {'rr_adjacent_2', 'rr_cross_2'}
                                for w in v2['by_budget'][share]['within_class']))

    def test_packages_replayed(self):
        replay = json.loads((EVIDENCE / 'replay.json').read_text())
        self.assertTrue(replay and all(v['verdict'] == 'REPLAYED' for v in replay.values()))
        pkg = json.loads((EVIDENCE / 'obstruction' / 'package.json').read_text())
        self.assertEqual(TP.replay(pkg)['verdict'], 'REPLAYED')


if __name__ == '__main__':
    unittest.main()
