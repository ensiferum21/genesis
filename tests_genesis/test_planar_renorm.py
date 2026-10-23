"""B20_R113: does renormalisation close the planar gap? (design): fresh seed, the two configurations read as recorded,
the planar graphs, the Part A label, the Part B summary with record candidates flagged, and the registered output;
the record."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r113_planar_renorm as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r113_planar_renorm.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_configs(self):
        c = M.configs()
        self.assertEqual((c['INCUMBENT']['rs'], c['RENORM']['rs'], c['RENORM']['L0']), (1, 2, 0.2))

    def test_planar_instances(self):
        from genesis import gset as GS
        fams = {t.family for t in GS.tasks(list(M.PLANAR_GSET))}
        self.assertEqual(len(M.PLANAR_GSET), 20)
        self.assertTrue(all('planar' in f for f in fams))

    def test_part_a_label(self):
        v = {f'g{i}': {'INCUMBENT': 1000 + i, 'RENORM': 1003 + i} for i in range(40)}
        self.assertEqual(M.part_a_label(v)['label'], 'RENORM_BETTER')
        v = {f'g{i}': {'INCUMBENT': 1000 + i, 'RENORM': 1000 + i} for i in range(40)}
        self.assertEqual(M.part_a_label(v)['label'], 'NO_DIFFERENCE')

    def test_part_b_summary(self):
        best = {f'G{i}': 100 for i in M.PLANAR_GSET}
        rows = [{'instance': f'G{i}', 'value': 100, 'incumbent_60': 99} for i in M.PLANAR_GSET]
        s = M.part_b_summary(rows, best)
        self.assertEqual((s['label'], s['reach_best_known'], s['record_candidates']), ('RENORM_BETTER', 20, []))
        rows[0]['value'] = 101
        self.assertEqual(len(M.part_b_summary(rows, best)['record_candidates']), 1)

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R113(unittest.TestCase):
    """B20_R113's record: Part A's label and Part B's summary recompute from the runs; the configurations are the
    recorded ones; Part B's incumbents are B20_R110's 60 s values."""

    def test_recomputes(self):
        from genesis import gset as GS
        ev = ROOT / 'evidence' / 'planar_renorm_b20r113'
        s = json.loads((ev / 'summary.json').read_text())
        runs = [json.loads(l) for l in (ev / 'runs.jsonl').read_text().splitlines() if l.strip()]
        self.assertTrue(s['valid'])
        self.assertEqual(s['configs'], M.configs())
        va = {}
        for r in runs:
            if r['part'] == 'A':
                va.setdefault(r['task'], {})[r['arm']] = r['value']
        self.assertEqual(len(va), M.N_GRAPHS)
        self.assertEqual(va, s['part_a_values'])
        a = json.loads(json.dumps(M.part_a_label(va)))
        self.assertEqual(a, s['part_a'])
        self.assertEqual((a['label'], a['wins'], a['losses']), ('RENORM_BETTER', 25, 8))
        r110 = {r['instance']: r['value'] for r in map(json.loads, (M.R110 / 'rows.jsonl').read_text().splitlines()) if r}
        b = {r['task'].split('-')[1]: r['value'] for r in runs if r['part'] == 'B'}
        self.assertEqual(sorted(b, key=lambda g: int(g[1:])), [f'G{k}' for k in M.PLANAR_GSET])
        rows = [{'instance': g, 'value': b[g], 'incumbent_60': r110[g]} for g in sorted(b, key=lambda g: int(g[1:]))]
        self.assertEqual(rows, s['part_b']['rows'])
        pb = json.loads(json.dumps(M.part_b_summary(rows, GS.best_known())))
        self.assertEqual(pb, {k: v for k, v in s['part_b'].items() if k != 'rows'})
        self.assertEqual((pb['label'], pb['wins'], pb['losses'], pb['reach_best_known'], pb['record_candidates']),
                         ('RENORM_BETTER', 13, 2, 5, []))


if __name__ == '__main__':
    unittest.main()
