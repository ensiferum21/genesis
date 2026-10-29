"""B20_R173 design tests: the constants and pins; the candidate is B20_R165's pre-specified engine; the calibration
programs follow the contract (REX and 47 seeded random 'L0' engines, distinct, valid); version 3's 16 mutants of REX;
the verdict rule; and the study run end to end through its REGISTERED path with a fake runner on small sets (the
output redirected), once where the candidate is far better than REX (released) and once where it is the same (not
released), so that the validity and the decision a registered run computes are themselves tested (B20_R141's
lesson). No real engine runs here."""
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r173_protected_release as S  # noqa: E402
from genesis.candidate_kinds import mcx3 as K3  # noqa: E402
from genesis.common import digest  # noqa: E402

PREREGISTRATION = 'd8cb798'         # the commit that preregistered the script


class Design(unittest.TestCase):
    def test_constants_and_pins(self):
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest(),
                         S.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual(K3.BINARY_SHA256, S.MCX3_SHA256)
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r173_protected_release.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        self.assertEqual((S.SIZE, S.N_TRUTH, S.POPULATION + S.CALIBRATION_EXTRA), (12, 24, 48))
        import subprocess
        try:
            out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{PREREGISTRATION}:scripts/b20r173_protected_release.py'],
                                 capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            out = None
        if out is not None and out.returncode == 0:
            self.assertEqual(hashlib.sha256(out.stdout).hexdigest(),
                             'a3e038415e1b57199dc2aeab759f413338e0f61fec05db6786077afdabaa7291')

    def test_the_candidate_is_r165s_prespecified_engine(self):
        import b20r165_planar_replication as R165
        cfg, ok = S.candidate()
        self.assertTrue(ok)
        self.assertEqual(R165.prespecified(), S.CANDIDATE)
        self.assertEqual(R165.engines()[0][S.CANDIDATE], cfg)
        self.assertEqual(hashlib.sha256((S.R151_DIR / 'summary.json').read_bytes()).hexdigest(),
                         S.R151_SUMMARY_SHA256)

    def test_calibration_programs(self):
        cal = S.calibration_programs()
        self.assertEqual(len(cal), 48)
        self.assertEqual(cal[0], dict(K3.DEFAULT))
        self.assertEqual(len({digest(c) for c in cal}), 48)
        for c in cal:
            self.assertIsNone(K3.check_config(c))
            self.assertTrue(K3.is_lambda0(K3.parse(c['prog'])))
        self.assertEqual(cal, S.calibration_programs())          # seeded
        v3 = S.v3_programs()
        self.assertEqual(len(v3), 16)
        self.assertNotIn(dict(K3.DEFAULT), v3)
        self.assertEqual(len({digest(c) for c in v3}), 16)
        self.assertTrue(all(K3.check_config(c) is None for c in v3))

    def test_verdict_and_split_size(self):
        self.assertEqual(S.verdict(False, {'released': True}), 'INVALID')
        self.assertEqual(S.verdict(True, {'released': True}), 'RELEASED')
        self.assertEqual(S.verdict(True, {'released': False}), 'NOT_RELEASED')
        self.assertEqual(S.split_size_needed({'tau': 0.02}, 0.01, 12), 49)
        self.assertIsNone(S.split_size_needed({'tau': 0.02}, 0.0, 12))

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])


def fake_runner(better):
    """A deterministic stand-in for the binary: REX's and random engines' cuts vary by graph and seed; the candidate's
    are 5% higher when `better`."""
    cand = digest(S.candidate()[0])[:16]

    def run(cfg, task, seed, budget):
        base = 10000 + (int(digest([task.task_id])[:4], 16) % 500)
        noise = (seed % 1000) / 1000.0 * 20
        v = base + noise
        if digest(cfg)[:16] == cand and better:
            v *= 1.05
        if budget == S.LONG:
            v *= 1.01
        return v, budget
    return run


class RegisteredPath(unittest.TestCase):
    def run_study(self, better):
        with tempfile.TemporaryDirectory() as d:
            rc = S.main([d], registered=True, limit=3, runner=fake_runner(better), excluded=set(), output=d)
            self.assertEqual(rc, 0)
            return json.loads((Path(d) / 'summary.json').read_text())

    def test_released_when_far_better(self):
        s = self.run_study(True)
        self.assertTrue(s['valid'], s['validity'])
        self.assertEqual(s['verdict'], 'RELEASED')
        self.assertGreater(s['S2']['mean'], 0.04)

    def test_not_released_when_the_same(self):
        s = self.run_study(False)
        self.assertTrue(s['valid'], s['validity'])
        self.assertEqual(s['verdict'], 'NOT_RELEASED')



R173 = ROOT / 'evidence' / 'protected_release_b20r173'


@unittest.skipUnless((R173 / 'summary.json').exists(), 'B20_R173 has not been recorded')
class RecordB20R173(unittest.TestCase):
    """The record of B20_R173 on its evidence: the script; validity recomputed; both judges rebuilt from the saved
    runs (the protected Judge class itself, replaying its calls from the cache), their taus and decisions recomputed;
    the truth recomputed; the verdict; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R173 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R173 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r173_protected_release.py').read_bytes()).hexdigest(),
                         'a3e038415e1b57199dc2aeab759f413338e0f61fec05db6786077afdabaa7291')

    def replay_runner(self):
        def run(cfg, task, seed, budget):
            raise AssertionError('a run missing from the evidence')
        return run

    def lab(self):
        lab = S.Lab(None, self.replay_runner())
        lab.cache = dict(self.runs)
        return lab

    def test_validity(self):
        s = self.s
        self.assertTrue(s['valid'] and all(s['validity'].values()))
        one = [r['cpu'] for k, r in self.runs.items() if k.endswith('|1')]
        ten = [r['cpu'] for k, r in self.runs.items() if k.endswith('|10')]
        self.assertGreaterEqual(statistics.median(one), 0.9)
        self.assertGreaterEqual(statistics.median(ten), 9.0)

    def test_the_judges_and_the_truth_recompute(self):
        G = S.graphs(S.excluded_identities())
        self.assertEqual({k: [t.task_id for t in v] for k, v in G.items()}, self.s['graphs'])
        lab = self.lab()
        cand, ok = S.candidate()
        self.assertTrue(ok)
        v2 = S.judge(S.evaluator(lab, G), S.calibration_programs(), dict(K3.DEFAULT), cand)
        v3 = S.judge(S.evaluator(lab, G), S.v3_programs(), dict(K3.DEFAULT), cand)
        for got, saved in ((v2, self.s['R1']), (v3, self.s['S1'])):
            for k in ('tau', 'start', 'b_candidate'):
                self.assertAlmostEqual(got[k], saved[k], places=12)
            self.assertEqual(got['released'], saved['released'])
        truth = []
        for t in G['T']:
            c = statistics.mean(lab.run(cand, t, f'truth{r}') for r in range(S.T_RUNS))
            x = statistics.mean(lab.run(dict(K3.DEFAULT), t, f'truth{r}') for r in range(S.T_RUNS))
            truth.append((c - x) / x)
        self.assertEqual([round(x, 12) for x in truth], [round(x, 12) for x in self.s['S2']['gains']])
        self.assertEqual(S.verdict(self.s['valid'], v2), self.s['verdict'])


if __name__ == '__main__':
    unittest.main()
