"""F1 (`docs/OMEGA_FRONTIER.md` §4; the record `docs/checkpoints/B20_R160_RECORD.md`): the Frontier engine on the
kernel-side planted world.

Acceptance (a)-(e) of §7, on development worlds (seeds 1001-1008 for development; the tests use their own seeds):
(a) forecast coverage on held-out synthetic curves; (b) a null world gives no discovery; (c) recombination veins are
found; (d) a run stopped and resumed reaches the identical result; (e) the No-Handholding Protocol: the research
plane imports no kernel side and reaches no kernel attribute, the public domain refuses kernel calls, renaming the
problems changes no decision, and the research plane reads no file but its own state."""
import ast
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import curves as CV  # noqa: E402
from genesis.frontier import direction as D  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest, PublicDomain  # noqa: E402
from genesis.frontier.world import PlantedWorld  # noqa: E402

PKG = ROOT / 'src' / 'genesis' / 'frontier'
RESEARCH_PLANE = ('__init__.py', 'direction.py', 'curves.py', 'converge.py', 'allocate.py', 'engine.py',
                  'manifest.py', 'procedure.py', 'meta.py')
KERNEL_SIDE = ('world.py',)
KERNEL_NAMES = ('oracle', 'keys', 'truth', 'verify_value', '_problems', '_f', '_token', '_curve', '_add_problem',
                'world')


def run(world_seed, policy='frontier', budget=3000, problems=3, seed=1, null=False, ab=None, max_steps=None):
    w = PlantedWorld(world_seed, problems=problems, horizon=budget, null=null)
    m = Manifest(w, w.verify, budget, quantum=10)
    e = Frontier(m, policy, seed=seed, abstraction=ab, branch_out=ab)
    status = e.run(max_steps)
    return w, m, e, status


class Curves(unittest.TestCase):
    def test_coverage_on_held_out_curves(self):
        """(a) 90% intervals cover f(H) at least 80% of the time once a quarter of the horizon is observed."""
        rng = np.random.default_rng(424242)
        H, dt, sig = 1000, 10, 0.02
        kinds = {'vein': (0.6, 100, 1.0), 'slow': (0.9, 600, 2.5), 'decoy': (0.3, 10, 1.0), 'dead': (0.02, 50, 1.0)}
        for name, (C, tau, k) in kinds.items():
            for frac in (0.25, 0.5):
                hits = 0
                for _ in range(30):
                    Cc, tt = C * rng.uniform(0.8, 1.2), tau * rng.uniform(0.7, 1.4)
                    f = lambda t: Cc * (1 - math.exp(-(t / tt) ** k))
                    ts = np.arange(dt, H + dt, dt)
                    ys = np.array([f(t) for t in ts]) + rng.normal(0, sig, len(ts))
                    m = int(len(ts) * frac)
                    fc = CV.forecast(ts[:m], ys[:m], H, B=60, rng=rng)
                    hits += fc['lo'] <= f(H) <= fc['hi']
                self.assertGreaterEqual(hits / 30, 0.8, (name, frac))

    def test_flat_and_rising(self):
        ts = np.arange(10, 510, 10.0)
        flat = np.full(len(ts), 0.3)
        self.assertAlmostEqual(CV.point(ts, flat, 2000), 0.3, places=3)
        rising = 0.8 * (1 - np.exp(-ts / 400))
        self.assertGreater(CV.point(ts, rising, 2000), rising[-1] + 0.1)


class World(unittest.TestCase):
    def test_determinism_forgery_and_null(self):
        w1, w2 = PlantedWorld(7), PlantedWorld(7)
        p = w1.problems()[0]
        d = D.make(p, 'r0', 'm0', {'p': 1})
        a1 = w1.step(p, d, 5, 0.0, 10)
        self.assertEqual(a1, w2.step(p, d, 5, 0.0, 10))
        art = a1[1][0]
        self.assertGreaterEqual(w1.verify(p, art), 0.0)
        forged = dict(art, origin=dict(art['origin'], t=10 ** 6))
        self.assertEqual(w1.verify(p, forged), 0.0)
        self.assertEqual(w1.verify(w1.problems()[1], art), 0.0)
        n = PlantedWorld(7, null=True)
        self.assertEqual(n.oracle(5000), 0.0)
        self.assertIsNone(n.abstract(n.problems()[0], 'anything'))

    def test_abstraction_only_on_true_attractors(self):
        w = PlantedWorld(11)
        p = w.problems()[0]
        self.assertIsNone(w.abstract(p, 'Xspurious'))
        true = w._problems[p]['attractors'][0]               # the judge's view, in a test
        rep = w.abstract(p, true)
        self.assertIn(rep, w.approaches(p)['representation'])


class Engine(unittest.TestCase):
    def test_null_world_gives_no_discovery(self):
        """(b)"""
        for pol in ('frontier', 'halving', 'ucb'):
            _, _, e, _ = run(31, pol, budget=2000, null=True)
            self.assertEqual(e.total(), 0.0, pol)

    def test_recombination_veins_are_found(self):
        """(c) in at least half of the development worlds that have one, the engine opens the recombination pair."""
        found = have = 0
        for ws in range(3001, 3007):
            w, _, e, _ = run(ws, budget=6000, problems=3, seed=ws, ab=False)
            for p, key in w.keys().items():
                pairs = [k for k, v in key.items() if v == 'recomb']
                if not pairs or p not in w.problems():
                    continue
                have += 1
                r, m = pairs[0].split('|')
                found += any(b['direction']['problem'] == p and b['direction']['representation'] == r
                             and b['direction']['method'] == m for b in e.branches.values())
        self.assertGreater(have, 0)
        self.assertGreaterEqual(found / have, 0.5, (found, have))

    def test_pause_and_resume_reach_the_same_result(self):
        """(d)"""
        _, _, whole, _ = run(41, budget=2500, ab=True)
        w = PlantedWorld(41, problems=3, horizon=2500)
        m = Manifest(w, w.verify, 2500, quantum=10)
        e = Frontier(m, 'frontier', seed=1, abstraction=True, branch_out=True)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            status = e.run(37)
            while status == 'paused':
                e.save(path)
                w = PlantedWorld(41, problems=3, horizon=2500)               # a fresh process: a fresh world
                m = Manifest(w, w.verify, 2500, quantum=10)
                e = Frontier.load(path, m)
                status = e.run(37)
        import json
        self.assertEqual(e.summary(), whole.summary())
        self.assertEqual(json.loads(json.dumps(e.events)), json.loads(json.dumps(whole.events)))

    def test_renaming_the_problems_changes_no_decision(self):
        """(e) the relabelling audit."""
        class Renamed:
            def __init__(self, w, mapping):
                self.w, self.f, self.b = w, mapping, {v: k for k, v in mapping.items()}

            def problems(self):
                return [self.f[p] for p in self.w.problems()]

            def statement(self, p):
                return self.w.statement(self.b[p])

            def approaches(self, p):
                return self.w.approaches(self.b[p])

            def neighbours(self, p):
                return [self.f[q] for q in self.w.neighbours(self.b[p])]

            def step(self, p, d, seed, t, q):
                pts, arts = self.w.step(self.b[p], dict(d, problem=self.b[p]), seed, t, q)
                return pts, [dict(a, problem=self.f[a['problem']]) for a in arts]

            def abstract(self, p, fp):
                return self.w.abstract(self.b[p], fp)

            def successors(self, p, art):
                out = self.w.successors(self.b[p], dict(art, problem=self.b[p]))
                for q in out:
                    self.f.setdefault(q, f'renamed-{len(self.f)}')
                    self.b[self.f[q]] = q
                return [self.f[q] for q in out]

            def verify(self, p, art):
                return self.w.verify(self.b[p], dict(art, problem=self.b[p]))
        base_w = PlantedWorld(51, problems=3, horizon=2500)
        e1 = Frontier(Manifest(base_w, base_w.verify, 2500), 'frontier', seed=3)
        e1.run()
        w = PlantedWorld(51, problems=3, horizon=2500)
        ids = w.problems()
        rng = random.Random(9)
        names = [f'renamed-{i}' for i in range(len(ids))]
        rng.shuffle(names)
        R = Renamed(w, dict(zip(ids, names)))
        e2 = Frontier(Manifest(R, R.verify, 2500), 'frontier', seed=3)
        e2.run()
        strip = lambda evs: [{k: v for k, v in ev.items() if k not in ('problem', 'by', 'direction')} for ev in evs]
        self.assertEqual(strip(e1.events), strip(e2.events))
        self.assertAlmostEqual(e1.total(), e2.total())


class Boundary(unittest.TestCase):
    def test_the_split_covers_the_package(self):
        self.assertEqual({p.name for p in PKG.glob('*.py')}, set(RESEARCH_PLANE) | set(KERNEL_SIDE))

    def test_the_research_plane_imports_and_reaches_no_kernel_side(self):
        bad = []
        for name in RESEARCH_PLANE:
            tree = ast.parse((PKG / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = [a.name for a in node.names] + [getattr(node, 'module', None) or '']
                    if any(x.split('.')[-1] == 'world' for x in mods):
                        bad.append(f'{name}: import')
                if isinstance(node, ast.Attribute) and node.attr in KERNEL_NAMES:
                    bad.append(f'{name}: .{node.attr}')
                reflective = ('vars', 'eval', 'exec', '__import__') + (() if name == 'manifest.py' else ('getattr',))
                if isinstance(node, ast.Call) and getattr(node.func, 'id', '') in reflective:
                    bad.append(f'{name}: {node.func.id}()')       # manifest.py's PublicDomain takes the public names
                if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'open':
                    bad.append(f'{name}: open()')
                if isinstance(node, ast.Attribute) and node.attr == 'read_text' and name != 'engine.py':
                    bad.append(f'{name}: read_text')
        self.assertEqual(bad, [])

    def test_the_public_domain_refuses_kernel_calls(self):
        w = PlantedWorld(5)
        pub = PublicDomain(w)
        self.assertTrue(pub.problems())
        for name in ('oracle', 'keys', 'verify', 'verify_value', '_problems'):
            with self.assertRaises(AttributeError):
                getattr(pub, name)
        with self.assertRaises(AttributeError):
            pub.anything = 1


if __name__ == '__main__':
    unittest.main()
