"""B20_R51: the C4 tree route, wired as an opt-in v5 reference with custody. Built for review; nothing adopts it.

**Custody.** A certificates_tree_c4 bundle replays checker-only:
  * it re-derives the registry from the package;
  * it re-checks the tree exactly;
  * it refuses revoked identities and altered objects.
The evaluator's own replay and the generated-rows custody refuse this schema.

**Requests.** 'generated-rows-tree-c4-v1' is a known v5 route:
  * over a known C4 package only (a triangle-free package digest is refused, and the reverse);
  * with the fast enumerator.

**Adapters.** Each adapter offers only its own route:
  * the C4 adapter computes the tree reference with custody;
  * the triangle-free adapter refuses the C4 route, and the C4 adapter refuses the triangle-free route.

**Rule.** The DRAFT `e1-hard-v2-c4tree-draft` is B20_R50's rule. The code knows it, so a record that uses
it can be checked, but no study adopts it.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from genesis import calibration as CAL
from genesis import custodian as CU
from genesis.common import canonical, digest
from genesis.discovery import generated_bnb_c4 as GB
from genesis.discovery import generated_certify_c4 as GC4
from genesis.domains import ADAPTERS, Unsupported
from genesis.kernel import receipts as R
from genesis.models import GraphTask
from genesis.store import Store
from genesis.verification import certificates as CB
from genesis.verification import certificates_rows as CROWS
from genesis.verification import certificates_tree_c4 as CT
from tests_genesis.test_wiring_v5 import REF as REF_TF, synthetic_record

ROOT = Path(__file__).resolve().parents[1]
TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'
PKG = json.loads(GC4.PACKAGE.read_text())
REF = dict(REF_TF, route='generated-rows-tree-c4-v1', package_sha256=digest(PKG), seconds=60)


def c4host(n, edges, tid='t-c4'):
    return GraphTask(task_id=tid, domain=C4, family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


def random_host(seed, n, p, tid):
    import itertools
    import random
    rng = random.Random(seed)
    return c4host(n, [e for e in itertools.combinations(range(n), 2) if rng.random() < p], tid)


H = random_host(2, 16, 0.25, 'h16')            # 30 edges, above the exact-search range (24); optimum 25
K8 = c4host(8, [(a, b) for a in range(8) for b in range(a + 1, 8)], 'k8')


class Custody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.bundle, cls.blobs = GB.reference_record(H, PKG, seconds=60, separation_seconds=15, max_rows=50000,
                                                             max_total=80000, order='dense-first', lp_rounding_seconds=1.0)

    def test_the_reference_certifies_and_replays(self):
        from genesis.invention.cuts_c4 import ex_milp
        self.assertEqual(len(H.edges), 30)
        self.assertEqual((self.out['status'], self.out['value']), ('FINITE_CERTIFIED', 25))
        self.assertEqual(ex_milp(list(H.edges))[0], 25)
        self.assertEqual(self.bundle['schema'], CT.SCHEMA)
        rep = CT.replay(self.bundle, self.blobs.__getitem__)
        self.assertEqual((rep['status'], rep['lower'], rep['upper']), ('OPTIMALITY_CHECKED', 'VALID', 'VALID'), rep)
        self.assertEqual(CT.custody_problems(self.bundle, lambda h: h in self.blobs), [])

    def test_alterations_and_revocations_are_refused(self):
        up = self.bundle['upper']
        rep = CT.replay(self.bundle, self.blobs.__getitem__, revoked={up['checker']})
        self.assertEqual(rep['upper'], 'REJECTED')
        rep = CT.replay(self.bundle, self.blobs.__getitem__, revoked={up['theory_package_sha256']})
        self.assertEqual(rep['upper'], 'REJECTED')
        cert = json.loads(self.blobs[up['certificate_sha256']])
        cert['upper'] = cert['upper'] - 1
        bad = dict(self.blobs, **{up['certificate_sha256']: canonical(cert)})
        self.assertEqual(CT.replay(self.bundle, bad.__getitem__)['upper'], 'REJECTED')
        reg = json.loads(self.blobs[up['registry_sha256']])
        reg['patterns'] = dict(list(reg['patterns'].items())[:3])
        bad = dict(self.blobs, **{up['registry_sha256']: canonical(reg)})
        self.assertEqual(CT.replay(self.bundle, bad.__getitem__)['upper'], 'REJECTED')
        lied = copy.deepcopy(self.bundle)
        lied['lower']['value'] += 1
        self.assertEqual(CT.replay(lied, self.blobs.__getitem__)['status'], 'REJECTED')
        self.assertNotEqual(CT.custody_problems(self.bundle, lambda h: False), [])

    def test_other_custody_paths_refuse_this_schema(self):
        self.assertEqual(CROWS.replay(self.bundle, self.blobs.__getitem__)['status'], 'REJECTED')
        try:
            rep = CB.replay(self.bundle, self.blobs.__getitem__)
            self.assertNotIn(rep.get('status'), ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED'))
        except (KeyError, ValueError, TypeError):
            pass


class Requests(unittest.TestCase):
    def test_the_route_is_known_and_closed(self):
        self.assertEqual(CU.reference_problems(REF), [])
        self.assertIn('generated-rows-tree-c4-v1', CU.REFERENCE_ROUTES)
        for bad in ({'enumerator': 'generic'}, {'package_sha256': REF_TF['package_sha256']}, {'package_sha256': '0' * 64},
                    {'seconds': 0}, {'route': 'generated-rows-tree-c5-v1'}):
            self.assertNotEqual(CU.reference_problems(dict(REF, **bad)), [], bad)
        self.assertNotEqual(CU.reference_problems(dict(REF_TF, package_sha256=REF['package_sha256'])), [])
        self.assertEqual(GC4.known_package(digest(PKG))[1], GC4.PACKAGE)
        with self.assertRaises(ValueError):
            GC4.known_package(REF_TF['package_sha256'])

    def test_each_adapter_offers_only_its_route(self):
        v5 = {'schema': R.REQUEST_V5, 'reference': REF}
        self.assertEqual(CU.reference_options(v5, ADAPTERS[C4]), {'joint': True, 'rows': REF})
        with self.assertRaisesRegex(ValueError, 'offers no generated-rows-tree-c4-v1 reference'):
            CU.reference_options(v5, ADAPTERS[TF])
        with self.assertRaisesRegex(ValueError, 'offers no generated-rows-v1 reference'):
            CU.reference_options(dict(v5, reference=REF_TF), ADAPTERS[C4])
        tf = GraphTask(task_id='tf', domain=TF, family='test', split='DEV', n=8,
                       edges=tuple((a, b) for a in range(8) for b in range(a + 1, 8)))
        self.assertIsInstance(ADAPTERS[TF].reference(tf, rows=REF), Unsupported)
        self.assertIsInstance(ADAPTERS[C4].reference(H, rows=REF_TF), Unsupported)
        self.assertIsInstance(ADAPTERS[C4].reference(H, rows=dict(REF, package_sha256='0' * 64)), Unsupported)


class Adapter(unittest.TestCase):
    def test_the_c4_adapter_computes_the_tree_reference_with_custody(self):
        with tempfile.TemporaryDirectory() as d, Store(Path(d) / 'ev') as s:
            out = ADAPTERS[C4].reference(H, evidence=s, joint=True, rows=REF)
            self.assertEqual((out['status'], out['value']), ('FINITE_CERTIFIED', 25))
            self.assertTrue(out['method'].startswith('GENERATED_ROWS_LP_DUAL_'))
            self.assertEqual((out['route'], out['package_sha256']), (REF['route'], REF['package_sha256']))
            bundle = s.get(out['certificate_bundle'])
            self.assertEqual(bundle['schema'], CT.SCHEMA)
            rep = CT.replay(bundle, s.get_bytes)
            self.assertEqual((rep['status'], rep['lower'], rep['upper']), ('OPTIMALITY_CHECKED', 'VALID', 'VALID'), rep)

    def test_an_uncertified_host_is_unsupported(self):
        out = ADAPTERS[C4].reference(K8, rows=dict(REF, seconds=5))           # small dense hosts are slow (B20_R51)
        self.assertIsInstance(out, Unsupported)

    def test_small_c4_hosts_keep_exact_search(self):
        small = c4host(6, [(a, b) for a in range(6) for b in range(a + 1, 6)], 'k6')
        out = ADAPTERS[C4].reference(small, rows=REF)
        self.assertEqual((out['value'], out['method']), (7, 'DUAL_EXACT_SEARCH'))


class DraftRule(unittest.TestCase):
    def test_the_c4_draft_checks_records_but_no_study_adopts_it(self):
        rule = CAL.SELECTION_RULE_E1_HARD_V2_C4TREE_DRAFT
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import b20r50_e1b_c4_readiness as R50
        self.assertEqual(rule, R50.RULE)
        self.assertNotIn(rule, CAL.RULES)
        self.assertNotIn(rule['name'], CAL.RULES_BY_NAME)
        self.assertIs(CAL.DRAFT_RULES_BY_NAME[rule['name']], rule)
        self.assertEqual(CAL.record_problems(synthetic_record(rule)), [])
        cfg = json.loads((ROOT / CAL.CONFIG).read_text())
        adopted = {e.get('rule') for s in cfg.get('studies', {}).values() for e in s.values()}
        self.assertNotIn(rule['name'], adopted)


if __name__ == '__main__':
    unittest.main()
