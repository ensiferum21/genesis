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


if __name__ == '__main__':
    unittest.main()
