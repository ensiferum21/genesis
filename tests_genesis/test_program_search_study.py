"""B20_R79: the program-search study. Design: fresh seeds, the fixed constants, the search budget fits a 2-hour
run, no hand-written program anywhere in the study, the study is pinned and not resumable."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r79_program_search as M  # noqa: E402
from genesis.invention import solver_search as SS  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r79_program_search.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.SEARCH_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_constants(self):
        self.assertEqual((M.PER_N, M.N, M.SEARCH_S), (16, 63, 6000.0))
        self.assertEqual((SS.POP, SS.CHILDREN, SS.LEADERS, SS.TOURNAMENT, SS.P_CROSS, SS.BUDGET),
                         (16, 8, 2, 3, 0.25, 0.25))
        self.assertEqual((SS.FINALISTS, SS.FINAL_BUDGETS, SS.FINAL_SEEDS), (4, (0.25, 1.0), 2))
        final = SS.FINALISTS * sum(SS.FINAL_BUDGETS) * SS.FINAL_SEEDS * M.PER_N   # 160 CPU s of final runs
        self.assertLess(M.SEARCH_S + final + 300, 7200)          # fits one 2-hour background run

    def test_no_hand_written_program_reaches_the_search(self):
        text = (ROOT / 'scripts' / 'b20r79_program_search.py').read_text()
        code = text.split('"""', 2)[2]
        for word in ("'body'", '"body"', "'descent'", "'sweep'", "'force'", "'drop'"):
            self.assertNotIn(word, code)
        self.assertIn('SS.search(tasks, reps, rep_by_id, SEARCH_S, SEARCH_SEED', code)

    def test_pinned_and_not_resumable(self):
        text = (ROOT / 'scripts' / 'b20r79_program_search.py').read_text()
        self.assertIn('R33.pinned_core()', text)
        self.assertIn('not resumable', text)


if __name__ == '__main__':
    unittest.main()
