"""B20_R141's design (`scripts/b20r141_ara_zoo.py`), checked before it runs, without touching its environments.

Fresh indices and a fresh sealed seed; 95 environments, 10 per defect class and 15 per control; the pinned judge;
the analysis on synthetic rows: a calibrated ARA passes A-D and S, and each failure condition fails its experiment;
experiment C catches a malformed promoted variant; and end to end on three environments of ANOTHER sealed seed, the
study runs, pauses at its slice limit and resumes to the same result."""
import copy
import hashlib
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
import b20r141_ara_zoo as S  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

TEST_SEED = 777001                         # never the study's
TEST_ENVS = [(30000, 'GLOBAL_ONLY'), (30002, 'EVAL_NOISY'), (30003, 'DECOY')]


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('b20r*.py') if p.name != 'b20r141_ara_zoo.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        dev = json.loads((ROOT / 'evidence/ara1_development/devlook.json').read_text())
        used = {r['index'] for r in dev['rows']}
        envs = S.environments()
        self.assertFalse({i for i, _ in envs} & used)
        self.assertTrue(all(i >= S.INDEX0 for i, _ in envs))
        self.assertEqual(len(envs), 5 * S.PER_DEFECT + 3 * S.PER_CONTROL)
        for c in Z.CLASSES:
            self.assertEqual(sum(1 for _, x in envs if x == c), S.PER_DEFECT if c in Z.DEFECTS else S.PER_CONTROL)
        self.assertEqual(hashlib.sha256((ROOT / 'src/genesis/architecture/judge.py').read_bytes()).hexdigest(),
                         S.ARA_JUDGE_SHA256)


def synthetic(good=True, blind_equal=False, random_diag=False, control_release=False):
    """Rows, ledger and keys for the analysis."""
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

    def test_c_catches_a_malformed_promoted_variant(self):
        rows, ledger, keys = synthetic()
        bad = copy.deepcopy(ledger)
        bad[0]['variant']['nodes']['out']['params'] = {'x': 1}
        self.assertTrue(S.check_promoted(bad))
        self.assertEqual(S.check_promoted(ledger), [])


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
            self.assertEqual({i: {k: {x: y for x, y in v.items() if x != 'cpu'} if isinstance(v, dict) else v
                                  for k, v in r.items()} for i, r in sa['rows'].items()},
                             {i: {k: {x: y for x, y in v.items() if x != 'cpu'} if isinstance(v, dict) else v
                                  for k, v in r.items()} for i, r in sb['rows'].items()})
            self.assertEqual(len(sa['rows']), len(TEST_ENVS))


if __name__ == '__main__':
    unittest.main()
