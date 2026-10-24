"""B20_R132: the bottleneck scientist on Genesis's invention (design): fresh seed; graphs (two truth sets, the splits,
disjoint, no Gset, the 4-graph splits inside the 12-graph ones); the protected judge's digest; the fixed
expressiveness pool; runs shared by the arms and the search shared by the protected and candidate judges until one
stops; charged evaluations; the release history reconstructed from each arm's own calls; the planted trait, the
zero-signal and planted pool searches and the power curves; the diagnosis rule, the primary tests and the verdict;
the registered output."""
from pathlib import Path
import hashlib
import json
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from genesis.common import digest  # noqa: E402
import b20r132_invention_bottleneck as M  # noqa: E402


def fake_runner(cfg, task, seed, budget):
    """A deterministic stand-in for the engine: a quality per engine (REX 0), per-graph quirks and seed noise."""
    q = 0.0 if cfg.get('prog') == 'B100 X I S2000 C' else (int(digest(cfg)[:6], 16) % 1000 - 600) / 1e5
    quirk = (int(digest([cfg, task.task_id])[:6], 16) % 1000 - 500) / 2e5
    noise = (seed % 1000 - 500) / 4e5
    return round(1000 * (1 + q + quirk + noise) * (1.002 if budget > 1 else 1.0), 3), budget


class Task:
    def __init__(self, name):
        self.task_id, self.n, self.edges = name, 3, [(0, 1, 1)]


class Design(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from genesis import gset as GS
        from genesis.domains import adapter
        cls.A = adapter('maxcut_v1')
        cls.ex = {cls.A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        cls.G = M.graphs(cls.ex)

    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r132_invention_bottleneck.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_graphs(self):
        ids = []
        for c in M.CLASSES:
            for s in ('T1', 'T2'):
                self.assertEqual(len(self.G[c][s]), 12)
                ids += [self.A.exposure_identity(t)['canonical'] for t in self.G[c][s]]
            for rep in range(M.REPLICATES):
                self.assertEqual({s: len(v) for s, v in self.G[c][rep].items()}, {'A': 4, 'B': 12, 'C': 12})
                ids += [self.A.exposure_identity(t)['canonical'] for v in self.G[c][rep].values() for t in v]
        self.assertEqual(len(ids), 3 * (24 + 3 * 28))
        self.assertEqual(len(set(ids)), len(ids))
        self.assertFalse(set(ids) & self.ex)

    def test_protected_judge_and_output(self):
        self.assertEqual(M.protected_digest(), M.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest(),
                         M.PROTECTED_FEEDBACK_SHA256)
        with self.assertRaises(SystemExit):
            M.main(['/tmp/elsewhere'])

    def test_fixed_pool(self):
        from genesis.candidate_kinds import mcx2 as K2
        import b20r127_self_invented_engine as R127
        p = M.fixed_pool('random')
        self.assertEqual(p, M.fixed_pool('random'))
        self.assertNotEqual(set(p), set(M.fixed_pool('planar')))
        self.assertNotIn(M.Lab.ekey(K2.DEFAULT), p)
        s127 = json.loads((ROOT / 'evidence/self_invented_engine_b20r127/search.json').read_text())
        for g in s127['generations'].values():
            self.assertIn(M.Lab.ekey(g['engine']), p)
        progs = {c['prog'] for c in p.values()}
        self.assertTrue(set(R127.TEMPLATES.values()) - {K2.DEFAULT['prog']} <= progs)
        for c in p.values():
            self.assertIsNone(K2.check_config(c))


class Arms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.splits = {s: [Task(f'{s}{i}') for i in range(n)] for s, n in M.SPLITS.items()}
        cls.lab = M.Lab(runner=fake_runner)
        cls.calls = {}
        cls.arms = {}
        for arm in M.ORDER:
            calls = []
            winner, rep = M.search(M.evaluator(cls.lab, cls.splits, M.ARMS[arm][1], calls), arm, 77)
            cls.calls[arm], cls.arms[arm] = calls, M.arm_summary(winner, rep, calls)

    def test_protected_and_candidate_judges_make_the_same_search(self):
        a = {arm: [(c['engine'], c['occ']) for c in v if c['split'] == 'A'] for arm, v in self.calls.items()}
        self.assertEqual(a['V2'][:len(a['V2@160'])], a['V2@160'])
        for x in ('L', 'L12'):
            n = min(len(a[x]), len(a['V2']))
            self.assertGreater(n, 50)
            self.assertEqual(a[x][:n], a['V2'][:n])
        self.assertGreater(len(a['L']), len(a['L12']))        # the better evaluator costs proposals

    def test_charged_evaluations_and_shared_runs(self):
        for arm, calls in self.calls.items():
            units = sum(3 if (c['split'] in 'BC' and M.ARMS[arm][1] == 12) else 1 for c in calls)
            self.assertEqual(units, self.arms[arm]['evaluations'])
            self.assertLessEqual(units, M.ARMS[arm][2] + 3)
        for c in self.calls['L']:
            if c['split'] in 'BC':
                for t in self.splits[c['split']][:4]:
                    self.assertIn(f"{c['engine']}|{t.task_id}|{c['occ']}|1", self.lab.cache)

    def test_calibration_sets(self):
        from genesis.autonomy import contract_v3 as V3
        from genesis.autonomy import selfimprove as SI
        start = self.arms['L']['history']['start']
        muts = V3.local_calibration(SI.engine_ops(), self.lab.programs[start], 77)
        self.assertEqual([c['engine'] for c in self.calls['L'] if c['split'] == 'C'], [M.Lab.ekey(m) for m in muts])
        self.assertEqual(M.n_calibration(self.calls['V2']), 32)
        self.assertEqual(self.arms['V2']['history']['start'], start)

    def test_history_reproduces_each_judge(self):
        for arm, a in self.arms.items():
            self.assertTrue(a['consistent'], arm)
        with self.assertRaises(ValueError):
            M.history([{'split': 'C', 'engine': 'x', 'value': 1.0}], 0.01, 0)


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.splits = {s: [Task(f'{s}{i}') for i in range(n)] for s, n in M.SPLITS.items()}
        cls.pool = {t.task_id: [1.0 + ((i * 7 + j) % 12 - 6) / 4000 for i in range(M.POOL)]
                    for j, t in enumerate(t for v in cls.splits.values() for t in v)}

    def test_trait(self):
        import random
        from genesis.candidate_kinds import mcx2 as K2
        self.assertFalse(M.has_trait(K2.DEFAULT))
        self.assertTrue(M.has_trait(dict(K2.DEFAULT, prog='B100 X D')))
        ops = M.search_ops(no_trait=True)
        self.assertEqual(ops['random'](random.Random(1)), dict(K2.DEFAULT))
        rng = random.Random(2)
        self.assertFalse(any(M.has_trait(ops['random'](rng)) for _ in range(200)))

    def test_pool_evaluator(self):
        ev = M.pool_evaluator(self.pool, self.splits, 4, 'x')
        vals = [ev({'prog': f'B{i}'}, 'B') for i in range(30)]
        again = M.pool_evaluator(self.pool, self.splits, 4, 'x')
        self.assertEqual([again({'prog': f'B{i}'}, 'B') for i in range(30)], vals)
        self.assertGreater(len(set(vals)), 10)
        up = M.pool_evaluator(self.pool, self.splits, 4, 'x', delta=0.01)
        self.assertAlmostEqual(up({'prog': 'B1 D'}, 'B'), ev({'prog': 'B1 D'}, 'B') * 1.01)
        self.assertEqual(up({'prog': 'B3'}, 'B'), M.pool_evaluator(self.pool, self.splits, 4, 'x')({'prog': 'B3'}, 'B'))

    def test_zero_signal_and_planted_searches(self):
        null = [M.pool_search(self.pool, self.splits, 'L', 100 + i, f'n{i}') for i in range(4)]
        self.assertLessEqual(sum(r['releases'] > 0 for r in null), 1)
        planted = [M.pool_search(self.pool, self.splits, 'L', 200 + i, f'p{i}', 0.05, no_trait=True)
                   for i in range(4)]
        self.assertFalse(any(r['start_trait'] for r in planted))
        self.assertGreaterEqual(sum(r['found'] for r in planted), 1)
        self.assertTrue(all(r['found'] for r in planted if r['released']))

    def test_power(self):
        pv = [self.pool[t.task_id] for t in self.splits['B']]
        p0 = M.power(pv, 4, 0.002, 0.0, 2000, 1)
        p1 = M.power(pv, 4, 0.002, 0.003, 2000, 1)
        p2 = M.power(pv, 4, 0.002, 0.01, 2000, 1)
        self.assertLess(p0, 0.05)
        self.assertLess(p0, p1)
        self.assertEqual(p2, 1.0)
        self.assertEqual(p1, M.power(pv, 4, 0.002, 0.003, 2000, 1))
        self.assertGreater(M.power(pv, 12, 0.002, 0.0025, 2000, 1), M.power(pv, 4, 0.002, 0.0025, 2000, 1))


class Analysis(unittest.TestCase):
    def fixture(self, l_better=True, null_l=0, headroom=True, expressible=True, search_finds=True, v2_sees=False):
        t1n = [f'a{i}' for i in range(12)]
        t2n = [f'b{i}' for i in range(12)]
        base = {c: {'T1': {t: 1000.0 for t in t1n}, 'T2': {t: 1000.0 for t in t2n}} for c in M.CLASSES}
        lv = 1005.0 if headroom is True else (1000.0 if headroom is False else headroom)
        long = {c: {t: lv for t in t1n + t2n} for c in M.CLASSES}
        good = 1004.0 if expressible else 999.0
        sub = (1003.0 if search_finds else 1000.5) if expressible else 999.0
        t1 = {c: {'REX': dict(base[c]['T1']), 'S': dict(base[c]['T1']), 'X': {t: good for t in t1n},
                  'W': {t: sub + (i % 2) for i, t in enumerate(t1n)}} for c in M.CLASSES}
        t2 = {c: {'REX': dict(base[c]['T2']), 'S': dict(base[c]['T2']), 'X': {t: good for t in t2n},
                  'W': {t: sub + (i % 2) for i, t in enumerate(t2n)}} for c in M.CLASSES}
        for c in M.CLASSES:
            for i in range(16):
                t1[c][f'm{i}'] = {t: (999.0 + (i % 4) + (j % 2) if expressible else 997.0 + (i % 4 + j % 2) / 2)
                                  for j, t in enumerate(t1n)}
        traj = {}
        for c in M.CLASSES:
            for r in range(3):
                arms = {}
                for arm in M.ARMS:
                    win = arm in ('L', 'L12') and l_better
                    subs = [{'engine': 'W', 'b': 1.01, 'released': win, 'replaced': 'S' if win else None}]
                    arms[arm] = {'tau': 0.002 if arm.startswith('L') else 0.012, 'final': 'W' if win else 'S',
                                 'history': {'start': 'S', 'submissions': subs, 'final': 'W' if win else 'S'},
                                 'proposals': 100, 'evaluations': 240, 'best_a_gain': 0.001}
                traj[f'{c}|{r}'] = {'start': 'S', 'mutations': [f'm{i}' for i in range(16)], 'arms': arms}
        null = [{'class': c, 'arm': a, 'releases': int(a == 'L' and i < null_l)} for c in M.CLASSES
                for i in range(20) for a in M.ARMS]
        planted = [{'class': c, 'arm': a, 'delta': d, 'found': True, 'released': a.startswith('L'),
                    'start_trait': False} for c in M.CLASSES for a in M.ARMS for d in M.PLANTED for _ in range(10)]
        powers = {c: {a: {f'{d:g}': (1.0 if d >= (0.002 if (a.startswith('L') or v2_sees) else 0.01) else 0.0)
                          for d in M.DELTAS} for a in M.ARMS} for c in M.CLASSES}
        return traj, t1, t2, base, long, {c: ['X'] for c in M.CLASSES}, null, planted, powers, 'REX'

    def test_judge_bottleneck(self):
        a = M.analyse(*self.fixture())
        self.assertEqual(a['P1']['label'], 'L_BETTER')
        self.assertEqual(a['P2']['label'], 'NO_DIFFERENCE')
        self.assertEqual(a['verdict'], 'JUDGE_WAS_THE_BOTTLENECK')
        self.assertEqual(a['confirmed']['L'], 9)
        self.assertEqual(a['releases']['V2'], 0)
        self.assertAlmostEqual(a['trajectories']['random|0']['arms']['L']['final_gain'], 0.35)
        d = a['diagnosis']['random']
        self.assertEqual(d['bottleneck'], 'EVALUATION')
        self.assertEqual(d['evaluation']['delta50_pct'], {'V2@160': 1.0, 'V2': 1.0, 'L': 0.2, 'L12': 0.2})
        self.assertEqual(d['expressiveness']['winner'], 'X')
        self.assertEqual(d['search']['planted']['L@0.01']['released'], 10)
        self.assertEqual(d['signal_better'], 36)

    def test_diagnosis_rule(self):
        self.assertEqual(M.analyse(*self.fixture(headroom=False))['diagnosis']['planar']['bottleneck'], 'HEADROOM')
        self.assertEqual(M.analyse(*self.fixture(headroom=1000.2))['diagnosis']['planar']['bottleneck'], 'HEADROOM')
        self.assertEqual(M.analyse(*self.fixture(headroom=1000.6))['diagnosis']['planar']['headroom']['label'], 'HEADROOM')
        self.assertEqual(M.analyse(*self.fixture(expressible=False))['diagnosis']['planar']['bottleneck'],
                         'EXPRESSIVENESS')
        self.assertEqual(M.analyse(*self.fixture(search_finds=False))['diagnosis']['planar']['bottleneck'], 'SEARCH')
        self.assertEqual(M.analyse(*self.fixture(v2_sees=True))['diagnosis']['planar']['bottleneck'],
                         'NONE_IDENTIFIED')

    def test_unsafe_and_not_shown(self):
        self.assertEqual(M.analyse(*self.fixture(null_l=5))['verdict'], 'V3_UNSAFE')
        a = M.analyse(*self.fixture(l_better=False))
        self.assertEqual(a['verdict'], 'NOT_SHOWN')
        self.assertEqual(a['P1']['p'], 1.0)
        self.assertEqual(a['null']['L'], {'searches': 60, 'with_release': 0, 'upper95': M.clopper_pearson_upper(0, 60)})

    def test_holm_and_bounds(self):
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.04}), {'a': 0.02, 'b': 0.04})
        self.assertAlmostEqual(M.clopper_pearson_upper(0, 60), 1 - 0.05 ** (1 / 60), places=6)
        self.assertLess(M.clopper_pearson_upper(2, 60), 0.11)


if __name__ == '__main__':
    unittest.main()
