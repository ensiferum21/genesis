"""The test matrix's reports (`scripts/run_test_matrix.py`): a report says which commit it tested and whether the tree
was clean; a matrix split across jobs (`--suites`) merges into one release report only if every part tested the same
clean commit and the parts cover the release profile's suites exactly once (`make_checkpoint.py --reports`); a suite
split into shards (`--shard K/N`, every N-th test module) merges only if the shards are 1..N and cover its modules
exactly once."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_test_matrix as M  # noqa: E402


def part(names, commit='c' * 40, clean=True, ok=True, profile='release'):
    return {'profile': profile, 'python': '3.13', 'commit': commit, 'clean': clean, 'selected': sorted(names),
            'suites': [{'suite': n, 'ran': 10, 'skipped': 0, 'ok': ok} for n in names]}


class Merge(unittest.TestCase):
    def setUp(self):
        self.all = M.release_suites()
        self.assertIn('integration', self.all)

    def test_parts_merge_into_one_release_report(self):
        rest = [n for n in self.all if n != 'integration']
        m = M.merge([part(['integration']), part(rest)], 'c' * 40)
        self.assertTrue(m['all_ok'])
        self.assertEqual(m['selected'], self.all)
        self.assertEqual(m['total_ran'], 10 * len(self.all))
        self.assertEqual(m['merged_from'], 2)
        self.assertFalse(M.merge([part(['integration'], ok=False), part(rest)], 'c' * 40)['all_ok'])

    def test_refusals(self):
        rest = [n for n in self.all if n != 'integration']
        for bad in ([part(['integration'], commit='d' * 40), part(rest)],          # another commit
                    [part(['integration'], clean=False), part(rest)],            # a dirty tree
                    [part(['integration'], profile='commit'), part(rest)],       # not the release profile
                    [part(['integration'])],                                     # a suite missing
                    [part(['integration']), part(self.all)]):                    # a suite twice
            with self.assertRaises(ValueError):
                M.merge(bad, 'c' * 40)

    def test_shards(self):
        names = M.modules('tests_genesis')
        self.assertIn('tests_genesis.test_matrix_reports', names)
        self.assertEqual(names, sorted(names))
        cut = [M.shard_of(names, k, 3) for k in (1, 2, 3)]
        self.assertEqual(sorted(m for c in cut for m in c), names)
        self.assertEqual(sum(len(c) for c in cut), len(names))
        with self.assertRaises(ValueError):
            M.shard_of(names, 4, 3)
        self.assertEqual(M.command('tests_genesis', cut[0])[-len(cut[0]):], cut[0])
        self.assertIn('discover', M.command('tests_genesis'))

    def shard(self, k, n, mods, ok=True, commit='c' * 40):
        r = part(['integration'], commit=commit, ok=ok)
        r['suites'][0].update(shard=[k, n], modules=mods, directory='tests_genesis', failures=0, errors=0, skips=[],
                              seconds=1.0)
        return r

    def test_shards_merge(self):
        rest = [n for n in self.all if n != 'integration']
        names = M.modules('tests_genesis')
        cut = [M.shard_of(names, k, 3) for k in (1, 2, 3)]
        m = M.merge([self.shard(k, 3, cut[k - 1]) for k in (1, 2, 3)] + [part(rest)], 'c' * 40)
        self.assertTrue(m['all_ok'])
        self.assertEqual(m['selected'], self.all)
        integ = next(x for x in m['suites'] if x['suite'] == 'integration')
        self.assertEqual((integ['shards'], integ['ran']), (3, 30))
        bad_ok = [self.shard(1, 3, cut[0], ok=False), self.shard(2, 3, cut[1]), self.shard(3, 3, cut[2]), part(rest)]
        self.assertFalse(M.merge(bad_ok, 'c' * 40)['all_ok'])
        for bad in ([self.shard(1, 3, cut[0]), self.shard(2, 3, cut[1]), part(rest)],              # a shard missing
                    [self.shard(1, 3, cut[0]), self.shard(2, 3, cut[1]), self.shard(2, 3, cut[2]), part(rest)],
                    [self.shard(1, 3, cut[0]), self.shard(2, 3, cut[1]), self.shard(3, 3, cut[2][1:]), part(rest)],
                    [self.shard(1, 3, cut[0]), self.shard(2, 3, cut[1] + cut[0][:1]), self.shard(3, 3, cut[2]),
                     part(rest)],                                                                   # a module twice
                    [self.shard(1, 2, cut[0]), self.shard(2, 3, cut[1]), self.shard(3, 3, cut[2]), part(rest)],
                    [self.shard(1, 3, cut[0]), self.shard(2, 3, cut[1]), self.shard(3, 3, cut[2]), part(self.all)],
                    [self.shard(1, 3, cut[0], commit='d' * 40), self.shard(2, 3, cut[1]), self.shard(3, 3, cut[2]),
                     part(rest)]):
            with self.assertRaises(ValueError):
                M.merge(bad, 'c' * 40)

    def test_git_state(self):
        commit, clean = M.git_state()
        self.assertTrue(commit is None or len(commit) == 40)
        self.assertIsInstance(clean, bool)


if __name__ == '__main__':
    unittest.main()
