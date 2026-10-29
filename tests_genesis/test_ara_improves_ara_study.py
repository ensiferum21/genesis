"""B20_R144 design tests: fresh seeds and indices, stratified sets of the right families; the change classifier and
the verdict rule; and main run end to end through its REGISTERED path on rehearsal environments (other seeds, two of
each set, the output redirected), so that the validity and the decision a registered run computes are themselves
tested (B20_R141's lesson)."""
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


if __name__ == '__main__':
    unittest.main()
