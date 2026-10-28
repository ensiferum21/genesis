"""Part 1's usefulness ablation (`frontier/ablation.py`; the proving test's open item 4), on a toy domain built so
that the answer is known, and on the conjecture domain with invented bounds (never family A or B).

The credited representation is the discovering branch's, with how it was made and its lineage; a discovery in a
starting representation credits nothing; the verified event records the branch's compute, and every replay gets
exactly that compute; useful when only the created representation verifies; not useful when a starting one does
too; the ablation's compute is reported; deterministic."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.frontier import ablation as AB  # noqa: E402
from genesis.frontier import direction as D  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402


class Toy:
    """One problem. Representation 'derived0' (derived from 'a') issues a verifiable artifact once a run has spent
    `after` units; 'a' and 'b' issue artifacts that never verify, unless `b_finds`."""

    def __init__(self, after=30, b_finds=False):
        self.after, self.b_finds = after, b_finds
        self.calls = []

    def problems(self):
        return ['q']

    def statement(self, pid):
        return 'toy'

    def approaches(self, pid):
        return {'representation': ['a', 'b', 'derived0'], 'method': ['m'], 'params': {'n': [1]}}

    def neighbours(self, pid):
        return []

    def derive(self, pid, rep, seed):
        return 'derived0' if rep == 'a' else None

    def step(self, pid, d, seed, t, quantum):
        self.calls.append((d['representation'], seed, t))
        t1 = t + quantum
        rep = d['representation']
        good = rep == 'derived0' or (rep == 'b' and self.b_finds)
        score = 1.0 + t1 if good and t1 >= self.after else 0.1 * t1
        art = {'problem': pid, 'fingerprint': f'{rep}-{t1}', 'score': score, 'ok': good and t1 >= self.after}
        return [(t1, score)], [art]

    def abstract(self, pid, fingerprint):
        return None

    def successors(self, pid, artifact):
        return []


def verify(pid, art):
    return 1.0 if art.get('ok') else 0.0


def toy_run(rep='derived0', **kw):
    dom = Toy(**kw)
    m = Manifest(dom, verify, budget=1000, quantum=10)
    e = Frontier(m, 'frontier', seed=1, abstraction=False, branch_out=False)
    if rep == 'derived0':
        e.derive('q', 'a')
    bid = e.open(D.make('q', rep, 'm', {'n': 1}))
    while not e.best_verified.get('q'):
        e.advance(bid)
    for _ in range(3):                           # the branch goes on after its discovery
        e.advance(bid)
    return dom, e


class Toyed(unittest.TestCase):
    def test_credit_and_lineage(self):
        _, e = toy_run()
        c = AB.credit(e, 'q')
        self.assertEqual((c['representation'], c['how']), ('derived0', 'derivation'))
        self.assertEqual(c['lineage'], [('derived0', 'derivation'), ('a', 'starting')])
        ev = e.events[c['event']]
        self.assertEqual(ev['kind'], 'verified')
        self.assertEqual(c['compute'], 30.0)                     # the branch's compute when it verified, not after
        self.assertEqual(e.branches[c['branch']]['t'], 60.0)

    def test_a_starting_representation_credits_nothing(self):
        _, e = toy_run(rep='b', b_finds=True)
        self.assertIsNone(AB.credit(e, 'q'))
        self.assertIsNone(AB.ablate(e, 'q', verify, ['a', 'b']))

    def test_useful_when_only_the_created_representation_verifies(self):
        dom, e = toy_run()
        n0 = len(dom.calls)
        r = AB.ablate(e, 'q', verify, ['a', 'b'], k=3)
        self.assertTrue(r['useful'])
        self.assertEqual(r['hits'], {'derived0': [True] * 3, 'a': [False] * 3, 'b': [False] * 3})
        calls = dom.calls[n0:]
        for rep in ('a', 'b'):                                   # matched compute: every replay ran to 30 units
            ts = [t for x, _, t in calls if x == rep]
            self.assertEqual(len(ts), 3 * 3)
            self.assertEqual(max(ts), 20.0)
        self.assertEqual(len({s for x, s, _ in calls}), 3)       # k fresh seeds, the same for every arm
        self.assertNotIn(e.branches[r['branch']]['seed'], {s for _, s, _ in calls})
        self.assertEqual(r["ablation_spent"], 3 * 3 * (30 + 3))         # 3 arms, 3 seeds: 3 steps and 3 verifications

    def test_not_useful_when_a_starting_representation_verifies_too(self):
        _, e = toy_run(b_finds=True)
        r = AB.ablate(e, 'q', verify, ['a', 'b'], k=2)
        self.assertFalse(r['useful'])
        self.assertEqual(r['hits']['b'], [True, True])

    def test_an_old_log_falls_back_to_the_branch_compute(self):
        _, e = toy_run()
        for ev in e.events:
            ev.pop('t', None)
        self.assertEqual(AB.credit(e, 'q')['compute'], 60.0)


class OnTheConjectureDomain(unittest.TestCase):
    """Invented bounds: `d + 1` is false and every representation refutes it, so a derived representation credited
    with its refutation is not useful; deterministic."""

    def run_once(self):
        from genesis.conjecture import verify as V
        from genesis.conjecture.domain import ConjectureDomain
        posed = {'q1': ('d + 1', 'vertex'), 'q2': ('2*d', 'vertex')}
        dom = ConjectureDomain(posed, n_values=(6, 8))
        e = Frontier(Manifest(dom, V.verifier(posed), budget=3000, quantum=100), 'frontier', seed=3,
                     policy_params={'p_derive': 0.5})
        e.run()
        derived = [b for b in e.branches.values() if b['direction']['representation'].startswith('derived')]
        self.assertTrue(derived)
        b = derived[0]
        e.events.append({'kind': 'verified', 'problem': 'q1', 'branch': b['id'], 'value': 1.0, 'step': 0,
                         'spent': e.spent, 't': 300.0})         # a stand-in record of a discovery in that branch
        return AB.ablate(e, 'q1', V.verifier(posed), list(dom.representations), k=2)

    def test_a_bound_every_representation_refutes(self):
        r = self.run_once()
        self.assertEqual(r['how'], 'derivation')
        self.assertEqual(r['lineage'][-1], ('gamma', 'starting'))
        self.assertEqual(r['compute'], 300.0)
        self.assertFalse(r['useful'])
        self.assertTrue(any(any(r['hits'][x]) for x in ('edges', 'tree', 'bounded', 'gamma')))
        self.assertEqual(r, self.run_once())


if __name__ == '__main__':
    unittest.main()
