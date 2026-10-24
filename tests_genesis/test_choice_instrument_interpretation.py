"""B20_R130: choice, instrument and interpretation, separated (design): fresh, disjoint seed ranges; the tests,
Holm and the verdicts; identifiability by intervened endpoints; validity; the registered output and its input."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r130_choice_instrument_interpretation as M  # noqa: E402


def synthetic(gain_interp, gain_choice, gain_inst, n=20):
    rows = []
    for s in range(n):
        for st in ('test', 'transfer'):
            def add(choice, interp, budget, f1, order=None):
                rows.append({'set': st, 'seed': s, 'choice': choice, 'order': order, 'interp': interp,
                             'budget': budget, 'targets': [0, 1], 'answer': {'bidirected': []}, 'problems': [],
                             'f1': f1, 'directed_f1': f1, 'cpu_s': 0.0})
            jit = 0.003 * s
            for b in M.BUDGETS:
                base = 0.2 + 0.02 * b + jit
                add('genesis', 'per_pair', b, base)
                add('genesis', 'global', b, base + gain_interp)
                add('genesis', 'joint', b, base + 0.01)
                for o in range(M.R_RANDOM):
                    add('random', 'global', b, base + gain_interp - gain_choice, o)
                    add('random', 'per_pair', b, base - 0.05, o)
                add('degree', 'global', b, base)
                add('oracle', 'global', b, base + 0.2)
            add('all', 'global', 'full', 0.7 + jit)
            add('all', 'llc', 'full', 0.7 + jit)
            add('all', 'per_pair', 'full', 0.5 + jit)
            add('all', 'per_pair_invented', 'full', 0.5 + gain_inst + jit)
    return rows


class Design(unittest.TestCase):
    def test_seeds_are_fresh_and_disjoint(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r130_choice_instrument_interpretation.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        import b20r129_adaptive_scientist as R129
        r129 = [(R129.SEED + off, R129.SEED + off + n) for off, n, _ in R129.SETS.values()]
        mine = sorted((M.SEED + off, M.SEED + off + n) for off, n, _ in M.SETS.values())
        for a0, a1 in mine:
            for b0, b1 in r129:
                self.assertTrue(a1 <= b0 or b1 <= a0)
        for (a0, a1), (b0, b1) in zip(mine, mine[1:]):
            self.assertLessEqual(a1, b0)
        with self.assertRaises(ValueError):
            M.world('test', 200)
        self.assertEqual((M.NOISE, M.BASE, M.SETS['test'][1]), ('gauss', R129.BASE, 200))

    def test_verdicts(self):
        a = M.analyse(synthetic(0.1, 0.1, 0.0))
        self.assertEqual((a['T_interpretation']['label'], a['T_choice']['label'], a['T_instrument']['label']),
                         ('INTERPRETATION_BETTER', 'CHOICE_BETTER', 'NO_DIFFERENCE'))
        self.assertEqual(a['verdict'], 'CHOICE+INTERPRETATION')
        a = M.analyse(synthetic(0.0, 0.0, 0.05))
        self.assertEqual(a['verdict'], 'INSTRUMENT')
        a = M.analyse(synthetic(-0.1, 0.0, 0.0))
        self.assertEqual(a['verdict'], 'NOT_SHOWN (WORSE: INTERPRETATION)')
        self.assertIn('headline_noninferiority', a['secondary'])
        self.assertIn('T_choice', M.analyse(synthetic(0.1, 0.1, 0.0), 'transfer'))

    def test_holm_and_identifiability(self):
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.02, 'c': 0.04}), {'a': True, 'b': True, 'c': True})
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.03, 'c': 0.04}), {'a': True, 'b': False, 'c': False})
        rows = [{'set': 'test', 'seed': 1, 'choice': 'genesis', 'interp': 'global', 'budget': 4, 'targets': [0, 3],
                 'answer': {'bidirected': [[0, 1]]}}]
        out = M.identifiability(rows, {1: {'confounded': [[0, 1], [2, 4], [3, 5]]}})
        self.assertEqual(out['4']['1'], {'marked': 1, 'hidden_causes': 2, 'recall': 0.5})
        self.assertEqual(out['4']['0'], {'marked': 0, 'hidden_causes': 1, 'recall': 0.0})

    def test_checks(self):
        r = {'problems': [], 'targets': [1, 2]}
        self.assertTrue(M.checks([r]))
        self.assertFalse(M.checks([dict(r, targets=[1, 1])]))
        self.assertFalse(M.checks([dict(r, problems=['x'])]))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
