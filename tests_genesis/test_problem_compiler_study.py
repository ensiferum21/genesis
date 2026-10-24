"""B20_R133: the Problem Compiler study (design): fresh seeds, the instance plan, the sign tests, Holm and the verdict,
validity, the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r133_problem_compiler as M  # noqa: E402


def rows_with(score):
    rows = []
    for spec in M.instances():
        for b in M.BUDGETS:
            for a in M.ARMS:
                rows.append({'family': spec['family'], 'seed': spec['seed'], 'arm': a, 'budget': b, 'valid': True,
                             'score': score(spec, a, b), 'info': {'violations_before_repair': 0}})
    return rows


class Design(unittest.TestCase):
    def test_seed_and_plan(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r133_problem_compiler.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        ins = M.instances()
        self.assertEqual(len(ins), 80)
        self.assertEqual(len({i['seed'] for i in ins}), 80)
        self.assertEqual({i['family'] for i in ins}, set(M.FAMILIES))

    def test_verdicts(self):
        def tie(spec, a, b):
            return 100 + spec['seed'] % 7 + (0 if a != 'milp' else -50) * (1 if spec['family'] != 'coloring' else -1)
        a = M.analyse(rows_with(tie))
        self.assertEqual(a['verdict'], 'COMPETITIVE_WITH_SPECIALISTS')
        self.assertEqual(set(a['tests']), {'mis', 'coloring', 'max2sat'})

        def behind(spec, a, b):
            s = 100 + spec['seed'] % 7
            if spec['family'] == 'coloring' and a == 'genesis':
                return s + 5                                  # more conflicts: worse
            return s
        self.assertEqual(M.analyse(rows_with(behind))['verdict'], 'BEHIND_SPECIALISTS_ON coloring')

        def beyond(spec, a, b):
            s = 100 + spec['seed'] % 7
            return s + 3 if spec['family'] == 'mis' and a == 'genesis' else s
        self.assertEqual(M.analyse(rows_with(beyond))['verdict'],
                         'COMPETITIVE_WITH_SPECIALISTS; BEYOND_SPECIALISTS_ON mis')

    def test_checks_and_holm(self):
        rows = rows_with(lambda s, a, b: 1)
        self.assertTrue(M.checks(rows))
        self.assertFalse(M.checks(rows[:-1]))
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.04}), {'a': True, 'b': True})
        self.assertEqual(M.holm({'a': 0.03, 'b': 0.04}), {'a': False, 'b': False})

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
