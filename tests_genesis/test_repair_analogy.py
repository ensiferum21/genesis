"""Genesis growing its own repair space (`genesis.repair.analogy`, SR-2c): transformations lifted from verified repairs
(donor, substitutions, edit), applied as productions, derived from one another by the group operations, admitted
only by another family's verified repair; and the loop's arms that use them. On the development catalogues only."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repair import analogy as AN  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

CATS = {d['id']: c for c in (DF2, DF3, DF4) for d in c.DEFECTS}


def ref(did):
    """(defective source, correct source) of a development defect."""
    c = CATS[did]
    return c.source(did, TG.KERNEL_SOURCES), TG.KERNEL_SOURCES[c.BY_ID[did]['target']]


def st(text):
    return ast.parse(text).body[0]


class Substitutions(unittest.TestCase):
    def test_leaves_skeletons_and_the_substitutions_that_explain_a_change(self):
        a, b = st('self.adj[u].add(v)'), st('self.adj[v].add(u)')
        self.assertEqual([x[3:] for x in AN.leaves(a)], [('meth', 'add'), ('attr', 'adj'), ('name', 'u'),
                                                         ('name', 'v')])
        self.assertEqual(AN.skeleton(a), AN.skeleton(b))
        self.assertEqual(AN.abstract_subs(AN.diff(a, b)), (('swap', 'name'),))
        self.assertEqual(AN.abstract_subs(AN.diff(st('self.n += k'), st('self.n -= k'))), (('map', 'op', 'Add', 'Sub'),))
        self.assertEqual(AN.abstract_subs(AN.diff(st('x = y < 3'), st('x = y < 2'))), (('shift', -1),))
        self.assertEqual(AN.abstract_subs(AN.diff(st('self.fwd[a] = b'), st('self.back[b] = a'))),
                         (('rename', 'attr'), ('swap', 'name')))
        self.assertIsNone(AN.diff(st('self.n += k'), st('self.n = k')))           # not the same tree
        self.assertNotEqual(AN.skeleton(st('x = a < b')), AN.skeleton(st('x = a + b')))

    def test_images_of_each_substitution(self):
        ctx = {'kinds': {'held': 'dict', 'reserved': 'dict', 'n': 'int'}, 'meths': ['add', 'discard'], 'funcs': ['max']}
        got = {ast.unparse(m) for m in AN.images(st('self.held[i] -= n'), [('rename', 'attr')], ctx, ['i', 'n'])}
        self.assertEqual(got, {'self.reserved[i] -= n'})
        got = {ast.unparse(m) for m in AN.images(st('y = max(a, 1)'), [('any', 'const')], ctx, [])}
        self.assertEqual(got, {'y = max(a, 2)', 'y = max(a, 0)'})
        got = {ast.unparse(m) for m in AN.images(st('if a < b: pass').test, [('any', 'op')], ctx, [])}
        self.assertEqual(got, {'a <= b', 'a > b', 'a >= b', 'a == b', 'a != b'})


class LiftAndApply(unittest.TestCase):
    def test_each_lifted_transformation_regenerates_its_repair(self):
        for did, edit, subs in (('N1', 'transplant', [['map', 'meth', 'discard', 'add']]),
                                ('X2', 'after', [['rename', 'attr']]),
                                ('K1', 'after', [['rename', 'attr'], ['swap', 'name']]),
                                ('B1', 'transplant', [['map', 'op', 'Sub', 'Add']]),
                                ('B2', 'replace', [['shift', -1]]),
                                ('X4', 'replace', [['map', 'op', 'Add', 'Sub']])):
            bad, good = ref(did)
            ts = AN.lift(bad, good, {'episode': did, 'family': did})
            self.assertEqual([(t['edit'], t['subs']) for t in ts], [(edit, subs)], did)
            self.assertIn(good, [c for _, c in AN.apply_transform(ts[0], bad)], did)

    def test_a_transformation_transfers_to_another_familys_defect(self):
        bad, good = ref('E3')                   # a lease forgets one of two paired deletions
        t = AN.lift(bad, good, {'episode': 'E3', 'family': 'E3'})[0]
        bad2, good2 = ref('X2')                 # the stock forgets one of two paired decrements
        self.assertIn(good2, [c for _, c in AN.apply_transform(t, bad2)])

    def test_nothing_is_lifted_from_what_the_language_cannot_say(self):
        bad, good = ref('C1')                   # a setdefault no statement of the component resembles
        self.assertEqual(AN.lift(bad, good, {'episode': 'C1', 'family': 'C1'}), [])


class Derivation(unittest.TestCase):
    def test_the_four_operators(self):
        t = {'id': 'a', 'edit': 'after', 'subs': [['rename', 'attr']], 'provenance': {'family': 'E3'}}
        u = {'id': 'b', 'edit': 'transplant', 'subs': [['map', 'meth', 'add', 'discard']], 'provenance': {'family': 'N2'}}
        v = {'id': 'c', 'edit': 'after', 'subs': [['swap', 'name']], 'provenance': {'family': 'N1'}}
        got = {(d['derived']['op'], AN.key(d)) for d in AN.derive([t, u, v])}
        self.assertIn(('transfer', ('replace', (('rename', 'attr'),))), got)
        self.assertIn(('invert', ('transplant', (('map', 'meth', 'discard', 'add'),))), got)
        self.assertIn(('generalise', ('transplant', (('any', 'meth'),))), got)
        self.assertIn(('compose', ('after', (('rename', 'attr'), ('swap', 'name')))), got)
        self.assertNotIn(AN.key(t), {k for _, k in got})
        for d in AN.derive([t, u, v]):
            self.assertIsNone(d['provenance']['family'])
            self.assertTrue(d['provenance']['derived_from_families'])

    def test_a_grandchild_carries_its_grandparents_families(self):
        # B20R187-ANCESTRY: until 31 Oct 2026 a third-generation transformation recorded '' for a derived parent
        t = {'id': 'a', 'edit': 'after', 'subs': [['map', 'op', 'In', 'NotIn']], 'provenance': {'family': 'M2'}}
        child = next(d for d in AN.derive([t]) if d['derived']['op'] == 'generalise')
        self.assertEqual(child['provenance']['derived_from_families'], ['M2'])
        u = {'id': 'b', 'edit': 'after', 'subs': [['rename', 'attr']], 'provenance': {'family': 'E3'}}
        grand = [d for d in AN.derive([child, u], generation=3) if d['derived']['op'] == 'compose']
        self.assertTrue(grand)
        self.assertEqual(grand[0]['provenance']['derived_from_families'], ['E3', 'M2'])
        with tempfile.TemporaryDirectory() as d:
            lib = AN.Transforms(Path(d) / 't.jsonl')
            g = lib.add(grand)[0]
            self.assertNotIn(g, lib.candidates('M2'))                  # never probed on an ancestor's family
            lib.record(g['id'], True, 'M2')
            self.assertEqual(lib.get(g['id'])['status'], 'candidate')  # nor admitted by it

    def test_a_derived_transformation_reaches_what_no_lifted_one_did(self):
        bad, good = ref('E3')
        t = AN.lift(bad, good, {'episode': 'E3', 'family': 'E3'})[0]       # after: another attribute
        transfer = next(d for d in AN.derive([t]) if d['derived']['op'] == 'transfer' and d['edit'] == 'replace')
        bad2, good2 = ref('K4')                 # a lookup in the wrong map: in place, another attribute
        self.assertNotIn(good2, [c for _, c in AN.apply_transform(t, bad2)])
        self.assertIn(good2, [c for _, c in AN.apply_transform(transfer, bad2)])


class Stores(unittest.TestCase):
    def test_admission_and_the_derivers_beliefs(self):
        with tempfile.TemporaryDirectory() as d:
            lib = AN.Transforms(Path(d) / 'transforms.jsonl')
            bad, good = ref('E3')
            t = lib.add(AN.lift(bad, good, {'episode': 'E3', 'family': 'E3'}))[0]
            self.assertEqual(lib.add(AN.lift(bad, good, {'episode': 'E3b', 'family': 'E3'})), [])   # one per key
            self.assertEqual(lib.candidates('E3'), [])
            lib.record(t['id'], True, 'E3')
            self.assertEqual(lib.get(t['id'])['status'], 'candidate')               # its own family: no admission
            lib.record(t['id'], True, 'X2')
            self.assertEqual(lib.get(t['id'])['status'], 'admitted')
            der = lib.add(AN.derive(lib.admitted()))
            self.assertTrue(der)
            self.assertEqual(lib.candidates('E3'), [])                              # a parent's family: not its test
            self.assertTrue(lib.candidates('K4'))
            dv = AN.Deriver(Path(d) / 'deriver.json')
            dv.learn(der[0], True)
            self.assertGreater(AN.Deriver(Path(d) / 'deriver.json').mean(der[0]['derived']['op']), 0.5)
            again = AN.Transforms(Path(d) / 'transforms.jsonl')
            self.assertEqual(len(again.rules), len(lib.rules))


class Episodes(unittest.TestCase):
    def test_v3learn_lifts_and_a_probe_admits_on_another_family(self):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d) / 'vault'
            job, _ = BN.make('E3', 1, Path(d) / 'e3', version=2)
            job.run()
            rec, _ = FD.handle_obstacle(job, vault_dir=vault, arm='dream', budget=600, repair_id='E3', isolated=False,
                                        log_path=Path(d) / 's.jsonl', family='E3')
            self.assertEqual(rec['outcome'], 'repaired')
            self.assertTrue(rec['lifted'])
            lib = AN.Transforms(vault / 'transforms.jsonl')
            self.assertTrue(lib.candidates('X2'))
            job2, _ = BN.make('X2', 1, Path(d) / 'x2', version=2)
            job2.run()
            rec2, _ = FD.handle_obstacle(job2, vault_dir=vault, arm='probe_t', budget=200, repair_id='X2',
                                         isolated=False, log_path=Path(d) / 's.jsonl', family='X2')
            self.assertEqual(rec2['outcome'], 'repaired', rec2.get('patch'))
            self.assertEqual(rec2['transform']['after'], 'admitted')
            job3, _ = BN.make('X2', 2, Path(d) / 'x2b', version=2)
            job3.run()
            rec3, _ = FD.handle_obstacle(job3, vault_dir=vault, arm='analogy', budget=300, repair_id='X2b',
                                         isolated=False, log_path=Path(d) / 's.jsonl', family='X2')
            self.assertEqual(rec3['outcome'], 'repaired')


if __name__ == '__main__':
    unittest.main()
