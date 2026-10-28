"""B20_R156 (F3)'s design (`scripts/b20r156_frontier_worlds.py`), checked before it runs, without generating any of
its sealed worlds: a fresh sealed seed; held-out families unlike development; the pins; the verdict rules on
synthetic rows; and end to end on worlds of ANOTHER seed at a small budget, the study runs, pauses at its slice
limit and resumes to the same rows."""
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
import b20r156_frontier_worlds as S  # noqa: E402
from genesis.frontier import world as W  # noqa: E402


def digest_at(commit, rel):
    """The SHA-256 of a file as committed at `commit` (None without git): the pins are checked against the
    preregistration commit, because the branch head may move on after a study is preregistered (the study itself
    runs from a clean worktree of that commit, where its own run-time pin check applies)."""
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r156_frontier_worlds.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        at = {m: digest_at('4a7e193', 'src/genesis/frontier/' + m) for m in S.PINNED}       # the preregistration commit
        if all(v is not None for v in at.values()):
            self.assertEqual(at, S.PINNED)
        for fam, spec in S.FAMILIES.items():
            self.assertTrue(spec['problems'] != 4 or spec['sigma'] != 0.02 or tuple(spec['types']) != W.TYPES, fam)
        ws = S.worlds()
        self.assertEqual(len(ws), 3 * (S.WORLDS_PER_FAMILY + S.NULLS_PER_FAMILY))
        self.assertEqual(sum(1 for w in ws if w[3]), 3 * S.NULLS_PER_FAMILY)
        self.assertFalse({w[2] for w in ws} & set(range(1001, 1009)))
        self.assertEqual(len({w[2] for w in ws}), len(ws))


def synthetic(gap):
    rows = {}
    for k, fam, seed, null in S.worlds():
        for i, arm in enumerate(S.ARMS):
            base = 0.6 + 0.01 * (hash(k) % 7)
            v = base + (gap if arm == 'F' else 0.0) + (0.001 * i if arm != 'F' else 0.0)
            rows[(k, arm)] = {'value': None if null else v, 'total': 0.0 if null else v, 'spent': S.BUDGET,
                              'coverage': {'n': 10, 'hits': 9}, 'recomb': {'planted': 1, 'opened': 1}}
    return rows


class Analysis(unittest.TestCase):
    def test_verdicts(self):
        good = S.analyse(synthetic(0.05))
        self.assertEqual(S.verdict(True, good)[0], 'FRONTIER_BETTER')
        self.assertEqual(S.verdict(False, good)[0], 'INVALID')
        none = S.analyse(synthetic(0.0))
        self.assertEqual(S.verdict(True, none)[0], 'NOT_SHOWN')
        small = S.analyse(synthetic(0.01))                     # beats every comparator, but not materially
        self.assertEqual(S.verdict(True, small)[0], 'NOT_SHOWN')
        self.assertAlmostEqual(good['S2']['coverage'], 0.9)


class EndToEnd(unittest.TestCase):
    WORLDS = [('t-0', 'Fa', 777101, False), ('t-1', 'Fb', 777102, False), ('t-null', 'Fc', 777103, True)]

    def test_runs_pauses_and_resumes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(S.main([a], registered=False, budget=400, world_list=self.WORLDS), 0)
            codes = []
            with mock.patch.object(S, 'SLICE_S', -1):              # each slice makes one new run, then pauses
                while not codes or codes[-1] != 0:
                    codes.append(S.main([b], registered=False, budget=400, world_list=self.WORLDS))
                    self.assertLess(len(codes), 40)
            self.assertIn(S.PAUSED, codes)
            read = lambda d: {(r['world'], r['arm']): r for r in
                              map(json.loads, (Path(d) / 'rows.jsonl').read_text().splitlines())}
            rows_a, rows_b = read(a), read(b)
            self.assertEqual(rows_a, rows_b)
            self.assertEqual(len(rows_a), len(self.WORLDS) * len(S.ARMS))
            s = json.loads((Path(a) / 'summary.json').read_text())
            self.assertTrue(s['nulls_ok'] and s['spent_ok'])


R156 = ROOT / 'evidence' / 'frontier_worlds_b20r156'


@unittest.skipUnless((R156 / 'summary.json').exists(), 'B20_R156 has not been recorded')
class RecordB20R156(unittest.TestCase):
    """The record of B20_R156 (F3) on its evidence: the amended script; the worlds; validity recomputed from the rows;
    the analysis and the verdict recomputed; one world re-run gives the same row."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R156 / 'summary.json').read_text())
        cls.rows = {}
        for line in (R156 / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['world'], r['arm'])] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r156_frontier_worlds.py').read_bytes()).hexdigest(),
                         '9ae034dbf8bde4cd9d2eba75807c16ef869917568cf4ffd5a8d2b2f20566353a')

    def test_the_worlds_and_validity(self):
        self.assertEqual(self.s['worlds'], [list(w) for w in S.worlds()])
        self.assertEqual(len(self.rows), len(S.worlds()) * len(S.ARMS))
        nulls = all(self.rows[(k, a)]['total'] == 0.0 for k, f, sd, null in S.worlds() if null for a in S.ARMS)
        spent = all(r['spent'] >= S.BUDGET - S.QUANTUM - 1 for r in self.rows.values())
        self.assertEqual((nulls, spent), (self.s['nulls_ok'], self.s['spent_ok']))
        self.assertTrue(self.s['valid'] and self.s['pins_ok'])

    def test_the_analysis_recomputes(self):
        res = S.analyse(self.rows)
        for c in S.PRIMARY:
            for k in ('label', 'p_holm', 'mean'):
                got, rec = res['P1'][c][k], self.s['results']['P1'][c][k]
                self.assertAlmostEqual(got, rec) if isinstance(got, float) else self.assertEqual(got, rec)
        self.assertEqual(S.verdict(self.s['valid'], res)[0], self.s['verdict'])
        self.assertEqual(res['S2']['hits'], self.s['results']['S2']['hits'])

    def test_one_world_reruns_identically(self):
        key, fam, seed, null = next(w for w in S.worlds() if not w[3])
        r = S.run_one(fam, seed, null, 'F', 0)
        rec = self.rows[(key, 'F')]
        self.assertEqual((r['total'], r['spent'], r['branches']), (rec['total'], rec['spent'], rec['branches']))


if __name__ == '__main__':
    unittest.main()
