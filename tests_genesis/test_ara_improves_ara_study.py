"""B20_R144 design tests: fresh seeds and indices, stratified sets of the right families; the change classifier and
the verdict rule; and main run end to end through its REGISTERED path on rehearsal environments (other seeds, two of
each set, the output redirected), so that the validity and the decision a registered run computes are themselves
tested (B20_R141's lesson)."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r144_ara_improves_ara as S  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

PREREGISTRATION = '7acf0e4'         # the commit that preregistered the script


class Design(unittest.TestCase):
    def test_sets(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/architecture/judge.py').read_bytes()).hexdigest(),
                         S.ARA_JUDGE_SHA256)
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r144_ara_improves_ara.py']
        for seed in (S.SEED_DEV, S.SEED_TEST):
            self.assertFalse(any(re.search(rf'\b{seed}\b', p.read_text()) for p in others))
        d = S.dev_sets()
        self.assertEqual((len(d['L']), len(d['C'])), (24, 24))
        idx = [i for v in d.values() for i, _ in v]
        self.assertEqual(len(set(idx)), 48)
        self.assertTrue(min(idx) >= S.DEV0 and max(idx) < S.TEST0)
        t = S.test_set()
        self.assertEqual(len(t), 80)
        self.assertEqual({f for f, _, _ in t}, {'H1', 'H2'})
        self.assertEqual(sum(c in Z.DEFECTS for _, _, c in t), 50)
        self.assertTrue(min(i for _, i, _ in t) >= S.TEST0)
        for name in ('L', 'C'):
            self.assertEqual(sorted(c for _, c in d[name]), sorted(list(Z.CLASSES) * S.PER_DEV))

    def test_change_class_and_verdict(self):
        self.assertEqual(S.change_class(S.V1, S.V1), ('NONE', []))
        self.assertEqual(S.change_class(S.V1, dict(S.V1, exact_repeats=8))[0], 'TUNING')
        self.assertEqual(S.change_class(S.V1, dict(S.V1, ranking='localised_prior'))[0], 'STRUCTURAL')
        self.assertEqual(S.verdict(False, True, True, True, True, 'STRUCTURAL'), 'INVALID')
        self.assertEqual(S.verdict(True, False, True, True, True, 'NONE'), 'NOTHING_ADOPTED')
        self.assertEqual(S.verdict(True, True, True, True, True, 'STRUCTURAL'), 'ARA_IMPROVED_ITSELF')
        self.assertEqual(S.verdict(True, True, True, True, True, 'TUNING'), 'ARA_TUNED_ITSELF')
        self.assertEqual(S.verdict(True, True, True, False, True, 'TUNING'), 'NOT_SHOWN')
        self.assertLess(S.clopper_pearson_upper(0, 30), 0.15)

    def test_the_script_at_the_preregistration_commit(self):
        import hashlib
        import subprocess
        try:
            out = subprocess.run(['git', '-C', str(ROOT), 'show',
                                  f'{PREREGISTRATION}:scripts/b20r144_ara_improves_ara.py'], capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return
        if out.returncode == 0:
            self.assertEqual(hashlib.sha256(out.stdout).hexdigest(),
                             '05523955c17aadcda17ef61f2191854b32711840bbdaf1e79726e74ed8f058c3')

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])


SETS = {'L': [(90001, 'GLOBAL_ONLY'), (90002, 'NULL')], 'C': [(90003, 'GLOBAL_ONLY'), (90004, 'NULL')]}
TESTS = [('H1', 92001, 'GLOBAL_ONLY'), ('H2', 92002, 'SEARCH_WEAK'), ('H1', 92003, 'NULL'), ('H2', 92004, 'DECOY')]


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path_and_resumes_to_the_same_result(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as d2:
            rc = S.main([d], registered=True, sets=SETS, tests=TESTS, output=d, seeds=(990011, 990013))
            self.assertEqual(rc, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
            runs = [json.loads(x) for x in (Path(d) / 'runs.jsonl').read_text().splitlines()]
            pauses = 0
            with mock.patch.object(S, 'SLICE_S', 20):
                while True:
                    rc2 = S.main([d2], registered=True, sets=SETS, tests=TESTS, output=d2, seeds=(990011, 990013))
                    if rc2 == 0:
                        break
                    self.assertEqual(rc2, S.PAUSED)
                    pauses += 1
                    self.assertLess(pauses, 200)
            s2 = json.loads((Path(d2) / 'summary.json').read_text())
        self.assertGreater(pauses, 0)
        self.assertEqual({k: v for k, v in s.items() if k != 'code_identity'},
                         {k: v for k, v in s2.items() if k != 'code_identity'})
        self.assertTrue(s['valid'], s['validity'])
        self.assertEqual(set(s['validity']), {'wellformed', 'budget', 'judge', 'families', 'in_space', 'no_hint'})
        self.assertIn(s['verdict'], ('NOTHING_ADOPTED', 'NOT_SHOWN', 'ARA_IMPROVED_ITSELF', 'ARA_TUNED_ITSELF'))
        self.assertEqual(s['S'], dict(s['S'], controls=2))
        self.assertTrue(all(r['spent'] <= r['budget'] + 1e-9 for r in runs))
        self.assertEqual({r['family'] for r in runs if r['which'] == 'test'}, {'H1', 'H2'})
        self.assertEqual({r['family'] for r in runs if r['which'] == 'dev'}, {'base'})
        self.assertGreater(s['S6']['evaluations_meta'], 0)


R144 = ROOT / 'evidence' / 'ara_improves_ara_b20r144'


@unittest.skipUnless((R144 / 'summary.json').exists(), 'B20_R144 has not been recorded')
class RecordB20R144(unittest.TestCase):
    """The record of B20_R144 on its evidence: the script; the saved runs well formed and within their units, of the
    right families, no held-out hint; the whole study replayed from the saved runs (main on a copy of runs.jsonl, every
    ARA cycle forbidden, so a missing run fails), which recomputes the meta-cycle's choice, the tuning control's,
    validity, P1, P2, S and the verdict; and a sample of saved runs re-executed from scratch to the same record."""
    DIR, SETS, TESTS, SEEDS = R144, None, None, (S.SEED_DEV, S.SEED_TEST)

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.runs = [json.loads(x) for x in (cls.DIR / 'runs.jsonl').read_text().splitlines() if x.strip()]

    def test_the_script(self):
        if self.DIR != R144:
            return
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r144_ara_improves_ara.py').read_bytes()).hexdigest(),
                         '05523955c17aadcda17ef61f2191854b32711840bbdaf1e79726e74ed8f058c3')

    def test_the_saved_runs(self):
        self.assertEqual(len({r['key'] for r in self.runs}), len(self.runs))
        self.assertTrue(all(r['wellformed'] and r['spent'] <= r['budget'] + 1e-9 for r in self.runs))
        self.assertEqual({r['family'] for r in self.runs if r['which'] == 'dev'}, {'base'})
        self.assertEqual({r['family'] for r in self.runs if r['which'] == 'test'}, {'H1', 'H2'})
        self.assertFalse(any(r['hint'] for r in self.runs if r['which'] == 'test'))
        from genesis.architecture import ara as A
        from genesis.common import digest
        s, tests = self.s, self.TESTS or S.test_set()
        arms = [(s['v2'], 0.0), (s['v1'], s['S6']['extra_units_v1m']), (s['tune'], 0.0), (s['v1'], 0.0)]
        want = set()
        for fam, i, c in tests:
            for cfg, extra in arms:
                prior = s['prior'] if A.config_of(cfg)['ranking'] == 'localised_prior' else None
                want.add(digest({'cfg': A.config_of(cfg), 'family': fam, 'index': i, 'cls': c, 'hint': False,
                                 'extra': extra, 'prior': prior, 'which': 'test'})[:24])
        self.assertEqual({r['key'] for r in self.runs if r['which'] == 'test'}, want)

    def test_the_study_replays_from_the_saved_runs(self):
        import shutil
        from unittest import mock
        from genesis.architecture import ara as A

        def forbidden(*a, **kw):
            raise AssertionError('a run missing from the evidence')
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(self.DIR / 'runs.jsonl', Path(d) / 'runs.jsonl')
            with mock.patch.object(A, 'cycle', forbidden):
                rc = S.main([d], registered=True, sets=self.SETS, tests=self.TESTS, output=d, seeds=self.SEEDS)
            self.assertEqual(rc, 0)
            self.assertEqual((Path(d) / 'runs.jsonl').read_text(), (self.DIR / 'runs.jsonl').read_text())
            got = json.loads((Path(d) / 'summary.json').read_text())
        drop = ('code_identity',)
        self.assertEqual({k: v for k, v in got.items() if k not in drop},
                         {k: v for k, v in self.s.items() if k not in drop})
        s = self.s
        self.assertEqual(s['verdict'], S.verdict(s['valid'], s['adopted'], s['P1']['passed'], s['P2']['passed'],
                                                 s['S']['passed'], s['change']['class']))

    def test_a_sample_of_runs_re_executes(self):
        """Re-executed from scratch, to the same saved record: ARA_v1 on the first two ladder environments, and the v2
        and v1m runs of the first defect environment and the first control of each held-out family."""
        from genesis.architecture import ara as A
        from genesis.architecture import zoo as Z
        from genesis.common import digest
        s = self.s
        by_key = {r['key']: r for r in self.runs}
        sets, tests = self.SETS or S.dev_sets(), self.TESTS or S.test_set()

        def prior_for(cfg):
            return s['prior'] if A.config_of(cfg)['ranking'] == 'localised_prior' else None
        todo = [(s['v1'], 'base', i, c, 0.0, None, 'dev') for i, c in sets['L'][:2]]
        for fam in ('H1', 'H2'):
            for defect in (True, False):
                env = next((t for t in tests if t[0] == fam and (t[2] in Z.DEFECTS) == defect), None)
                if env:
                    todo.append((s['v2'], fam, env[1], env[2], 0.0, prior_for(s['v2']), 'test'))
                    todo.append((s['v1'], fam, env[1], env[2], s['S6']['extra_units_v1m'], prior_for(s['v1']), 'test'))
        self.assertGreaterEqual(len(todo), 4)
        with tempfile.TemporaryDirectory() as d:
            lab = S.Lab(Path(d) / 'runs.jsonl', None, self.SEEDS)
            for cfg, fam, i, c, extra, prior, which in todo:
                k = digest({'cfg': A.config_of(cfg), 'family': fam, 'index': i, 'cls': c, 'hint': False,
                            'extra': extra, 'prior': prior, 'which': which})[:24]
                self.assertIn(k, by_key)
                got = lab.run(cfg, fam, i, c, False, extra_units=extra, prior=prior, which=which)
                self.assertEqual(got['key'], k)
                for f in ('gain', 'promoted', 'diagnosis', 'located', 'spent', 'arm', 'budget'):
                    self.assertEqual(json.loads(json.dumps(got.get(f), default=str)), by_key[k].get(f), (k, f))


if __name__ == '__main__':
    unittest.main()
