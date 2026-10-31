# Draft record tests for B20_R151 and B20_R152 (not yet in the test suite)

These are written before the studies finish, from the scripts only (no study data seen). When a study exits 0,
copy its evidence into `evidence/`, append the matching class to its design test file, run it, and adjust
**only** what the saved summary's actual structure requires (never a threshold or rule). Each class skips itself
until its `summary.json` exists.

The helper `scratchpad/r151_report.py` text is included at the end: it prints every number the record needs from
B20_R151's `summary.json`.

## RecordB20R151 (append to `tests_genesis/test_expressiveness_study.py`)

**Appended on 28 Oct 2026, 02:00 SGT; it passed unchanged on B20_R151's evidence.**

It needs these imports in that file: `hashlib`, `json`, `unittest`, `ROOT`, `S` (the study script) and `K3`
(`genesis.candidate_kinds.mcx3`).

```python


R151 = ROOT / 'evidence' / 'expressiveness_b20r151'


@unittest.skipUnless((R151 / 'summary.json').exists(), 'B20_R151 has not been recorded')
class RecordB20R151(unittest.TestCase):
    """The record of B20_R151 on its evidence: the amended script that ran its later slices; validity; the gate and the
    truth tables from the saved runs; the analysis (every class's P1, S1-S5, labels, Holm and the verdict) recomputed
    from the saved inputs; the graphs regenerate with the recorded identities."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R151 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R151 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r
        cls.rex = S.Lab.ekey(dict(K3.DEFAULT))

    def run_value(self, ek, task, occ, budget='1'):
        return self.runs[f'{ek}|{task}|{occ}|{budget}']['value']

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r151_expressiveness.py').read_bytes()).hexdigest(),
                         '8742dd8de359f6596367bdde49d73bfaa8a8f4d602a48dd4a7d9e735d998035c')

    def test_validity(self):
        import statistics
        s = self.s
        self.assertTrue(s['valid'] and s['spent'] and s['disjoint'] and all(s['pins'].values()))
        cpus = {}
        for r in self.runs.values():
            b = r['key'].rsplit('|', 1)[1]
            cpus.setdefault(b, []).append(r['cpu'] / float(b))
        self.assertTrue(all(statistics.median(v) >= 0.9 for v in cpus.values()))
        self.assertEqual({b: statistics.median(v) for b, v in cpus.items()}, s['cpu_median'])

    def test_the_gate_from_the_runs(self):
        for c, ids in self.s['graphs'].items():
            base = {t: (self.run_value(self.rex, t, 0) + self.run_value(self.rex, t, 1)) / 2 for t in ids['H']}
            long = {t: self.run_value(self.rex, t, 0, '10') for t in ids['H']}
            g = S.gate(base, long)
            self.assertAlmostEqual(g['mean'], self.s['gates'][c]['mean'])
            self.assertAlmostEqual(g['p'], self.s['gates'][c]['p'])
            self.assertEqual(g['pass'], self.s['gates'][c]['pass'])
        self.assertEqual(S.select(self.s['gates']), self.s['studied'])

    def test_the_truth_tables_from_the_runs(self):
        import statistics
        for c in self.s['studied']:
            f = self.s['finals'][c]
            for t, b in f['base'].items():
                self.assertAlmostEqual(b, statistics.mean(self.run_value(self.rex, t, o) for o in range(S.T_RUNS)))
            for ek, vals in f['values'].items():
                for t, v in vals.items():
                    self.assertAlmostEqual(v, statistics.mean(self.run_value(ek, t, o) for o in range(S.T_RUNS)))

    def test_the_analysis_recomputes(self):
        import statistics
        per = {}
        for c in self.s['studied']:
            f = self.s['finals'][c]
            g = S.gains(f['values'], f['base'])
            per[c] = S.analyse_class(self.s['arms'][c], g)
        v, ph = S.verdict(self.s['studied'], per, self.s['valid'])
        self.assertEqual(v, self.s['verdict'])
        for c in self.s['studied']:
            got, rec = per[c], self.s['per_class'][c]
            for k in ('P1', 'S1'):
                self.assertEqual(got[k]['label'], rec[k]['label'])
                self.assertAlmostEqual(got[k]['p'], rec[k]['p'])
                self.assertAlmostEqual(got[k]['mean'], rec[k]['mean'])
                self.assertAlmostEqual(got[k]['replicates']['p'], rec[k]['replicates']['p'])
            self.assertAlmostEqual(got['P1']['replicates']['margin'], rec['P1']['replicates']['margin'])
            self.assertEqual(got['reading'], rec['reading'])
            for lang in ('L0', 'L1'):
                self.assertEqual(got['S4'][lang]['label'], rec['S4'][lang]['label'])
            for k, x in got['lanes'].items():
                self.assertAlmostEqual(x, rec['lanes'][k])

    def test_the_lambda0_arms_wrote_lambda0_only(self):
        calls = json.loads((R151 / 'calls.json').read_text())
        progs = json.loads((R151 / 'programs.json').read_text())
        for key, cs in calls.items():
            if key.split('|')[1][1] == '0':
                for c in cs:
                    self.assertTrue(K3.is_lambda0(K3.parse(progs[c['engine']]['prog'])), key)

    def test_the_graphs_regenerate(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        G = S.graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()})
        for c, ids in self.s['graphs'].items():
            self.assertEqual([t.task_id for t in G[c]['H']], ids['H'])
            self.assertEqual([t.task_id for t in G[c]['T']], ids['T'])
            self.assertEqual([[t.task_id for t in a] for a in G[c]['A']], ids['A'])
```

## RecordB20R152 (append to `tests_genesis/test_self_extension_study.py`)

**Appended on 28 Oct 2026, 04:42 SGT; it passed unchanged on B20_R152's evidence (the confirmation test skips: nothing was admitted).**

```python


R152 = ROOT / 'evidence' / 'self_extension_b20r152'


def _rows(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r['key']] = r
    return out


@unittest.skipUnless((R152 / 'summary.json').exists(), 'B20_R152 has not been recorded')
class RecordB20R152(unittest.TestCase):
    """The record of B20_R152 on its evidence: the amended script; validity recomputed from the runs; P1, the verdict
    and the confirmation replicates recomputed from the saved runs; the judge's decisions against its ledger; the vault
    holds one record per decision; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R152 / 'summary.json').read_text())
        cls.runs = _rows(R152 / 'runs.jsonl')
        cls.judge_runs = _rows(R152 / 'judge_runs.jsonl')

    def test_the_script(self):
        self.assertEqual(S.file_digest(ROOT / 'scripts' / 'b20r152_self_extension.py'),
                         '2d3d8f899162c381beddf559a7a392487645e0984484b3d71a37b59a9e215b98')

    def test_validity(self):
        import statistics
        s = self.s
        self.assertTrue(s['valid'] and s['spent'] and s['disjoint'] and all(s['pins'].values()), s['pins'])
        self.assertTrue(all(r['evaluations'] >= S.INV_EVALS for r in s['reports']))
        cpus = [r['cpu'] for r in self.runs.values()] + [r['cpu'] for r in self.judge_runs.values()]
        self.assertAlmostEqual(statistics.median(cpus) / S.BUDGET, s['cpu_median'])
        self.assertGreaterEqual(s['cpu_median'], 0.9)

    def test_the_verdict_and_p1_recompute(self):
        s = self.s
        admitted1 = bool(s['generations'] and s['generations'][0]['admitted'])
        p = S.p1(s['confirm']) if s['confirm'] else None
        self.assertEqual(p, s['P1'])
        self.assertEqual(S.verdict(s['valid'], admitted1, p), s['verdict'])

    def test_the_confirmation_from_the_runs(self):
        """Each confirmation replicate's mean truth gain is that of an engine run on every truth graph, and the lanes
        are the per-graph means of those engines' gains."""
        import statistics
        s = self.s
        if not s['confirm']:
            self.skipTest('nothing was admitted: no confirmation')
        truth = s['graphs']['truth']
        rex = S.Lab.ekey(dict(K3.DEFAULT))
        val = lambda ek, t: statistics.mean(self.runs[f'{ek}|{t}|{o}|1']['value'] for o in range(S.T_RUNS))
        base = {t: val(rex, t) for t in truth}
        engines = {k.split('|')[0] for k in self.runs if k.split('|')[1] in set(truth)}
        gains = {e: [(val(e, t) - base[t]) / base[t] for t in sorted(truth)] for e in engines
                 if all(f'{e}|{t}|{o}|1' in self.runs for t in truth for o in range(S.T_RUNS))}
        for name, c in s['confirm'].items():
            chosen = []
            for m in c['reps']:
                hits = [e for e, g in gains.items() if abs(statistics.mean(g) - m) < 1e-12]
                self.assertTrue(hits, (name, m))
                chosen.append(gains[hits[0]])
            for a, b in zip(c['lane'], [statistics.mean(x) for x in zip(*chosen)]):
                self.assertAlmostEqual(a, b)

    def test_the_decisions_and_the_ledger(self):
        s = self.s
        decisions = [d for g in s['generations'] for d in g['decisions']]
        self.assertEqual(len(s['judge_ledger']), len(decisions))
        for g in s['generations']:
            self.assertEqual(g['admitted'], [d['name'] for d in g['decisions'] if d['admitted']])
        if len(s['generations']) < S.GENERATIONS:
            self.assertEqual(s['generations'][-1]['admitted'], [])            # the line ended by stagnation

    def test_the_vault(self):
        self.assertTrue((R152 / 'vault' / '.complete').exists())

    def test_the_graphs_regenerate(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        G, _ = S.study_graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()} | S.r151_identities())
        self.assertEqual({k: [t.task_id for t in v] for k, v in G.items()}, self.s['graphs'])
```

## B20_R151 report helper (`python3 r151_report.py evidence/expressiveness_b20r151`)

```python
"""Print B20_R151's results from its finished summary.json (run only after the study exits 0)."""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
s = json.loads((d / 'summary.json').read_text())
pct = lambda x: f'{100 * x:+.3f}%'
print('verdict', s['verdict'], 'valid', s['valid'], 'spent', s['spent'], 'disjoint', s['disjoint'], 'pins', s['pins'])
print('cpu_median', s['cpu_median'])
for c, g in s['gates'].items():
    print('gate', c, pct(g['mean']), 'p', g['p'], g['pass'])
print('studied', s['studied'], 'p_holm', s['p_holm'])
for c in s['studied']:
    r = s['per_class'][c]
    print(f'\n== {c}: reading {r["reading"]}')
    print('lanes', {k: pct(v) for k, v in r['lanes'].items()})
    p1 = r['P1']
    print('P1', p1['label'], pct(p1['mean']), 'p', p1['p'], 'p_holm', p1['p_holm'], 'rep p', p1['replicates']['p'],
          'margin', pct(p1['replicates']['margin']), 'reps', p1['replicates'])
    s1 = r['S1']
    print('S1', s1['label'], pct(s1['mean']), 'p', s1['p'], 'rep', s1['replicates'])
    for lang, w in r['S2'].items():
        print('S2', lang, pct(w['mean']), 'p', w['p'])
    print('S3', pct(r['S3']['mean']), 'p', r['S3']['p'])
    for lang, w in r['S4'].items():
        print('S4', lang, w['label'], pct(w['mean']), 'p', w['p'])
    for n, w in r['S5'].items():
        print('S5', n, pct(w['mean']), 'p', round(w['p'], 4))
    for n, w in r['winners'].items():
        print('winner', n, pct(w['mean_gain']), repr(w['prog']), w['constructs'])
    print('ablations', {k: pct(v) for k, v in r['ablations'].items()})
    print('usage_L1', r['usage_L1'])
for k, rep in sorted(s['reports'].items()):
    print('report', k, {x: rep[x] for x in ('evaluations', 'max_evals', 'distinct_programs', 'reported') if x in rep})
```

## RecordB20R165 (append to `tests_genesis/test_planar_replication_study.py`)

**Appended on 28 Oct 2026, 05:53 SGT; it passed unchanged on B20_R165's evidence.**

Written on 28 Oct 2026, 02:40 SGT, from the script only, before the study ran. Needs `import statistics` in that
file (it has `json`, `unittest`, `ROOT` and `S`).

```python


R165 = ROOT / 'evidence' / 'planar_replication_b20r165'


@unittest.skipUnless((R165 / 'summary.json').exists(), 'B20_R165 has not been recorded')
class RecordB20R165(unittest.TestCase):
    """The record of B20_R165 on its evidence: the script; validity with the CPU medians recomputed; every final value
    recomputed from the saved runs; the analysis and the verdict recomputed; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R165 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R165 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r165_planar_replication.py').read_bytes()).hexdigest(),
                         'fbf968c5e2cf22f3e6f2720df16ae2586f08dbcc32f5f556ca4df99ed523516f')

    def test_validity(self):
        s = self.s
        self.assertTrue(s['valid'] and s['disjoint'] and all(s['pins'].values()))
        cpus = {}
        for r in self.runs.values():
            b = r['key'].rsplit('|', 1)[1]
            cpus.setdefault(b, []).append(r['cpu'] / float(b))
        self.assertTrue(all(statistics.median(v) >= 0.9 for v in cpus.values()))
        self.assertEqual({b: statistics.median(v) for b, v in cpus.items()}, s['cpu_median'])

    def test_the_finals_from_the_runs(self):
        from genesis.candidate_kinds import mcx3 as K3
        from genesis.common import digest
        eng, ok = S.engines()
        self.assertTrue(ok)
        rex = digest(dict(K3.DEFAULT))[:16]
        val = lambda ek, t, o, b='1': self.runs[f'{ek}|{t}|{o}|{b}']['value']
        for cls, f in self.s['finals'].items():
            for t, b in f['base'].items():
                self.assertAlmostEqual(b, statistics.mean(val(rex, t, o) for o in range(S.T_RUNS)))
            for n, vals in f['values'].items():
                ek = digest(eng[n])[:16]
                for t, v in vals.items():
                    self.assertAlmostEqual(v, statistics.mean(val(ek, t, o) for o in range(S.T_RUNS)))
            if cls == S.PRIMARY:
                for t, v in f['long'].items():
                    self.assertAlmostEqual(v, val(rex, t, 0, '10'))

    def test_the_analysis_recomputes(self):
        primary, res = S.analyse(self.s['finals'], self.s['families'], self.s['prespecified'])
        for k in ('P1', 'P2'):
            self.assertEqual(primary[k]['label'], self.s['primary'][k]['label'])
            self.assertAlmostEqual(primary[k]['p_holm'], self.s['primary'][k]['p_holm'])
            self.assertAlmostEqual(primary[k]['mean'], self.s['primary'][k]['mean'])
        self.assertEqual(S.verdict(self.s['valid'], primary), self.s['verdict'])
        self.assertEqual(self.s['prespecified'], S.PRESPECIFIED)

    def test_the_graphs_regenerate(self):
        G = S.graphs(S.excluded_identities())
        self.assertEqual({c: [t.task_id for t in ts] for c, ts in G.items()}, self.s['graphs'])
```

## RecordB20R156 (F3; append to `tests_genesis/test_frontier_worlds_study.py`)

**Appended on 28 Oct 2026, 09:20 SGT; it passed unchanged on B20_R156's evidence.**

Written on 28 Oct 2026, 02:55 SGT, from the script only, before the study ran. Needs `import hashlib`,
`import json` (already there) and `ROOT`, `S` (the study script).

```python


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
```

## RecordB20R163 (F6; append to `tests_genesis/test_frontier_meta_study.py`)

Written on 28 Oct 2026, 02:55 SGT, from the script only, before the study ran. The file already has `json`,
`unittest`, `ROOT`, `S` and `MT`.

```python


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
```

## RecordB20R157 (F4; append to `tests_genesis/test_laplacian_bounds_study.py`)

**Updated on 28 Oct 2026, 11:10 SGT, for the amendment (`ff9eada`): the script's digest is the amended one. Nothing
else in the draft changes. The study has not been re-run.**

Written on 28 Oct 2026, 02:55 SGT, from the script only, before the study ran. Needs `json`, `unittest`, `ROOT` and
`S` (the study script).

```python


R157 = ROOT / 'evidence' / 'laplacian_bounds_b20r157'


@unittest.skipUnless((R157 / 'summary.json').exists(), 'B20_R157 has not been recorded')
class RecordB20R157(unittest.TestCase):
    """The record of B20_R157 (F4) on its evidence: the script; every artifact double checked again by the kernel;
    the refuted sets, the null check, the analysis and the verdict recomputed."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R157 / 'summary.json').read_text())
        cls.rows = {}
        for line in (R157 / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['arm'], r.get('problem'))] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r157_laplacian_bounds.py').read_bytes()).hexdigest(),
                         'fb5dd07e5ccce94a8d80fe951611d1a21235be26ab6a45ad26149fc67f075785')

    def test_the_kernel_checks_recompute(self):
        from genesis.conjecture import sealed as SD
        problems, number_of = S.posed()
        self.assertEqual({p: number_of[p] for p in problems}, {k: v for k, v in self.s['ids'].items()})
        refuted = {}
        for arm in S.ARMS:
            arts = self.rows[(arm, None)]['artifacts'] if arm in S.JOINT else \
                {p: self.rows[(arm, p)]['artifact'] for p in problems if 'artifact' in self.rows[(arm, p)]}
            refuted[arm] = {p for p, art in arts.items() if S.double_check(*problems[p], art) == 'CONFIRMED'}
            self.assertEqual(sorted(number_of[p] for p in refuted[arm]), self.s['refuted'][arm])
        status_of = {p: SD.status(number_of[p]) for p in problems}
        nulls = sorted({number_of[p] for a in S.ARMS for p in refuted[a] if status_of[p] == 'proved'})
        self.assertEqual(nulls, self.s['proved_bounds_refuted'])
        res = S.analyse(refuted, status_of, number_of)
        for c in S.COMPARATORS:
            for k in ('frontier_only', 'comparator_only', 'label'):
                self.assertEqual(res['P1'][c][k], self.s['results']['P1'][c][k])
            self.assertAlmostEqual(res['P1'][c]['p_holm'], self.s['results']['P1'][c]['p_holm'])
        self.assertEqual(S.verdict(self.s['valid'], res)[0], self.s['verdict'])
```

## RecordB20R141 (append to `tests_genesis/test_ara_zoo_study.py`)

**Appended on 28 Oct 2026, 09:20 SGT, with one assertion changed (disclosed in `docs/checkpoints/B20_R141_RECORD.md`):
the draft asserted that the run was valid, and it is not. The appended version asserts the validity record as it
is, reproduces the defect (`test_the_freshness_defect`), and adds two re-derivations (the environments regenerated
from the sealed seed; every submission re-judged).**

Written on 28 Oct 2026, 04:55 SGT, from the script only (`a3b3eda`, sha256 `ccec4633…60bf`), before the study ran.
The file already has `json`, `hashlib`, `unittest`, `ROOT`, `S` and `Z`.

```python


R141 = ROOT / 'evidence' / 'ara_zoo_b20r141'


@unittest.skipUnless((R141 / 'summary.json').exists(), 'B20_R141 has not been recorded')
class RecordB20R141(unittest.TestCase):
    """The record of B20_R141 on its evidence: the script; the environments; validity recomputed from the rows; the
    analysis, experiment C and the verdict recomputed from the saved rows, ledger and keys."""

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
        self.assertTrue(self.s['valid'] and all(self.s['validity'].values()), self.s['validity'])

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
```

## RecordB20R158 (F5; append to `tests_genesis/test_open_conjectures_study.py`)

**Updated on 28 Oct 2026, 11:10 SGT, for the amendment (`ff9eada`): the script's digest is the amended one, and the
audit re-derivation reads the research plane at `ff9eada`.**

**Updated again on 30 Oct 2026, 11:15 SGT, for the second amendment (after the first attempt crashed): the script's
digest is the second amendment's (`f44333c3…c06c`), and the audit re-derivation reads the research plane at the
second amendment commit (`AMENDMENT` in the test file: `f7803e3`). Nothing else in the draft changes.**

Written on 28 Oct 2026, 09:40 SGT, from the script only (`703b2ee`, sha256 `50d2de64…f9b5`), before the study ran.
The file already has `json`, `unittest`, `ROOT` and `S`; the audit re-derivation reads the research plane as it
was at the preregistration commit through `git show`, because the branch head has moved on.

```python


R158 = ROOT / 'evidence' / 'open_conjectures_b20r158'


@unittest.skipUnless((R158 / 'summary.json').exists(), 'B20_R158 has not been recorded')
class RecordB20R158(unittest.TestCase):
    """The record of B20_R158 (F5) on its evidence: the script; validity recomputed (the budgets, no proved bound
    refuted, the audit of the research plane at the preregistration commit); every certified refutation
    double-checked again; the analysis and the verdict recomputed; generation 1's posed set regenerated from the
    data seed; the survivors' small exhaustive check repeated."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R158 / 'summary.json').read_text())
        cls.gens = [json.loads(x) for x in (R158 / 'generations.jsonl').read_text().splitlines() if x.strip()]

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r158_open_conjectures.py').read_bytes()).hexdigest(),
                         'f44333c3355607da31fd54d10bf6444ecc3a753d8d431b12d7dd9ea15f85c06c')

    def test_validity(self):
        self.assertEqual(len(self.gens), S.G)
        spent = all(g[a]['spent'] >= g[a]['budget'] - S.QUANTUM - 1 for g in self.gens for a in ('FULL', 'PLAIN'))
        self.assertEqual(spent, self.s['spent_ok'])
        hits = sorted({g['posed'][p][0] for g in self.gens for a in ('FULL', 'PLAIN') for p in g['confirmed'][a]
                       if S.proved_equivalent(g['posed'][p][0])})
        self.assertEqual(hits, self.s['proved_equivalents_refuted'])
        self.assertEqual(self.s['audit_hits'], [])
        self.assertTrue(self.s['pins_ok'])
        self.assertEqual(self.s['valid'], spent and not hits and self.s['pins_ok'] and not self.s['audit_hits'])

    def test_the_audit_at_the_preregistration_commit(self):
        import subprocess
        import tempfile
        from genesis.conjecture import audit as AU
        with tempfile.TemporaryDirectory() as tmp:
            files = []
            for path in AU.research_plane(Path(tmp)):
                rel = path.relative_to(tmp).as_posix()
                out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{AMENDMENT}:{rel}'], capture_output=True)
                if out.returncode != 0:                          # a module that did not exist then
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(out.stdout)
                files.append(path)
            self.assertTrue(files)
            self.assertEqual(AU.scan(files), [])

    def test_every_refutation_double_checks_again(self):
        for g in self.gens:
            for arm in ('FULL', 'PLAIN'):
                got = [p for p, art in sorted(g[arm]['artifacts'].items())
                       if p in g[arm]['refuted'] and S.double_check(g['posed'][p][0], 'vertex', art) == 'CONFIRMED']
                self.assertEqual(got, g['confirmed'][arm], (g['k'], arm))

    def test_the_analysis_recomputes(self):
        both = {a: set().union(*[set(g['confirmed'][a]) for g in self.gens]) for a in ('FULL', 'PLAIN')}
        b, c = len(both['FULL'] - both['PLAIN']), len(both['PLAIN'] - both['FULL'])
        self.assertEqual((self.s['P1']['full_only'], self.s['P1']['plain_only']), (b, c))
        self.assertAlmostEqual(self.s['P1']['p'], S.mcnemar_one_sided(b, c))
        want = 'INVALID' if not self.s['valid'] else ('FULL_BETTER' if S.mcnemar_one_sided(b, c) < S.ALPHA
                                                      else 'NOT_SHOWN')
        self.assertEqual(self.s['verdict'], want)
        for g in self.gens:
            surv = sorted(p for p in g['posed'] if p not in g['confirmed']['FULL'] and p not in g['confirmed']['PLAIN'])
            self.assertEqual(surv, g['survivors'])

    def test_generation_one_is_posed_again_from_the_data_seed(self):
        import numpy as np
        from genesis.conjecture import generate as GN
        data = GN.data(np.random.default_rng(S.DATA_SEED), count=S.DATA_COUNT)
        kept = [f for f, _ in GN.conjectures(data)]
        g1 = self.gens[0]
        self.assertEqual(len(kept), g1['kept'])
        posed = sorted(f for f, _ in g1['posed'].values())
        self.assertEqual(sorted(f for f in kept if not S.labels(f)[0]), posed)
        self.assertEqual(sorted(f for f in kept if S.labels(f)[0]), sorted(g1['withheld']))

    def test_the_survivors_small_check_repeats(self):
        for g in self.gens:
            for p in g['survivors']:
                self.assertEqual(S.survives_small(g['posed'][p][0], 'vertex'), g['survivors_small_exhaustive'][p])
```

## RecordB20R167 (append to `tests_genesis/test_ara_zoo_rerun_study.py`)

Written on 28 Oct 2026, 09:40 SGT, from the script only (`33e8905`, sha256 `233610d0…af81`), before the study ran.
The file already has `json`, `hashlib`, `unittest`, `ROOT`, `S` and `Z`.

```python


R167 = ROOT / 'evidence' / 'ara_zoo_b20r167'


@unittest.skipUnless((R167 / 'summary.json').exists(), 'B20_R167 has not been recorded')
class RecordB20R167(unittest.TestCase):
    """The record of B20_R167 on its evidence: the script; the environments; validity recomputed, the freshness
    clause included; the analysis, experiment C and the verdict recomputed from the saved rows, ledger and keys; the
    environments regenerated from the sealed seed and every judged submission re-judged."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R167 / 'summary.json').read_text())
        cls.done = {}
        for line in (R167 / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.done[(r['index'], r['arm'])] = r
        entries = {}
        for line in (R167 / 'ledger.jsonl').read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                entries[(e['index'], e['arm'])] = e
        cls.ledger = [entries[k] for k in sorted(entries)]

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r167_ara_zoo_rerun.py').read_bytes()).hexdigest(),
                         '233610d030b8a0af747834e2d0006e209348f3a52a590283f779d3a03eb1af81')

    def test_the_environments_and_validity(self):
        envs = S.environments()
        rows = sorted(int(i) for i in self.s['rows'])
        self.assertEqual(rows, sorted(i for i, _ in envs))
        self.assertEqual(len(self.done), len(envs) * len(S.ARMS))
        self.assertTrue(all(r['spent'] <= r['budget'] + 1e-9 for r in self.done.values()))
        self.assertEqual(self.s['validity']['fresh'], S.freshness(rows, True, False, S.SEALED_SEED))
        self.assertEqual(self.s['validity']['budget'], True)
        self.assertEqual(self.s['valid'], all(self.s['validity'].values()))

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

    def test_the_environments_regenerate_and_every_submission_rejudges(self):
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
            gain = diff / rng if rng > 1e-12 else 0.0
            self.assertAlmostEqual(gain, e['gain'], places=9, msg=(e['index'], e['arm']))
            if e['promoted']:
                self.assertIsNone(e['failed'])
                self.assertGreaterEqual(gain, J.MATERIAL)
```

## RecordB20R173 (append to `tests_genesis/test_protected_release_study.py`)

Written on 29 Oct 2026, 23:30 SGT, from the script only (`d8cb798`, sha256 `a3e03841…7291`), before the study ran.
The file has `hashlib`, `json`, `unittest`, `ROOT`, `S`, `K3` and `digest`; it needs `import statistics`.

```python


R173 = ROOT / 'evidence' / 'protected_release_b20r173'


@unittest.skipUnless((R173 / 'summary.json').exists(), 'B20_R173 has not been recorded')
class RecordB20R173(unittest.TestCase):
    """The record of B20_R173 on its evidence: the script; validity recomputed; both judges rebuilt from the saved
    runs (the protected Judge class itself, replaying its calls from the cache), their taus and decisions recomputed;
    the truth recomputed; the verdict; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R173 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R173 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r173_protected_release.py').read_bytes()).hexdigest(),
                         'a3e038415e1b57199dc2aeab759f413338e0f61fec05db6786077afdabaa7291')

    def replay_runner(self):
        def run(cfg, task, seed, budget):
            raise AssertionError('a run missing from the evidence')
        return run

    def lab(self):
        lab = S.Lab(None, self.replay_runner())
        lab.cache = dict(self.runs)
        return lab

    def test_validity(self):
        s = self.s
        self.assertTrue(s['valid'] and all(s['validity'].values()))
        one = [r['cpu'] for k, r in self.runs.items() if k.endswith('|1')]
        ten = [r['cpu'] for k, r in self.runs.items() if k.endswith('|10')]
        self.assertGreaterEqual(statistics.median(one), 0.9)
        self.assertGreaterEqual(statistics.median(ten), 9.0)

    def test_the_judges_and_the_truth_recompute(self):
        G = S.graphs(S.excluded_identities())
        self.assertEqual({k: [t.task_id for t in v] for k, v in G.items()}, self.s['graphs'])
        lab = self.lab()
        cand, ok = S.candidate()
        self.assertTrue(ok)
        v2 = S.judge(S.evaluator(lab, G), S.calibration_programs(), dict(K3.DEFAULT), cand)
        v3 = S.judge(S.evaluator(lab, G), S.v3_programs(), dict(K3.DEFAULT), cand)
        for got, saved in ((v2, self.s['R1']), (v3, self.s['S1'])):
            for k in ('tau', 'start', 'b_candidate'):
                self.assertAlmostEqual(got[k], saved[k], places=12)
            self.assertEqual(got['released'], saved['released'])
        truth = []
        for t in G['T']:
            c = statistics.mean(lab.run(cand, t, f'truth{r}') for r in range(S.T_RUNS))
            x = statistics.mean(lab.run(dict(K3.DEFAULT), t, f'truth{r}') for r in range(S.T_RUNS))
            truth.append((c - x) / x)
        self.assertEqual([round(x, 12) for x in truth], [round(x, 12) for x in self.s['S2']['gains']])
        self.assertEqual(S.verdict(self.s['valid'], v2), self.s['verdict'])
```

## RecordB20R136 (append to `tests_genesis/test_sense_choice_study.py`)

Written on 29 Oct 2026, 23:30 SGT, from the script only (`6bb39ab`, sha256 `357cd5ed…2bcb`), before the study ran.
The file has `json`, `unittest`, `ROOT`, `S`, `K3` and `digest`; it needs `import statistics`.

```python


R136 = ROOT / 'evidence' / 'sense_choice_b20r136'


@unittest.skipUnless((R136 / 'summary.json').exists(), 'B20_R136 has not been recorded')
class RecordB20R136(unittest.TestCase):
    """The record of B20_R136 on its evidence: the script; validity; the search's choice recomputed (the sense
    search is deterministic in its seed and the saved training runs); every test row recomputed from the saved runs
    and sense timings; the analysis and the verdict; the graphs regenerate."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R136 / 'summary.json').read_text())
        cls.runs = {}
        for line in (R136 / 'runs.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.runs[r['key']] = r

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r136_sense_choice.py').read_bytes()).hexdigest(),
                         '357cd5ed202b8b79987668d081d408ad8fcbf32ef51cb5cae6d6fa3c979b2bcb')

    def test_everything_recomputes(self):
        import numpy as np
        from genesis.senses import graph as SG
        from genesis.senses import synthesis as SY
        G = S.graphs(S.excluded_identities())
        self.assertEqual({k: [t.task_id for _, t in v] for k, v in G.items()}, self.s['graphs'])
        lab = S.Lab(None, lambda *a: (_ for _ in ()).throw(AssertionError('a run missing from the evidence')))
        lab.cache = dict(self.runs)
        eng, ok = S.engines()
        self.assertTrue(ok)
        names, Mtr = S.score_matrix(lab, eng, G['train'])
        ctx = [SG.Context(S.as_graph(t)) for _, t in G['train']]
        r = SY.synthesise(ctx, Mtr, S.SEARCH_BUDGET, seed=0)
        self.assertEqual(r['sense'], self.s['S2']['sense'])
        self.assertAlmostEqual(r['value'], self.s['S2']['cv_value'], places=12)
        rows = self.s['rows']
        for row, (fam, t) in zip(rows, G['test']):
            sv = self.runs[f'sense|sense|{t.task_id}']['value']
            cs = int(SY.act(tuple(self.s['S2']['sense_theta']), np.array([sv]))[0])
            self.assertEqual(names[cs], row['choice_sense'])
            got, b = S.chosen_score(lab, eng, names, cs, t, row['cpu_sense'], 'sense')
            self.assertAlmostEqual(got, row['SENSE'], places=12)
        col = lambda a: [x[a] for x in rows]                              # noqa: E731
        t1 = S.wilcoxon([a - b for a, b in zip(col('SENSE'), col('FIXED'))], 'greater')
        self.assertAlmostEqual(t1['p'], self.s['P1']['p'], places=12)
        self.assertTrue(self.s['valid'] and all(self.s['validity'].values()))
        self.assertEqual(S.verdict(self.s['valid'], self.s['P1']['passed'], self.s['P2']['passed']), self.s['verdict'])
```

## RecordB20R144 (append to `tests_genesis/test_ara_improves_ara_study.py`)

Written on 30 Oct 2026 from the script only (`7acf0e4`, sha256 `05523955…58c3`). It was dry-run on a rehearsal output
(the design test's small sets and seeds 990011 and 990013), where all four tests pass. **Disclosed:** the study
started at 07:38:30 SGT, before this draft was committed (07:40); no file of the study's output had been opened. The
file has `hashlib`, `json`, `Path`, `tempfile`, `unittest`, `ROOT` and `S`.

```python

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
```

## RecordB20R170 (Foundry G2; append to `tests_genesis/test_forecast_calibration_study.py`)

Written on 30 Oct 2026, 07:50 SGT, from the script only (`405741e`, sha256 `8aa46929…357d`), before the study ran.
The branch's `frontier/allocate.py` has changed since the preregistration (G4's state feature, `0f87109`), so
everything that runs the engine runs in a temporary worktree of `405741e`, whose modules are the pinned ones. It was
dry-run on a rehearsal output made at `405741e` (the design test's worlds and budgets), where all three tests pass.
The file has `json`, `Path`, `sys`, `tempfile`, `unittest`, `ROOT` and `S`.

```python

R170 = ROOT / 'evidence' / 'forecast_calibration_b20r170'


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


@unittest.skipUnless((R170 / 'summary.json').exists(), 'B20_R170 has not been recorded')
class RecordB20R170(unittest.TestCase):
    """The record of B20_R170 on its evidence: the script; the rows complete and the arms' budgets; validity, the
    analysis and the verdict recomputed in this tree; then, at the preregistration commit (its pinned engine modules):
    main re-run on the saved meta-search and rows to the same summary, the meta-search replayed to the same record,
    and the first and last worlds' runs re-executed to the same rows."""
    DIR, KW, OUT = R170, {}, 'evidence/forecast_calibration_b20r170'

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.meta = json.loads((cls.DIR / 'meta.json').read_text())
        cls.rows = {}
        for line in (cls.DIR / 'rows.jsonl').read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cls.rows[(r['world'], r['arm'])] = r

    def ws(self):
        wl = self.KW.get('world_list')
        return [tuple(w) for w in wl] if wl is not None else S.worlds()

    def test_the_script(self):
        if self.DIR != R170:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r170_forecast_calibration.py').read_bytes()).hexdigest(),
                         '8aa46929e64a743b5eaba1eadde2dc285a6b445643486405e6eae5b691e2357d')

    def test_validity_and_the_analysis_recompute(self):
        from genesis.frontier import calibrate as CAL
        ws, budget = self.ws(), self.KW.get('budget', S.B)
        self.assertEqual([list(x) for x in ws], self.s['worlds'])
        self.assertEqual(set(self.rows), {(k, a) for k, f, sd, null in ws for a in S.ARMS})
        nulls_ok = all(self.rows[(k, a)]['total'] == 0.0 for k, f, sd, null in ws if null for a in S.ARMS)
        spent_ok = all(r['spent'] >= r['budget'] - S.QUANTUM - 1 for r in self.rows.values())
        self.assertEqual((nulls_ok, spent_ok), (self.s['nulls_ok'], self.s['spent_ok']))
        self.assertEqual(self.s['valid'], nulls_ok and spent_ok and self.s['pins_ok'] and self.meta['on_grid'])
        extra = S.extra_budget(self.meta['c_meta'], sum(1 for w in ws if not w[3]))
        self.assertEqual(extra, self.s['S4']['extra_budget_per_world'])
        for (k, a), r in self.rows.items():
            self.assertEqual(r['budget'], budget + (extra if a == 'D' else 0))
        self.assertEqual(set(self.meta['promoted']), set(CAL.GRID))
        res = S.analyse(self.rows, ws)
        self.assertEqual(json.loads(json.dumps(res, sort_keys=True, default=list)), self.s['results'])
        self.assertEqual(S.verdict(self.s['valid'], res, self.meta['identity_promoted']), self.s['verdict'])

    def test_at_the_preregistration_commit(self):
        files = {f'{self.OUT}/meta.json': self.DIR / 'meta.json', f'{self.OUT}/rows.jsonl': self.DIR / 'rows.jsonl'}
        kw = dict(self.KW)
        code = f'''
import json, sys
sys.path.insert(0, 'src'); sys.path.insert(0, 'scripts')
import b20r170_forecast_calibration as S
from genesis.frontier import calibrate as CAL
kw = json.loads({json.dumps(json.dumps(kw))})
if 'world_list' in kw:
    kw['world_list'] = [tuple(w) for w in kw['world_list']]
if 'meta' in kw:
    kw['meta'] = tuple(kw['meta'])
extra_kw = dict(output='{self.OUT}', pinned=S.pins()) if kw else {{}}
rc = S.main(['{self.OUT}'], registered=True, **kw, **extra_kw)
summary = json.load(open('{self.OUT}/summary.json'))
ms = S.meta_search(kw.get('meta'), b_in=kw.get('b_in', S.B_IN), budget=kw.get('meta_budget', S.META_BUDGET))
ws = kw.get('world_list') or S.worlds()
budget = kw.get('budget', S.B)
extra = S.extra_budget(ms['c_meta'], sum(1 for w in ws if not w[3]))
plan = {{'P': (ms['promoted'], budget), 'D': (CAL.DEFAULT, budget + extra), 'D0': (CAL.DEFAULT, budget)}}
runs = []
for idx in sorted({{0, len(ws) - 1}}):
    key, fam, seed, null = ws[idx]
    for arm in S.ARMS:
        params, bud = plan[arm]
        r = S.run_one(fam, seed, null, arm, idx, params, bud)
        r['world'] = key
        runs.append(r)
json.dump({{'rc': rc, 'summary': summary, 'meta': json.loads(json.dumps(ms, sort_keys=True, default=list)),
           'runs': runs}}, open('answer.json', 'w'), default=list)
'''
        got = at_commit('405741e', files, code)
        self.assertEqual(got['rc'], 0)
        drop = ('code_identity',)
        self.assertEqual({k: v for k, v in got['summary'].items() if k not in drop},
                         {k: v for k, v in self.s.items() if k not in drop})
        self.assertEqual(got['meta'], self.meta)
        for r in got['runs']:
            saved = self.rows[(r['world'], r['arm'])]
            for f in ('total', 'reference', 'value', 'spent', 'budget', 'branches', 'verify_calls', 'coverage',
                      'resolved'):
                self.assertEqual(r[f], saved[f], (r['world'], r['arm'], f))
```

## RecordB20R172 (Foundry G4; append to `tests_genesis/test_state_features_study.py`)

Written on 30 Oct 2026, 07:55 SGT, from the script only (`73f8ad4`, sha256 `46e571f4…9b33`), before the study ran.
As RecordB20R170: what runs the engine runs in a temporary worktree of `73f8ad4`. It was dry-run on a rehearsal output
made there (the design test's worlds and budgets), where all three tests pass. The file has `json`, `Path`, `sys`,
`tempfile`, `unittest`, `ROOT` and `S`.

```python

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
```

## RecordB20R174 (append to `tests_genesis/test_search_vs_random_study.py`)

Written on 30 Oct 2026, 08:20 SGT, with the script (sha256 `842a9d73…2924`), before the study ran. It was dry-run on
a rehearsal output (the design test's small graphs, fake runner, `excluded=set()`, sizes (2, 4, 2), 10 evaluations),
where the replay and the CPU/verdict tests pass (the digest test then checks the real script). The file has `json`,
`Path`, `tempfile`, `unittest`, `ROOT` and `S`.

```python

R174 = ROOT / 'evidence' / 'search_vs_random_b20r174'


@unittest.skipUnless((R174 / 'summary.json').exists(), 'B20_R174 has not been recorded')
class RecordB20R174(unittest.TestCase):
    """The record of B20_R174 on its evidence: the script; the CPU medians; the whole study replayed from the saved
    runs (main on a copy of runs.jsonl with every engine run forbidden, so a missing run fails), which regenerates the
    graphs, re-derives the three random arms' samples, finalists and winners, the truth, validity, P1 and the
    verdict, to the same summary."""
    DIR, KW = R174, {}

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.runs = [json.loads(x) for x in (cls.DIR / 'runs.jsonl').read_text().splitlines() if x.strip()]

    def test_the_script(self):
        if self.DIR != R174:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r174_search_vs_random.py').read_bytes()).hexdigest(),
                         '842a9d730182a23b5c94790c81b858f1b3e70704b0b9a09d8f2e4122e5302924')

    def test_cpu_and_the_verdict(self):
        import statistics
        one = [r['cpu'] for r in self.runs if r['key'].endswith('|1')]
        self.assertEqual(self.s['validity']['cpu'], statistics.median(one) >= 0.9 * S.BUDGET)
        self.assertEqual(self.s['valid'], all(self.s['validity'].values()))
        self.assertEqual(self.s['verdict'], S.verdict(self.s['valid'], self.s['results']))
        self.assertEqual(len({r['key'] for r in self.runs}), len(self.runs))

    def test_the_study_replays_from_the_saved_runs(self):
        import shutil

        def forbidden(*a, **kw):
            raise AssertionError('a run missing from the evidence')
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(self.DIR / 'runs.jsonl', Path(d) / 'runs.jsonl')
            rc = S.main([d], registered=True, runner=forbidden, output=d, **self.KW)
            self.assertEqual(rc, 0)
            self.assertEqual((Path(d) / 'runs.jsonl').read_text(), (self.DIR / 'runs.jsonl').read_text())
            got = json.loads((Path(d) / 'summary.json').read_text())
        drop = ('code_identity',)
        self.assertEqual({k: v for k, v in got.items() if k not in drop},
                         {k: v for k, v in self.s.items() if k not in drop})
```

## RecordB20R159 (PT-1; append to `tests_genesis/test_proving_test_study.py`)

Written on 30 Oct 2026, 14:15 SGT, with the preregistered script (sha256 `56037017…3a05`), before the study ran. It
was dry-run on a rehearsal output made through the registered path on the design tests' invented families (the
posing functions patched), where both tests pass. It uses the test file's `SHA256` constant (set at the
preregistration's pin commit) and needs `json`, `Path`, `unittest`, `ROOT` and `S`.

```python

R159 = ROOT / 'evidence' / 'proving_test_b20r159'


@unittest.skipUnless((R159 / 'summary.json').exists(), 'B20_R159 has not been recorded')
class RecordB20R159(unittest.TestCase):
    """The record of PT-1 (B20_R159) on its evidence: the script; every certificate of every stage checked again by
    the kernel (A and C: the Rayleigh certificate and the second exact check; B: both invariant implementations); the
    families posed again from the sealed seed and the data seeds; the parts, the statistics, validity and the verdict
    recomputed from the saved stages."""
    DIR = R159

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.done = json.loads((cls.DIR / 'stages.json').read_text())

    def test_the_script(self):
        if self.DIR != R159:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r159_proving_test.py').read_bytes()).hexdigest(),
                         SHA256)

    def families(self):
        pa, na = S.posed_a(S.SEALED_SEED)
        pb, nb = S.posed_b(S.SEALED_SEED)
        pc, lc, wc = S.posed_c(S.SEALED_SEED, S.C_SEEDS)
        return pa, na, pb, nb, pc, lc, wc

    def test_every_certificate_checks_again_and_the_analysis_recomputes(self):
        pa, na, pb, nb, pc, lc, wc = self.families()
        self.assertEqual(self.s['C']['posed'], len(pc))
        self.assertEqual(self.s['C']['withheld'], len(wc))
        for key in ('A_P0', 'A_G', 'part3_replay'):
            rec = self.done.get(key)
            if rec is None:
                continue
            got = [p for p in rec['claimed'] if S.double_check(*pa[p], rec['artifacts'][p]) == 'CONFIRMED']
            self.assertEqual(sorted(got), sorted(rec['certified']), key)
        vb = S.b_verifier(nb)
        for fam, problems, ok in (('B', pb, lambda p, a: vb(p, a) > 0),
                                  ('C', pc, lambda p, a: S.double_check(*pc[p], a) == 'CONFIRMED')):
            for arm in S.ARMS_LATER:
                rec = self.done.get(f'{fam}_{arm}')
                if not rec or 'skipped' in rec:
                    continue
                mine = {p for p in rec['claimed'] if ok(p, rec['artifacts'][p])}
                self.assertTrue(mine <= set(rec['certified']), (fam, arm))
                self.assertTrue(set(rec['certified']) <= set(problems), (fam, arm))
        got = S.analyse(self.done, pa, pb, pc, na, nb, lc, wc, False)
        norm = lambda x: json.loads(json.dumps(x, sort_keys=True, default=list))          # noqa: E731
        for k in ('parts', 'stats', 'labels', 'discovery', 'discovery_bound', 'certified_A', 'part1', 'part3',
                  'certified_B', 'C', 'proved_equivalents_refuted', 'spent_ok'):
            self.assertEqual(norm(got[k]), norm(self.s[k]), k)
        self.assertTrue(self.s['pins_ok'])
        self.assertEqual(self.s['audit_hits'], [])
        self.assertEqual(self.s['valid'], got['valid'] and self.s['pins_ok'] and not self.s['audit_hits'])
        self.assertEqual(list(S.verdict(dict(got, valid=self.s['valid']))), [self.s['verdict'], self.s['failed']])
```

## RecordB20R175 (F6b; append to `tests_genesis/test_meta_repaired_study.py`)

Written on 30 Oct 2026, before the study ran, from the script at its preregistration (the commit and digest are the
design test's `PREREGISTRATION` and `SHA256`). Everything that runs the engine runs in a temporary worktree of the
preregistration commit, whose modules are the pinned ones. `KW` lets a rehearsal subclass check a small run made with
`main(..., registered=False, **KW)`; it was dry-run so on a rehearsal output made at `7878cdb` (the design test's
worlds and budgets), where all four tests pass. The file has `json`, `Path`, `sys`, `tempfile`, `unittest`, `ROOT`, `S`, `MT`,
`PREREGISTRATION` and `SHA256`.

```python

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
```

## RecordB20R177 (PT-2; append to `tests_genesis/test_proving_test_2_study.py`)

Written on 30 Oct 2026, with the script, before the study ran (amended at `25eadb7` and `75b5bac` after two
attempts crashed: the test file's `SHA256` is the second amendment's): RecordB20R159 with the per-bound gate (three
predecessor runs on A, A' and the discovery in A'). It was dry-run on a rehearsal output made through the registered
path on the design tests' invented families (the posing functions patched). It uses the test file's `SHA256` constant
and needs `json`, `Path`, `unittest`, `ROOT` and `S`.

```python

R177 = ROOT / 'evidence' / 'proving_test_2_b20r177'


@unittest.skipUnless((R177 / 'summary.json').exists(), 'B20_R177 has not been recorded')
class RecordB20R177(unittest.TestCase):
    """The record of PT-2 (B20_R177) on its evidence: the script; every certificate of every stage checked again by
    the kernel (A and C: the Rayleigh certificate and the second exact check; B: both invariant implementations); A'
    recomputed from the predecessor's runs and the discovery inside it; the families posed again from the sealed seed
    and the data seeds; the parts, the statistics, validity and the verdict recomputed from the saved stages."""
    DIR = R177

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((cls.DIR / 'summary.json').read_text())
        cls.done = json.loads((cls.DIR / 'stages.json').read_text())

    def test_the_script(self):
        if self.DIR != R177:
            return
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r177_proving_test_2.py').read_bytes()).hexdigest(),
                         SHA256)

    def families(self):
        pa, na = S.posed_a(S.SEALED_SEED)
        pb, nb = S.posed_b(S.SEALED_SEED)
        pc, lc, wc = S.posed_c(S.SEALED_SEED, S.C_SEEDS)
        return pa, na, pb, nb, pc, lc, wc

    def test_every_certificate_checks_again_and_the_analysis_recomputes(self):
        pa, na, pb, nb, pc, lc, wc = self.families()
        self.assertEqual(self.s['C']['posed'], len(pc))
        self.assertEqual(self.s['C']['withheld'], len(wc))
        gate_keys = [f'A_P0_{k}' for k in range(S.K_GATE)]
        for key in gate_keys + ['A_G', 'part3_replay']:
            rec = self.done.get(key)
            if rec is None:
                continue
            got = [p for p in rec['claimed'] if S.double_check(*pa[p], rec['artifacts'][p]) == 'CONFIRMED']
            self.assertEqual(sorted(got), sorted(rec['certified']), key)
        hit = {p for k in gate_keys for p in self.done[k]['certified']}
        beyond = sorted(p for p in pa if p not in hit)
        self.assertEqual(sorted(na[p] for p in beyond), self.s['beyond_p0'])
        if self.s['discovery'] is not None:
            self.assertIn(self.s['discovery'], beyond)
        vb = S.b_verifier(nb)
        for fam, problems, ok in (('B', pb, lambda p, a: vb(p, a) > 0),
                                  ('C', pc, lambda p, a: S.double_check(*pc[p], a) == 'CONFIRMED')):
            for arm in S.ARMS_LATER:
                rec = self.done.get(f'{fam}_{arm}')
                if not rec or 'skipped' in rec:
                    continue
                mine = {p for p in rec['claimed'] if ok(p, rec['artifacts'][p])}
                self.assertTrue(mine <= set(rec['certified']), (fam, arm))
                self.assertTrue(set(rec['certified']) <= set(problems), (fam, arm))
        got = S.analyse(self.done, pa, pb, pc, na, nb, lc, wc, False)
        norm = lambda x: json.loads(json.dumps(x, sort_keys=True, default=list))          # noqa: E731
        for k in ('parts', 'stats', 'labels', 'discovery', 'discovery_bound', 'certified_A', 'beyond_p0', 'part1',
                  'part3', 'certified_B', 'C', 'proved_equivalents_refuted', 'spent_ok'):
            self.assertEqual(norm(got[k]), norm(self.s[k]), k)
        self.assertTrue(self.s['pins_ok'])
        self.assertEqual(self.s['audit_hits'], [])
        self.assertEqual(self.s['valid'], got['valid'] and self.s['pins_ok'] and not self.s['audit_hits'])
        self.assertEqual(list(S.verdict(dict(got, valid=self.s['valid']))), [self.s['verdict'], self.s['failed']])
```

## RecordB20R178 (SR-1a; append to `tests_genesis/test_repair_bench_study.py`)

Dry-run on the rehearsal (`--rehearse`, development defects only) before the sealed run.

```python
R178 = ROOT / 'evidence' / 'repair_bench_b20r178'


class RecordB20R178(unittest.TestCase):
    """The record of SR-1a (B20_R178) on its evidence: the script and the sealed catalogue; the verdicts and tables
    recomputed from the rows and the isolation report; every promoted component source verified again by the kernel
    verifier on a rebuilt job; no control proposed or changed anything; nothing outside a job's component promoted."""
    DIR = R178

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())

    def test_the_script_and_the_catalogue(self):
        if self.DIR == R178:
            self.assertEqual(digest(ROOT / 'scripts/b20r178_repair_bench.py'), SHA256)
        self.assertEqual(self.result['defects_sha256'], S.DEFECTS_SHA256)

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.result['retention']['vault_entries_dev'],
                        self.result['retention']['vault_entries_grown'])
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'obstacles', 'milestone_obstacles', 'per_arm',
                  'comparison', 'reuse', 'retention', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_promoted_source_verifies_again(self):
        from genesis.repairkernel import verify as VF
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'))
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 2]
        self.assertEqual(len(controls), 12)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R180 (SR-1a2; append to `tests_genesis/test_repair_bench_2_study.py`)

Dry-run on the rehearsal (`--rehearse`, six development defects) before the sealed run.

```python
R180 = ROOT / 'evidence' / 'repair_bench_2_b20r180'


class RecordB20R180(unittest.TestCase):
    """The record of SR-1a2 (B20_R180) on its evidence: the script and both catalogues; the verdicts and tables
    recomputed from the rows and the isolation report; every promoted component source verified again by the kernel
    verifier (version 2: the resource check, rollback) on a rebuilt job interrupted at the same operation; the 18
    controls."""
    DIR = R180

    @classmethod
    def setUpClass(cls):
        import json
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())

    def test_the_script_and_the_catalogues(self):
        if self.DIR == R180:
            self.assertEqual(digest(ROOT / 'scripts/b20r180_repair_bench_2.py'), SHA256)
        self.assertEqual(self.result['defects2_sha256'], S.DEFECTS2_SHA256)
        self.assertEqual(self.result['job_version'], 2)

    def test_the_verdicts_recompute(self):
        import json
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.result['retention']['vault_entries_dev'],
                        self.result['retention']['vault_entries_grown'])
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'obstacles', 'milestone_obstacles', 'per_arm',
                  'comparison', 'reuse', 'retention', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 2]
        self.assertEqual(len(controls), 18)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R181 (SR-1a3; append to `tests_genesis/test_repair_bench_3_study.py`)

Dry-run on the rehearsal (`--rehearse`, six development defects (three of them the operators' sources)) before the sealed run.

```python
R181 = ROOT / 'evidence' / 'repair_bench_3_b20r181'


class RecordB20R181(unittest.TestCase):
    """The record of SR-1a3 (B20_R181) on its evidence: the script and both catalogues; the verdicts and tables
    recomputed from the rows and the isolation report; every promoted component source verified again by the kernel
    verifier (version 2: the resource check, rollback) on a rebuilt job interrupted at the same operation; the 24
    controls."""
    DIR = R181

    @classmethod
    def setUpClass(cls):
        import json
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())

    def test_the_script_and_the_catalogues(self):
        if self.DIR == R181:
            self.assertEqual(digest(ROOT / 'scripts/b20r181_repair_bench_3.py'), SHA256)
        self.assertEqual(self.result['defects3_sha256'], S.DEFECTS3_SHA256)
        self.assertEqual(self.result['job_version'], 2)

    def test_the_verdicts_recompute(self):
        import json
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.result['retention']['vault_entries_dev'],
                        self.result['retention']['vault_entries_grown'])
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'obstacles', 'milestone_obstacles', 'per_arm',
                  'comparison', 'invention_reach', 'loop_operators', 'reuse', 'retention',
                  'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 2]
        self.assertEqual(len(controls), 24)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R182 (SR-2a; append to `tests_genesis/test_rule_invention_study.py`)

Dry-run on the rehearsal (`--rehearse`) before the sealed run.

```python
R182 = ROOT / 'evidence' / 'rule_invention_b20r182'


class RecordB20R182(unittest.TestCase):
    """The record of SR-2a (B20_R182) on its evidence: the script and the catalogue; the verdicts and tables recomputed
    from the rows, the isolation report and Genesis's frozen library; every admitted rule admitted by a verified
    repair of another family, in a probe row that names it; every promoted component source verified again; the
    30 controls."""
    DIR = R182

    @classmethod
    def setUpClass(cls):
        import json
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        lib = cls.DIR / 'genesis_library'
        cls.library = [json.loads(x) for x in (lib / 'rules.jsonl').read_text().splitlines() if x.strip()] \
            if (lib / 'rules.jsonl').exists() else []
        cls.inventor = json.loads((lib / 'inventor.json').read_text()) if (lib / 'inventor.json').exists() else {}

    def test_the_script_and_the_catalogue(self):
        if self.DIR == R182:
            self.assertEqual(digest(ROOT / 'scripts/b20r182_rule_invention.py'), SHA256)
        self.assertEqual(self.result['defects4_sha256'], S.DEFECTS4_SHA256)

    def test_the_verdicts_recompute(self):
        import json
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.library, self.inventor)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'invention', 'obstacles', 'milestone',
                  'milestone_obstacles', 'per_arm', 'comparison', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_rule_was_admitted_by_another_familys_verified_repair(self):
        for r in self.library:
            if r['status'] != 'admitted':
                continue
            self.assertTrue(r['admitted_by'])
            self.assertNotIn(r['provenance']['family'], r['admitted_by'])
            probes = [x for x in self.rows if x['phase'].startswith('admit') and x['rule'] and x['rule']['id'] == r['id']
                      and x['rule']['after'] == 'admitted']
            self.assertTrue(probes, r['id'])
            self.assertTrue(any(S.repaired(x) and x['name'] in r['admitted_by'] for x in probes), r['id'])

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R183 (SR-2b; append to `tests_genesis/test_rule_invention_replica_study.py`)

Dry-run on the rehearsal (`--rehearse`) before the sealed run.

```python
R183 = ROOT / 'evidence' / 'rule_invention_b20r183'


class RecordB20R183(unittest.TestCase):
    """The record of SR-2b (B20_R183) on its evidence: the script and the catalogue; the verdicts, the step-6
    comparison and the replication table recomputed from the rows, the isolation report and Genesis's frozen library;
    every admitted rule admitted by a verified repair of another family, in a probe row that names it; every promoted
    component source verified again; the 30 controls."""
    DIR = R183

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        lib = cls.DIR / 'genesis_library'
        cls.library = [json.loads(x) for x in (lib / 'rules.jsonl').read_text().splitlines() if x.strip()] \
            if (lib / 'rules.jsonl').exists() else []
        cls.inventor = json.loads((lib / 'inventor.json').read_text()) if (lib / 'inventor.json').exists() else {}

    def test_the_script_the_catalogue_and_the_seeds(self):
        if self.DIR == R183:
            self.assertEqual(digest(ROOT / 'scripts/b20r183_rule_invention_replica.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects4_sha256'], S.DEFECTS4_SHA256)
        self.assertEqual(self.result['seeds'], {'detect': 4, 'admit': 5, 'search': 1, 'control': 9})
        self.assertEqual(self.result['job_seeds'], [6, 7, 8])
        self.assertTrue(all(r['seed'] in (4, 5, 6, 7, 8, 9) for r in self.rows))

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.library, self.inventor)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'invention', 'obstacles', 'milestone',
                  'milestone_obstacles', 'per_arm', 'comparison', 'inventor', 'replication', 'replicated',
                  'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_rule_was_admitted_by_another_familys_verified_repair(self):
        for r in self.library:
            if r['status'] != 'admitted':
                continue
            self.assertTrue(r['admitted_by'])
            self.assertNotIn(r['provenance']['family'], r['admitted_by'])
            probes = [x for x in self.rows if x['phase'].startswith('admit') and x['rule'] and x['rule']['id'] == r['id']
                      and x['rule']['after'] == 'admitted']
            self.assertTrue(probes, r['id'])
            self.assertTrue(any(S.repaired(x) and x['name'] in r['admitted_by'] for x in probes), r['id'])

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R185 (SR-2c; append to `tests_genesis/test_space_invention_study.py`)

Dry-run on the rehearsal (`--rehearse`) before the sealed run.

```python
R185 = ROOT / 'evidence' / 'space_invention_b20r185'


class RecordB20R185(unittest.TestCase):
    """The record of SR-2c (B20_R185) on its evidence: the script and the catalogue; the verdict, the generations,
    the tables, the three questions with Holm's adjustment and the invented reach recomputed from the rows, the
    isolation report and the frozen libraries; every admitted transformation admitted by a verified repair of a
    family it did not come from (nor its parents), in a probe row that names it; generation 1's admissions kept in
    generation 2; the test vaults differ in their transformations only; every promoted source verified again; the
    30 controls."""
    DIR = R185

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        cls.g1 = S._store(cls.DIR / 'genesis_g1', 'transforms.jsonl')
        cls.g2 = S._store(cls.DIR / 'genesis_g2', 'transforms.jsonl')
        p = cls.DIR / 'genesis_g2' / 'deriver.json'
        cls.deriver = json.loads(p.read_text()) if p.exists() else {}

    def test_the_script_and_the_catalogue(self):
        if self.DIR == R185:
            self.assertEqual(digest(ROOT / 'scripts/b20r185_space_invention.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects5_sha256'], S.DEFECTS5_SHA256)
        self.assertEqual(self.result['job_seeds'], [11, 12, 13])

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.g1, self.g2, self.deriver)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'generations', 'obstacles', 'per_arm', 'questions',
                  'secondary', 'invented_reach', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_transformation_was_admitted_by_a_family_it_did_not_come_from(self):
        for t in self.g2:
            if t['status'] != 'admitted':
                continue
            own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
            self.assertTrue(t['admitted_by'])
            self.assertFalse(own & set(t['admitted_by']), t['id'])
            probes = [x for x in self.rows if x['phase'].startswith('probe') and x['transform']
                      and x['transform']['id'] == t['id'] and x['transform']['after'] == 'admitted']
            self.assertTrue(any(S.repaired(x) and x['name'] in t['admitted_by'] for x in probes), t['id'])
        ids1 = {t['id'] for t in self.g1 if t['status'] == 'admitted'}
        ids2 = {t['id'] for t in self.g2 if t['status'] == 'admitted'}
        self.assertTrue(ids1 <= ids2)

    def test_the_test_vaults_differ_in_their_transformations_only(self):
        a, b = self.DIR / 'test_vault_g1', self.DIR / 'test_vault_g2'
        names = sorted(f.name for f in a.iterdir())
        self.assertEqual(names, sorted(f.name for f in b.iterdir()))
        for n in names:
            if n != 'transforms.jsonl':
                self.assertEqual((a / n).read_bytes(), (b / n).read_bytes(), n)
        self.assertEqual(S._store(a, 'transforms.jsonl'), self.g1)
        self.assertEqual(S._store(b, 'transforms.jsonl'), self.g2)

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R186 (SR-2c'; append to `tests_genesis/test_space_invention_replica_study.py`)

Dry-run on the rehearsal (`--rehearse`) before the sealed run.

```python
R186 = ROOT / 'evidence' / 'space_invention_b20r186'


class RecordB20R186(unittest.TestCase):
    """The record of SR-2c' (B20_R186) on its evidence: the script, the catalogue and the seeds; the verdict, the
    generations, the tables, the three questions with Holm's adjustment, the invented reach and the replication table
    recomputed; every admitted transformation admitted by a family it (and its parents) did not come from, in a probe
    row naming it; generation 1's admissions kept; the test vaults differ in their transformations only; every
    promoted source verified again; the 30 controls."""
    DIR = R186

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        cls.g1 = S._store(cls.DIR / 'genesis_g1', 'transforms.jsonl')
        cls.g2 = S._store(cls.DIR / 'genesis_g2', 'transforms.jsonl')
        p = cls.DIR / 'genesis_g2' / 'deriver.json'
        cls.deriver = json.loads(p.read_text()) if p.exists() else {}

    def test_the_script_the_catalogue_and_the_seeds(self):
        if self.DIR == R186:
            self.assertEqual(digest(ROOT / 'scripts/b20r186_space_invention_replica.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects6_sha256'], S.DEFECTS6_SHA256)
        self.assertEqual(self.result['job_seeds'], [14, 15, 16])
        self.assertEqual(self.result['seeds'], {'detect1': 31, 'probe1': 32, 'learn2': 33, 'probe2': 34, 'controls': 35})
        self.assertTrue(all(r['seed'] in (14, 15, 16, 31, 32, 33, 34, 35) for r in self.rows))

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.g1, self.g2, self.deriver)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'generations', 'obstacles', 'per_arm', 'questions',
                  'secondary', 'invented_reach', 'replication', 'replicated', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_transformation_was_admitted_by_a_family_it_did_not_come_from(self):
        for t in self.g2:
            if t['status'] != 'admitted':
                continue
            own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
            self.assertTrue(t['admitted_by'])
            self.assertFalse(own & set(t['admitted_by']), t['id'])
            probes = [x for x in self.rows if x['phase'].startswith('probe') and x['transform']
                      and x['transform']['id'] == t['id'] and x['transform']['after'] == 'admitted']
            self.assertTrue(any(S.repaired(x) and x['name'] in t['admitted_by'] for x in probes), t['id'])
        ids1 = {t['id'] for t in self.g1 if t['status'] == 'admitted'}
        ids2 = {t['id'] for t in self.g2 if t['status'] == 'admitted'}
        self.assertTrue(ids1 <= ids2)

    def test_the_test_vaults_differ_in_their_transformations_only(self):
        a, b = self.DIR / 'test_vault_g1', self.DIR / 'test_vault_g2'
        names = sorted(f.name for f in a.iterdir())
        self.assertEqual(names, sorted(f.name for f in b.iterdir()))
        for n in names:
            if n != 'transforms.jsonl':
                self.assertEqual((a / n).read_bytes(), (b / n).read_bytes(), n)
        self.assertEqual(S._store(a, 'transforms.jsonl'), self.g1)
        self.assertEqual(S._store(b, 'transforms.jsonl'), self.g2)

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```

## RecordB20R187 (SR-2d; append to `tests_genesis/test_third_generation_study.py`)

Dry-run on the rehearsal (`--rehearse`) before the sealed run.

```python
import json  # noqa: E402

R187 = ROOT / 'evidence' / 'third_generation_b20r187'


class RecordB20R187(unittest.TestCase):
    """The record of SR-2d (B20_R187) on its evidence: the script, the catalogue and the seeds; the verdict, the three
    generations, the tables, the questions with Holm's adjustment and the invented reach recomputed; every admitted
    transformation admitted by a family it (and its parents) did not come from, in a probe row naming it; each
    generation's admissions kept in the next; the test vaults differ in their transformations only; every promoted
    source verified again; the 30 controls."""
    DIR = R187

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((cls.DIR / 'result.json').read_text())
        cls.rows = [json.loads(x) for x in (cls.DIR / 'rows.jsonl').read_text().splitlines() if x.strip()]
        cls.episodes = [json.loads(x) for x in (cls.DIR / 'episodes.jsonl').read_text().splitlines() if x.strip()]
        cls.iso = json.loads((cls.DIR / 'isolation.json').read_text())
        cls.g = {g: S._store(cls.DIR / f'genesis_{g}', 'transforms.jsonl') for g in ('g1', 'g2', 'g3')}
        p = cls.DIR / 'genesis_g3' / 'deriver.json'
        cls.deriver = json.loads(p.read_text()) if p.exists() else {}

    def test_the_script_the_catalogue_and_the_seeds(self):
        if self.DIR == R187:
            self.assertEqual(digest(ROOT / 'scripts/b20r187_third_generation.py'), SHA256)
            self.assertEqual(self.result['script_sha256'], SHA256)
        self.assertEqual(self.result['defects7_sha256'], S.DEFECTS7_SHA256)
        self.assertEqual(self.result['job_seeds'], [17, 18, 19])
        self.assertTrue(all(r['seed'] in set(S.JOB_SEEDS) | set(S.SEEDS.values()) for r in self.rows))

    def test_the_verdicts_recompute(self):
        got = S.analyse(self.rows, self.iso, self.result['heldout_used'], self.g['g1'], self.g['g2'], self.g['g3'],
                        self.deriver)
        for k in ('verdict', 'isolation_ok', 'controls_ok', 'generations', 'obstacles', 'per_arm', 'questions',
                  'secondary', 'invented_reach', 'promotions_outside_component'):
            self.assertEqual(json.loads(json.dumps(got[k])), self.result[k], k)

    def test_every_admitted_transformation_was_admitted_by_a_family_it_did_not_come_from(self):
        for t in self.g['g3']:
            if t['status'] != 'admitted':
                continue
            own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
            self.assertTrue(t['admitted_by'])
            self.assertFalse(own & set(t['admitted_by']), t['id'])
            probes = [x for x in self.rows if x['phase'].startswith('probe') and x['transform']
                      and x['transform']['id'] == t['id'] and x['transform']['after'] == 'admitted']
            self.assertTrue(any(S.repaired(x) and x['name'] in t['admitted_by'] for x in probes), t['id'])
        ids = {g: {t['id'] for t in self.g[g] if t['status'] == 'admitted'} for g in self.g}
        self.assertTrue(ids['g1'] <= ids['g2'] <= ids['g3'])

    def test_the_test_vaults_differ_in_their_transformations_only(self):
        vs = {g: self.DIR / f'test_vault_{g}' for g in ('g1', 'g2', 'g3')}
        names = sorted(f.name for f in vs['g3'].iterdir())
        for g, v in vs.items():
            self.assertEqual(sorted(f.name for f in v.iterdir()), names, g)
            for n in names:
                if n != 'transforms.jsonl':
                    self.assertEqual((v / n).read_bytes(), (vs['g3'] / n).read_bytes(), (g, n))
            self.assertEqual(S._store(v, 'transforms.jsonl'), self.g[g])

    def test_every_promoted_source_verifies_again(self):
        rows = {r['key']: r for r in self.rows}
        n = 0
        with tempfile.TemporaryDirectory() as d:
            for e in self.episodes:
                r = rows[e['key']]
                if not r['promoted']:
                    self.assertIsNone(e['final_source'], e['key'])
                    continue
                job, _ = BN.make(r['name'], r['seed'], Path(d) / e['key'].replace('/', '_'), version=2)
                self.assertEqual(job.run()['op'], r['interrupted_at'])
                v = VF.verify(job.dir, job.target, job.seed, job.n_ops, job.every, e['final_source'])
                self.assertTrue(v['accepted'], e['key'])
                n += 1
        self.assertGreater(n, 0)

    def test_no_control_proposed_or_changed_anything(self):
        controls = [r for r in self.rows if r['phase'] == 'controls']
        self.assertEqual(len(controls), 30)
        for r in controls:
            self.assertTrue(S.control_passes(r), r['key'])
```
