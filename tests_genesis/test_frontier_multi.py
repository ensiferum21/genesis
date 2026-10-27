"""Several domains as one (`frontier/multi.py`): the Frontier allocating across a planted world, the Laplacian bound
domain and the invariant-statement domain at once (invented bounds and statements only)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.conjecture import invariants as I  # noqa: E402
from genesis.conjecture import statement as ST  # noqa: E402
from genesis.conjecture import verify as V  # noqa: E402
from genesis.conjecture.domain import ConjectureDomain  # noqa: E402
from genesis.conjecture.invariant_domain import InvariantDomain  # noqa: E402
from genesis.frontier import multi as MU  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402
from genesis.frontier.world import PlantedWorld  # noqa: E402

BOUNDS = {'q1': ('d + 1', 'vertex'), 'q2': ('2*d', 'vertex')}
STATEMENTS = {'s1': 'alpha <= max_degree', 's2': 'radius <= diameter'}


def statement_verifier(pid, art):
    G = I.Graph(art['n'], [tuple(e) for e in art['edges']])
    return 1.0 if G.connected() and ST.Statement(STATEMENTS[pid]).check(G)['violated'] else 0.0


def build(world_seed=31):
    w = PlantedWorld(world_seed, problems=2, horizon=6000)
    members = {'world': w, 'bounds': ConjectureDomain(BOUNDS, n_values=(6, 8)),
               'graffiti': InvariantDomain(STATEMENTS, n_values=(6, 8))}
    verify = MU.multi_verifier({'world': w.verify, 'bounds': V.verifier(BOUNDS), 'graffiti': statement_verifier})
    return MU.MultiDomain(members), verify, w


class Multi(unittest.TestCase):
    def test_the_namespace(self):
        dom, verify, w = build()
        ps = dom.problems()
        self.assertEqual(len(ps), 2 + 2 + 2)
        self.assertTrue(all('/' in p for p in ps))
        self.assertTrue(dom.statement('bounds/q1').startswith('bounds: '))
        self.assertEqual(dom.neighbours('bounds/q1'), ['bounds/q2'])
        self.assertIsNone(dom.derive('world/' + w.problems()[0], 'r0', 1))      # the planted world cannot derive
        self.assertEqual(dom.derive('bounds/q1', 'gamma', 7), 'derived0')
        self.assertEqual(verify('nowhere/x', {}), 0.0)
        with self.assertRaises(ValueError):
            MU.MultiDomain({'a/b': w})

    def test_the_frontier_allocates_across_domains(self):
        dom, verify, w = build()
        e = Frontier(Manifest(dom, verify, budget=9000, quantum=100), 'frontier', seed=2,
                     policy_params={'p_derive': 0.2})
        e.run()
        touched = {b['direction']['problem'].split('/')[0] for b in e.branches.values()}
        self.assertEqual(touched, {'world', 'bounds', 'graffiti'})
        self.assertEqual(e.best_verified.get('bounds/q1'), 1.0)              # false bound refuted
        self.assertEqual(e.best_verified.get('graffiti/s1'), 1.0)            # false statement refuted
        self.assertFalse(e.best_verified.get('bounds/q2'))                   # the proved ones never
        self.assertFalse(e.best_verified.get('graffiti/s2'))
        self.assertTrue(any(k.startswith('world/') and v > 0 for k, v in e.best_verified.items()))

    def test_deterministic(self):
        runs = []
        for _ in range(2):
            dom, verify, _ = build()
            e = Frontier(Manifest(dom, verify, budget=3000, quantum=100), 'frontier', seed=4)
            e.run()
            runs.append((e.events, e.best_verified))
        self.assertEqual(runs[0], runs[1])


if __name__ == '__main__':
    unittest.main()
