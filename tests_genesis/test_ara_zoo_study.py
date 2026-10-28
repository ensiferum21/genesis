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


R141 = ROOT / 'evidence' / 'ara_zoo_b20r141'


@unittest.skipUnless((R141 / 'summary.json').exists(), 'B20_R141 has not been recorded')
class RecordB20R141(unittest.TestCase):
    """The record of B20_R141 on its evidence: the script; the environments; validity recomputed from the rows; the
    analysis, experiment C and the verdict recomputed from the saved rows, ledger and keys; the environments
    regenerated from the sealed seed and every judged submission re-judged.

    Drafted before the study ran (`docs/handoff/RECORD_TEST_DRAFTS.md`, 28 Oct 2026, 04:55 SGT). One assertion of
    the draft is changed, and the change is disclosed in `docs/checkpoints/B20_R141_RECORD.md`: the draft asserted
    that the run was valid. It is not. The script's freshness clause is False in every registered run (a defect of
    the script, `test_the_freshness_defect`), so the verdict is INVALID by the preregistered rule, and these tests
    assert that. The two re-derivation tests were added at recording."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R141 / 'summary.json').read_text())
        cls.done = {}
        for line in (R141 / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.done[(r['index'], r['arm'])] = r
        entries = {}
        for line in (R141 / 'ledger.jsonl').read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                entries[(e['index'], e['arm'])] = e
        cls.ledger = [entries[k] for k in sorted(entries)]

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r141_ara_zoo.py').read_bytes()).hexdigest(),
                         'ccec4633599faa628a26c8ca4aeeaa6061a8e857a114bc6b24d46875025660bf')

    def test_the_environments_and_validity(self):
        envs = S.environments()
        self.assertEqual(sorted(int(i) for i in self.s['rows']), sorted(i for i, _ in envs))
        self.assertEqual(len(self.done), len(envs) * len(S.ARMS))
        self.assertTrue(all(r['spent'] <= r['budget'] + 1e-9 for r in self.done.values()))
        # The draft asserted validity here. The run is INVALID: only the freshness clause failed.
        self.assertEqual(self.s['validity'], {'wellformed': True, 'budget': True, 'judge': True, 'fresh': False})
        self.assertFalse(self.s['valid'])
        self.assertEqual((self.s['verdict'], self.s['failed']), ('INVALID', []))

    def test_the_freshness_defect(self):
        """`main` replaces `envs` by the registered list (`envs = envs or environments()`) before the freshness
        clause asks `envs is None`, so in a registered run at the sealed seed the clause is False whatever the
        indices. What it was meant to establish did hold: the registered environments, at indices from INDEX0,
        none used by the development look."""
        src = (ROOT / 'scripts' / 'b20r141_ara_zoo.py').read_text()
        self.assertLess(src.index('envs = envs or environments()'),
                        src.index('fresh = all(i >= INDEX0 for i in rows)'))
        envs, registered, sealed_seed = S.environments(), True, S.SEALED_SEED     # the registered run's values
        self.assertFalse(sealed_seed != S.SEALED_SEED or envs is None or not registered)
        rows = sorted(int(i) for i in self.s['rows'])
        self.assertEqual(rows, sorted(i for i, _ in envs))
        self.assertTrue(all(i >= S.INDEX0 for i in rows))
        dev = json.loads((ROOT / 'evidence/ara1_development/devlook.json').read_text())
        self.assertFalse(set(rows) & {r['index'] for r in dev['rows']})

    def test_the_analysis_recomputes(self):
        rows = {int(i): r for i, r in self.s['rows'].items()}
        keys = {int(i): k for i, k in self.s['keys'].items()}
        res = S.analyse(rows, self.ledger, keys)
        for x in ('A', 'B', 'D', 'S'):
            self.assertEqual(res[x]['pass'], self.s[x]['pass'], x)
        self.assertEqual((res['A']['localised'], res['A']['of']), (self.s['A']['localised'], self.s['A']['of']))
        c = S.check_promoted(self.ledger)
        self.assertEqual(c, self.s['C_failures'])
        self.assertEqual(list(S.verdict(self.s['valid'], res, c)), [self.s['verdict'], self.s['failed']])
        # Descriptive only, not the verdict: had validity held, every experiment would have passed.
        self.assertEqual(S.verdict(True, res, c), ('ARA_CALIBRATED', []))
        self.assertEqual(res['mean_gain_defects'], self.s['mean_gain_defects'])

    def test_the_environments_regenerate_and_every_submission_rejudges(self):
        """Every environment from the sealed seed: its key, and for every judged submission its oracle, its range,
        and its sealed gain from re-executing the submitted variant at the arm's seed (the index)."""
        from genesis.architecture import graph as G
        from genesis.architecture import judge as J
        H = J.Harness(sealed_seed=S.SEALED_SEED)
        for index, cls in S.environments():
            H.open(index, cls)
            self.assertEqual(H.key(index), self.s['keys'][str(index)])
        for e in self.ledger:
            env = H._env(e['index'])
            rng = H._range(env)
            self.assertAlmostEqual(env.oracle('sealed'), e['oracle'], places=9)
            self.assertAlmostEqual(rng, e['range'], places=9)
            inc = G.execute(env.incumbent, env.view(), 'dev_a', seed=e['index'])
            var = G.execute(e['variant'], env.view(), 'dev_a', seed=e['index'])
            diff = H.sealed_value(e['index'], var['policy']) - H.sealed_value(e['index'], inc['policy'])
            gain = diff / rng if rng > 1e-12 else 0.0                             # the judge's convention
            self.assertAlmostEqual(gain, e['gain'], places=9, msg=(e['index'], e['arm']))
            if e['promoted']:
                self.assertIsNone(e['failed'])
                self.assertGreaterEqual(gain, J.MATERIAL)


if __name__ == '__main__':
    unittest.main()
