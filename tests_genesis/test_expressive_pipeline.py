"""X2 (B20_R154): the engine-invention workflow as an Architecture Graph with ARA's ladder (`genesis.expressive.workflow`)
and one generation of Daniel's pipeline (`genesis.expressive.pipeline`), end to end on the planted fixture.

The workflow graph is checked and its changes classified in ARA's classes; the ladder finds a planted
expressiveness, search or evaluation loss, says NONE without an attainable range and AMBIGUOUS between two equal
terms, and names the next step. A generation learns statements from Genesis's own dev engines, has the judge decide
each, keeps every decision in the vault, excludes refused statements and resumes from the new language: on the
planted fixture it admits a statement that raises truth values; in a null world it admits nothing; when the ladder
diagnoses something other than expressiveness it attempts no language repair unless told to."""
from pathlib import Path
import random
import statistics
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import vault as V  # noqa: E402
from genesis.autonomy import feedback as FB  # noqa: E402
from genesis.autonomy import selfimprove as SI  # noqa: E402
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import fixture as F  # noqa: E402
from genesis.expressive import judge as J  # noqa: E402
from genesis.expressive import lambda1 as L1  # noqa: E402
from genesis.expressive import operators as O  # noqa: E402
from genesis.expressive import pipeline as P  # noqa: E402
from genesis.expressive import workflow as W  # noqa: E402


class Workflow(unittest.TestCase):
    def test_graph_and_classes(self):
        a = W.make()
        self.assertEqual(W.check(a), [])
        self.assertEqual(W.classify(a, W.make(library='lang-1')), 'LANGUAGE')
        self.assertEqual(W.classify(a, W.make(language='L0')), 'LANGUAGE')
        self.assertEqual(W.classify(a, W.make(search='ceiling')), 'STRUCTURAL')
        self.assertEqual(W.classify(a, W.make(judge='v2')), 'STRUCTURAL')
        self.assertEqual(W.classify(a, W.make(evals=480)), 'TUNING')
        self.assertEqual(W.classify(a, W.make()), 'NONE')
        bad = W.make()
        bad['nodes']['output'] = {'check': 'none'}
        self.assertTrue(W.check(bad))
        self.assertTrue(W.check(W.make(language='L0', library='lang-1')))
        with self.assertRaises(ValueError):
            W.classify(a, bad)

    def measures(self, **lift):
        rng = random.Random(4)
        base = {k: 0.0 for k in ('A', 'S_exact', 'C_cur', 'C_rich')}
        steps = {'evaluation': ('S_exact', 'C_cur', 'C_rich'), 'search': ('C_cur', 'C_rich'), 'expressiveness': ('C_rich',)}
        for term, v in lift.items():
            for k in steps.get(term, ()):
                base[k] += v
        top = max(base.values()) + 0.002
        out = {k: [b + rng.gauss(0, 0.0002) for _ in range(24)] for k, b in base.items()}
        out['O'] = [lift.get('range', top) + rng.gauss(0, 0.0002) for _ in range(24)]
        return out

    def test_the_ladder(self):
        self.assertEqual(W.ladder(self.measures(expressiveness=0.004))['diagnosis'], 'EXPRESSIVENESS')
        self.assertEqual(W.ladder(self.measures(search=0.004))['diagnosis'], 'SEARCH')
        self.assertEqual(W.ladder(self.measures(evaluation=0.004))['diagnosis'], 'EVALUATION')
        self.assertEqual(W.ladder(self.measures(search=0.003, expressiveness=0.003))['diagnosis'], 'AMBIGUOUS')
        self.assertEqual(W.ladder(self.measures(range=0.0))['diagnosis'], 'NONE')       # nothing beats REX
        beyond = W.ladder(self.measures(expressiveness=0.004, range=0.0))               # beyond REX's long runs
        self.assertEqual((beyond['diagnosis'], beyond['attained_by']), ('EXPRESSIVENESS', 'C_rich'))
        self.assertLess(beyond['terms']['residual']['value'], 0)
        r = W.ladder(self.measures(expressiveness=0.004))
        self.assertEqual((r['locate'], r['next'][:4]), ('language', 'grow'))
        with self.assertRaises(ValueError):
            W.ladder({'A': [0.0]})


def dev_search(domain, seed=123, n=8, evals=400):
    """Genesis's own dev searches on the fixture's development view (the research plane's data)."""
    ev_dev = F.dev_view(domain, seed)

    def search(lib):
        out = []
        for r in range(n):
            occ = {}

            def ev(g, split):
                cfg = L1.config(g, lib)
                k = cfg['prog']
                occ[k] = occ.get(k, -1) + 1
                return ev_dev(cfg, occ[k])
            w, _ = FB.steady_state_search(SI.seeded_ops(O.ops('L1', lib, bound=domain.bound), [dict(K.DEFAULT)]), ev,
                                          evals, r, contract=False)
            out.append(w)
        return out
    return search


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dom = F.FixtureDomain(search_scale=0.5)
        cls.judge = J.LanguageJudge(cls.dom, sealed_seed=11)
        cls.dir = tempfile.TemporaryDirectory()
        cls.vault = V.Vault(cls.dir.name)
        cls.g1 = P.generation(1, L1.EMPTY, dev_search(cls.dom), cls.judge.submit, claim='search', vault=cls.vault)
        cls.g2 = P.generation(2, cls.g1['library'], dev_search(cls.dom), cls.judge.submit, claim='search',
                              vault=cls.vault)

    @classmethod
    def tearDownClass(cls):
        cls.vault.close()
        cls.dir.cleanup()

    def test_a_planted_statement_is_admitted_and_kept(self):
        g1 = self.g1
        self.assertTrue(g1['admitted'], g1['decisions'])
        lib = g1['library']
        self.assertEqual(lib.parent, L1.EMPTY.version)
        body = lib.get(g1['admitted'][0])['body']
        self.assertIn('D@c', body)
        rec = self.vault.get(g1['records'][-1]['statements'][g1['admitted'][-1]])
        self.assertTrue(rec['content']['verification']['admitted'])
        refused = [d for d in g1['decisions'] if not d['admitted']]
        for d in refused:
            self.assertEqual(d['failed'], 'sealed')
        self.assertEqual(len(g1['decisions']), len(g1['records']))

    def test_the_next_generation_resumes_from_the_new_language(self):
        self.assertEqual(self.g2['parent'], self.g1['library'].version)
        gen1 = set(self.g1['library'].names())
        composed = [n for n in self.g2['admitted']
                    if {x[1] for x in K.walk(K.parse(self.g2['library'].get(n)['body'], calls=True)) if x[0] == 'call'}
                    & gen1]
        self.assertTrue(composed, self.g2['decisions'])     # a generation-2 statement built from generation 1's
        for s in self.g1['seeds']:
            L1.config(s, self.g1['library'])                # the seeds are written in the new language
        lib = self.g2['library']
        self.assertEqual(lib.defs[:len(self.g1['library'].defs)], self.g1['library'].defs)

    def test_truth_values_rise_with_the_admitted_language(self):
        admitted = [r for r in self.judge.ledger() if r['admitted']]
        self.assertGreaterEqual(len(admitted), 2)
        for r in admitted:
            self.assertGreater(r['lanes']['candidate'], r['lanes']['parent'] + 0.01)
        self.assertGreater(admitted[-1]['lanes']['candidate'], admitted[0]['lanes']['candidate'])   # compounding

    def test_a_null_world_admits_nothing(self):
        dom = F.FixtureDomain(search_scale=0.5, null=True)
        g = P.generation(1, L1.EMPTY, dev_search(dom, n=4, evals=200), J.LanguageJudge(dom, 11).submit, max_tries=2)
        self.assertEqual(g['admitted'], [])
        self.assertEqual(g['library'].version, L1.EMPTY.version)

    def test_no_language_repair_unless_the_ladder_says_expressiveness(self):
        m = Workflow().measures(search=0.004)
        g = P.generation(1, L1.EMPTY, dev_search(self.dom), self.judge.submit, measures=m)
        self.assertEqual((g['diagnosis']['diagnosis'], g['decisions']), ('SEARCH', []))
        g = P.generation(1, L1.EMPTY, dev_search(self.dom), self.judge.submit, measures=m, force=True, max_tries=1)
        self.assertEqual(len(g['decisions']), 1)


if __name__ == '__main__':
    unittest.main()
