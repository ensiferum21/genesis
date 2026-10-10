import base64
import json
from pathlib import Path
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from genesis.custodian import register,evaluate,verify,release_preflight
from genesis.models import Limits,SolverProgram
from genesis.common import canonical,digest,code_identity
from genesis.graphs import canonical_graph,relabel
from genesis.research import make_panel
from genesis.store import Store


class CustodianTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.root.chmod(0o700)
        k=Ed25519PrivateKey.generate();self.key=self.root/'fixture-key.pem'
        self.key.write_bytes(k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        self.public=base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        self.tasks,_=make_panel(781,2,'c4_host_v2','CONFIRM')
        self.pool=self.root/'fixture-pool.json';self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in self.tasks]))
        source=code_identity(Path(__file__).resolve().parents[1])['sha256']
        self.request={'schema':'genesis-evaluation-request-v1','campaign_id':'a'*64,'candidate_version':'b'*64,
                      'source_hash':source,'programs':{'baseline':SolverProgram().model_dump(mode='json'),
                      'candidate':SolverProgram(weights=(0,0,0,1)).model_dump(mode='json')},
                      'limits':Limits().model_dump(mode='json'),'seed':42,'task_count':2,'domain':'c4_host_v2',
                      'analysis':{'primary':'paired-edge-count','alpha':.05,'family_sensitivity':True,'hypotheses':1},
                      'exposed_graph_fingerprints':[],'expected_evaluator_hash':source}

    def test_real_signed_fixture_and_replay_reservation(self):
        anchor=register(self.root,self.request,self.key,'TEST_FIXTURE_NOT_INDEPENDENT')
        rid=digest(self.request)
        receipt=evaluate(self.root,rid,self.pool,self.key,'TEST_FIXTURE_NOT_INDEPENDENT')
        payload=verify(receipt,self.public)
        self.assertEqual(payload['completed_rows'],4);self.assertFalse(payload['promotion_allowed'])
        self.assertEqual(payload['anchor_hash'],digest(anchor))
        public=canonical(receipt)
        self.assertNotIn(self.tasks[0].task_id.encode(),public)
        with self.assertRaises(FileExistsError):evaluate(self.root,rid,self.pool,self.key,'fixture')
        with Store(self.root/'evaluations'/rid) as evidence:
            self.assertEqual(evidence.db.execute('SELECT count(*) FROM attempts').fetchone()[0],6)
            self.assertGreater(evidence.verify()['events'],0)

    def test_relabelled_pool_cannot_reset_exposure(self):
        register(self.root,self.request,self.key,'fixture');evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')
        changed=[relabel(t,tuple(reversed(range(t.n)))) for t in self.tasks]
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in changed]))
        self.request['campaign_id']='c'*64;register(self.root,self.request,self.key,'fixture')
        with self.assertRaises(Exception):evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')

    def test_visible_graph_exposure_blocks_panel(self):
        self.request['exposed_graph_fingerprints']=[canonical_graph(self.tasks[0])]
        register(self.root,self.request,self.key,'fixture')
        with self.assertRaisesRegex(ValueError,'research-visible'):evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')

    def test_missing_external_role_pins_block(self):
        r=release_preflight(self.request,{}, {},{},pins={})
        self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['promotion_allowed'])

    def test_same_key_cannot_claim_separate_roles(self):
        pins={k:self.public for k in ('custodian_key','prereg_key','auditor_key')};pins['release_authority_id']='fixture'
        self.assertEqual(release_preflight(self.request,{}, {},{},pins=pins)['status'],'BLOCKED')

    def test_candidate_mutation_breaks_signature(self):
        anchor=register(self.root,self.request,self.key,'fixture')
        anchor['payload']['request_hash']='d'*64
        with self.assertRaises(Exception):verify(anchor,self.public)
