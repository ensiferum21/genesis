"""The proving test's parts 3-5 machinery (`frontier/procedure.py`, `docs/OMEGA_FRONTIER.md` §7b): a procedure is
extracted from the engine's own records of a discovery (never written by hand), refers to no problem or template by
name, and the improved inventor (the 'procedure' policy) opens the procedure's approaches on new problems first,
within its share of compute. Mechanics only, on the planted world; what it is worth is the proving test's question."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import procedure as PR  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402
from genesis.frontier.world import PlantedWorld  # noqa: E402


def run(seed, policy='frontier', params=None, budget=6000):
    w = PlantedWorld(seed, problems=3, horizon=budget)
    e = Frontier(Manifest(w, w.verify, budget), policy, seed=1, abstraction=True, branch_out=False,
                 policy_params=params)
    e.run()
    return w, e


class Procedures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w, cls.e = run(2001)
        cls.procs = {p: PR.extract(cls.e, p) for p in sorted(cls.e.best_verified)}

    def test_extraction(self):
        self.assertTrue(self.procs)
        for p, proc in self.procs.items():
            self.assertEqual(proc['kind'], 'procedure')
            text = json.dumps(proc)
            self.assertNotIn(p, text)                                  # no problem named
            self.assertNotIn('rep*', text)                             # no abstracted representation named
            ev = self.e.events[proc['provenance']['verified_event']]
            self.assertEqual((ev['kind'], ev['problem']), ('verified', p))
        abstracted = [x for x in self.procs.values() if x['steps'][-1]['abstracted']]
        self.assertTrue(abstracted)
        steps = [s['op'] for s in abstracted[0]['steps']]
        self.assertEqual(steps, ['explore', 'converge', 'abstract', 'exploit'])
        self.assertGreaterEqual(abstracted[0]['provenance']['consilience'], 2)

    def test_the_improved_inventor_uses_its_library_first(self):
        lib = [x for x in self.procs.values() if x['steps'][-1]['abstracted']]
        _, e2 = run(2101, 'procedure', {'procedures': lib})
        opens = [ev for ev in e2.events if ev['kind'] == 'open']
        self.assertEqual(opens[0]['op'], 'procedure')
        self.assertLessEqual(e2.policy.proc_spent, 0.5 * e2.spent + e2.quantum)
        _, plain = run(2101, 'procedure', {'procedures': []})
        self.assertFalse(any(ev['op'] == 'procedure' for ev in plain.events if ev['kind'] == 'open'))


if __name__ == '__main__':
    unittest.main()
