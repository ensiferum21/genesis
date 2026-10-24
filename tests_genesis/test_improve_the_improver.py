"""B20_R128: improving the process of invention (design): fresh seed; graph sets disjoint from each other and from
Gset; the meta-search's shape; the test, the verdict and the summary measures; the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r128_improve_the_improver as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        import b20r127_self_invented_engine as R127
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r128_improve_the_improver.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        mine = range(M.SEED, M.SEED + 10000 * (M.REPETITIONS + 1))          # the graph seeds this study can use
        theirs = range(R127.SEED, R127.SEED + 100 * 4 * 3)
        self.assertFalse(set(mine) & set(theirs))

    def test_graph_sets_are_disjoint(self):
        from genesis import gset as GS
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        seen = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
        ex = set(seen)
        ids = []
        for i in range(2):
            g, seen = M.graph_set(i, seen)
            self.assertEqual({s: len(v) for s, v in g.items()}, {'A': 6, 'B': 6, 'C': 6, 'D': 12})
            ids += [A.exposure_identity(t)['canonical'] for v in g.values() for _, t in v]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertFalse(set(ids) & ex)

    def test_analysis(self):
        meta = [{'gen': 0, 'index': 0, 'process': 'o', 'yield': 1.001}, {'gen': 0, 'index': 1, 'process': 'a', 'yield': 1.004},
                {'gen': 1, 'index': 2, 'process': 'b', 'yield': 1.002}]
        final = [{'rep': i, 'ORIGINAL': 1.0 + 0.001 * i, 'EVOLVED': 1.003 + 0.001 * i + 0.0001 * i} for i in range(8)]
        a = M.analyse(meta, final)
        self.assertEqual(a['evolved']['process'], 'a')
        self.assertEqual((a['test']['label'], a['verdict']), ('PROCESS_IMPROVED', 'SELF_IMPROVEMENT_SHOWN'))
        self.assertEqual(a['beats_rex'], {'ORIGINAL': 7, 'EVOLVED': 8})
        self.assertEqual(a['meta_best_by_generation'], {'0': 1.004, '1': 1.002})
        flat = [{'rep': i, 'ORIGINAL': 1.0, 'EVOLVED': 1.0} for i in range(8)]
        self.assertEqual(M.analyse(meta, flat)['verdict'], 'NOT_SHOWN')

    def test_shape(self):
        self.assertEqual((M.GEN0_RANDOM, M.GENERATIONS, M.CHILDREN, M.REPETITIONS, M.INNER_EVALS), (5, 2, 4, 8, 120))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
