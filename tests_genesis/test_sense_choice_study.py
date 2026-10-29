"""B20_R136 design tests: the constants, pins and engines; the hand features are the builder's (B20_R105's two degree
statistics, up to a monotone transform, which a stump cannot tell apart); the charged budget; the verdict rule; and
the study run end to end through its REGISTERED path with a fake runner on small sets (the output redirected), where
the candidate is better only on ±1 planar graphs. No real engine runs here."""
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r136_sense_choice as S  # noqa: E402
from genesis.candidate_kinds import mcx3 as K3  # noqa: E402
from genesis.common import digest  # noqa: E402

PREREGISTRATION = '6bb39ab'         # the commit that preregistered the script


class Design(unittest.TestCase):
    def test_constants_engines_and_hand_features(self):
        import hashlib
        import b20r105_mcx_configure as R105
        from genesis.models_maxcut import MaxCutTask
        from genesis.senses import graph as SG
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest(),
                         S.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual(K3.BINARY_SHA256, S.MCX3_SHA256)
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r136_sense_choice.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        eng, ok = S.engines()
        self.assertTrue(ok)
        self.assertEqual(eng['REX'], dict(K3.DEFAULT))
        t = MaxCutTask(task_id='x', n=6, edges=((0, 1, 1), (0, 2, 1), (0, 4, 1), (1, 2, 1), (2, 3, -1), (3, 4, 1),
                                                 (4, 5, 1)), family='test')
        cv, lr = R105.features(t)
        ctx = SG.Context(S.as_graph(t))
        self.assertAlmostEqual(SG.evaluate(S.HAND[0], ctx), cv)
        self.assertAlmostEqual(math.expm1(SG.evaluate(S.HAND[1], ctx)), math.exp(lr))   # log1p(max/mean) vs log

    def test_the_script_at_the_preregistration_commit(self):
        import hashlib
        import subprocess
        try:
            out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{PREREGISTRATION}:scripts/b20r136_sense_choice.py'],
                                 capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return
        if out.returncode == 0:
            self.assertEqual(hashlib.sha256(out.stdout).hexdigest(),
                             '357cd5ed202b8b79987668d081d408ad8fcbf32ef51cb5cae6d6fa3c979b2bcb')

    def test_charged_budget_and_verdict(self):
        self.assertEqual(S.charged_budget(0.0), 1.0)
        self.assertEqual(S.charged_budget(0.0123), 0.98)
        self.assertEqual(S.charged_budget(0.9), S.MIN_BUDGET)
        self.assertEqual(S.verdict(False, True, True), 'INVALID')
        self.assertEqual(S.verdict(True, True, True), 'SENSE_INVENTION_HELPS')
        self.assertEqual(S.verdict(True, True, False), 'BEATS_FIXED_ONLY')
        self.assertEqual(S.verdict(True, False, True), 'NOT_SHOWN')
        self.assertEqual(S.holm({'P1': 0.04, 'P2': 0.01}), {'P2': 0.02, 'P1': 0.04})

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])


def fake_runner(cfg, task, seed, budget):
    cand = digest(S.engines()[0][S.CANDIDATE])[:16]
    base = 10000 + (int(digest([task.task_id])[:4], 16) % 300) + (seed % 100) / 50.0
    pm1_planar = task.family == 'planar2_pm1'
    if digest(cfg)[:16] == cand:
        base *= 1.012 if pm1_planar else 0.997
    return base * (0.999 + 0.001 * budget), budget


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path(self):
        with tempfile.TemporaryDirectory() as d:
            rc = S.main([d], registered=True, runner=fake_runner, excluded=set(), sizes=(4, 3), search_budget=40,
                        output=d)
            self.assertEqual(rc, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertTrue(s['valid'], s['validity'])
        self.assertEqual(len(s['rows']), 15)
        self.assertEqual(s['S2']['names'], ['C0_1', 'REX'])
        self.assertEqual(s['S2']['names'][s['S2']['fixed']], 'REX')
        self.assertGreaterEqual(s['S1']['ORACLE'], max(s['S1']['FIXED'], s['S1']['SENSE']) - 1e-12)
        self.assertIn(s['verdict'], ('SENSE_INVENTION_HELPS', 'BEATS_FIXED_ONLY', 'NOT_SHOWN'))



R136 = ROOT / 'evidence' / 'sense_choice_b20r136'


@unittest.skipUnless((R136 / 'summary.json').exists(), 'B20_R136 has not been recorded')
class RecordB20R136(unittest.TestCase):
    """The record of B20_R136 on its evidence: the script; validity; the search's choice recomputed (the sense
    search is deterministic in its seed and the saved training runs); every test row recomputed from the saved runs
    and sense timings; the analysis and the verdict; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R136 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R136 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r136_sense_choice.py').read_bytes()).hexdigest(),
                         '357cd5ed202b8b79987668d081d408ad8fcbf32ef51cb5cae6d6fa3c979b2bcb')

    def test_everything_recomputes(self):
        import numpy as np
        from genesis.senses import graph as SG
        from genesis.senses import synthesis as SY
        G = S.graphs(S.excluded_identities())
        self.assertEqual({k: [t.task_id for _, t in v] for k, v in G.items()}, self.s['graphs'])
        lab = S.Lab(None, lambda *a: (_ for _ in ()).throw(AssertionError('a run missing from the evidence')))
        lab.cache = dict(self.runs)
        eng, ok = S.engines()
        self.assertTrue(ok)
        names, Mtr = S.score_matrix(lab, eng, G['train'])
        ctx = [SG.Context(S.as_graph(t)) for _, t in G['train']]
        r = SY.synthesise(ctx, Mtr, S.SEARCH_BUDGET, seed=0)
        self.assertEqual(r['sense'], self.s['S2']['sense'])
        self.assertAlmostEqual(r['value'], self.s['S2']['cv_value'], places=12)
        rows = self.s['rows']
        for row, (fam, t) in zip(rows, G['test']):
            sv = self.runs[f'sense|sense|{t.task_id}']['value']
            cs = int(SY.act(tuple(self.s['S2']['sense_theta']), np.array([sv]))[0])
            self.assertEqual(names[cs], row['choice_sense'])
            got, b = S.chosen_score(lab, eng, names, cs, t, row['cpu_sense'], 'sense')
            self.assertAlmostEqual(got, row['SENSE'], places=12)
        col = lambda a: [x[a] for x in rows]                              # noqa: E731
        t1 = S.wilcoxon([a - b for a, b in zip(col('SENSE'), col('FIXED'))], 'greater')
        self.assertAlmostEqual(t1['p'], self.s['P1']['p'], places=12)
        self.assertTrue(self.s['valid'] and all(self.s['validity'].values()))
        self.assertEqual(S.verdict(self.s['valid'], self.s['P1']['passed'], self.s['P2']['passed']), self.s['verdict'])

    def test_the_decision_recomputes_from_the_rows(self):
        """Added at recording: P1 and P2, Holm, the material rule, S1's means and the verdict, from the saved rows."""
        import statistics
        rows = self.s['rows']
        col = lambda a: [x[a] for x in rows]                              # noqa: E731
        t1 = S.wilcoxon([a - b for a, b in zip(col('SENSE'), col('FIXED'))], 'greater')
        t2 = S.wilcoxon([a - b for a, b in zip(col('SENSE'), col('HAND'))], 'greater')
        adj = S.holm({'P1': t1['p'], 'P2': t2['p']})
        for t, key in ((t1, 'P1'), (t2, 'P2')):
            self.assertAlmostEqual(t['p'], self.s[key]['p'], places=12)
            self.assertAlmostEqual(t['mean'], self.s[key]['mean'], places=12)
            self.assertAlmostEqual(adj[key], self.s[key]['p_holm'], places=12)
            self.assertEqual(adj[key] < S.ALPHA and t['mean'] >= S.MATERIAL, self.s[key]['passed'])
        for arm in ('SENSE', 'HAND', 'FIXED', 'ORACLE'):
            self.assertAlmostEqual(statistics.mean(col(arm)), self.s['S1'][arm], places=12)
        self.assertEqual(len(rows), 60)
        self.assertEqual(self.s['verdict'], 'NOT_SHOWN')


if __name__ == '__main__':
    unittest.main()
