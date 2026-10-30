"""B20_R172 (Foundry G4) design tests: fresh, disjoint seeds and families; even spacing of replayed decisions; the
extra budget; the verdict rule; the analysis on synthetic rows; the refusals; and the study run end to end through
its REGISTERED path (registered=True) on rehearsal worlds with the output, pins and budgets redirected (B20_R141's
lesson). Rehearsal worlds use seeds no study uses (889xxx)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r172_state_features as S  # noqa: E402

PREREGISTRATION = '73f8ad4'         # the commit that preregistered the script


def digest_at(commit, rel):
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_pins_at_the_preregistration_commit(self):
        import re
        self.assertEqual(set(S.PINNED), set(S.MODULES))
        if PREREGISTRATION:
            at = {m: digest_at(PREREGISTRATION, 'src/genesis/frontier/' + m) for m in S.PINNED}
            if all(v is not None for v in at.values()):
                self.assertEqual(at, S.PINNED)
            script = digest_at(PREREGISTRATION, 'scripts/b20r172_state_features.py')
            if script is not None:
                self.assertEqual(script, '46e571f4f763ace626a8962bd6e21c103b91f99c2e095e299ee3571677739b33')
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r172_state_features.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))

    def test_worlds_are_fresh_and_disjoint(self):
        import b20r156_frontier_worlds as F3
        import b20r163_frontier_meta as F6
        import b20r170_forecast_calibration as G2
        ws = S.worlds()
        self.assertEqual((len(ws), sum(1 for w in ws if w[3])), (30, 6))
        seeds = {w[2] for w in ws} | {w[2] for w in S.training_worlds()}
        self.assertEqual(len(seeds), 32)
        others = {w[2] for w in F3.worlds()} | {w[2] for w in F6.worlds()} | {w[2] for w in G2.worlds()}
        others |= {F6.meta_world()[2], G2.meta_world()[2]} | set(range(887000, 887100)) | set(range(881000, 881006))
        self.assertFalse(seeds & others)
        specs = list(F3.FAMILIES.values()) + list(F6.FAMILIES.values()) + list(G2.FAMILIES.values())
        for fam, spec in S.FAMILIES.items():
            self.assertNotIn(spec, specs, fam)
        self.assertNotIn(S.SEALED_SEED, (F3.SEALED_SEED, F6.SEALED_SEED, G2.SEALED_SEED))

    def test_spacing_and_extra_budget(self):
        self.assertEqual(S.spaced(list(range(10)), 20), list(range(10)))
        self.assertEqual(S.spaced(list(range(100)), 4), [0, 25, 50, 75])
        self.assertEqual(S.extra_budget(72000), 3000)
        self.assertEqual(S.extra_budget(72009, 24), 3000)

    def test_verdict_and_analysis(self):
        ws = [(f'L-{i}', 'La', 889100 + i, False) for i in range(12)] + [('L-null', 'La', 889199, True)]
        rows = {}
        for i, (k, fam, s, null) in enumerate(ws):
            for arm, v in (('P', 0.86), ('D', 0.84), ('D0', 0.80)):
                rows[(k, arm)] = {'value': v + 0.002 * i * (arm == 'P'), 'cpu_s': 1.0, 'total': 0.0 if null else 1.0}
            if not null:
                rows[(k, 'D0')]['S7'] = {'index': 0.80, 'feature': 0.85 + 0.001 * i}
        r = S.analyse(rows, ws)
        self.assertEqual(r['P1']['label'], 'FEATURE_PAYS')
        self.assertEqual(r['S1']['label'], 'FEATURE_BETTER')
        self.assertEqual(r['S7']['label'], 'FEATURE_GENERALISES')
        self.assertEqual(S.verdict(True, r, False), 'FEATURE_PAYS')
        self.assertEqual(S.verdict(False, r, False), 'INVALID')
        r['P1']['label'] = 'NOT_SHOWN'
        self.assertEqual(S.verdict(True, r, True), 'NOT_SHOWN (NOTHING_PROPOSED)')

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])
            with self.assertRaises(SystemExit):
                S.main([d], output=d, pinned={'allocate.py': 'x'})


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path(self):
        ws = [('La-r0', 'La', 889001, False), ('Lb-r0', 'Lb', 889002, False), ('La-rnull', 'La', 889003, True)]
        train = [('Ka-r0', 'Ka', 889000, False)]
        with tempfile.TemporaryDirectory() as d:
            rc = S.main([d], registered=True, world_list=ws, train=train, budget=3000, pairs_per=30, output=d,
                        pinned=S.pins())                  # at the preregistration commit, S.pins() == S.PINNED
            self.assertEqual(rc, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertTrue(s['pins_ok'] and s['nulls_ok'] and s['spent_ok'], s)
        self.assertTrue(s['valid'])
        self.assertGreater(s['S4']['c_search'], 3000)
        self.assertIn(s['verdict'], ('NOT_SHOWN', 'NOT_SHOWN (NOTHING_PROPOSED)', 'FEATURE_PAYS'))


R172 = ROOT / 'evidence' / 'state_features_b20r172'


def at_commit(commit, files, code, timeout=7200):
    """Run Python `code` in a temporary worktree of `commit` with `files` ({path in the worktree: source}) copied in;
    `code` writes its answer as JSON to `answer.json` in the worktree, which is returned. The study's pinned engine
    modules are the ones at that commit, whatever the branch has since."""
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


@unittest.skipUnless((R172 / 'summary.json').exists(), 'B20_R172 has not been recorded')
class RecordB20R172(unittest.TestCase):
    """The record of B20_R172 on its evidence: the script; the rows complete and the arms' budgets; validity, the
    analysis and the verdict recomputed in this tree; then, at the preregistration commit (its pinned engine modules):
    main re-run on the saved search and rows to the same summary, the feature search replayed to the same record, and
    the first and last worlds' runs re-executed to the same rows (S7 included)."""
    DIR, KW, OUT = R172, {}, 'evidence/state_features_b20r172'

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.sr = json.loads((cls.DIR / 'search.json').read_text())
        cls.rows = {}
        for line in (cls.DIR / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['world'], r['arm'])] = r

    def ws(self):
        wl = self.KW.get('world_list')
        return [tuple(w) for w in wl] if wl is not None else S.worlds()

    def test_the_script(self):
        if self.DIR != R172:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r172_state_features.py').read_bytes()).hexdigest(),
                         '46e571f4f763ace626a8962bd6e21c103b91f99c2e095e299ee3571677739b33')

    def test_validity_and_the_analysis_recompute(self):
        ws, budget = self.ws(), self.KW.get('budget', S.B)
        self.assertEqual([list(x) for x in ws], self.s['worlds'])
        self.assertEqual(set(self.rows), {(k, a) for k, f, sd, null in ws for a in S.ARMS})
        nulls_ok = all(self.rows[(k, a)]['total'] == 0.0 for k, f, sd, null in ws if null for a in S.ARMS)
        spent_ok = all(r['spent'] >= r['budget'] - S.QUANTUM - 1 for r in self.rows.values())
        self.assertEqual((nulls_ok, spent_ok), (self.s['nulls_ok'], self.s['spent_ok']))
        self.assertEqual(self.s['valid'], nulls_ok and spent_ok and self.s['pins_ok'] and self.sr['in_language'])
        extra = S.extra_budget(self.sr['c_search'], sum(1 for w in ws if not w[3]))
        self.assertEqual(extra, self.s['S4']['extra_budget_per_world'])
        for (k, a), r in self.rows.items():
            self.assertEqual(r['budget'], budget + (extra if a == 'D' else 0))
        self.assertEqual(self.s['S4']['feature'], self.sr['feature'])
        res = S.analyse(self.rows, ws)
        self.assertEqual(json.loads(json.dumps(res, sort_keys=True, default=list)), self.s['results'])
        self.assertEqual(S.verdict(self.s['valid'], res, self.sr['nothing_proposed']), self.s['verdict'])

    def test_at_the_preregistration_commit(self):
        files = {f'{self.OUT}/search.json': self.DIR / 'search.json', f'{self.OUT}/rows.jsonl': self.DIR / 'rows.jsonl'}
        kw = dict(self.KW)
        code = f'''
import json, sys
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
import b20r172_state_features as S
kw = json.loads({json.dumps(json.dumps(kw))})
if 'world_list' in kw:
    kw['world_list'] = [tuple(w) for w in kw['world_list']]
if 'train' in kw:
    kw['train'] = [tuple(w) for w in kw['train']]
extra_kw = dict(output='{self.OUT}', pinned=S.pins()) if kw else {{}}
rc = S.main(['{self.OUT}'], registered=True, **kw, **extra_kw)
summary = json.load(open('{self.OUT}/summary.json'))
budget = kw.get('budget', S.B)
sr = S.search(kw.get('train'), budget=budget, pairs_per=kw.get('pairs_per', S.PAIRS))
ws = kw.get('world_list') or S.worlds()
extra = S.extra_budget(sr['c_search'], sum(1 for w in ws if not w[3]))
feature = sr['feature']
p_params = {{'state_feature': {{'expr': feature['expr'], 'weight': feature['weight']}}}} if feature else {{}}
plan = {{'P': (p_params, budget), 'D': ({{}}, budget + extra), 'D0': ({{'log_decisions': True}}, budget)}}
runs = []
for idx in sorted({{0, len(ws) - 1}}):
    key, fam, seed, null = ws[idx]
    for arm in S.ARMS:
        params, bud = plan[arm]
        r = S.run_one(fam, seed, null, arm, idx, params, bud, feature)
        r['world'] = key
        runs.append(r)
json.dump({{'rc': rc, 'summary': summary, 'search': json.loads(json.dumps(sr, sort_keys=True, default=list)),
           'runs': runs}}, open('answer.json', 'w'), default=list)
'''
        got = at_commit('73f8ad4', files, code)
        self.assertEqual(got['rc'], 0)
        drop = ('code_identity',)
        self.assertEqual({k: v for k, v in got['summary'].items() if k not in drop},
                         {k: v for k, v in self.s.items() if k not in drop})
        self.assertEqual(got['search'], self.sr)
        for r in got['runs']:
            saved = self.rows[(r['world'], r['arm'])]
            for f in ('total', 'reference', 'value', 'spent', 'budget', 'branches', 'verify_calls', 'S7'):
                self.assertEqual(r.get(f), saved.get(f), (r['world'], r['arm'], f))


if __name__ == '__main__':
    unittest.main()
