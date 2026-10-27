"""X2 (B20_R154): the consolidator (`genesis.expressive.consolidate`): what the language judge admits is kept with
its contract, tests, verification, cost and provenance; what it refuses is kept dormant with its failure; language
versions form a chain of parents; nothing is verified or promoted without a recorded study's evidence."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import vault as V  # noqa: E402
from genesis.expressive import consolidate as C  # noqa: E402
from genesis.expressive import lambda1 as L1  # noqa: E402

ADMIT = {'admitted': True, 'failed': None, 'claim': 'expressiveness'}


class Consolidator(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.v = V.Vault(self.d.name)
        self.lib1 = L1.EMPTY.extend('pat', 'D@c D@c D@c D@c', provenance={'generation': 1, 'uses': 5})
        self.out1 = C.consolidate(self.v, L1.EMPTY, self.lib1, ['pat'], ADMIT, ledger_entry=1, budget=480)

    def tearDown(self):
        self.v.close()
        self.d.cleanup()

    def test_an_admitted_statement_is_kept_with_its_record(self):
        aid = self.out1['statements']['pat']
        c = self.v.get(aid)['content']
        self.assertEqual(c['kind'], 'statement')
        self.assertEqual(c['contract']['body'], 'D@c D@c D@c D@c')
        self.assertTrue(all(c['tests'].values()), c['tests'])
        self.assertEqual(c['verification'], {'admitted': True, 'failed': None, 'claim': 'expressiveness', 'ledger': 1})
        self.assertEqual((c['cost']['items'], c['cost']['budget']), (4, 480))
        self.assertEqual(c['failure_envelope'], [])
        self.assertEqual(c['provenance']['uses'], 5)
        self.assertEqual(self.v.status(aid)['status'], 'reproducible')
        lang = self.out1['language']
        self.assertEqual(self.v.status(lang)['status'], 'reproducible')
        self.assertEqual(self.v.get(lang)['content']['version'], self.lib1.version)
        kinds = sorted(e['kind'] for e in self.v.edges())
        self.assertEqual(kinds, ['combines_with', 'improves'])

    def test_refusals_are_kept_dormant_with_their_failure(self):
        lib2 = self.lib1.extend('dec', 'H@a H@a')
        out = C.consolidate(self.v, self.lib1, lib2, ['dec'], {'admitted': False, 'failed': 'sealed', 'claim': 'search'})
        aid = out['statements']['dec']
        self.assertIsNone(out['language'])
        self.assertEqual(self.v.status(aid), {'status': 'dormant', 'explanation': 'unknown', 'failure': 'context_limited',
                                             'novelty': None})
        self.assertEqual(self.v.get(aid)['content']['failure_envelope'], [{'claim': 'search', 'failed': 'sealed'}])
        lib3 = self.lib1.extend('bad', 'X I')
        out = C.consolidate(self.v, self.lib1, lib3, ['bad'], {'admitted': False, 'failed': 'correctness'})
        self.assertEqual(self.v.status(out['statements']['bad'])['failure'], 'incorrect')

    def test_versions_chain_and_requires(self):
        lib2 = self.lib1.extend('pat2', 'pat pat')
        out = C.consolidate(self.v, self.lib1, lib2, ['pat2'], dict(ADMIT, claim='search'))
        self.assertEqual([x[1] for x in C.registry(self.v)], [L1.EMPTY.version, self.lib1.version, lib2.version])
        req = self.v.edges(kind='requires')
        self.assertEqual([(e['src'], e['dst']) for e in req], [(out['statements']['pat2'], self.out1['statements']['pat'])])
        self.assertEqual(C.find_language(self.v, lib2.version), out['language'])

    def test_nothing_is_verified_without_a_recorded_study(self):
        with self.assertRaises(V.VaultError):
            self.v.annotate(self.out1['statements']['pat'], status='verified', reason='no evidence')
        self.assertEqual(self.v.verify()['integrity'], 'LOCAL_HASH_CHECKED')

    def test_property_tests_cover_both_ends_of_every_range(self):
        tests = C.property_tests(self.lib1, 'pat')
        self.assertEqual(set(tests), {'rebuilds', 'expands_low', 'stable_low', 'expands_high', 'stable_high'})
        self.assertTrue(all(tests.values()))


if __name__ == '__main__':
    unittest.main()
