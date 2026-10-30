"""B20_R174 design tests: the pins and the fixed search winners (C0_1 is B20_R173's candidate); the random arm matches
the search's evaluations and final rule and draws only Λ0 programs within the bound; the permutation test, the
analysis and the verdict on synthetic gains; and main run end to end through its REGISTERED path with a fake runner
on small sets of small graphs (the output redirected), paused and resumed to the same summary. No real engine runs here."""
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r174_search_vs_random as S  # noqa: E402
from genesis.candidate_kinds import mcx3 as K3  # noqa: E402
from genesis.common import digest  # noqa: E402

PREREGISTRATION = None              # the commit that preregistered the script (set after it)


def fake_runner(cfg, task, seed, budget):
    """Deterministic values: REX the baseline; each engine its own offset; noise from the run seed."""
    key = digest(cfg)[:16]
    base = 10000 + int(digest([task.task_id])[:4], 16) % 300
    off = 0.0 if cfg == dict(K3.DEFAULT) else (int(key[:4], 16) % 200 - 120) / 10000.0
    return base * (1 + off) + (seed % 7) / 10.0, budget


class Design(unittest.TestCase):
    def test_pins_and_the_search_winners(self):
        import hashlib
        import b20r173_protected_release as R173
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest(),
                         S.PROTECTED_FEEDBACK_SHA256)
        self.assertEqual(K3.BINARY_SHA256, S.MCX3_SHA256)
        self.assertEqual(S.file_digest(S.R151_DIR / 'summary.json'), S.R151_SUMMARY_SHA256)
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r174_search_vs_random.py']
        self.assertFalse(any(re.search(rf'\b{S.SEED}\b', p.read_text()) for p in others))
        w, ok = S.search_winners()
        self.assertTrue(ok)
        self.assertEqual(sorted(w), sorted(S.SEARCH_WINNERS))
        self.assertEqual(w['C0_1'], R173.candidate()[0])
        for cfg in w.values():
            self.assertTrue(K3.is_lambda0(K3.parse(cfg['prog'])))

    def test_the_random_arm(self):
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        tasks = [A.generate(990100 + i, 1, 'DEV', 'planar2_pm1', {'n': 60, 'density': 0.99})[0][0] for i in range(2)]
        lab = S.Lab(None, fake_runner)
        cfg, rec = S.random_arm(lab, tasks, seed=7, evals=20)
        self.assertEqual(rec['evaluations'], 20 + S.FINALISTS * S.FINAL_EVALS)
        self.assertEqual(rec['distinct'], 20)
        self.assertEqual(len(set(rec['scores'])), len(rec['scores']))
        self.assertIn(rec['winner'], [f['key'] for f in rec['finalists']])
        self.assertEqual(digest(cfg)[:16], rec['winner'])
        best = max(rec['finalists'], key=lambda f: f['final'])
        self.assertAlmostEqual(rec['winner_final'], best['final'])
        lab2 = S.Lab(None, fake_runner)
        self.assertEqual(S.random_arm(lab2, tasks, seed=7, evals=20)[1], rec)          # deterministic
        self.assertNotEqual(S.random_arm(S.Lab(None, fake_runner), tasks, seed=8, evals=20)[1]['scores'],
                            rec['scores'])

    def test_permutation_analysis_and_verdict(self):
        self.assertAlmostEqual(S.permutation([3, 4, 5], [0, 1, 2]), 1 / 20)
        self.assertAlmostEqual(S.permutation([0, 1, 2], [3, 4, 5]), 1.0)
        rnd = [f'RANDOM_{r}' for r in range(S.REPS)]

        def gains(search, random_):
            g = {w: [search + 0.0001 * i * (j + 1) for i in range(12)] for j, w in enumerate(S.SEARCH_WINNERS)}
            g.update({w: [random_ + 0.0001 * i * (j + 1) - 0.00005 * j for i in range(12)] for j, w in enumerate(rnd)})
            return g
        better = S.analyse(gains(0.012, 0.009), gains(0.0, 0.0))
        self.assertTrue(better['P1']['passed'])
        self.assertEqual(better['reading'], 'SEARCH_BEATS_RANDOM')
        self.assertEqual(S.verdict(True, better), 'SEARCH_BEATS_RANDOM')
        self.assertEqual(S.verdict(False, better), 'INVALID')
        same = S.analyse(gains(0.010, 0.010), gains(0.0, 0.0))
        self.assertFalse(same['P1']['passed'])
        self.assertEqual(same['reading'], 'RANDOM_MATCHES_SEARCH')
        self.assertEqual(S.verdict(True, same), 'NOT_SHOWN')
        worse = S.analyse(gains(0.008, 0.012), gains(0.0, 0.0))
        self.assertEqual(worse['reading'], 'RANDOM_BETTER')
        self.assertEqual(worse['S1']['best_random'], 'RANDOM_2')          # the synthetic random means rise with r

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path_and_resumes_to_the_same_result(self):
        kw = dict(registered=True, runner=fake_runner, excluded=set(), sizes=(2, 4, 2), evals=10)

        def slow(cfg, task, seed, budget):
            time.sleep(0.002)
            return fake_runner(cfg, task, seed, budget)
        small = (('planar2', {'n': 80, 'density': 0.99}), ('planar2_pm1', {'n': 80, 'density': 0.99}))
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as d2, \
                mock.patch.object(S, 'PLANAR', small):
            self.assertEqual(S.main([d], output=d, **kw), 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
            pauses = 0
            with mock.patch.object(S, 'SLICE_S', 0.5):
                while True:
                    rc = S.main([d2], output=d2, **dict(kw, runner=slow))
                    if rc == 0:
                        break
                    self.assertEqual(rc, S.PAUSED)
                    pauses += 1
                    self.assertLess(pauses, 500)
            s2 = json.loads((Path(d2) / 'summary.json').read_text())
        self.assertGreater(pauses, 0)
        self.assertEqual({k: v for k, v in s.items() if k != 'code_identity'},
                         {k: v for k, v in s2.items() if k != 'code_identity'})
        v = s['validity']
        self.assertTrue(v['disjoint'] and v['winner_keys'] and v['r151_summary'] and v['evaluations'] and v['mcx3']
                        and v['feedback'], v)
        self.assertTrue(v['cpu'])                       # the fake runner reports its budget as its CPU
        self.assertTrue(s['valid'])
        self.assertIn(s['verdict'], ('SEARCH_BEATS_RANDOM', 'NOT_SHOWN'))
        self.assertEqual(sorted(s['gains']), sorted(list(S.SEARCH_WINNERS) + [f'RANDOM_{r}' for r in range(S.REPS)]))
        self.assertEqual(len(s['gains']['C0_1']), 4)
        self.assertEqual(len(s['gains_T2']['C0_1']), 2)
        self.assertEqual({w: r['evaluations'] for w, r in s['S3'].items()},
                         {f'RANDOM_{r}': 10 + S.FINALISTS * S.FINAL_EVALS for r in range(S.REPS)})
        self.assertIn(s['results']['reading'], ('SEARCH_BEATS_RANDOM', 'RANDOM_BETTER', 'RANDOM_MATCHES_SEARCH',
                                                'UNRESOLVED'))


if __name__ == '__main__':
    unittest.main()
