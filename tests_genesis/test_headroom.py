"""B20_R99: the headroom pilot of docs/DISCOVERY_PLAN.md. Design: fresh seeds, the arms and programs, the exchange
enumerator against brute force, the gap pieces, the region re-optimizer, the recognizer search and the verdict rule."""
from pathlib import Path
import itertools
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r99_headroom as M  # noqa: E402


def random_maximal(n, host, rng):
    order = host[:]
    rng.shuffle(order)
    S, N = set(), [0] * n
    for a, b in order:
        if not (N[a] & N[b]):
            S.add((a, b))
            N[a] |= 1 << b
            N[b] |= 1 << a
    return S


def brute(n, host, S, r):
    """Every anchor of r chosen edges whose removal admits r + 1 unchosen edges, by brute force."""
    S = {M.key(*e) for e in S}
    un = [M.key(*e) for e in host if M.key(*e) not in S]
    out = set()
    for R in itertools.combinations(sorted(S), r):
        base = S - set(R)
        for adds in itertools.combinations(un, r + 1):
            if M.is_triangle_free(base | set(adds), n):
                out.add(R)
                break
    return out


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r99_headroom.py':
                continue
            for s in (M.HOST_SEED, M.CENTRE_SEED, M.NULL_SEED, *(M.HOST_SEED + c for c in range(len(M.CELLS)))):
                self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_settings(self):
        self.assertEqual([c[0] for c in M.CELLS], ['planted_cluster', 'erdos', 'planted_cluster', 'erdos'])
        self.assertEqual([c[1]['n'] for c in M.CELLS], [128, 128, 256, 256])
        self.assertEqual(M.PER_CELL, 4)
        self.assertEqual(M.STATES, (('tfxw', 2.0), ('tfxw', 10.0), ('hybrid', 2.0), ('hybrid', 10.0),
                                    ('gen1', 2.0), ('gen2', 2.0), ('gen3', 2.0), ('control', 2.0)))
        self.assertEqual((M.CENTRES, M.REGIONS, M.CPSAT_DET), (16, ('ball2', 'ball4', 'rand4'), 2.0))
        self.assertEqual((M.HEADROOM_SHARE, M.MIN_LIFT, M.MIN_RECALL, M.NULL_DRAWS), (0.10, 2.0, 0.3, 1000))
        self.assertEqual(M.SOURCES['gen3'], ROOT / 'evidence' / 'generation3_b20r85' / 'program.json')

    def test_the_tfxw_arm_is_b20r97_s_engine(self):
        import json
        d = M.tfxw_descriptors()
        cfg = json.loads(M.TFXW_CONFIG.read_text())['config']
        self.assertEqual({b: (x['kind'], x['parameters']['config']) for b, x in d.items()},
                         {2.0: ('tfxw-v1', cfg), 10.0: ('tfxw-v1', cfg)})

    def test_exchanges_match_brute_force(self):
        rng = random.Random(5)
        for _ in range(40):
            n = rng.choice([7, 8, 9, 10])
            host = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.6]
            S = random_maximal(n, host, rng)
            x = M.exchanges(n, host, S)
            self.assertEqual({(e,) for e in x['r1']}, brute(n, host, S, 1))
            b2 = brute(n, host, S, 2)
            self.assertTrue(set(x['r2']) <= b2)
            for p in b2 - set(x['r2']):          # missed only when one edge alone frees three compatible edges
                self.assertTrue(set(p) & set(x['r1_gain2']), p)
            for p, adds in x['r2'].items():
                self.assertTrue(M.is_triangle_free((S - set(p)) | set(adds), n))

    def test_descent_never_loses_and_stays_triangle_free(self):
        rng = random.Random(6)
        for _ in range(20):
            n = 12
            host = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.5]
            S = random_maximal(n, host, rng)
            D, steps = M.exchange_descent(n, host, S)
            self.assertGreaterEqual(len(D), len(S) + steps[1] + steps[2])
            self.assertTrue(M.is_triangle_free(D, n) and D <= {M.key(*e) for e in host})

    def test_gap_pieces_swap_alone(self):
        rng = random.Random(9)
        for _ in range(60):
            n = rng.choice([8, 12, 16])
            host = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.5]
            S, B = random_maximal(n, host, rng), random_maximal(n, host, rng)
            comps = M.gap_components(n, host, S, B)
            self.assertEqual(sum(c['gain'] for c in comps), len(B) - len(S))
            self.assertEqual(sum(c['size'] for c in comps), len(S ^ B))

    def test_region_reoptimization_is_exact_on_a_small_case(self):
        try:
            cp = M.cpsat_module()
        except SystemExit:
            self.skipTest('the pinned CP-SAT tree is not installed')
        rng = random.Random(3)
        n = 10
        host = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.6]
        S = random_maximal(n, host, rng)
        region = [0, 1, 2]
        g, outcome, new = M.reoptimize(cp, n, host, S, region, seed=1)
        free = [M.key(*e) for e in host if e[0] in region or e[1] in region]
        fixed = S - set(free)
        best = max(len(fixed | set(c)) for k in range(len(free) + 1) for c in itertools.combinations(free, k)
                   if M.is_triangle_free(fixed | set(c), n)) if len(free) <= 16 else None
        if best is not None:
            self.assertEqual(outcome in ('IMPROVES', 'PROVED_NONE'), True)
            self.assertEqual(len(S) + g, best)

    def test_recognizer_finds_a_planted_rule_and_the_null_does_not(self):
        rng = random.Random(4)
        X, y, h = [], [], []
        for i in range(4000):
            a, b, c = rng.random(), rng.random(), rng.random()
            X.append([a, b, c])
            y.append(a > 0.8 and b < 0.3 or rng.random() < 0.01)
            h.append(f'h{i % 8}')
        items = M.Items(['a', 'b', 'c'], X, y, h)
        res = M.q2_class(items, {'h0', 'h1', 'h2', 'h3'})
        self.assertEqual(res['verdict'], 'PASSES')
        self.assertEqual(sorted(p[0] for p in res['recognizer'])[:2], ['a', 'b'])
        noise = M.Items(['a', 'b', 'c'], X, [rng.random() < 0.05 for _ in X], h)
        self.assertNotEqual(M.q2_class(noise, {'h0', 'h1', 'h2', 'h3'})['verdict'], 'PASSES')

    def test_rule(self):
        q2 = lambda *v: {k: {'verdict': x} for k, x in zip(('anchors_r1', 'regions'), v)}
        self.assertEqual(M.label({'tfxw_share': 0.05, 'programs_share': 0.09}, q2('PASSES', 'PASSES')), 'NO_HEADROOM')
        self.assertEqual(M.label({'tfxw_share': 0.10, 'programs_share': 0.0}, q2('FAILS', 'PASSES')), 'HEADROOM_STRUCTURED')
        self.assertEqual(M.label({'tfxw_share': 0.0, 'programs_share': 0.5}, q2('FAILS', 'UNDERPOWERED')),
                         'HEADROOM_UNSTRUCTURED')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])

    def test_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r99_headroom.py').read_text())



class RecordB20R99(unittest.TestCase):
    """B20_R99's record: the verdict and every summary figure recompute from the rows; the hosts are fresh; the
    programs and tfxw's configuration are the recorded files."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.ev = ROOT / 'evidence' / 'headroom_b20r99'
        cls.s = json.loads((cls.ev / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (cls.ev / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.tasks = json.loads((cls.ev / 'hosts.json').read_text())['tasks']

    def test_summary_recomputes(self):
        import json
        by_id = {r['task_id']: r for r in self.rows}
        rows = [by_id[t['task_id']] for t in self.tasks]
        a = json.loads(json.dumps(M.analyse(rows, {t['task_id']: t for t in self.tasks})))
        for k in ('verdict', 'q1', 'q2', 'q3', 'descriptive', 'part_b', 'part_c', 'train_hosts', 'host_order'):
            self.assertEqual(a[k], self.s[k], k)
        self.assertEqual(a['verdict'], 'HEADROOM_UNSTRUCTURED')
        self.assertEqual((a['q1']['tfxw_with_local_headroom'], a['q1']['tfxw_states']), (2, 32))
        self.assertEqual((a['q1']['programs_with_r2_after_r1_descent'], a['q1']['programs_states']), (23, 64))
        self.assertEqual((a['q2']['anchors_r1']['verdict'], a['q2']['regions']['verdict']), ('FAILS', 'UNDERPOWERED'))

    def test_hosts_are_fresh(self):
        import json
        from genesis.common import canonical
        from genesis.domains import adapter
        from genesis.models_large import LargeGraphTask
        a = adapter('triangle_free_large_v1')
        mine = {a.exposure_identity(LargeGraphTask.model_validate_json(canonical(t)))['canonical'] for t in self.tasks}
        self.assertEqual(len(mine), 16)
        others = set()
        for p in sorted((ROOT / 'evidence').glob('*/hosts.json')):
            if p.parent.name == 'headroom_b20r99':
                continue
            data = json.loads(p.read_text())
            for t in data.get('tasks', []) if isinstance(data, dict) else []:
                if isinstance(t, dict) and t.get('domain') == 'triangle_free_large_v1':
                    others.add(a.exposure_identity(LargeGraphTask.model_validate_json(canonical(t)))['canonical'])
        self.assertFalse(mine & others)

    def test_recorded_inputs(self):
        import hashlib
        for arm, rec in self.s['programs'].items():
            self.assertEqual(hashlib.sha256((ROOT / rec['path']).read_bytes()).hexdigest(), rec['sha256'], arm)
        self.assertEqual(hashlib.sha256(M.TFXW_CONFIG.read_bytes()).hexdigest(), self.s['tfxw']['config_sha256'])
        self.assertEqual(self.s['seeds'], {'hosts': M.HOST_SEED, 'centres': M.CENTRE_SEED, 'null': M.NULL_SEED})


if __name__ == '__main__':
    unittest.main()
