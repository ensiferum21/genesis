"""B20_R106: mcx-v1 on Gset against B20_R102's tools (design): the comparators read from B20_R102's rows, the seven
sign tests and the headline, record candidates flagged (never claimed), the refusals before B20_R102 and B20_R105
have finished validly, and the registered output."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r106_mcx_gset as M  # noqa: E402


def r102_row(burer, dsb, others):
    runs = {'burer': {'1': {'value': burer[0]}, '10': {'value': burer[1]}},
            'dsb': {'1': {'value': dsb[0]}, '10': {'value': dsb[1]}}}
    for i, v in enumerate(others):
        runs[f'h{i}'] = {'10': {'value': v}}
    return {'runs': runs}


def rows(n, chosen, other, fam='random'):
    return [{'instance': f'G{i + 1}', 'family': fam, 'class': fam, 'chosen@1': chosen, 'chosen@10': chosen,
             'default@1': other, 'default@10': other, 'burer@1': other, 'burer@10': other, 'dsb@1': other,
             'dsb@10': other, 'vbs@10': other} for i in range(n)]


class Design(unittest.TestCase):
    def test_tests(self):
        self.assertEqual(len(M.TESTS), 7)
        self.assertAlmostEqual(M.ALPHA, 0.05 / 7)
        self.assertIn(('chosen@10', 'vbs@10'), M.TESTS)

    def test_comparators(self):
        c = M.comparators(r102_row((10, 12), (9, 11), (13, None, 8)))
        self.assertEqual(c, {'burer@1': 10, 'burer@10': 12, 'dsb@1': 9, 'dsb@10': 11, 'vbs@10': 13})

    def test_headline_and_records(self):
        best = {f'G{i + 1}': 100 for i in range(54)}
        a = M.analyse(rows(54, 101, 99), best)
        self.assertEqual(a['headline'], 'MCX_LEADS')
        self.assertEqual(a['tests']['chosen@10 vs vbs@10']['label'], 'AHEAD')
        self.assertEqual(len(a['record_candidates']), 54 * 2)                  # chosen@1 and @10; never comparators
        self.assertEqual(a['classifier_agrees_with_gset_family'], 1.0)
        a = M.analyse(rows(54, 99, 101), best)
        self.assertEqual(a['headline'], 'MCX_BEHIND')
        self.assertEqual({c['arm'] for c in a['record_candidates']}, {'default@1', 'default@10'})   # mcx arms only
        mixed = rows(27, 101, 100) + [dict(r, instance=f'G{i + 28}') for i, r in enumerate(rows(27, 100, 101))]
        self.assertEqual(M.analyse(mixed, best)['headline'], 'MCX_COMPARABLE')
        tie = M.sign_test(rows(10, 5, 5), 'chosen@1', 'burer@1')
        self.assertEqual((tie['ties'], tie['p'], tie['label']), (10, 1.0, 'COMPARABLE'))

    def test_refuses_before_the_inputs_exist(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(M, 'R105', Path(d) / 'a'), mock.patch.object(M, 'R102', Path(d) / 'b'):
                with self.assertRaises(SystemExit):
                    M.inputs()
            for name in ('a', 'b'):
                (Path(d) / name).mkdir()
                (Path(d) / name / 'summary.json').write_text(json.dumps({'valid': True, 'configs_sha256': 'x'}))
            (Path(d) / 'a' / 'configs.json').write_text('{}')
            with mock.patch.object(M, 'R105', Path(d) / 'a'), mock.patch.object(M, 'R102', Path(d) / 'b'):
                with self.assertRaises(SystemExit):                            # configs.json not the recorded one
                    M.inputs()

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


class RecordB20R106(unittest.TestCase):
    """B20_R106's record: the tests, headline and per-arm figures recompute from the rows; the comparators are
    B20_R102's recorded runs; the configurations are B20_R105's."""

    @classmethod
    def setUpClass(cls):
        ev = ROOT / 'evidence' / 'mcx_gset_b20r106'
        cls.s = json.loads((ev / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_analysis_recomputes(self):
        from genesis import gset as GS
        self.assertEqual([r['instance'] for r in self.rows], [f'G{k}' for k in range(1, 55)])
        flat = [dict({k: v for k, v in r.items() if k != 'runs'}, **{a: x['value'] for a, x in r['runs'].items()})
                for r in self.rows]
        a = json.loads(json.dumps(M.analyse(flat, GS.best_known(as_of='2026-10-24T12:00:00+08:00'))))
        for k in ('tests', 'headline', 'per_arm', 'record_candidates', 'classifier_agrees_with_gset_family'):
            self.assertEqual(a[k], self.s[k], k)

    def test_inputs_are_the_recorded_ones(self):
        from genesis.common import digest
        configs, r102 = M.inputs()
        self.assertEqual(digest(configs), self.s['configs_sha256'])
        for r in self.rows:
            self.assertEqual({k: r[k] for k in ('burer@1', 'burer@10', 'dsb@1', 'dsb@10', 'vbs@10')},
                             M.comparators(r102[r['instance']]), r['instance'])

if __name__ == '__main__':
    unittest.main()
