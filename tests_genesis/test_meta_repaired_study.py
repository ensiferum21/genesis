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



R175 = ROOT / 'evidence' / 'meta_repaired_b20r175'


def at_commit(commit, files, code, timeout=7200):
    """Run Python `code` in a temporary worktree of `commit` with `files` ({path in the worktree: source}) copied in;
    `code` writes its answer as JSON to `answer.json` in the worktree, which is returned."""
    import shutil
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        wt = Path(d) / 'wt'
        subprocess.run(['git', '-C', str(ROOT), 'worktree', 'add', '--detach', str(wt), commit], check=True,
                       capture_output=True)
        try:
            for rel, src in files.items():
                (wt / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, wt / rel)
            out = subprocess.run([sys.executable, '-c', code], cwd=wt, capture_output=True, text=True, timeout=timeout)
            if out.returncode != 0:
                raise AssertionError(out.stderr[-3000:])
            return json.loads((wt / 'answer.json').read_text())
        finally:
            subprocess.run(['git', '-C', str(ROOT), 'worktree', 'remove', '--force', str(wt)], capture_output=True)


@unittest.skipUnless((R175 / 'summary.json').exists(), 'B20_R175 has not been recorded')
class RecordB20R175(unittest.TestCase):
    """The record of B20_R175 on its evidence: the script; the bracket's schedule, the guard and the promotion; the
    rows complete and the arms' budgets; validity, the analysis and the verdict recomputed in this tree; then, at the
    preregistration commit: main re-run on the saved search and rows to the same summary, the bracket, the guard and
    F6's procedure replayed to the same records, and the first and last worlds' runs re-executed to the same rows."""
    DIR, KW, OUT = R175, {}, 'evidence/meta_repaired_b20r175'

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.ms = json.loads((cls.DIR / 'search.json').read_text())
        cls.f6 = json.loads((cls.DIR / 'f6.json').read_text())
        cls.rows = {}
        for line in (cls.DIR / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['world'], r['arm'])] = r

    def ws(self):
        wl = self.KW.get('world_list')
        return [tuple(w) for w in wl] if wl is not None else S.worlds()

    def test_the_script(self):
        if self.DIR != R175:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r175_meta_repaired.py').read_bytes()).hexdigest(),
                         SHA256)

    def test_the_search_the_guard_and_the_promotion(self):
        ms, sk = self.ms, self.KW.get('search_kw', {})
        b_in = sk.get('b_in', S.B)
        br = MT.halving_bracket(sk.get('pool', S.POOL), sk.get('eta', S.ETA), sk.get('rung', S.RUNG))
        self.assertEqual([tuple(x) for x in ms['stages']], br['stages'])
        self.assertEqual(len(ms['branches']), sk.get('pool', S.POOL))
        self.assertTrue(ms['as_scheduled'])
        top = max(ms['branches'], key=lambda r: (r['t'], -r['branch']))
        self.assertEqual(top['params'], ms['survivor'])
        self.assertTrue(all(x + S.QUANTUM > b_in for x in top['member_spent']))
        g, k = ms['guard'], len(self.KW.get('train') or S.train_worlds())
        for which in ('survivor', 'defaults'):
            self.assertEqual(len(g['runs'][which]), k)
            self.assertAlmostEqual(g['means'][which], sum(r['value'] for r in g['runs'][which]) / k)
        self.assertEqual(g['promote'], g['means']['survivor'] > g['means']['defaults'])
        self.assertEqual(ms['promoted'], ms['survivor'] if g['promote'] else MT.DEFAULT)
        self.assertEqual(ms['nothing_promoted'], not g['promote'])
        self.assertEqual(ms['c_k'], ms['c_search'] + g['c_guard'])
        self.assertEqual(g['c_guard'], sum(r['spent'] for v in g['runs'].values() for r in v))

    def test_validity_and_the_analysis_recompute(self):
        ws, budget = self.ws(), self.KW.get('budget', S.B)
        self.assertEqual([list(x) for x in ws], self.s['worlds'])
        self.assertEqual(set(self.rows), {(k, a) for k, f, sd, null in ws for a in S.ARMS})
        extra = S.extra_budget(self.ms['c_k'], sum(1 for w in ws if not w[3]))
        self.assertEqual(extra, self.s['S6']['extra_budget_per_world'])
        for (k, a), r in self.rows.items():
            self.assertEqual(r['budget'], budget + (extra if a == 'D24' else 0))
        nulls_ok = all(self.rows[(k, a)]['total'] == 0.0 for k, f, sd, null in ws if null for a in S.ARMS)
        guard_runs = [r for v in self.ms['guard']['runs'].values() for r in v]
        spent_ok = all(r['spent'] >= r['budget'] - S.QUANTUM - 1 for r in list(self.rows.values()) + guard_runs)
        grid_ok = S.on_grid(self.ms['promoted']) and S.on_grid(self.f6['promoted'])
        self.assertEqual((nulls_ok, spent_ok, grid_ok), (self.s['nulls_ok'], self.s['spent_ok'], self.s['grid_ok']))
        self.assertEqual(self.s['valid'], nulls_ok and spent_ok and grid_ok and self.s['pins_ok']
                         and self.ms['as_scheduled'])
        res = S.analyse(self.rows, ws)
        self.assertEqual(json.loads(json.dumps(res, sort_keys=True, default=list)), self.s['results'])
        self.assertEqual(S.verdict(self.s['valid'], res, self.ms['nothing_promoted']), self.s['verdict'])

    def test_at_the_preregistration_commit(self):
        files = {f'{self.OUT}/{n}': self.DIR / n for n in ('search.json', 'f6.json', 'rows.jsonl')}
        code = f'''
import json, sys
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
import b20r175_meta_repaired as S
from genesis.frontier import meta as MT
kw = json.loads({json.dumps(json.dumps(self.KW))})
for k in ('world_list', 'train'):
    if k in kw:
        kw[k] = [tuple(w) for w in kw[k]]
rc = S.main(['{self.OUT}'], **(dict(kw, registered=False) if kw else {{}}))
summary = json.load(open('{self.OUT}/summary.json'))
train = kw.get('train') or S.train_worlds()
budget = kw.get('budget', S.B)
ms = S.suite_search(train, **kw.get('search_kw', {{}}))
gd = S.guard(ms['survivor'], train, budget)
f6 = S.f6_search(train[0], **kw.get('f6_kw', {{}}))
ws = kw.get('world_list') or S.worlds()
saved = json.load(open('{self.OUT}/search.json'))
extra = S.extra_budget(saved['c_k'], sum(1 for w in ws if not w[3]))
plan = {{'PK': (saved['promoted'], budget), 'P1': (f6['promoted'], budget), 'D0': (MT.DEFAULT, budget),
        'D24': (MT.DEFAULT, budget + extra)}}
runs = []
for idx in sorted({{0, len(ws) - 1}}):
    key, fam, seed, null = ws[idx]
    for arm in S.ARMS:
        params, bud = plan[arm]
        r = S.run_one(fam, seed, null, arm, idx, params, bud)
        r['world'] = key
        runs.append(r)
json.dump({{'rc': rc, 'summary': summary, 'search': ms, 'guard': gd, 'f6': f6, 'runs': runs}},
          open('answer.json', 'w'), default=list)
'''
        got = at_commit(PREREGISTRATION, files, code)
        self.assertEqual(got['rc'], 0)
        drop = ('code_identity',)
        self.assertEqual({k: v for k, v in got['summary'].items() if k not in drop},
                         {k: v for k, v in self.s.items() if k not in drop})
        for k in ('survivor', 'survivor_value', 'branches', 'stages', 'stages_seen', 'as_scheduled', 'c_search',
                  'outer_spent'):
            self.assertEqual(json.loads(json.dumps(got['search'][k])), self.ms[k], k)
        self.assertEqual(json.loads(json.dumps(got['guard'])), self.ms['guard'])
        self.assertEqual(json.loads(json.dumps(got['f6'])), self.f6)
        for r in got['runs']:
            saved = self.rows[(r['world'], r['arm'])]
            for f in ('total', 'reference', 'value', 'spent', 'budget', 'branches', 'verify_calls'):
                self.assertEqual(r[f], saved[f], (r['world'], r['arm'], f))


if __name__ == '__main__':
    unittest.main()
