"""B20_R152's design (`scripts/b20r152_self_extension.py`) and its kernel-side domain (`expressive/maxcut_domain.py`),
checked before it runs.

A fresh seed; planar2000 graphs, fresh, disjoint from each other, from Gset and from B20_R151's; the pins; the
domain's cache replays runs and pauses past its deadline; the random library matches the grown one's sizes; Page's
test; P1's rule (both comparisons, over graphs and over replicates); the verdict; and, end to end with a stub engine
that rewards an operator pattern, Genesis grows a language the judge admits and the confirmation holds, while with
no reward nothing is admitted; paused in short slices and resumed, it reaches the same result."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r152_self_extension as S  # noqa: E402
from genesis.candidate_kinds import mcx3 as K3  # noqa: E402
from genesis.expressive import lambda1 as L1  # noqa: E402
from genesis.expressive import maxcut_domain as MD  # noqa: E402

PATTERN = ('op', 'D', None, 'c')


def stub_runner(bonus=0.002):
    """A stand-in for the engine: a value per graph, noise from the seed, and (1 + bonus) per D@c item in the
    expanded program (at most 40)."""
    def run(cfg, task, seed, budget):
        base = 5000 + int(hashlib.sha256(task.task_id.encode()).hexdigest()[:4], 16) % 500
        hits = sum(1 for x in K3.walk(K3.parse(cfg['prog'])) if x == PATTERN)
        noise = 1 + 0.0004 * (random.Random(seed).random() - 0.5)
        return base * (1 + bonus * min(40, hits)) * noise, budget
    return run


class FakeClock:
    """time.monotonic for the resume test: 1 ms per reading."""

    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        self.t += 0.001
        return self.t


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('b20r*.py') if p.name != 'b20r152_self_extension.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        import b20r151_expressiveness as R151
        self.assertEqual(S.FAMILIES, R151.CANDIDATES['planar2000'])
        self.assertEqual(S.file_digest(ROOT / 'src/genesis/expressive/judge.py'), S.LANGUAGE_JUDGE_SHA256)
        self.assertEqual(S.file_digest(ROOT / 'src/genesis/autonomy/feedback.py'), S.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual(K3.BINARY_SHA256, S.MCX3_SHA256)
        self.assertEqual((S.INV_EVALS, S.INV_SIZE, S.BUDGET, S.BOUND), (240, 4, 1.0, 32))
        self.assertEqual(S.CONFIRM_GRAPHS, 4 * S.CONFIRM_REPS)

    def test_graphs_are_fresh_and_disjoint(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        gset = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        r151 = S.r151_identities()
        G, seen = S.study_graphs(gset | r151)
        ids = [A.exposure_identity(t)['canonical'] for s in G for t in G[s]]
        self.assertEqual(len(ids), S.DEV_GRAPHS + S.CONFIRM_GRAPHS + S.T_GRAPHS)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & (gset | r151))
        self.assertTrue(all(t.n == 2000 for s in G for t in G[s]))
        dom = MD.MaxCutDomain(S.FAMILIES, exclude=seen)
        drawn = dom.draw(5, 3, 'train')
        jid = [A.exposure_identity(dom.graph(g))['canonical'] for g in drawn]
        self.assertFalse(set(jid) & set(ids))


class Domain(unittest.TestCase):
    def test_the_cache_replays_and_pauses(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            calls = []

            def runner(cfg, task, seed, budget):
                calls.append(seed)
                return 100 + seed % 7, budget
            dom = MD.MaxCutDomain(S.FAMILIES[:1], cache=Path(d) / 'c.jsonl', runner=runner)
            g = dom.draw(3, 1, 'train')[0]
            v = dom.run(K3.DEFAULT, g, 12)
            self.assertEqual(dom.run(K3.DEFAULT, g, 12), v)
            self.assertEqual(len(calls), 1)
            again = MD.MaxCutDomain(S.FAMILIES[:1], cache=Path(d) / 'c.jsonl', runner=runner,
                                    deadline=time.monotonic() - 1)
            g2 = again.draw(3, 1, 'train')[0]
            self.assertEqual(g2, g)                               # the graphs are regenerated from the seed
            self.assertEqual(again.run(K3.DEFAULT, g2, 12), v)    # a cached run is served past the deadline
            again.run(K3.DEFAULT, g2, 13)                         # every slice makes at least one new run
            self.assertEqual(len(calls), 2)
            with self.assertRaises(MD.Paused):                     # then it pauses
                again.run(K3.DEFAULT, g2, 14)
            self.assertEqual(len(calls), 2)
            shared = {'new': 1}                                   # a counter shared with the study's lab
            third = MD.MaxCutDomain(S.FAMILIES[:1], cache=Path(d) / 'c.jsonl', runner=runner,
                                    deadline=time.monotonic() - 1, progress=shared)
            third.draw(3, 1, 'train')
            with self.assertRaises(MD.Paused):
                third.run(K3.DEFAULT, g2, 15)


class Analysis(unittest.TestCase):
    def test_random_library_sizes(self):
        grown = L1.EMPTY.extend('g1a', 'D@c D@c').extend('g1b', 'R B$1 X')
        rnd = S.random_library(grown, 9)
        self.assertEqual(len(rnd), 2)
        for a, b in zip(grown.defs, rnd.defs):
            self.assertEqual(L1.length(K3.parse(a['body'], calls=True, params=True)), L1.length(K3.parse(b['body'])))

    def test_page(self):
        rng = random.Random(1)
        up = [[i * 0.01 + rng.gauss(0, 0.002) for i in range(4)] for _ in range(24)]
        flat = [[rng.gauss(0, 0.002) for _ in range(4)] for _ in range(24)]
        self.assertLess(S.page_test(up)['p'], 0.001)
        self.assertGreater(S.page_test(flat)['p'], 0.05)

    def confirm(self, lift, lucky=False):
        rng = random.Random(2)
        out = {}
        n = S.CONFIRM_REPS
        for name in ('none', 'grown', 'random'):
            reps = [[rng.gauss(0, 0.0002) + lift.get(name, 0.0) for _ in range(24)] for _ in range(n)]
            if lucky and name == 'grown':
                reps[0] = [x + 0.012 for x in reps[0]]
            out[name] = {'lane': [sum(x) / n for x in zip(*reps)], 'reps': [sum(r) / 24 for r in reps]}
        return out

    def test_p1_and_verdict(self):
        self.assertTrue(S.p1(self.confirm({'grown': 0.002}))['holds'])
        self.assertFalse(S.p1(self.confirm({}))['holds'])
        self.assertFalse(S.p1(self.confirm({}, lucky=True))['holds'])                     # one lucky search
        self.assertFalse(S.p1(self.confirm({'grown': 0.002, 'random': 0.002}))['holds'])  # any library would do
        a, b = [3.0, 5.6, 5.6, 4.9, 5.1], [3.6, 1.0, 1.8, 2.2, 1.5]                       # one overlap, 5 against 5
        self.assertLessEqual(S.replicate_test(a, b), S.ALPHA)
        self.assertGreater(S.replicate_test(a[:3], b[:3]), S.ALPHA)                     # 3 against 3 would refuse
        good = S.p1(self.confirm({'grown': 0.002}))
        self.assertEqual(S.verdict(True, True, good), 'SELF_EXTENSION_HELPS')
        self.assertEqual(S.verdict(True, False, None), 'NOTHING_ADMITTED')
        self.assertEqual(S.verdict(True, True, S.p1(self.confirm({}))), 'NOT_SHOWN')
        self.assertEqual(S.verdict(False, True, good), 'INVALID')


class EndToEnd(unittest.TestCase):
    """The whole study with a stub engine that rewards D@c items."""

    def run_study(self, bonus):
        with tempfile.TemporaryDirectory() as d:
            code = S.main([d], runner=stub_runner(bonus), registered=False, exclude_r151=False)
            self.assertEqual(code, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
            s['vault_ok'] = (Path(d) / 'vault' / '.complete').exists()
            return s

    def test_rewarded_and_null(self):
        s = self.run_study(0.002)
        self.assertTrue(s['valid'], s['pins'])
        self.assertTrue(s['generations'][0]['admitted'], s['generations'][0]['decisions'])
        self.assertIn(s['verdict'], ('SELF_EXTENSION_HELPS', 'NOT_SHOWN'))
        self.assertGreater(s['P1']['none']['mean'], 0.005)                  # the grown language helps on average
        self.assertEqual(len(s['confirm']['grown']['reps']), S.CONFIRM_REPS)
        self.assertTrue(s['vault_ok'])
        self.assertGreater(s['trend']['means'][-1], s['trend']['means'][0])
        self.assertEqual(len(s['judge_ledger']), sum(len(g['decisions']) for g in s['generations']))
        n = self.run_study(0.0)
        self.assertEqual(n['verdict'], 'NOTHING_ADMITTED', n['generations'])

    def test_paused_and_resumed_to_the_same_result(self):
        small = (('planar2', {'n': 200, 'density': 0.99}), ('planar2_pm1', {'n': 200, 'density': 0.99}))
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, \
                mock.patch.object(S, 'FAMILIES', small), mock.patch('genesis.gset.tasks', return_value=[]):
            # Gset's identities are left out here only for speed: test_graphs_are_fresh_and_disjoint checks them
            self.assertEqual(S.main([a], runner=stub_runner(0.002), registered=False, exclude_r151=False), 0)
            codes = []
            while not codes or codes[-1] != 0:
                # a fake clock that moves 1 ms at each reading: the deadline is read once per new run, so a slice of
                # 2 s is about 2,000 new runs whatever the replay of the cached ones costs
                clock = FakeClock()
                with mock.patch.object(S, 'SLICE_S', 2), mock.patch.object(S, 'time', clock), \
                        mock.patch.object(MD, 'time', clock):
                    codes.append(S.main([b], runner=stub_runner(0.002), registered=False, exclude_r151=False))
                self.assertLess(len(codes), 60)
            self.assertIn(S.PAUSED, codes)
            sa, sb = (json.loads((Path(d) / 'summary.json').read_text()) for d in (a, b))
            self.assertEqual({k: v for k, v in sa.items() if k != 'code_identity'},
                             {k: v for k, v in sb.items() if k != 'code_identity'})



R152 = ROOT / 'evidence' / 'self_extension_b20r152'


def _rows(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r['key']] = r
    return out


@unittest.skipUnless((R152 / 'summary.json').exists(), 'B20_R152 has not been recorded')
class RecordB20R152(unittest.TestCase):
    """The record of B20_R152 on its evidence: the amended script; validity recomputed from the runs; P1, the verdict
    and the confirmation replicates recomputed from the saved runs; the judge's decisions against its ledger; the vault
    holds one record per decision; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R152 / 'summary.json').read_text())
        cls.runs = _rows(R152 / 'runs.jsonl')
        cls.judge_runs = _rows(R152 / 'judge_runs.jsonl')

    def test_the_script(self):
        self.assertEqual(S.file_digest(ROOT / 'scripts' / 'b20r152_self_extension.py'),
                         '2d3d8f899162c381beddf559a7a392487645e0984484b3d71a37b59a9e215b98')

    def test_validity(self):
        import statistics
        s = self.s
        self.assertTrue(s['valid'] and s['spent'] and s['disjoint'] and all(s['pins'].values()), s['pins'])
        self.assertTrue(all(r['evaluations'] >= S.INV_EVALS for r in s['reports']))
        cpus = [r['cpu'] for r in self.runs.values()] + [r['cpu'] for r in self.judge_runs.values()]
        self.assertAlmostEqual(statistics.median(cpus) / S.BUDGET, s['cpu_median'])
        self.assertGreaterEqual(s['cpu_median'], 0.9)

    def test_the_verdict_and_p1_recompute(self):
        s = self.s
        admitted1 = bool(s['generations'] and s['generations'][0]['admitted'])
        p = S.p1(s['confirm']) if s['confirm'] else None
        self.assertEqual(p, s['P1'])
        self.assertEqual(S.verdict(s['valid'], admitted1, p), s['verdict'])

    def test_the_confirmation_from_the_runs(self):
        """Each confirmation replicate's mean truth gain is that of an engine run on every truth graph, and the lanes
        are the per-graph means of those engines' gains."""
        import statistics
        s = self.s
        if not s['confirm']:
            # No confirmation stage runs unless something was admitted: assert that, rather than skip (an
            # undeclared skip fails the release matrix; changed at the B20_R169 checkpoint, disclosed there).
            admitted = [d['name'] for g in s['generations'] for d in g['decisions'] if d['admitted']]
            self.assertEqual(admitted, [])
            self.assertEqual(s['verdict'], 'NOTHING_ADMITTED')
            return
        truth = s['graphs']['truth']
        rex = S.Lab.ekey(dict(K3.DEFAULT))
        val = lambda ek, t: statistics.mean(self.runs[f'{ek}|{t}|{o}|1']['value'] for o in range(S.T_RUNS))
        base = {t: val(rex, t) for t in truth}
        engines = {k.split('|')[0] for k in self.runs if k.split('|')[1] in set(truth)}
        gains = {e: [(val(e, t) - base[t]) / base[t] for t in sorted(truth)] for e in engines
                 if all(f'{e}|{t}|{o}|1' in self.runs for t in truth for o in range(S.T_RUNS))}
        for name, c in s['confirm'].items():
            chosen = []
            for m in c['reps']:
                hits = [e for e, g in gains.items() if abs(statistics.mean(g) - m) < 1e-12]
                self.assertTrue(hits, (name, m))
                chosen.append(gains[hits[0]])
            for a, b in zip(c['lane'], [statistics.mean(x) for x in zip(*chosen)]):
                self.assertAlmostEqual(a, b)

    def test_the_decisions_and_the_ledger(self):
        s = self.s
        decisions = [d for g in s['generations'] for d in g['decisions']]
        self.assertEqual(len(s['judge_ledger']), len(decisions))
        for g in s['generations']:
            self.assertEqual(g['admitted'], [d['name'] for d in g['decisions'] if d['admitted']])
        if len(s['generations']) < S.GENERATIONS:
            self.assertEqual(s['generations'][-1]['admitted'], [])            # the line ended by stagnation

    def test_the_vault(self):
        self.assertTrue((R152 / 'vault' / '.complete').exists())

    def test_the_graphs_regenerate(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        G, _ = S.study_graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()} | S.r151_identities())
        self.assertEqual({k: [t.task_id for t in v] for k, v in G.items()}, self.s['graphs'])


if __name__ == '__main__':
    unittest.main()
