"""B20_R98: the harness check of DeepDist-c and NuWLS-c-2026 on large hosts. Design: the hosts (B20_R97's, one per
cell), the solvers and conditions, the reading of a solver's own claims, and the labelling rule."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r98_harness_check as M  # noqa: E402


class Design(unittest.TestCase):
    def test_hosts_are_one_per_b20r97_cell(self):
        H = M.hosts()
        self.assertEqual(sorted((t.family.split(':')[0], t.n) for t, _ in H),
                         [('erdos', 128), ('erdos', 256), ('planted_cluster', 128), ('planted_cluster', 256)])
        for t, row in H:
            self.assertEqual(row['task_id'], t.task_id)

    def test_solvers_and_conditions(self):
        self.assertEqual(M.COLLAPSING, ('deepdist-c', 'nuwls-c-2026'))
        self.assertEqual(M.CONTROLS, ('deepdist', 'nuwls-c-2026-ub'))
        self.assertEqual(M.CONDITIONS, ('kind', 'pipe', 'file', 'file_grace', 'file_60'))
        self.assertEqual((M.BUDGET, M.LONG, M.GRACE, M.EFFECT), (10.0, 60.0, 5.0, 0.05))
        from genesis.candidate_kinds import maxsat_large as ML
        self.assertTrue(set(M.SOLVERS) <= set(ML.SOLVERS))

    def test_claims(self):
        out = 'c hi\no 40\no 31\ns SATISFIABLE\nv 0110\n'
        c = M.claims(out, 100)
        self.assertEqual((c['last_o'], c['claimed_value'], c['v_lines'], c['v_format']), (31, 69, 1, 'bits'))
        c = M.claims('o 5\nv 1 -2 3\nv -4 5\n', 10)
        self.assertEqual((c['v_lines'], c['v_format'], c['claimed_value']), (2, 'literals', 5))
        self.assertIsNone(M.claims('c nothing\n', 10)['last_o'])

    def test_labels(self):
        best = {f't{i}': 100 for i in range(4)}

        def runs(solver, vals, claimed=None):
            out = {}
            for i in range(4):
                for c, v in vals.items():
                    out[(f't{i}', solver, c)] = {'value': v, 'claimed_value': (claimed or {}).get(c)}
            return out
        flat = {'kind': 60, 'pipe': 60, 'file': 60, 'file_grace': 60, 'file_60': 61}
        R = {}
        for s in M.SOLVERS:
            R.update(runs(s, flat))
        labs = M.labels(R, best)
        self.assertEqual(labs, {s: ['NO_HARNESS_EFFECT'] for s in M.SOLVERS})
        self.assertEqual(M.headline(labs), ('NOT_THE_HARNESS', []))
        R.update(runs('deepdist-c', dict(flat, pipe=70)))
        self.assertEqual(M.labels(R, best)['deepdist-c'], ['SANDBOX_EFFECT'])
        R.update(runs('nuwls-c-2026', flat, claimed={'pipe': 90}))
        labs = M.labels(R, best)
        self.assertEqual(labs['nuwls-c-2026'], ['PARSE_MISMATCH'])
        self.assertEqual(M.headline(labs)[0], 'HARNESS_DEFECT')
        R.update(runs('deepdist-c', dict(flat, file_60=70)))
        R.update(runs('nuwls-c-2026', flat))
        labs = M.labels(R, best)
        self.assertEqual((labs['deepdist-c'], M.headline(labs)[0]), (['BUDGET_EFFECT'], 'NOT_THE_HARNESS'))
        R.update(runs('deepdist', dict(flat, file=70)))
        self.assertEqual(M.headline(M.labels(R, best))[1], ['deepdist'])

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])

    def test_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r98_harness_check.py').read_text())


if __name__ == '__main__':
    unittest.main()
