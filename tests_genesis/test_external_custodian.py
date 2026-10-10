import base64
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from genesis.custodian import register,evaluate,verify,release_preflight
from genesis.kernel import receipts as R
from tests_genesis.signed_fixtures import campaign_export
from genesis.models import Limits,SolverProgram
from genesis.common import canonical,digest,code_identity,bytes_hash
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
        self.source=source
        self.export=campaign_export(self.root,campaign_id='a'*64,source_hash=source)
        self.manifest=self.root/'exposure_manifest.json'
        self.manifest.write_text(json.dumps({'schema':'genesis-exposure-manifest-v1','sources':[]}));self.manifest.chmod(0o600)
        self.request={'schema':'genesis-evaluation-request-v3','campaign_id':'a'*64,'candidate_version':'b'*64,
                      'claim_id':'utility-fixture','evidence_kind':'sealed_evaluation','generation_transition':None,
                      'statement_hash':'5'*64,'scope':'fixture panel',
                      'transfer_source_domain':None,
                      'campaign_export_sha256':bytes_hash(self.export.read_bytes()),
                      'source_hash':source,'programs':{'baseline':SolverProgram().model_dump(mode='json'),
                      'candidate':SolverProgram(weights=(0,0,0,1)).model_dump(mode='json')},
                      'limits':Limits().model_dump(mode='json'),'seed':42,'task_count':2,'domain':'c4_host_v2',
                      'analysis':{'primary':'paired-edge-count','alpha':.05,'family_sensitivity':True,'hypotheses':1},
                      'exposed_graph_fingerprints':[],'expected_evaluator_hash':source}

    def test_real_signed_fixture_and_replay_reservation(self):
        anchor=register(self.root,self.request,self.key,'TEST_FIXTURE_NOT_INDEPENDENT',**self.reg())
        rid=digest(self.request)
        receipt=evaluate(self.root,rid,self.pool,self.key,'TEST_FIXTURE_NOT_INDEPENDENT')
        payload=verify(receipt,self.public)
        self.assertEqual(payload['completed_rows'],4);self.assertNotIn('promotion_allowed',payload)
        self.assertEqual(payload['anchor_hash'],digest(anchor))
        self.assertEqual(payload['panel_commitment'],anchor['payload']['panel_commitment'])
        self.assertEqual(payload['claim_id'],'utility-fixture')
        self.assertEqual(payload['outcome'],R.derive_outcome(payload))
        self.assertEqual(R.check_receipt(payload,'sealed_evaluation'),[])
        public=canonical(receipt)
        self.assertNotIn(self.tasks[0].task_id.encode(),public)
        with self.assertRaises(FileExistsError):evaluate(self.root,rid,self.pool,self.key,'fixture')
        with Store(self.root/'evaluations'/rid) as evidence:
            self.assertEqual(evidence.db.execute('SELECT count(*) FROM attempts').fetchone()[0],6)
            self.assertGreater(evidence.verify()['events'],0)

    def test_relabelled_pool_cannot_reset_exposure(self):
        register(self.root,self.request,self.key,'fixture',**self.reg());evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')
        changed=[relabel(t,tuple(reversed(range(t.n)))) for t in self.tasks]
        self.pool.write_bytes(canonical([t.model_dump(mode='json') for t in changed]))
        self.request['campaign_id']='c'*64;self.request['claim_id']='utility-relabelled'
        self.export=campaign_export(self.root,campaign_id='c'*64,source_hash=self.source,name='export-c.zip')
        self.request['campaign_export_sha256']=bytes_hash(self.export.read_bytes())
        register(self.root,self.request,self.key,'fixture',**self.reg())
        with self.assertRaises(Exception):evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')

    def test_visible_graph_exposure_blocks_panel(self):
        self.request['exposed_graph_fingerprints']=[canonical_graph(self.tasks[0])]
        register(self.root,self.request,self.key,'fixture',**self.reg())
        with self.assertRaisesRegex(ValueError,'research-visible'):evaluate(self.root,digest(self.request),self.pool,self.key,'fixture')

    def reg(self):
        return {'exposure_manifest':self.manifest,'campaign_export':self.export,'pool':self.pool}

    def test_pool_must_match_the_registered_commitment(self):
        register(self.root,self.request,self.key,'fixture',**self.reg())
        other,_=make_panel(9182,2,'c4_host_v2','CONFIRM')
        swapped=self.root/'swapped.json';swapped.write_bytes(canonical([t.model_dump(mode='json') for t in other]))
        with self.assertRaisesRegex(ValueError,'committed at registration'):
            evaluate(self.root,digest(self.request),swapped,self.key,'fixture')

    def test_one_registration_per_claim_slot(self):
        register(self.root,self.request,self.key,'fixture',**self.reg())
        again=dict(self.request,seed=43)  # same candidate, kind, domain: a second draw
        with self.assertRaisesRegex(ValueError,'already registered'):
            register(self.root,again,self.key,'fixture',**self.reg())
        renamed=dict(self.request,claim_id='utility-fixture (v2)',statement_hash='6'*64)  # B14 round-2 H2
        with self.assertRaisesRegex(ValueError,'already registered'):
            register(self.root,renamed,self.key,'fixture',**self.reg())

    def test_request_facts_must_match_the_campaign_export(self):
        for change,fragment in (({'campaign_id':'d'*64},'campaign_id'),({'source_hash':'d'*64},'source_hash'),
                                ({'evidence_kind':'sealed_transfer_evaluation','transfer_source_domain':'triangle_free_host_v1'},
                                 'transfer'),
                                ({'evidence_kind':'sealed_improver_evaluation'},'lineage'),
                                ({'domain':'triangle_free_host_v1'},'domain')):
            with self.assertRaisesRegex(ValueError,fragment):
                register(self.root,dict(self.request,**change),self.key,'fixture',**self.reg())
        bare=self.root/'bare.zip'
        with zipfile.ZipFile(bare,'w') as z:z.writestr('MANIFEST.json','{}')
        with self.assertRaisesRegex(ValueError,'no event history'):
            register(self.root,dict(self.request,campaign_export_sha256=bytes_hash(bare.read_bytes())),self.key,
                     'fixture',exposure_manifest=self.manifest,campaign_export=bare,pool=self.pool)

    def test_v2_request_without_claim_binding_refused(self):
        legacy={k:v for k,v in self.request.items() if k not in ('claim_id','evidence_kind','generation_transition',
                                                               'transfer_source_domain','statement_hash','scope')}
        legacy['schema']='genesis-evaluation-request-v2'
        with self.assertRaisesRegex(ValueError,'schema'):register(self.root,legacy,self.key,'fixture',**self.reg())

    def test_missing_external_trust_root_blocks(self):
        r=release_preflight(self.request,{}, {},{},trust_root=self.root/'absent')
        self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['promotion_allowed'])

    def test_candidate_mutation_breaks_signature(self):
        anchor=register(self.root,self.request,self.key,'fixture',**self.reg())
        anchor['payload']['request_hash']='d'*64
        with self.assertRaises(Exception):verify(anchor,self.public)
