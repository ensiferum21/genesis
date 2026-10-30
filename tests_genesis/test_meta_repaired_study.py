"""B20_R175 (F6b)'s design (`scripts/b20r175_meta_repaired.py`), checked before it runs, without generating any of
its sealed worlds: a fresh sealed seed; F6's families; the bracket's schedule and the members' inner budget; the
pins; the verdict rules on synthetic rows; and end to end on worlds of ANOTHER seed at small budgets, the study
runs, pauses at its slice limit and resumes to the same rows."""
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
import b20r175_meta_repaired as S  # noqa: E402
import b20r163_frontier_meta as F6  # noqa: E402
from genesis.frontier import meta as MT  # noqa: E402

PREREGISTRATION = '7878cdb'         # the commit that preregistered the script
SHA256 = 'b5c957f6669b078b3dc1a4bf19ef4a38fe1b16d31b5b8fa54bb5096fade178ba'


def digest_at(commit, rel):
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_the_script_is_the_preregistered_one(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r175_meta_repaired.py').read_bytes()).hexdigest(),
                         SHA256)
        self.assertEqual(digest_at(PREREGISTRATION, 'scripts/b20r175_meta_repaired.py') or SHA256, SHA256)

    def test_constants(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r175_meta_repaired.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        self.assertEqual(S.FAMILIES, F6.FAMILIES)                          # F6's families, new worlds
        self.assertEqual((S.F6_B_IN, S.F6_META_BUDGET, S.F6_META_QUANTUM), (F6.B_IN, F6.META_BUDGET, F6.META_QUANTUM))
        self.assertEqual(S.OUTPUT, ROOT / 'evidence' / 'meta_repaired_b20r175')
        ws, tr = S.worlds(), S.train_worlds()
        self.assertEqual(len(ws), 2 * (S.WORLDS_PER_FAMILY + S.NULLS_PER_FAMILY))
        self.assertEqual(len(tr), S.K_TRAIN)
        seeds = {w[2] for w in ws} | {w[2] for w in tr}
        self.assertEqual(len(seeds), len(ws) + len(tr))
        f6 = {w[2] for w in F6.worlds()} | {F6.meta_world()[2]}
        self.assertFalse(seeds & (f6 | {101, 202, 303} | set(range(990001, 990005))))
        self.assertEqual(S.extra_budget(258000, 24), 10750)

    def test_the_bracket_gives_the_survivor_exactly_the_inner_budget(self):
        br = MT.halving_bracket(S.POOL, S.ETA, S.RUNG)
        self.assertEqual(br['stages'], [(27, 2), (9, 3), (3, 9), (1, 27)])
        self.assertEqual((br['final'] - 1) * S.Q_MEMBER, S.B)             # the 41st quantum finds it finished
        self.assertEqual(S.Q_MEMBER % S.QUANTUM, 0)
        per_member = sum(n * min(r, (br['final'] - 1) - sum(x for _, x in br['stages'][:i]))
                         for i, (n, r) in enumerate(br['stages'])) * S.Q_MEMBER
        self.assertEqual(per_member, 40200)                                # 160,800 over four members

    def test_pins(self):
        self.assertEqual(set(S.MODULES), {p.name for p in (ROOT / 'src/genesis/frontier').glob('*.py')}
                         - {'__init__.py', 'ablation.py', 'multi.py', 'procedure.py'})
        if PREREGISTRATION:
            at = {m: digest_at(PREREGISTRATION, 'src/genesis/frontier/' + m) for m in S.MODULES}
            if all(v is not None for v in at.values()):
                self.assertEqual(at, S.PINNED)
            self.assertEqual(set(S.PINNED), set(S.MODULES))

    def test_the_engine_does_not_import_the_modules_left_unpinned(self):
        for m in S.MODULES:
            text = (ROOT / 'src/genesis/frontier' / m).read_text()
            pat = r'import (ablation|multi|procedure)\b|from \. import .*\b(ablation|multi|procedure)\b'
            self.assertFalse(re.search(pat, text), m)


def synthetic(pk_d0, pk_d24, pk_p1):
    rows = {}
    for k, fam, seed, null in S.worlds():
        base = 0.6 + 0.01 * (hash(k) % 7)
        vals = {'D0': base, 'PK': base + pk_d0, 'D24': base + pk_d0 - pk_d24, 'P1': base + pk_d0 - pk_p1}
        for arm in S.ARMS:
            v = vals[arm] + 0.0005 * (hash((k, arm)) % 3)
            rows[(k, arm)] = {'value': None if null else v, 'total': 0.0 if null else v, 'spent': S.B,
                              'budget': S.B}
    return rows


class Analysis(unittest.TestCase):
    def test_verdicts(self):
        good = S.analyse(synthetic(0.05, 0.03, 0.04))
        self.assertEqual(S.verdict(True, good, False), 'CONFIG_TRANSFERS')
        self.assertEqual(good['S1']['label'], 'PAYS')
        self.assertEqual(good['S2']['label'], 'REPAIR_BETTER')
        self.assertAlmostEqual(good['S7_break_even_worlds'], 24 * good['S4']['mean'] / good['P1']['mean'])
        self.assertEqual(S.verdict(False, good, False), 'INVALID')
        costly = S.analyse(synthetic(0.05, -0.1, 0.0))
        self.assertEqual(S.verdict(True, costly, False), 'CONFIG_TRANSFERS')
        self.assertEqual(costly['S1']['label'], 'DOES_NOT_PAY')
        self.assertEqual(costly['S2']['label'], 'TIE')
        self.assertGreater(costly['S7_break_even_worlds'], 24)
        none = S.analyse(synthetic(0.0, -0.15, 0.0))
        self.assertEqual(S.verdict(True, none, True), 'NOT_SHOWN (NOTHING_PROMOTED)')
        self.assertIsNone(none['S7_break_even_worlds'])
        small = S.analyse(synthetic(0.01, -0.1, 0.0))                     # better, but not materially
        self.assertEqual(S.verdict(True, small, False), 'NOT_SHOWN')


class EndToEnd(unittest.TestCase):
    TRAIN = [('t-a', 'Ma', 777301, False), ('t-b', 'Ma', 777302, False)]
    WORLDS = [('t-0', 'Ha', 777303, False), ('t-1', 'Hb', 777304, False), ('t-null', 'Ha', 777305, True)]
    KW = dict(registered=False, search_kw=dict(b_in=600, q_member=150, pool=3, eta=3, rung=1),
              f6_kw=dict(b_in=600, budget=2400, quantum=300), budget=600)

    def test_runs_pauses_and_resumes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(S.main([a], train=self.TRAIN, world_list=self.WORLDS, **self.KW), 0)
            codes = []
            with mock.patch.object(S, 'SLICE_S', -1):              # each slice makes one new run, then pauses
                while not codes or codes[-1] != 0:
                    codes.append(S.main([b], train=self.TRAIN, world_list=self.WORLDS, **self.KW))
                    self.assertLess(len(codes), 20)
            self.assertIn(S.PAUSED, codes)
            ra = sorted((Path(a) / 'rows.jsonl').read_text().splitlines())
            rb = sorted((Path(b) / 'rows.jsonl').read_text().splitlines())
            self.assertEqual(ra, rb)
            s = json.loads((Path(a) / 'summary.json').read_text())
            ms = json.loads((Path(a) / 'search.json').read_text())
            f6 = json.loads((Path(a) / 'f6.json').read_text())
            self.assertEqual(ms, json.loads((Path(b) / 'search.json').read_text()))
        self.assertTrue(s['nulls_ok'] and s['spent_ok'] and s['grid_ok'] and s['as_scheduled'])
        self.assertEqual(ms['stages'], [[3, 2], [1, 3]])
        self.assertEqual(len(ms['branches']), 3)
        top = max(ms['branches'], key=lambda r: r['t'])
        self.assertTrue(all(x + S.QUANTUM > 600 for x in top['member_spent']))
        self.assertEqual(ms['c_k'], ms['c_search'] + ms['guard']['c_guard'])
        self.assertEqual(ms['promoted'], top['params'] if ms['guard']['promote'] else MT.DEFAULT)
        self.assertEqual(len(ms['guard']['runs']['survivor']), 2)
        rows = [json.loads(x) for x in ra]
        budgets = {r['arm']: r['budget'] for r in rows}
        self.assertEqual(budgets['D24'], 600 + S.extra_budget(ms['c_k'], 2))
        self.assertEqual({budgets[a] for a in ('PK', 'P1', 'D0')}, {600})
        self.assertGreater(f6['c_meta'], 0)
        self.assertTrue(S.on_grid(f6['promoted']))

    def test_the_registered_run_refuses_other_outputs_and_other_pins(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(SystemExit):
                S.main([a])
        with mock.patch.object(S, 'PINNED', {'engine.py': 'x'}):
            with self.assertRaises(SystemExit):
                S.main([str(S.OUTPUT)])


if __name__ == '__main__':
    unittest.main()
