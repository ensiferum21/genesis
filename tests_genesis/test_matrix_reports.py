"""The test matrix's reports (`scripts/run_test_matrix.py`): a report says which commit it tested and whether the tree
was clean; a matrix split across jobs (`--suites`) merges into one release report only if every part tested the same
clean commit and the parts cover the release profile's suites exactly once (`make_checkpoint.py --reports`)."""
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

    def test_git_state(self):
        commit, clean = M.git_state()
        self.assertTrue(commit is None or len(commit) == 40)
        self.assertIsInstance(clean, bool)


if __name__ == '__main__':
    unittest.main()
