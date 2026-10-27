"""ARA-1, the proposal engine (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §5, §6): every operator generated where its
precondition holds and nowhere else; the kernel never targeted; each operator's class; holes filled on dev data only;
rediscoveries recognised by behaviour; bounded limitation inversion."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import diagnose as D  # noqa: E402
from genesis.architecture import graph as G  # noqa: E402
from genesis.architecture import model as M  # noqa: E402
from genesis.architecture import rewrite as R  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402


class Generator(unittest.TestCase):
    def test_every_operator_where_its_precondition_holds(self):
        ops = set()
        for policy in ('global', 'threshold'):
            ag = M._fixture_ag(policy=policy)
            ag['budget']['split'] = {'search': 0.6, 's1': 0.1}
            ops |= {r['op'] for r in R.generate(ag, archive=[{'expr': ['mean_n', 'clust'], 'fingerprint': 'x'}])}
        self.assertEqual(ops, set(R.OPERATORS))
        self.assertNotIn('LIFT', {r['op'] for r in R.generate(M._fixture_ag(policy='global'))})
        plain = {r['op'] for r in R.generate(M._fixture_ag(policy='knn'))}
        self.assertNotIn('SPECIALISE', plain)                 # only a global policy is specialised
        self.assertNotIn('GENERALISE', plain)                 # knn is the most flexible family
        self.assertNotIn('RETRIEVE', plain)                   # nothing archived
        self.assertNotIn('REALLOCATE', plain)                 # one node with a share

    def test_the_kernel_is_never_a_target(self):
        ag = M._fixture_ag()
        for r in R.generate(ag):
            self.assertNotEqual(r.get('target'), 'out')

    def test_classes_of_the_realised_rewrites(self):
        ag = M._fixture_ag(policy='threshold')
        ag['budget']['split'] = {'search': 0.6, 's1': 0.1}
        for r in R.generate(ag):
            fill = {'expr': ['mean_n', 'clust']} if r['op'] in ('INSERT', 'RETRIEVE') else \
                ({'op': 'sub_s', 'scale': 1.0} if r['op'] == 'FUSE' else {})
            new = R.apply(ag, r, fill)
            self.assertIsNone(G.admissible(ag, new), r)
            self.assertEqual(G.classify(ag, new), R.CLASS[r['op']], r)

    def test_specialise_keeps_one_sense(self):
        ag = M._fixture_ag(policy='global')
        r = [x for x in R.generate(ag) if x['op'] == 'SPECIALISE' and x['args']['sense'] == 's1'][0]
        new = R.apply(ag, r, {})
        self.assertEqual(new['nodes']['pol']['op'], 'threshold')
        self.assertNotIn('s2', new['nodes'])
        self.assertEqual(G.check(new), [])

    def test_lineage_and_added_nodes(self):
        ag = M._fixture_ag()
        r = [x for x in R.generate(ag) if x['op'] == 'INSERT'][0]
        new = R.apply(ag, r, {'expr': ['mean_n', 'clust']})
        self.assertEqual(new['lineage']['parent'], G.ag_id(ag))
        self.assertEqual(new['lineage']['added'], ['s3'])
        fol = R.followups(new, r)
        self.assertTrue(fol and all(f['op'] == 'FUSE' and 's3' in (f['args']['a'], f['args']['b']) for f in fol))


class Holes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = Z.Environment(41, 7, 'SENSE_BLIND')
        cls.view = env.view()
        cls.lab = D.Lab(cls.view, 0)
        cls.synth = R.Synthesis(cls.view, cls.lab, 0)

    def test_synthesis_reads_dev_a_only(self):
        self.assertIs(self.synth.graphs, self.view.graphs('dev_a'))
        rec = self.synth.sense([])
        self.assertIsNone(__import__('genesis.senses.graph', fromlist=['check']).check(rec['expr']))
        self.assertGreater(rec['tried'], 50)
        self.assertGreater(self.synth.sense_units, 0)

    def test_fusion_fills_from_the_menu(self):
        rec = self.synth.fusion(['mean_n', 'deg'], 'n')
        self.assertIn(rec['op'], G.FUSE_OPS)
        self.assertIn(rec['scale'], G.FUSE_SCALES)

    def test_rediscovery_by_behaviour(self):
        same = ['mean_n', 'deg']
        twin = ['mean_n', ['add_n', 'deg', ['scale', 'one', 0.0]]]
        self.assertEqual(R.fingerprint(same), R.fingerprint(twin))      # different trees, identical behaviour
        self.assertNotEqual(R.fingerprint(same), R.fingerprint(['mean_n', 'clust']))
        s = R.Synthesis(self.view, self.lab, 0, archive=[{'expr': same, 'fingerprint': R.fingerprint(same)}])
        rec = s.sense([])
        self.assertEqual(rec['rediscovery'], rec['fingerprint'] == R.fingerprint(same))

    def test_realise_refuses_an_inadmissible_result(self):
        ag = self.view.incumbent
        rw = {'op': 'SUBSTITUTE', 'target': 'out', 'args': {'to': 'reattempt'}}
        new, why = R.realise(ag, rw, self.synth)
        self.assertIsNone(new)
        self.assertIn('kernel', why)


if __name__ == '__main__':
    unittest.main()
