# Draft record tests for B20_R151 and B20_R152 (not yet in the test suite)

These are written before the studies finish, from the scripts only (no study data seen). When a study exits 0,
copy its evidence into `evidence/`, append the matching class to its design test file, run it, and adjust
**only** what the saved summary's actual structure requires (never a threshold or rule). Each class skips itself
until its `summary.json` exists.

The helper `scratchpad/r151_report.py` text is included at the end: it prints every number the record needs from
B20_R151's `summary.json`.

## RecordB20R151 (append to `tests_genesis/test_expressiveness_study.py`)

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
