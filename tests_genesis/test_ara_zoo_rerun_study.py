"""B20_R167's design (`scripts/b20r167_ara_zoo_rerun.py`), checked before it runs, without touching its environments.

B20_R141 again with its validity defect repaired: a fresh sealed seed and fresh indices; the design otherwise
B20_R141's, function for function; the freshness clause as a function of what it means; and, the path B20_R141's
tests never ran, `main` as a registered run (output, seed and environments redirected to rehearsal ones), whose
validity must hold. Then the analysis on synthetic rows and the run, pause and resume on three environments of
ANOTHER sealed seed, as for B20_R141."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r141_ara_zoo as R141  # noqa: E402
import b20r167_ara_zoo_rerun as S  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

TEST_SEED = 777001                         # never the study's
TEST_ENVS = [(30000, 'GLOBAL_ONLY'), (30002, 'EVAL_NOISY'), (30003, 'DECOY')]


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('b20r*.py') if p.name != 'b20r167_ara_zoo_rerun.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        self.assertNotEqual(S.SEALED_SEED, R141.SEALED_SEED)
        self.assertNotEqual(S.SEALED_SEED, TEST_SEED)
        dev = json.loads((ROOT / 'evidence/ara1_development/devlook.json').read_text())
        used = {r['index'] for r in dev['rows']} | {i for i, _ in R141.environments()} | {i for i, _ in TEST_ENVS}
        envs = S.environments()
        self.assertFalse({i for i, _ in envs} & used)
        self.assertTrue(all(i >= S.INDEX0 for i, _ in envs))
        self.assertEqual(len(envs), 5 * S.PER_DEFECT + 3 * S.PER_CONTROL)
        for c in Z.CLASSES:
            self.assertEqual(sum(1 for _, x in envs if x == c), S.PER_DEFECT if c in Z.DEFECTS else S.PER_CONTROL)
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/architecture/judge.py').read_bytes()).hexdigest(),
                         S.ARA_JUDGE_SHA256)
        self.assertEqual(S.OUTPUT, ROOT / 'evidence' / 'ara_zoo_b20r167')

    def test_the_design_is_b20r141s(self):
        """Everything but the three changes is B20_R141's: the constants and every function except `main`, the
        environments (shifted to the new indices) and the new `freshness`."""
        for name in ('PER_DEFECT', 'PER_CONTROL', 'ARMS', 'MATERIAL', 'ALPHA', 'NONE_RATE', 'RELEASE_BOUND',
                     'ARA_JUDGE_SHA256', 'SLICE_S', 'PAUSED'):
            self.assertEqual(getattr(S, name), getattr(R141, name), name)
        for name in ('run_arm', 'binom_greater', 'wilcoxon_greater', 'holm', 'clopper_pearson_upper', 'released',
                     'analyse', 'check_promoted', 'verdict', 'file_digest'):
            self.assertEqual(inspect.getsource(getattr(S, name)), inspect.getsource(getattr(R141, name)), name)
        self.assertEqual([c for _, c in S.environments()], [c for _, c in R141.environments()])
        self.assertEqual([i - S.INDEX0 for i, _ in S.environments()], [i - R141.INDEX0 for i, _ in R141.environments()])

    def test_main_differs_from_b20r141s_only_by_the_repair(self):
        a = inspect.getsource(R141.main).splitlines()
        b = inspect.getsource(S.main).splitlines()
        import difflib
        changed = [x for x in difflib.unified_diff(a, b, lineterm='', n=0)
                   if x[:1] in '+-' and not x.startswith(('+++', '---'))]
        self.assertEqual(changed, [
            "-    if registered and out != (ROOT / 'evidence' / 'ara_zoo_b20r141').resolve():",
            "-        raise SystemExit('the registered output is evidence/ara_zoo_b20r141')",
            "+    if registered and out != OUTPUT.resolve():",
            "+        raise SystemExit(f'the registered output is {OUTPUT}')",
            "+    custom = envs is not None",
            "-    fresh = all(i >= INDEX0 for i in rows) and (sealed_seed != SEALED_SEED or envs is None or not registered)",
            "+    fresh = freshness(list(rows), registered, custom, sealed_seed)",
            "-    summary = {'study': STUDY, 'schema': 'genesis-b20r141-ara-zoo-v1', 'verdict': v, 'failed': failed,",
            "+    summary = {'study': STUDY, 'schema': 'genesis-b20r167-ara-zoo-v1', 'verdict': v, 'failed': failed,",
        ])


class Freshness(unittest.TestCase):
    def test_the_clause(self):
        envs = [i for i, _ in S.environments()]
        rehearsal = [i for i, _ in TEST_ENVS]
        self.assertTrue(S.freshness(envs, True, False, S.SEALED_SEED))             # the registered run
        self.assertFalse(S.freshness(envs, True, True, S.SEALED_SEED))             # registered on a custom list
        self.assertFalse(S.freshness(rehearsal, False, True, S.SEALED_SEED))       # a custom list at the sealed seed
        self.assertTrue(S.freshness(rehearsal, False, True, TEST_SEED))            # a rehearsal
        self.assertFalse(S.freshness(envs + [S.INDEX0 - 1], True, False, S.SEALED_SEED))   # an index below INDEX0


class RegisteredPath(unittest.TestCase):
    """The path B20_R141's tests never ran: `main` as a registered run, with the output, the sealed seed and the
    environments redirected to rehearsal ones. Its validity must hold."""

    def test_a_registered_run_is_valid(self):
        import b20r33_strong_baseline_audit as R33
        with tempfile.TemporaryDirectory() as d, mock.patch.object(S, 'OUTPUT', Path(d)), \
                mock.patch.object(S, 'SEALED_SEED', TEST_SEED), \
                mock.patch.object(S, 'environments', lambda: list(TEST_ENVS)), \
                mock.patch.object(R33, 'pinned_core', lambda: 1):
            self.assertEqual(S.main([d], registered=True, sealed_seed=TEST_SEED), 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
            with self.assertRaises(SystemExit):                    # any other output is refused when registered
                S.main([str(Path(d) / 'elsewhere')], registered=True, sealed_seed=TEST_SEED)
        self.assertEqual(s['validity'], {'wellformed': True, 'budget': True, 'judge': True, 'fresh': True})
        self.assertTrue(s['valid'])
        self.assertNotEqual(s['verdict'], 'INVALID')
        self.assertEqual(sorted(int(i) for i in s['rows']), [i for i, _ in TEST_ENVS])


def synthetic(good=True, blind_equal=False, random_diag=False, control_release=False):
    """Rows, ledger and keys for the analysis (B20_R141's, `test_ara_zoo_study.synthetic`)."""
    rows, ledger, keys = {}, [], {}
    i = 0
    for c in Z.CLASSES:
        for r in range(S.PER_DEFECT if c in Z.DEFECTS else S.PER_CONTROL):
            loc = Z.LOCATION[c]
            diag = loc if (good and not random_diag) else ['information', 'search', 'evaluation', 'NONE'][(i + r) % 4]
            rows[i] = {'class': c}
            for arm in S.ARMS:
                rows[i][arm] = {'diagnosis': diag if arm.startswith('ara') else None, 'spent': 1000, 'budget': 36000}
            keys[i] = {'class': c, 'location': loc}
            if c in Z.DEFECTS:
                for arm, g in (('ara', 0.6 + 0.01 * r), ('ara2', 0.5 + 0.01 * r),
                               ('blind2', (0.5 + 0.01 * r) if blind_equal else (0.4 if r % 3 == 0 else 0.0)),
                               ('blind', 0.55), ('tuning', 0.0 if c in ('GLOBAL_ONLY', 'FUSION_NEEDED') else 0.3)):
                    if g > 0:
                        ledger.append({'index': i, 'arm': arm, 'promoted': True, 'gain': g, 'failed': None,
                                       'variant': copy.deepcopy(Z.Environment(1, 2, 'GLOBAL_ONLY').remedy())})
            elif control_release and r < 3:
                ledger.append({'index': i, 'arm': 'ara2', 'promoted': True, 'gain': 0.1, 'failed': None,
                               'variant': copy.deepcopy(Z.Environment(1, 2, 'GLOBAL_ONLY').remedy())})
            i += 1
    return rows, ledger, keys


class Analysis(unittest.TestCase):
    """B20_R141's analysis tests, against this script's copy of the functions."""

    def test_a_calibrated_ara_passes(self):
        rows, ledger, keys = synthetic()
        res = S.analyse(rows, ledger, keys)
        self.assertEqual(S.verdict(True, res, S.check_promoted(ledger)), ('ARA_CALIBRATED', []))
        self.assertEqual(S.verdict(False, res, [])[0], 'INVALID')

    def test_each_failure_condition(self):
        res = S.analyse(*synthetic(random_diag=True))
        self.assertIn('A', S.verdict(True, res, [])[1])
        res = S.analyse(*synthetic(blind_equal=True))
        self.assertEqual(S.verdict(True, res, [])[1], ['D'])
        res = S.analyse(*synthetic(control_release=True))
        self.assertIn('S', S.verdict(True, res, [])[1])
        self.assertEqual(S.verdict(True, S.analyse(*synthetic()), [{'index': 0}])[1], ['C'])


class EndToEnd(unittest.TestCase):
    def run_once(self, d, slice_s):
        with mock.patch.object(S, 'SLICE_S', slice_s):
            return S.main([d], registered=False, envs=TEST_ENVS, sealed_seed=TEST_SEED)

    def test_runs_pauses_and_resumes_to_the_same_result(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(self.run_once(a, 10 ** 6), 0)
            codes = []
            while True:
                codes.append(self.run_once(b, 0.5))
                if codes[-1] == 0:
                    break
                self.assertLessEqual(len(codes), len(TEST_ENVS) * len(S.ARMS) + 1)    # at least one arm per slice
            self.assertIn(S.PAUSED, codes)
            sa = json.loads((Path(a) / 'summary.json').read_text())
            sb = json.loads((Path(b) / 'summary.json').read_text())
            strip = lambda s: {k: v for k, v in s.items() if k not in ('rows', 'code_identity')}
            self.assertEqual(strip(sa), strip(sb))
            self.assertTrue(sa['valid'])
            self.assertEqual(len(sa['rows']), len(TEST_ENVS))


if __name__ == '__main__':
    unittest.main()
