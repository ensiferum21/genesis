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
        from genesis.autonomy import selfimprove as SI
        self.assertEqual(SI.PROCESS_SPACE['algorithm'], ('steady', 'map-elites'))   # the amendment's choices
        self.assertEqual(SI.PROCESS_SPACE['calib_extra'], (4, 8, 16))

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


R128 = ROOT / 'evidence' / 'improve_the_improver_b20r128'


@unittest.skipUnless((R128 / 'summary.json').exists(), 'B20_R128 has not run in this tree')
class RecordB20R128(unittest.TestCase):
    """The record of B20_R128 on its evidence: the preregistered script unchanged; one row per search; every engine
    valid; the meta-search re-derived from the preregistered seed; the test, the verdict and the measures recomputed
    by `analyse` from the saved yields; no release in any inner search."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((R128 / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (R128 / 'yields.jsonl').read_text().splitlines() if l.strip()]
        cls.by = {r['key']: r for r in cls.rows}

    def test_the_preregistered_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r128_improve_the_improver.py').read_bytes()).hexdigest(),
                         '59df2af9ae09b2038b8b7d95476d4b6dea43adc6997439dc24f8c5ece27ab0ee')

    def test_rows_and_engines(self):
        from genesis.candidate_kinds import mcx2 as K2
        self.assertEqual(len(self.by), len(self.rows))
        self.assertEqual(len(self.rows), M.GEN0_RANDOM + 1 + M.GENERATIONS * M.CHILDREN + 2 * M.REPETITIONS)
        for r in self.rows:
            self.assertIsNone(K2.check_config(r['engine']), r['key'])
            self.assertEqual(r['evaluations'], M.INNER_EVALS)

    def test_the_meta_search_rederived(self):
        import random
        from genesis.autonomy import selfimprove as SI
        rng = random.Random(M.SEED)
        meta = []
        for p in [SI.ORIGINAL] + [SI.random_process(rng) for _ in range(M.GEN0_RANDOM)]:
            meta.append({'gen': 0, 'index': len(meta), 'process': p,
                         'yield': self.by[f'meta{len(meta)}|0|{SI.key(p)}']['yield']})
        for g in range(1, M.GENERATIONS + 1):
            top = sorted(meta, key=lambda r: (-r['yield'], r['index']))[:2]
            for _ in range(M.CHILDREN):
                p = (SI.mutate_process(top[0]['process'], rng) if rng.random() < 0.5
                     else SI.crossover_process(top[0]['process'], top[1]['process'], rng))
                meta.append({'gen': g, 'index': len(meta), 'process': p,
                             'yield': self.by[f'meta{len(meta)}|0|{SI.key(p)}']['yield']})
        self.assertEqual(meta, self.s['meta'])

    def test_the_analysis_recomputes(self):
        from genesis.autonomy import selfimprove as SI
        evolved = self.s['evolved']['process']
        final = [{'rep': i, 'ORIGINAL': self.by[f'final-ORIGINAL|{i}|{SI.key(SI.ORIGINAL)}']['yield'],
                  'EVOLVED': self.by[f'final-EVOLVED|{i}|{SI.key(evolved)}']['yield']}
                 for i in range(1, M.REPETITIONS + 1)]
        self.assertEqual(final, self.s['final'])
        res = M.analyse(self.s['meta'], final)
        for k in ('evolved', 'test', 'verdict', 'beats_rex', 'mean_yield', 'meta_best_by_generation'):
            self.assertEqual(res[k], self.s[k], k)

    def test_no_release_in_any_search(self):
        self.assertEqual(sum(r['judge']['releases'] for r in self.rows), 0)


if __name__ == '__main__':
    unittest.main()
