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


if __name__ == '__main__':
    unittest.main()
