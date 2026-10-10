"""R-02 regression: effective revocation survives every report, export and rebuild.

Acceptance (roadmap §3.2): revoke a direct dependency, an ancestor, a verifier or
an imported capability; export and independently rebuild the bundle; every
dependent claim is downgraded consistently. A bundle asserting stale valid
levels is rejected. Unaffected claims remain valid.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from genesis.common import canonical, code_identity
from genesis.kernel.evidence import EvidenceKernel
from genesis.kernel.index import build_index
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store
from tests_genesis.signed_fixtures import witness_payload

REPO = Path(__file__).resolve().parents[1]
SRC = 'a' * 64


def rewrite(bundle, out, victim, transform):
    """Replace one bundled file and re-hash it in MANIFEST.json (a producer that lies consistently)."""
    with zipfile.ZipFile(bundle) as zin, zipfile.ZipFile(out, 'w') as zout:
        names = zin.namelist()
        base = names[0].split('/')[0] + '/'
        data = {n: zin.read(n) for n in names}
        data[base + victim] = transform(data[base + victim])
        manifest = json.loads(data[base + 'MANIFEST.json'])
        manifest['files'][victim] = hashlib.sha256(data[base + victim]).hexdigest()
        data[base + 'MANIFEST.json'] = canonical(manifest)
        for n in names:
            zout.writestr(n, data[n])


class ExportRevocation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.root = self.d / 'campaign'
        with Store(self.root) as s:
            s.set_state('source_hash', code_identity(REPO)['sha256'])
            k = EvidenceKernel(s)
            k.register_verifier('dual-predicates', 'f' * 64)
            self.vreg = k.register_verifier('revocable-checker', 'e' * 64)
            capability = k.record('compiled_capability', {'macro': 'imported'}, route='genesis.campaign',
                                  source_hash=SRC, verdict='VALID')
            runs = {name: k.record('execution_receipt', {'run': name}, route='genesis.campaign', source_hash=SRC,
                                   verdict='VALID', parents=[capability] if name == 'imported' else [])
                    for name in ('direct', 'ancestor', 'verifier', 'imported', 'unaffected')}
            self.runs = runs
            self.checks = {}
            for name, run in runs.items():
                verifier = 'revocable-checker' if name == 'verifier' else 'dual-predicates'
                self.checks[name] = k.record('witness_check', witness_payload(s), parents=[run],
                                             route='genesis.campaign', source_hash=SRC, verdict='VALID',
                                             verifier=verifier)
                k.create_claim(name, f'claim {name}: host path4 has a valid subgraph with 3 edges', 'host path4', [self.checks[name]])
                k.promote(name, 'math', 'WITNESS_VALID')
            self.capability = capability
        self.before = self.d / 'before.zip'
        build_bundle(self.root, self.before, report='The returned witness passed the registered checks.')

    def revoke_all(self):
        with Store(self.root) as s:
            k = EvidenceKernel(s)
            k.revoke(self.checks['direct'], 'checker receipt found faulty', 'auditor')
            k.revoke(self.runs['ancestor'], 'run used a leaked lemma', 'auditor')
            k.revoke(self.vreg, 'verifier bug: accepts a 4-cycle', 'auditor')
            k.revoke(self.capability, 'imported macro was compiled from sealed material', 'auditor')

    def levels(self, bundle):
        with zipfile.ZipFile(bundle) as z:
            name = next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))
            claims = json.loads(z.read(name))
        return {c['claim_id']: c for c in claims['claims']}

    def test_every_dependent_claim_is_downgraded_in_export_and_rebuild(self):
        self.revoke_all()
        after = self.d / 'after.zip'
        build_bundle(self.root, after)
        claims = self.levels(after)
        for name in ('direct', 'ancestor', 'verifier', 'imported'):
            self.assertEqual(claims[name]['effective_levels']['math'], 'UNCHECKED', name)
            self.assertTrue(claims[name]['effective_levels'].get('invalidated'), name)
            self.assertTrue(claims[name]['invalidated_by'], name)
            # History is kept, clearly separated from current status.
            self.assertEqual(claims[name]['historical']['recorded_levels']['math'], 'WITNESS_VALID')
        self.assertEqual(claims['unaffected']['effective_levels']['math'], 'WITNESS_VALID')
        reasons = {r['target']: r for c in claims.values() for r in c['invalidated_by']}
        self.assertIn('verifier:revocable-checker', reasons)
        result = verify_bundle(after)  # rebuilds the store from events + objects and re-derives every claim
        self.assertTrue(result['ok'], result['problems'])

    def test_bundle_asserting_stale_levels_is_rejected(self):
        self.revoke_all()
        after = self.d / 'after.zip'
        build_bundle(self.root, after)

        def stale(raw):
            c = json.loads(raw)
            for claim in c['claims']:
                claim['effective_levels'] = claim['historical']['recorded_levels']
            return canonical(c)

        lying = self.d / 'lying.zip'
        rewrite(after, lying, 'CLAIMS.json', stale)
        result = verify_bundle(lying)
        self.assertFalse(result['ok'])
        self.assertTrue(any('does not license' in p for p in result['problems']), result['problems'])

        def legacy(raw):  # the B13 CLAIMS.json shape
            c = json.loads(raw)
            return canonical({'claims': [{'claim_id': x['claim_id'], 'levels': x['historical']['recorded_levels']}
                                         for x in c['claims']], 'promotion_allowed': False})

        old = self.d / 'legacy.zip'
        rewrite(after, old, 'CLAIMS.json', legacy)
        result = verify_bundle(old)
        self.assertFalse(result['ok'])
        self.assertTrue(any('predates effective-level export' in p for p in result['problems']))

        def hide(raw):
            return canonical({'schema': 'genesis-revocations-v1', 'records': []})

        hidden = self.d / 'hidden.zip'
        rewrite(after, hidden, 'REVOCATIONS.json', hide)
        self.assertFalse(verify_bundle(hidden)['ok'])

    def test_older_release_checked_against_a_later_revocation_feed(self):
        self.revoke_all()
        after = self.d / 'after.zip'
        build_bundle(self.root, after)
        feed = self.d / 'REVOCATIONS.json'
        with zipfile.ZipFile(after) as z:
            feed.write_bytes(z.read(next(n for n in z.namelist() if n.endswith('/REVOCATIONS.json'))))
        result = verify_bundle(self.before, later_revocations=feed)
        self.assertTrue(result['ok'], result['problems'])  # valid as released
        self.assertEqual(result['current']['downgraded_since_release'], ['ancestor', 'direct', 'imported', 'verifier'])
        self.assertEqual(result['current']['applied'], 4)

    def test_forged_state_cannot_unrevoke_or_promote(self):
        self.revoke_all()
        with Store(self.root) as s:
            s.set_state('evrevoked', [])
            s.set_state('evrevoked_keys', [])
            s.set_state('claimlevels:direct', {'math': 'OPTIMALITY_CHECKED'})
            s.set_state(f'evnode:{self.checks["direct"]}', {'kind': 'witness_check', 'parents': [], 'verdict': 'VALID',
                                                            'effects': [], 'route': 'x', 'source_hash': SRC,
                                                            'verifier': None, 'payload_hash': '0' * 64,
                                                            'schema': 'genesis-evidence-node-v1', 'scope': None})
            k = EvidenceKernel(s)
            self.assertTrue(k.levels('direct').get('invalidated'))
            self.assertEqual(k.recorded_levels('direct')['math'], 'WITNESS_VALID')
        after = self.d / 'after.zip'
        build_bundle(self.root, after)
        self.assertEqual(self.levels(after)['direct']['effective_levels']['math'], 'UNCHECKED')
        self.assertTrue(verify_bundle(after)['ok'])

    def test_cached_report_outrunning_current_evidence_is_not_shipped(self):
        self.revoke_all()
        with self.assertRaisesRegex(ValueError, 'exceeds the current effective evidence'):
            build_bundle(self.root, self.d / 'x.zip', report='This construction is optimal.')

    def test_relational_index_uses_effective_levels(self):
        self.revoke_all()
        with Store(self.root) as s:
            build_index(s, self.d / 'index.sqlite3')
        db = sqlite3.connect(self.d / 'index.sqlite3')
        rows = dict(db.execute('SELECT claim_id, current_levels FROM claims'))
        db.close()
        self.assertEqual(json.loads(rows['direct'])['math'], 'UNCHECKED')
        self.assertEqual(json.loads(rows['unaffected'])['math'], 'WITNESS_VALID')


if __name__ == '__main__':
    unittest.main()
