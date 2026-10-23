"""B20_R112: the inventor under contract v2 (design): fresh seed, the A/B/C split by cell, the refusal before B20_R111
has finished, and the registered output."""
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r112_inventor_v2 as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r112_inventor_v2.py':
                self.assertIsNone(re.search(rf'\b{M.HOST_SEED}\b', path.read_text()), path.name)

    def test_splits_take_one_host_per_cell_each(self):
        tasks = [f'c{i % 4}-{i // 4}' for i in range(12)]          # qet's cell-interleaved order
        s = M.splits(tasks, 4)
        self.assertEqual(s['A'], ['c0-0', 'c1-0', 'c2-0', 'c3-0'])
        self.assertEqual(s['C'], ['c0-2', 'c1-2', 'c2-2', 'c3-2'])
        self.assertFalse(set(s['A']) & set(s['B']) or set(s['B']) & set(s['C']))

    def test_refuses_before_b20r111(self):
        with mock.patch.object(M, 'R111', ROOT / 'evidence' / 'does_not_exist'):
            with self.assertRaises(SystemExit):
                M.main([str(ROOT / 'evidence' / 'inventor_v2_b20r112')])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
