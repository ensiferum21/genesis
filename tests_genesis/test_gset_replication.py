"""B20_R109: the replication on Gset (design): seeds, the per-instance means, the three sign tests including the
stringent one, the headline, record candidates flagged never claimed, and the registered output."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r109_gset_replication as M  # noqa: E402


def rows(n, mcx, tools, fam='random'):
    return [{'instance': f'G{i + 1}', 'family': fam, 'earlier': {'mcx': mcx, 'burer': tools, 'dsb': tools},
             'new': {'mcx': [mcx, mcx], 'burer': [tools, tools], 'dsb': [tools, tools]}} for i in range(n)]


class Design(unittest.TestCase):
    def test_seeds_differ(self):
        seeds = {M.run_seed(f'gset-G{k}', a, r) for k in range(1, 55) for a in M.ARMS for r in range(M.REPLICATES)}
        self.assertEqual(len(seeds), 54 * 3 * 2)

    def test_analysis(self):
        best = {f'G{i + 1}': 100 for i in range(54)}
        a = M.analyse(rows(54, 100, 99), best)
        self.assertEqual(a['headline'], 'REPLICATED')
        self.assertEqual(a['tests']['mcx worst new vs tools best new']['label'], 'AHEAD')
        self.assertEqual(a['per_arm']['mcx']['instances_reaching_best_known'], 54)
        self.assertEqual(a['record_candidates'], [])
        a = M.analyse(rows(54, 99, 100), best)
        self.assertEqual(a['headline'], 'NOT_REPLICATED')
        r = rows(54, 100, 99)
        for x in r:
            x['new']['dsb'] = [101, 99]
            x['earlier']['dsb'] = 101
        a = M.analyse(r, best)
        self.assertEqual((a['tests']['mcx vs dsb']['label'], a['headline']), ('BEHIND', 'PARTLY'))
        self.assertEqual(len(a['record_candidates']), 54)           # dSB's 101: flagged, never claimed
        self.assertEqual(a['tests']['mcx worst new vs tools best new']['label'], 'BEHIND')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])



class RecordB20R109(unittest.TestCase):
    """B20_R109's record: the tests and figures recompute from the rows; the earlier values are B20_R102's and
    B20_R106's recorded runs."""

    def test_recomputes(self):
        import json
        from genesis import gset as GS
        ev = ROOT / 'evidence' / 'gset_replication_b20r109'
        s = json.loads((ev / 'summary.json').read_text())
        rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual([r['instance'] for r in rows], [f'G{k}' for k in range(1, 55)])
        a = json.loads(json.dumps(M.analyse(rows, GS.best_known(as_of='2026-10-24T12:00:00+08:00'))))
        for k in ('tests', 'headline', 'per_arm', 'record_candidates'):
            self.assertEqual(a[k], s[k], k)
        self.assertEqual(s['headline'], 'REPLICATED')
        r102 = {r['instance']: r for r in map(json.loads, (M.R102 / 'rows.jsonl').read_text().splitlines()) if r}
        r106 = {r['instance']: r for r in map(json.loads, (M.R106 / 'rows.jsonl').read_text().splitlines()) if r}
        for r in rows:
            self.assertEqual(r['earlier'], {'mcx': r106[r['instance']]['runs']['chosen@10']['value'],
                                            'burer': r102[r['instance']]['runs']['burer']['10']['value'],
                                            'dsb': r102[r['instance']]['runs']['dsb']['10']['value']})
            self.assertEqual(len(r['runs']), 6)


if __name__ == '__main__':
    unittest.main()
