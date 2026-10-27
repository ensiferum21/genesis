"""B20_R165's design (`scripts/b20r165_planar_replication.py`), checked before it runs, without generating its graphs:
the frozen engines come from B20_R151's committed evidence with their recorded keys; the pre-specified engine is the
best by training score; the verdict rules on synthetic gains; and end to end, on graphs of ANOTHER seed with a stub
runner, the study runs, pauses at its slice limit and resumes to the same runs."""
import json
from pathlib import Path
import re
import statistics
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r165_planar_replication as S  # noqa: E402


class Design(unittest.TestCase):
    def test_constants_and_the_frozen_engines(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r165_planar_replication.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        self.assertEqual(S.file_digest(S.R151_DIR / 'summary.json'), S.R151_SUMMARY_SHA256)
        eng, ok = S.engines()
        self.assertTrue(ok)
        self.assertEqual(len(eng), 18)
        self.assertEqual(S.prespecified(), S.PRESPECIFIED)
        self.assertEqual(eng[S.PRESPECIFIED]['prog'], 'R B1296 B703 C b1 R B703 B703 C C')
        self.assertEqual(S.CLASSES[S.PRIMARY][1], 48)
        self.assertEqual(S.MATERIAL, 0.001)


def synthetic(gain, single_gain=None):
    import random
    rng = random.Random(1)
    eng, _ = S.engines()
    tasks = [f't{i}' for i in range(48)]
    base = {t: 1000.0 + rng.random() for t in tasks}
    values = {}
    for n in eng:
        g = single_gain if (n == S.PRESPECIFIED and single_gain is not None) else gain
        values[n] = {t: base[t] * (1 + g + 0.0005 * (rng.random() - 0.5)) for t in tasks}
    finals = {S.PRIMARY: {'base': base, 'values': values, 'long': {t: base[t] * 1.005 for t in tasks}}}
    fams = {t: ('planar2#0' if i % 2 == 0 else 'planar2_pm1#1') for i, t in enumerate(tasks)}
    return finals, fams


class Analysis(unittest.TestCase):
    def test_verdicts(self):
        primary, res = S.analyse(*synthetic(0.006))
        self.assertEqual(S.verdict(True, primary), 'REPLICATED_WITH_SINGLE_ENGINE')
        self.assertEqual(S.verdict(False, primary), 'INVALID')
        primary, _ = S.analyse(*synthetic(0.006, single_gain=-0.002))
        self.assertEqual(S.verdict(True, primary), 'REPLICATED')
        primary, _ = S.analyse(*synthetic(0.0005))                      # positive, but below the material 0.1%
        self.assertEqual(S.verdict(True, primary), 'NOT_REPLICATED')
        primary, _ = S.analyse(*synthetic(-0.003))
        self.assertEqual(S.verdict(True, primary), 'NOT_REPLICATED')
        self.assertIn('rex10_vs_rex1', res[S.PRIMARY]['S3'])
        self.assertEqual(set(res[S.PRIMARY]['S4']), {'planar2#0', 'planar2_pm1#1'})


def stub_runner(cfg, task, seed, budget):
    import hashlib
    h = int(hashlib.sha256(repr((cfg['prog'], task.task_id, seed, budget)).encode()).hexdigest()[:8], 16)
    return 1000.0 + (h % 100) / 10.0 + (5.0 if cfg['prog'] != 'B100 X I S2000 C' else 0.0), budget


class EndToEnd(unittest.TestCase):
    def test_runs_pauses_and_resumes(self):
        with mock.patch.object(S, 'SEED', 777165):
            G = S.graphs(set(), limit=1)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(S.main([a], runner=stub_runner, registered=False, graph_set=G, excluded=set()), 0)
            codes = []
            with mock.patch.object(S, 'SLICE_S', -1):
                while not codes or codes[-1] != 0:
                    codes.append(S.main([b], runner=stub_runner, registered=False, graph_set=G, excluded=set()))
                    self.assertLess(len(codes), 200)
            self.assertIn(S.PAUSED, codes)
            ra = sorted((Path(a) / 'runs.jsonl').read_text().splitlines())
            rb = sorted((Path(b) / 'runs.jsonl').read_text().splitlines())
            self.assertEqual(ra, rb)
            s = json.loads((Path(a) / 'summary.json').read_text())
        self.assertTrue(s['disjoint'])
        self.assertEqual(len(ra), 3 * 1 * 19 * 2 + 1)                   # classes x graphs x engines x runs + 10 s
        self.assertEqual(set(s['results']), set(S.CLASSES))

    def test_the_registered_run_refuses_other_outputs(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(SystemExit):
                S.main([a])



R165 = ROOT / 'evidence' / 'planar_replication_b20r165'


@unittest.skipUnless((R165 / 'summary.json').exists(), 'B20_R165 has not been recorded')
class RecordB20R165(unittest.TestCase):
    """The record of B20_R165 on its evidence: the script; validity with the CPU medians recomputed; every final value
    recomputed from the saved runs; the analysis and the verdict recomputed; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R165 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R165 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r165_planar_replication.py').read_bytes()).hexdigest(),
                         'fbf968c5e2cf22f3e6f2720df16ae2586f08dbcc32f5f556ca4df99ed523516f')

    def test_validity(self):
        s = self.s
        self.assertTrue(s['valid'] and s['disjoint'] and all(s['pins'].values()))
        cpus = {}
        for r in self.runs.values():
            b = r['key'].rsplit('|', 1)[1]
            cpus.setdefault(b, []).append(r['cpu'] / float(b))
        self.assertTrue(all(statistics.median(v) >= 0.9 for v in cpus.values()))
        self.assertEqual({b: statistics.median(v) for b, v in cpus.items()}, s['cpu_median'])

    def test_the_finals_from_the_runs(self):
        from genesis.candidate_kinds import mcx3 as K3
        from genesis.common import digest
        eng, ok = S.engines()
        self.assertTrue(ok)
        rex = digest(dict(K3.DEFAULT))[:16]
        val = lambda ek, t, o, b='1': self.runs[f'{ek}|{t}|{o}|{b}']['value']
        for cls, f in self.s['finals'].items():
            for t, b in f['base'].items():
                self.assertAlmostEqual(b, statistics.mean(val(rex, t, o) for o in range(S.T_RUNS)))
            for n, vals in f['values'].items():
                ek = digest(eng[n])[:16]
                for t, v in vals.items():
                    self.assertAlmostEqual(v, statistics.mean(val(ek, t, o) for o in range(S.T_RUNS)))
            if cls == S.PRIMARY:
                for t, v in f['long'].items():
                    self.assertAlmostEqual(v, val(rex, t, 0, '10'))

    def test_the_analysis_recomputes(self):
        primary, res = S.analyse(self.s['finals'], self.s['families'], self.s['prespecified'])
        for k in ('P1', 'P2'):
            self.assertEqual(primary[k]['label'], self.s['primary'][k]['label'])
            self.assertAlmostEqual(primary[k]['p_holm'], self.s['primary'][k]['p_holm'])
            self.assertAlmostEqual(primary[k]['mean'], self.s['primary'][k]['mean'])
        self.assertEqual(S.verdict(self.s['valid'], primary), self.s['verdict'])
        self.assertEqual(self.s['prespecified'], S.PRESPECIFIED)

    def test_the_graphs_regenerate(self):
        G = S.graphs(S.excluded_identities())
        self.assertEqual({c: [t.task_id for t in ts] for c, ts in G.items()}, self.s['graphs'])


if __name__ == '__main__':
    unittest.main()
