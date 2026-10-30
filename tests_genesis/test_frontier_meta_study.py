"""B20_R163 (F6)'s design (`scripts/b20r163_frontier_meta.py`), checked before it runs, without generating any of its
sealed worlds: a fresh sealed seed; families unlike development, the test suite and F3; the pins; the verdict rules
on synthetic rows; and end to end on worlds of ANOTHER seed at small budgets, the study runs, pauses at its slice
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
import b20r163_frontier_meta as S  # noqa: E402
import b20r156_frontier_worlds as F3  # noqa: E402
from genesis.frontier import meta as MT  # noqa: E402
from genesis.frontier import world as W  # noqa: E402

PREREGISTRATION = '77d725d'         # the commit that preregistered the script


def digest_at(commit, rel):
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r163_frontier_meta.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        if PREREGISTRATION:
            at = {m: digest_at(PREREGISTRATION, 'src/genesis/frontier/' + m) for m in S.PINNED}
            if all(v is not None for v in at.values()):
                self.assertEqual(at, S.PINNED)
        self.assertEqual(set(S.PINNED), set(S.MODULES))
        dev = (4, 0.02, tuple(W.TYPES))
        f3 = {(v['problems'], v['sigma'], tuple(v['types'])) for v in F3.FAMILIES.values()}
        for fam, spec in S.FAMILIES.items():
            sig = (spec['problems'], spec['sigma'], tuple(spec['types']))
            self.assertNotEqual(sig, dev, fam)
            self.assertNotIn(sig, f3, fam)
        ws = S.worlds()
        self.assertEqual(len(ws), 2 * (S.WORLDS_PER_FAMILY + S.NULLS_PER_FAMILY))
        seeds = {w[2] for w in ws} | {S.meta_world()[2]}
        self.assertEqual(len(seeds), len(ws) + 1)
        self.assertFalse(seeds & ({101, 202} | set(range(1001, 1009)) | {w[2] for w in F3.worlds()}))
        self.assertEqual(S.extra_budget(144000, 24), 6000)
        self.assertEqual(S.extra_budget(144005, 24), 6000)


def synthetic(gap_p_d, gap_p_d0):
    rows = {}
    for k, fam, seed, null in S.worlds():
        base = 0.6 + 0.01 * (hash(k) % 7)
        vals = {'D': base, 'D0': base + gap_p_d - gap_p_d0, 'P': base + gap_p_d}
        for i, arm in enumerate(S.ARMS):
            v = vals[arm] + 0.0005 * (hash((k, arm)) % 3)
            rows[(k, arm)] = {'value': None if null else v, 'total': 0.0 if null else v, 'spent': S.B,
                              'budget': S.B}
    return rows


class Analysis(unittest.TestCase):
    def test_verdicts(self):
        good = S.analyse(synthetic(0.05, 0.08))
        self.assertEqual(S.verdict(True, good, False), 'SELF_IMPROVED')
        self.assertEqual(good['S1']['label'], 'CONFIG_BETTER')
        self.assertEqual(S.verdict(False, good, False), 'INVALID')
        none = S.analyse(synthetic(-0.03, 0.0))
        self.assertEqual(S.verdict(True, none, False), 'NOT_SHOWN')
        self.assertEqual(none['S1']['label'], 'TIE')
        self.assertEqual(S.verdict(True, none, True), 'NOT_SHOWN (NOTHING_PROMOTED)')
        small = S.analyse(synthetic(0.01, 0.01))                 # better, but not materially
        self.assertEqual(S.verdict(True, small, False), 'NOT_SHOWN')


class EndToEnd(unittest.TestCase):
    META = ('t-meta', 'Ma', 777201, False)
    WORLDS = [('t-0', 'Ha', 777202, False), ('t-1', 'Hb', 777203, False), ('t-null', 'Ha', 777204, True)]
    KW = dict(registered=False, b_in=600, meta_budget=2400, budget=400)

    def test_runs_pauses_and_resumes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(S.main([a], world_list=self.WORLDS, meta=self.META, **self.KW), 0)
            codes = []
            with mock.patch.object(S, 'SLICE_S', -1):              # each slice makes one new run, then pauses
                while not codes or codes[-1] != 0:
                    codes.append(S.main([b], world_list=self.WORLDS, meta=self.META, **self.KW))
                    self.assertLess(len(codes), 20)
            self.assertIn(S.PAUSED, codes)
            ra = sorted((Path(a) / 'rows.jsonl').read_text().splitlines())
            rb = sorted((Path(b) / 'rows.jsonl').read_text().splitlines())
            self.assertEqual(ra, rb)
            s = json.loads((Path(a) / 'summary.json').read_text())
            ms = json.loads((Path(a) / 'meta.json').read_text())
        self.assertTrue(s['nulls_ok'] and s['spent_ok'] and ms['on_grid'])
        self.assertGreater(ms['c_meta'], 0)
        self.assertEqual(s['S4']['extra_budget_per_world'], S.extra_budget(ms['c_meta'], 2))
        rows = [json.loads(x) for x in ra]
        budgets = {r['arm']: r['budget'] for r in rows}
        self.assertEqual(budgets['D'], 400 + S.extra_budget(ms['c_meta'], 2))
        self.assertEqual(budgets['P'], budgets['D0'])
        self.assertTrue(all(ms['promoted'][k] in v for k, v in MT.GRID.items()))

    def test_the_registered_run_refuses_other_outputs_and_other_pins(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(SystemExit):
                S.main([a])
        with mock.patch.object(S, 'PINNED', {'engine.py': 'x'}):
            with self.assertRaises(SystemExit):
                S.main([str(ROOT / 'evidence' / 'frontier_meta_b20r163')])



R163 = ROOT / 'evidence' / 'frontier_meta_b20r163'


@unittest.skipUnless((R163 / 'summary.json').exists(), 'B20_R163 has not been recorded')
class RecordB20R163(unittest.TestCase):
    """The record of B20_R163 (F6) on its evidence: the script; the meta-search's record; the matched budgets;
    validity and the analysis recomputed from the rows; one evaluation re-run gives the same row."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R163 / 'summary.json').read_text())
        cls.meta = json.loads((R163 / 'meta.json').read_text())
        cls.rows = {}
        for line in (R163 / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['world'], r['arm'])] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r163_frontier_meta.py').read_bytes()).hexdigest(),
                         'e71bfb69365bb5fa4a1129e59c13637ce048ab0cc15dbdaa4ddd8878a620777f')

    def test_the_budgets_and_validity(self):
        extra = S.extra_budget(self.meta['c_meta'], 24)
        self.assertEqual(self.s['S4']['extra_budget_per_world'], extra)
        for (w, a), r in self.rows.items():
            self.assertEqual(r['budget'], S.B + (extra if a == 'D' else 0))
        nulls = all(self.rows[(k, a)]['total'] == 0.0 for k, f, sd, null in S.worlds() if null for a in S.ARMS)
        spent = all(r['spent'] >= r['budget'] - S.QUANTUM - 1 for r in self.rows.values())
        self.assertEqual((nulls, spent), (self.s['nulls_ok'], self.s['spent_ok']))
        self.assertTrue(self.meta['on_grid'])
        self.assertTrue(self.s['valid'] and self.s['pins_ok'])

    def test_the_analysis_recomputes(self):
        res = S.analyse(self.rows)
        for k in ('P1', 'S1', 'S2'):
            self.assertAlmostEqual(res[k]['p'], self.s['results'][k]['p'])
            self.assertAlmostEqual(res[k]['mean'], self.s['results'][k]['mean'])
        self.assertEqual(S.verdict(self.s['valid'], res, self.meta['nothing_promoted']), self.s['verdict'])

    def test_one_evaluation_reruns_identically(self):
        idx, (key, fam, seed, null) = next((i, w) for i, w in enumerate(S.worlds()) if not w[3])
        r = S.run_one(fam, seed, null, 'P', idx, self.meta['promoted'], S.B)
        self.assertEqual((r['total'], r['spent']), (self.rows[(key, 'P')]['total'], self.rows[(key, 'P')]['spent']))


if __name__ == '__main__':
    unittest.main()
