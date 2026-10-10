"""Harder panels beyond the exhaustive range, evaluated by the custodian with SAT certificates."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.common import bytes_hash, canonical, code_identity, digest
from genesis.custodian import register, evaluate, reference_optimum
from genesis.graphs import check_witness
from genesis.models import Limits, SolverProgram
from genesis.panels import make_hard_panel
from genesis.store import Store
from genesis.verification.tools import available

READY = available('cadical') and available('drat-trim')
REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(READY, 'pinned CaDiCaL/drat-trim not installed')
class HardPanels(unittest.TestCase):
    def test_generator_is_deterministic_distinct_and_beyond_exhaustive_range(self):
        a, stats = make_hard_panel(77, 4, 'c4_host_v2', 'DEV', certify_seconds=60)
        b, _ = make_hard_panel(77, 4, 'c4_host_v2', 'DEV', certify_seconds=60)
        self.assertEqual([t.model_dump() for t in a], [t.model_dump() for t in b])
        self.assertTrue(all(len(t.edges) > 24 for t in a))
        self.assertEqual(stats['generator'], 'panels.make_hard_panel-v1')
        for t in a:
            opt = reference_optimum(t)
            self.assertEqual(opt['method'], 'SAT_DRAT_UPPER+CHECKED_WITNESS')
            self.assertEqual(check_witness(t, opt['witness'])['value'], opt['value'])

    def test_custodian_evaluates_a_hard_confirm_panel(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); private = base / 'private'; private.mkdir(mode=0o700); private.chmod(0o700)
            key = base / 'k.pem'
            key.write_bytes(Ed25519PrivateKey.generate().private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            manifest = private / 'm.json'
            manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
            manifest.chmod(0o600)
            export = base / 'e.zip'
            with zipfile.ZipFile(export, 'w') as z:
                z.writestr('MANIFEST.json', '{}')
            tasks, _ = make_hard_panel(4401, 2, 'c4_host_v2', 'CONFIRM', certify_seconds=60)
            pool = base / 'pool.json'; pool.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
            source = code_identity(REPO)['sha256']
            request = {'schema': 'genesis-evaluation-request-v2', 'campaign_id': 'a' * 64, 'candidate_version': 'b' * 64,
                       'campaign_export_sha256': bytes_hash(export.read_bytes()), 'source_hash': source,
                       'programs': {'baseline': SolverProgram(rounds=8).model_dump(mode='json'),
                                    'candidate': SolverProgram(rounds=8, exchange=True).model_dump(mode='json')},
                       'limits': Limits(cpu_seconds=10).model_dump(mode='json'), 'seed': 1, 'task_count': 2,
                       'domain': 'c4_host_v2',
                       'analysis': {'primary': 'paired-edge-count', 'alpha': 0.05, 'family_sensitivity': True,
                                    'hypotheses': 1},
                       'exposed_graph_fingerprints': [], 'expected_evaluator_hash': source}
            register(private, request, key, 'fixture', exposure_manifest=manifest, campaign_export=export)
            receipt = evaluate(private, digest(request), pool, key, 'fixture')
            self.assertEqual(receipt['payload']['completed_rows'], 4)
            with Store(private / 'evaluations' / digest(request)) as s:
                optima = [s.get(r[0]) for r in s.db.execute("SELECT receipt FROM attempts WHERE trial_id LIKE 'optimum-%'")]
                self.assertTrue(all(o['result']['method'] == 'SAT_DRAT_UPPER+CHECKED_WITNESS' for o in optima))
                proof = optima[0]['result']['upper_certificate'].get('proof_object')
                if proof:
                    self.assertTrue(s.get_bytes(proof))


if __name__ == '__main__':
    unittest.main()
