"""B20_R135: invented representations against textbook ones (design): fresh seeds; the instance sets; the relations of
Part A; the pipeline's repair, validity weight and independent checkers; the sign tests, Holm and the verdicts; the
registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r135_invented_representations as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r135_invented_representations.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)

    def test_instances(self):
        G = M.colouring_graphs()
        seeds = []
        for k in M.KS:
            self.assertEqual(len(G[k]['train']), M.N_TRAIN)
            self.assertEqual(len(G[k]['test']), M.N_PER * len(M.SIZES))
            self.assertTrue(all(g['k'] == k for g in G[k]['train'] + G[k]['test']))
            seeds += [g['seed'] for g in G[k]['train'] + G[k]['test']]
        fam = M.family_instances()
        self.assertEqual(len(fam), 4 * 2 * M.N_PER)
        seeds += [i['seed'] for i in fam]
        self.assertEqual(len(seeds), len(set(seeds)))
        big = [i for i in fam if i['family'] == 'max3sat' and i['size'] == 2000][0]
        self.assertEqual(len(big['constraints']), 8400)

    def test_part_a_relations(self):
        reps, rand = M.part_a_relations()
        self.assertTrue(all(0 < r.size() < 8 and r.k == 3 for r in reps))
        self.assertEqual(len({r.id() for r in reps}), len(reps))
        self.assertEqual(len(rand), M.N_RANDOM4)
        self.assertEqual(len({r.id() for r in rand}), M.N_RANDOM4)

    def test_pipeline_pieces(self):
        from genesis.compiler import families as FM
        from genesis.representation import families as F
        inst = FM.generate('coloring', 1, {'n': 30, 'd': 4.0, 'k': 3})
        col = M.repair_colours(inst, [None] * 30)
        self.assertTrue(all(c in (0, 1, 2) for c in col))
        self.assertEqual(M.independent_conflicts(inst, col), FM.verify('coloring', inst, {'colours': col})[1])
        for fam in F.FAMILIES:
            fi = F.generate(fam, 3, {'n': 20, 'm': 30})
            x = [(i * 7) % 2 for i in range(20)]
            self.assertEqual(M.independent_satisfied(fi, x), F.check(fi, x)[1])

    def test_validity_weight(self):
        from genesis.compiler import families as FM
        from genesis.representation import encodings as E
        from genesis.representation import library as LB
        inst = FM.generate('coloring', 2, {'n': 20, 'd': 4.0, 'k': 3})
        anc, nz, lib, plan = E.cost(E.binary(3), M.NEQ, {'neq': 1}, 1, LB.EMPTY, M.synth)
        w = M.validity_weight(inst, plan, lib)
        deg = max(sum(v in e for e in inst['edges']) for v in range(20))
        self.assertGreater(w, deg)

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main(['/tmp/elsewhere'])


class Analysis(unittest.TestCase):
    def rows(self, gain3=-2):
        rows = []
        for k in M.KS:
            for s in range(20):
                base = 10 + (s % 3)
                for arm, v in (('chosen', base + (gain3 if k == 3 else 0)), ('one_hot', base),
                               ('compiler', base + 1), ('maxsat', base - 1)):
                    rows.append({'k': k, 'seed': s, 'arm': arm, 'conflicts': v})
        return rows

    def test_verdicts(self):
        choices = {3: {'chosen': {'code': [[0, 0]]}, 'is_one_hot': False},
                   4: {'chosen': {'code': [[1]]}, 'is_one_hot': True}, 5: {'chosen': {'code': [[1]]}, 'is_one_hot': True}}
        a = M.analyse(choices, self.rows(-2), [], [])
        self.assertEqual(a['colouring']['3']['P']['label'], 'INVENTED_BETTER')
        self.assertEqual(a['verdict'], 'INVENTED_REPRESENTATION_BETTER')
        self.assertNotIn('P', a['colouring']['4'])
        self.assertEqual(M.analyse(choices, self.rows(2), [], [])['verdict'], 'INVENTED_REPRESENTATION_WORSE')
        self.assertEqual(M.analyse(choices, self.rows(0), [], [])['verdict'], 'NOT_SHOWN')
        allh = {k: {'chosen': {'code': [[1]]}, 'is_one_hot': True} for k in M.KS}
        self.assertEqual(M.analyse(allh, self.rows(0), [], [])['verdict'], 'NO_INVENTION')

    def test_families_and_synthesis(self):
        fr = [{'family': 'nae3', 'seed': s, 'arm': a, 'satisfied': 100 + (5 if a == 'genesis' else 0)}
              for s in range(20) for a in ('genesis', 'maxsat')]
        syn = [{'set': 'arity3', 'milp': True, 'search': i % 2 == 0, 'uniform': True, 'milp_ancillas': 0,
                'search_ancillas': 0} for i in range(20)]
        a = M.analyse({k: {'chosen': {}, 'is_one_hot': True} for k in M.KS}, Analysis.rows(self), fr, syn)
        self.assertEqual(a['families']['nae3']['test']['label'], 'GENESIS_BETTER')
        self.assertEqual(a['synthesis']['arity3']['milp_only'], 10)
        self.assertLess(a['synthesis']['arity3']['p_mcnemar'], 0.01)


if __name__ == '__main__':
    unittest.main()
