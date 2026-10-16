"""B20_R39: custody of certificates over generated rows (built, not wired into the evaluator). A
bundle replays checker-only; every alteration is rejected: of the certificate, the package, the
registry, the witness or the bound. So are revoked identities. The evaluator's bundle replay does
not accept this schema, and the generated-rows reference produces custody for both its upper-bound
methods."""
import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from genesis.common import canonical
from genesis.discovery import generated_certify as GC
from genesis.models import GraphTask
from genesis.verification import certificates as CB
from genesis.verification import certificates_rows as CR
from genesis.verification import lp_dual_rows as V

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = json.loads((ROOT / 'evidence' / 'generator_v2_b20r37' / 'package.json').read_text())
K6 = GraphTask(task_id='k6-rows', domain='triangle_free_host_v1', family='test', split='DEV', n=6,
               edges=tuple(itertools.combinations(range(6), 2)))
BIPARTITE = [(u, v) for u, v in K6.edges if (u < 3) != (v < 3)]          # K_{3,3}: 9 edges, optimal


def bundle():
    from genesis.formal_research.triangle_theory import DEFS_SOURCE
    reg = V.registry_from_package(PACKAGE, defs_source=DEFS_SOURCE)
    cert, _, _ = GC.lp_dual_rows(K6, reg)
    return CR.build(K6, witness=BIPARTITE, lower=9, certificate=cert, package=PACKAGE)


class Custody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b, cls.blobs = bundle()
        cls.get = lambda self, h: self.blobs[h]

    def replay(self, b=None, blobs=None, **kw):
        blobs = self.blobs if blobs is None else blobs
        return CR.replay(b or self.b, lambda h: blobs[h], **kw)

    def test_bundle_replays_checker_only(self):
        self.assertEqual(self.b['status'], 'OPTIMALITY_CHECKED')
        r = self.replay()
        self.assertEqual((r['status'], r['lower'], r['upper'], r['problems']), ('OPTIMALITY_CHECKED', 'VALID', 'VALID', []))
        self.assertEqual(CR.custody_problems(self.b, lambda h: h in self.blobs), [])

    def test_alterations_are_rejected(self):
        up = self.b['upper']

        def with_object(key, f):
            blobs = dict(self.blobs)
            obj = json.loads(blobs[up[key]])
            f(obj)
            blobs[up[key]] = canonical(obj)
            return self.replay(blobs=blobs)
        r = with_object('certificate_sha256', lambda c: c['inequalities'][0].__setitem__('weight', '1/1000000'))
        self.assertEqual(r['upper'], 'REJECTED')
        r = with_object('package_sha256', lambda p: p['statements'][3].__setitem__('lean', p['statements'][3]['lean'] + ' '))
        self.assertEqual(r['upper'], 'REJECTED')
        r = with_object('registry_sha256', lambda g: g['patterns'].popitem())
        self.assertEqual(r['upper'], 'REJECTED')
        b = copy.deepcopy(self.b)
        b['upper']['value'] = 8
        self.assertEqual(self.replay(b)['upper'], 'REJECTED')
        b = copy.deepcopy(self.b)
        b['lower']['value'] = 10
        self.assertEqual(self.replay(b)['status'], 'REJECTED')
        blobs = dict(self.blobs)
        del blobs[up['package_sha256']]
        self.assertIn('package object missing or altered', CR.custody_problems(self.b, lambda h: h in blobs))
        self.assertEqual(self.replay(blobs=blobs)['upper'], 'REJECTED')

    def test_revoked_identities_are_refused(self):
        self.assertEqual(self.replay(revoked=[V.checker_identity()])['upper'], 'REJECTED')
        self.assertEqual(self.replay(revoked=[PACKAGE['package_sha256']])['upper'], 'REJECTED')

    def test_build_refuses_bad_inputs(self):
        from genesis.formal_research.triangle_theory import DEFS_SOURCE
        reg = V.registry_from_package(PACKAGE, defs_source=DEFS_SOURCE)
        cert, _, _ = GC.lp_dual_rows(K6, reg)
        bad = copy.deepcopy(cert)
        bad['bound'] = 8
        with self.assertRaises(ValueError):
            CR.build(K6, witness=BIPARTITE, lower=9, certificate=bad, package=PACKAGE)
        with self.assertRaises(ValueError):
            CR.build(K6, witness=BIPARTITE, lower=10, certificate=cert, package=PACKAGE)
        tampered = copy.deepcopy(PACKAGE)
        tampered['statements'][0]['status'] = 'DISPROVED'
        with self.assertRaises(ValueError):
            CR.build(K6, witness=BIPARTITE, lower=9, certificate=cert, package=tampered)

    def test_evaluator_replay_does_not_accept_this_schema(self):
        self.assertNotIn(CR.METHOD, CB.CHECKED_METHODS_V2)
        r = CB.replay(self.b, lambda h: self.blobs[h])
        self.assertNotEqual(r['status'], 'OPTIMALITY_CHECKED')


class Reference(unittest.TestCase):
    def test_reference_takes_its_result_into_custody(self):
        with tempfile.TemporaryDirectory() as d:
            out = GC.reference(K6, PACKAGE, seconds=30, evidence=d)
            self.assertEqual((out['status'], out['value'], out['method']), ('FINITE_CERTIFIED', 9, 'GENERATED_ROWS_LP_DUAL_GENERATED_EXACT'))
            bundle = json.loads((Path(d) / 'bundles' / f'{out["certificate_bundle"]}.json').read_text())
            r = CR.replay(bundle, lambda h: (Path(d) / 'objects' / h).read_bytes())
            self.assertEqual(r['status'], 'OPTIMALITY_CHECKED')


if __name__ == '__main__':
    unittest.main()
