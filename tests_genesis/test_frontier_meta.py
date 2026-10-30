"""F6 machinery (`docs/OMEGA_FRONTIER.md` §4.8): the Frontier searching its own configurations over meta-tasks
(`frontier/meta.py`), with planted worlds as the meta-tasks and a kernel record as the meta verifier."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import meta as MT  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402
from genesis.frontier.world import PlantedWorld  # noqa: E402

INNER_BUDGET = 1200


def study(world_seeds, grid=None, policies=('frontier', 'ucb')):
    """What a study does on the kernel side: meta-tasks as manifest factories over planted worlds, a record of what
    each inner run's verifier confirmed, and a meta verifier that answers from that record."""
    records, sizes = {}, {}

    def factory_for(task, seed):
        def factory(key):
            w = PlantedWorld(seed, problems=2, horizon=INNER_BUDGET)
            rec = records.setdefault(key, {})
            sizes[task] = len(w.problems())

            def verify(p, a):
                v = w.verify(p, a)
                rec[p] = max(rec.get(p, 0.0), v)
                return v
            return Manifest(w, verify, INNER_BUDGET, quantum=10)
        return factory
    posed = {f'T{i}': factory_for(f'T{i}', s) for i, s in enumerate(world_seeds)}

    def meta_verify(task, art):
        rec = records.get(art.get('run'))
        if not rec:
            return 0.0
        return sum(rec.values()) / sizes[task]
    dom = MT.MetaDomain(posed, policies=policies, grid=grid)
    return dom, meta_verify, records


SMALL = {'eps': [0.1, 0.4], 'lam_lp': [0.0, 1.0], 'k_imagine': [1, 8]}


class Meta(unittest.TestCase):
    def outer(self, seed=3, budget=6 * INNER_BUDGET, max_steps=None, path=None):
        dom, verify, records = study([101, 202], grid=SMALL)
        m = Manifest(dom, verify, budget, quantum=300)
        if path is not None and Path(path).exists():
            e = Frontier.load(path, m)
        else:
            e = Frontier(m, 'frontier', seed=seed)
        status = e.run(max_steps)
        return dom, e, records, status

    def test_the_frontier_searches_configurations_and_the_kernel_record_verifies(self):
        dom, e, records, status = self.outer()
        self.assertEqual(status, 'done')
        self.assertTrue(e.best_verified)
        for task, v in e.best_verified.items():
            art = e.best_artifact[task]
            self.assertIn(art['run'], records)
            self.assertAlmostEqual(v, art['score'])                    # the record confirms the claimed score
            self.assertIn(art['config']['policy'], ('frontier', 'ucb'))
        self.assertTrue(dom.statement('T0').startswith('meta: '))
        self.assertNotEqual(dom.statement('T0'), dom.statement('T1'))

    def test_deterministic(self):
        _, a, _, _ = self.outer(seed=5)
        _, b, _, _ = self.outer(seed=5)
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.best_verified, b.best_verified)

    def test_a_resumed_meta_search_ends_where_an_uninterrupted_one_does(self):
        _, whole, _, _ = self.outer(seed=7)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'meta.json'
            _, first, _, status = self.outer(seed=7, max_steps=5)
            self.assertEqual(status, 'paused')
            first.save(path)
            _, second, _, status = self.outer(seed=7, path=path)       # a fresh domain: inner runs are replayed
            self.assertEqual(status, 'done')
        self.assertEqual(second.best_verified, whole.best_verified)
        self.assertEqual([ev['kind'] for ev in second.events], [ev['kind'] for ev in whole.events])

    def test_a_forged_artifact_is_refused(self):
        dom, verify, _ = study([101])
        self.assertEqual(verify('T0', {'run': 'nothing-ran-under-this-key', 'score': 1.0}), 0.0)
        self.assertEqual(verify('T0', {'score': 1.0}), 0.0)

    def test_the_grammar_and_the_inner_compute(self):
        dom, _, _ = study([101], grid=SMALL)
        g = dom.approaches('T0')
        self.assertEqual(g['representation'], ['frontier', 'ucb'])
        self.assertEqual(g['params'], SMALL)
        d = {'problem': 'T0', 'representation': 'frontier', 'method': 'run',
             'params': {'eps': 0.1, 'lam_lp': 1.0, 'k_imagine': 8}, 'op': 'seed', 'parent': None}
        pts, _ = dom.step('T0', d, 9, 0.0, 300)
        self.assertEqual(pts[-1][0], 300)
        key = MT.run_key('T0', d, 9)
        inner = dom._runs[key][0]
        self.assertGreaterEqual(inner.spent, 300)                         # the quantum, plus the last step's
        self.assertLessEqual(inner.spent, 300 + 10 + inner.verify_calls)   # verifications at most
        self.assertEqual(dom.inner_compute(), inner.spent)
        self.assertEqual(MT.run_key('T0', d, 9), key)
        self.assertNotEqual(MT.run_key('T0', dict(d, params={'eps': 0.4, 'lam_lp': 1.0, 'k_imagine': 8}), 9), key)
        self.assertEqual(set(MT.DEFAULT), set(MT.GRID))
        self.assertTrue(all(MT.DEFAULT[k] in MT.GRID[k] for k in MT.GRID))


def suite_study(world_seeds, inner=INNER_BUDGET, grid=SMALL):
    """A suite meta-task over several training worlds; the kernel's record keeps every member's confirmations."""
    records, sizes = {}, {}

    def factory(key):
        ms = []
        for i, s in enumerate(world_seeds):
            w = PlantedWorld(s, problems=2, horizon=inner)
            rec = records.setdefault(key, {}).setdefault(i, {})
            sizes[i] = len(w.problems())

            def verify(p, a, w=w, rec=rec):
                v = w.verify(p, a)
                rec[p] = max(rec.get(p, 0.0), v)
                return v
            ms.append(Manifest(w, verify, inner, quantum=10))
        return ms

    def meta_verify(task, art):
        rec = records.get(art.get('run'))
        if not rec:
            return 0.0
        return sum(sum(rec.get(i, {}).values()) / sizes[i] for i in range(len(world_seeds))) / len(world_seeds)
    return MT.SuiteMetaDomain({'T0': factory}, policies=('frontier',), grid=grid), meta_verify, records


class Suite(unittest.TestCase):
    """The repair of B20R163-META: configurations compared at equal spend on several worlds."""
    SEEDS = (101, 202, 303)
    POOL, ETA, RUNG = 6, 3, 1              # stages (6, 2), (2, 3), (1, 9): the survivor has 14 quanta
    Q_MEMBER = 100                         # 1,200 of the inner budget per member by its 12th

    def outer(self, max_steps=None, path=None):
        dom, verify, records = suite_study(self.SEEDS)
        br = MT.halving_bracket(self.POOL, self.ETA, self.RUNG)
        q = self.Q_MEMBER * len(self.SEEDS)
        m = Manifest(dom, verify, br['quanta'] * q + q - 1, quantum=q)
        params = {'pool': self.POOL, 'eta': self.ETA, 'rung': self.RUNG}
        if path is not None and Path(path).exists():
            e = Frontier.load(path, m, policy_params=params)
        else:
            e = Frontier(m, 'halving', seed=4, policy_params=params)
        return dom, e, records, e.run(max_steps), br, q

    def test_one_bracket_compares_at_equal_spend_and_the_survivor_gets_the_whole_inner_budget(self):
        dom, e, records, status, br, q = self.outer()
        self.assertEqual(status, 'done')
        ts = sorted((b['t'] for b in e.branches.values()), reverse=True)
        self.assertEqual(len(ts), self.POOL)                               # one bracket, no second pool
        want, cum = [], 0
        for n, r in br['stages']:
            cum += r
            want.append((n, cum))
        # every branch stopped at a stage boundary: n_i branches reached the i-th cumulative spend
        for n, cum in want[:-1]:
            self.assertEqual(sum(1 for t in ts if t >= cum * q), n)
        top = max(e.branches.values(), key=lambda b: b['t'])
        key = MT.run_key('T0', top['direction'], top['seed'])
        engines, ks = dom._runs[key]
        self.assertTrue(all(eng.spent + eng.quantum > eng.budget for eng in engines))   # the whole inner budget
        self.assertEqual(top['t'], INNER_BUDGET // self.Q_MEMBER * q)       # its last two quanta returned nothing
        self.assertEqual(dom.inner_compute(), sum(eng.spent for es, _ in dom._runs.values() for eng in es))
        art = e.best_artifact['T0']
        self.assertAlmostEqual(e.best_verified['T0'], art['score'])         # the kernel's record confirms it
        self.assertAlmostEqual(e.m.verify('T0', art), art['score'])
        self.assertEqual(len(art['inner_spent']), len(self.SEEDS))

    def test_deterministic_and_resumable(self):
        _, a, _, _, _, _ = self.outer()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'outer.json'
            _, first, _, status, _, _ = self.outer(max_steps=7)
            self.assertEqual(status, 'paused')
            first.save(path)
            _, b, _, status, _, _ = self.outer(path=path)                  # a fresh domain replays the inner runs
            self.assertEqual(status, 'done')
        self.assertEqual(a.best_verified, b.best_verified)
        self.assertEqual([ev['kind'] for ev in a.events], [ev['kind'] for ev in b.events])
        self.assertEqual({k: v['t'] for k, v in a.branches.items()}, {k: v['t'] for k, v in b.branches.items()})

    def test_the_members_split_the_quantum_and_a_finished_run_returns_nothing(self):
        dom, _, _ = suite_study(self.SEEDS, inner=600)
        d = {'problem': 'T0', 'representation': 'frontier', 'method': 'run',
             'params': {'eps': 0.1, 'lam_lp': 1.0, 'k_imagine': 8}, 'op': 'seed', 'parent': None}
        with self.assertRaises(ValueError):
            dom.step('T0', d, 9, 0.0, 301)
        t = 0.0
        for _ in range(2):
            pts, _ = dom.step('T0', d, 9, t, 900)
            t = pts[-1][0]
        engines, _ = dom._runs[MT.run_key('T0', d, 9)]
        self.assertTrue(all(eng.spent + eng.quantum > eng.budget for eng in engines))
        self.assertEqual(dom.step('T0', d, 9, t, 900), ([], []))
        self.assertTrue(dom.statement('T0').startswith('meta: '))

    def test_the_bracket_helper(self):
        self.assertEqual(MT.halving_bracket(27, 3, 1), {'stages': [(27, 2), (9, 3), (3, 9), (1, 27)],
                                                        'quanta': 135, 'final': 41})
        self.assertEqual(MT.halving_bracket(1, 3, 1)['stages'], [(1, 2)])


class F6Defect(unittest.TestCase):
    """B20R163-META as it was: `MetaDomain` kept returning points after its inner run had spent its budget (kept
    unchanged, so that B20_R163 and B20_R170 replay)."""

    def test_a_finished_inner_run_still_returns_points(self):
        dom, _, _ = study([101], grid=SMALL)
        d = {'problem': 'T0', 'representation': 'frontier', 'method': 'run',
             'params': {'eps': 0.1, 'lam_lp': 1.0, 'k_imagine': 8}, 'op': 'seed', 'parent': None}
        pts, _ = dom.step('T0', d, 9, float(INNER_BUDGET), 300)
        self.assertEqual(pts[-1][0], INNER_BUDGET + 300)
        inner = dom._runs[MT.run_key('T0', d, 9)][0]
        self.assertLessEqual(inner.spent, INNER_BUDGET)


if __name__ == '__main__':
    unittest.main()
