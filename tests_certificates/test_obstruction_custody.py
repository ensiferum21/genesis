"""Repair D (B20-REVIEW-04): joint construction/obstruction bounds keep full certificate custody.

B19 exported 12 joint upper bounds (all LP_DUAL_EXACT, 11 closing the gap) without the
final witness or the exact LP certificate. The repaired ``obstruction.certify`` returns a
``genesis-certificate-bundle-v2`` with the witness, the exact rational LP certificate and,
for SAT/DRAT bounds, the original CNF and DRAT bytes. Every bundle replays from its
objects alone, with the producers disabled, and the optimisation path obeys the shared
kernel's promotion and revocation rules. Requires the pinned CaDiCaL and drat-trim
(release-blocking suite: missing tools fail, never skip).
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import unittest

from genesis.common import canonical, digest
from genesis.discovery import obstruction as O
from genesis.domains import ADAPTERS
from genesis.dsl import solve
from genesis.kernel.anchors import pinned_tool_anchors
from genesis.kernel.evidence import EvidenceKernel
from genesis.models import SolverProgram
from genesis.store import Store
from genesis.verification import certificates as CB
from genesis.verification import lp_dual as LP
from genesis.verification.tools import tool

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def no_producers():
    """scipy (the LP producer) cannot be imported and the SAT solver refuses to run."""
    saved = {k: sys.modules[k] for k in list(sys.modules) if k == 'scipy' or k.startswith('scipy.')}
    for k in saved:
        del sys.modules[k]
    sys.modules['scipy'] = None
    try:
        with CB.checker_only():
            yield
    finally:
        del sys.modules['scipy']
        sys.modules.update(saved)


def tasks(n, p, count, seed=4242):
    return ADAPTERS['triangle_free_host_v1'].generate(seed, count, 'DEV', 'erdos', {'n': n, 'p': p})[0]


def greedy(t):
    return solve(t, SolverProgram(rounds=8), 100000, 0)['selected']


class _Fx:
    lp = None
    sat = None

    @classmethod
    def lp_record(cls):
        if cls.lp is None:
            t = tasks(14, 0.5, 1)[0]
            cls.lp = (t, O.certify(t, greedy(t), seconds=20))
        return cls.lp

    @classmethod
    def sat_bundle(cls):
        """A SAT_DRAT bundle from the B13 certified_bounds route on a small dense host."""
        if cls.sat is None:
            from genesis.verification.sat import certified_bounds, encode
            for t in tasks(8, 0.7, 6, seed=77):
                r = certified_bounds(t, seconds=60)
                cert = r['upper_certificate']
                if r['status'] == 'OPTIMALITY_CHECKED' and cert.get('method') == 'SAT_DRAT':
                    cnf = encode(t, cert['upper'] + 1)
                    b, objs = CB.build_v2(t, witness=[list(e) for e in r['witness']], lower=r['lower'],
                                          upper={'method': 'SAT_DRAT', 'certificate': cert, 'cnf': cnf,
                                                 'proof': r['proof']})
                    cls.sat = (t, b, objs)
                    break
            else:
                raise AssertionError('no SAT_DRAT-certified fixture host found')
        return cls.sat


def store_of(objs):
    d = dict(objs)

    def get(h):
        data = d[h]
        if CB._sha(data) != h:
            raise ValueError('object corruption')
        return data
    return d, get, (lambda h: h in d and CB._sha(d[h]) == h)


class OriginalFinding(unittest.TestCase):
    def test_b19_rows_lack_custody_and_stay_as_history(self):
        f = json.loads((ROOT / 'audit' / 'review_b20' / 'findings.json').read_text())
        r04 = next(x for x in f['findings'] if x['finding'] == 'B20-REVIEW-04')
        self.assertEqual((r04['status'], r04['rows'], r04['optimality_checked'], r04['rows_without_witness'],
                          r04['rows_without_certificate']), ('REPRODUCED', 12, 11, 12, 12))
        ev = ROOT / 'evidence' / 'discovery_b19' / 'obstruction' / 'evaluation.json'
        self.assertEqual(CB._sha(ev.read_bytes()), r04['sources']['obstruction/evaluation.json'])


class LPCustody(unittest.TestCase):
    def setUp(self):
        self.t, self.rec = _Fx.lp_record()

    def test_certify_returns_a_complete_bundle(self):
        b = self.rec['bundle']
        self.assertEqual(b['schema'], CB.SCHEMA_V2)
        self.assertEqual(b['upper']['method'], 'LP_DUAL_EXACT')
        self.assertEqual(b['upper']['checker'], LP.checker_identity())
        _, _, has = store_of(self.rec['objects'])
        self.assertEqual(CB.custody_problems(b, has), [])
        self.assertTrue(b['attempts'])
        self.assertEqual(self.rec['status'], b['status'])

    def test_lp_replay_without_the_optimisation_producer(self):
        _, get, _ = store_of(self.rec['objects'])
        with no_producers():
            r = CB.replay(json.loads(canonical(self.rec['bundle'])), get)
        self.assertEqual(r['status'], self.rec['status'])
        self.assertIn(r['status'], ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED'))
        self.assertEqual(r['problems'], [])

    def test_persisted_directory_replays_via_the_cli(self):
        d = Path(tempfile.mkdtemp())
        h = CB.persist_dir(d, self.rec['bundle'], self.rec['objects'])
        import os
        import subprocess
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        p = subprocess.run([sys.executable, '-m', 'genesis.verification.certificates', str(d / 'bundles' / f'{h}.json'),
                            '--objects', str(d / 'objects')], capture_output=True, text=True, env=env, timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(self.rec['status'], p.stdout)

    def test_changed_rational_coefficient(self):
        objs, _, _ = store_of(self.rec['objects'])
        b = json.loads(canonical(self.rec['bundle']))
        cert = json.loads(objs[b['upper']['certificate_sha256']])
        from fractions import Fraction
        cert['inequalities'][0]['weight'] = str(Fraction(cert['inequalities'][0]['weight']) / 2)
        nb = canonical(cert)
        objs[CB._sha(nb)] = nb
        b['upper']['certificate_sha256'] = CB._sha(nb)
        _, get, _ = store_of(objs)
        with no_producers():
            r = CB.replay(b, get)
        self.assertEqual(r['status'], 'REJECTED')
        self.assertTrue(any('LP certificate' in p for p in r['problems']))

    def test_altered_object_bytes(self):
        objs, _, has = store_of(self.rec['objects'])
        h = self.rec['bundle']['upper']['certificate_sha256']
        objs[h] = objs[h].replace(b'"rhs"', b'"RHS"')
        _, get, has = store_of(objs)
        self.assertIn('LP certificate object missing or altered', CB.custody_problems(self.rec['bundle'], has))
        with no_producers():
            self.assertEqual(CB.replay(self.rec['bundle'], get)['status'], 'REJECTED')

    def test_changed_task(self):
        b = json.loads(canonical(self.rec['bundle']))
        b['problem']['task']['edges'] = b['problem']['task']['edges'][:-1]
        b['problem']['task_sha256'] = digest(b['problem']['task'])
        _, get, _ = store_of(self.rec['objects'])
        with no_producers():
            r = CB.replay(b, get)
        self.assertEqual(r['status'], 'REJECTED')

    def test_swapped_witness(self):
        other = tasks(14, 0.5, 2)[1]
        w = canonical([list(e) for e in greedy(other)])
        objs, _, _ = store_of(self.rec['objects'])
        objs[CB._sha(w)] = w
        b = json.loads(canonical(self.rec['bundle']))
        b['lower']['witness_sha256'] = CB._sha(w)
        b['lower']['witness'] = json.loads(w)
        _, get, _ = store_of(objs)
        with no_producers():
            r = CB.replay(b, get)
        self.assertEqual(r['lower'], 'REJECTED')
        self.assertNotIn(r['status'], ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED'))

    def test_missing_objects_and_unsupported_method(self):
        objs, _, _ = store_of(self.rec['objects'])
        del objs[self.rec['bundle']['upper']['certificate_sha256']]
        _, get, has = store_of(objs)
        self.assertTrue(CB.custody_problems(self.rec['bundle'], has))
        with no_producers():
            self.assertEqual(CB.replay(self.rec['bundle'], get)['status'], 'REJECTED')
        b = json.loads(canonical(self.rec['bundle']))
        b['upper'] = {'method': 'THEOREM', 'value': b['upper']['value']}
        _, get, has = store_of(self.rec['objects'])
        self.assertTrue(any('not independently certified' in p for p in CB.custody_problems(b, has)))
        self.assertEqual(CB.replay(b, get)['status'], 'REJECTED')

    def test_revoked_checker_blocks_replay(self):
        _, get, has = store_of(self.rec['objects'])
        dead = [LP.checker_identity()]
        self.assertTrue(any('revoked' in p for p in CB.custody_problems(self.rec['bundle'], has, dead)))
        with no_producers():
            self.assertEqual(CB.replay(self.rec['bundle'], get, dead)['status'], 'REJECTED')

    def test_builder_refuses_invalid_or_inconsistent_bounds(self):
        bad = dict(self.rec['bundle'])
        cert = json.loads(store_of(self.rec['objects'])[0][self.rec['bundle']['upper']['certificate_sha256']])
        cert['bound'] = cert['bound'] - 1
        with self.assertRaises(ValueError):
            CB.build_v2(self.t, witness=self.rec['witness'], lower=self.rec['lower'],
                        upper={'method': 'LP_DUAL_EXACT', 'certificate': cert})
        with self.assertRaises(ValueError):
            CB.build_v2(self.t, witness=self.rec['witness'], lower=len(self.t.edges) + 1,
                        upper={'method': 'HOST_EDGE_COUNT'})
        with self.assertRaises(ValueError):
            CB.build_v2(self.t, witness=self.rec['witness'], lower=self.rec['lower'], upper={'method': 'THEOREM'})
        self.assertTrue(bad)

    def test_unknown_schema_is_not_a_bundle(self):
        b = dict(self.rec['bundle'], schema='genesis-certificate-bundle-v9')
        _, get, has = store_of(self.rec['objects'])
        self.assertEqual(CB.custody_problems(b, has), ['not a certificate bundle'])
        self.assertEqual(CB.replay(b, get)['status'], 'REJECTED')


class SATCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool('cadical'); tool('drat-trim')                      # fail, not skip, without the pinned tools
        cls.t, cls.b, cls.objs = _Fx.sat_bundle()

    def test_sat_replay_with_only_the_checker(self):
        _, get, has = store_of(self.objs)
        self.assertEqual(CB.custody_problems(self.b, has), [])
        with no_producers():
            r = CB.replay(self.b, get)
        self.assertEqual(r['status'], 'OPTIMALITY_CHECKED', r)

    def test_corrupted_cnf_and_proof(self):
        objs, _, _ = store_of(self.objs)
        cnf = objs[self.b['upper']['cnf_sha256']]
        fake = cnf.replace(b'p cnf', b'c tampered\np cnf', 1)
        objs[CB._sha(fake)] = fake
        b = json.loads(canonical(self.b))
        b['upper']['cnf_sha256'] = CB._sha(fake)
        _, get, _ = store_of(objs)
        with no_producers():
            r = CB.replay(b, get)
        self.assertEqual(r['status'], 'REJECTED')
        objs, _, _ = store_of(self.objs)
        del objs[self.b['upper']['proof_sha256']]
        _, get, has = store_of(objs)
        self.assertTrue(CB.custody_problems(self.b, has))
        with no_producers():
            self.assertEqual(CB.replay(self.b, get)['status'], 'REJECTED')


class KernelPath(unittest.TestCase):
    """The optimisation path obeys the same promotion, replay and revocation rules."""

    def setUp(self):
        self.t, self.rec = _Fx.lp_record()
        self.assertEqual(self.rec['gap'], 0)       # the fixed DEV host closes its gap (no skips in this suite)
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.s.close)
        self.k = EvidenceKernel(self.s, anchors=pinned_tool_anchors())

    def test_promotion_replays_and_revocation_lowers_the_level(self):
        out = O.record_evidence(self.s, self.k, self.t, self.rec, source_hash='test')
        self.assertTrue(out['promoted'], out['rejection'])
        self.assertEqual(self.k.levels(out['claim'])['math'], 'OPTIMALITY_CHECKED')
        self.assertEqual(out['soundness']['optimum_problems'], [])             # CRPD-1: BOUND on both sides
        self.assertEqual((out['soundness']['lower']['established'], out['soundness']['upper']['established']),
                         ('BOUND', 'BOUND'))
        reg = self.k.register_verifier(LP.checker_identity(), LP.checker_identity().split('@')[1])
        self.k.revoke(reg, 'test: LP checker withdrawn', 'test')
        self.assertNotEqual(self.k.levels(out['claim'])['math'], 'OPTIMALITY_CHECKED')
        self.assertIsNotNone(self.k._bound_state_problems(out['bound_state']))

    def test_incomplete_bundle_cannot_reach_optimality(self):
        rec = dict(self.rec, objects={h: v for h, v in self.rec['objects'].items()
                                      if h != self.rec['bundle']['upper']['certificate_sha256']})
        out = O.record_evidence(self.s, self.k, self.t, rec, source_hash='test')
        self.assertFalse(out['promoted'])
        self.assertTrue(out['soundness']['optimum_problems'])                  # the upper side does not replay
        self.assertIn('LP certificate', out['rejection'][0] if isinstance(out['rejection'], list)
                      else str(out['rejection']))


if __name__ == '__main__':
    unittest.main()
