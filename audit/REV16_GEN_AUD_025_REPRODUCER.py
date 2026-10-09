import base64, json, tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from custody_reference.evaluator import ARMS,SCHEMA,canonical,sha256,file_sha,evaluate_frozen,verify_bundle
from scripts.external_custody_protocol import canonical_bytes
with tempfile.TemporaryDirectory() as td:
 root=Path(td); pool=root/'pool.json'; pool.write_bytes(canonical([{'id':'a','features':{'x':1},'answer':2},{'id':'b','features':{'x':2},'answer':4}]))
 cs={}
 for a in ARMS:
  p=root/(a+'.json');p.write_bytes(canonical({'expr':{'op':'const','value':2}}));cs[a]=p
 hs={a:file_sha(p) for a,p in cs.items()};pr=root/'prereg.json';pr.write_bytes(canonical({'protocol':SCHEMA,'pool_sha256':file_sha(pool),'candidate_sha256':hs,'evaluation_budget_per_arm':2,'campaign_id':'actual-campaign'}))
 key=Ed25519PrivateKey.generate();kp=root/'key.pem';kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
 pub=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
 out=root/'out';evaluate_frozen(pool,cs,pr,kp,out,custodian_id='actual-custodian')
 aggregate=json.loads((out/'aggregate.json').read_bytes());aggregate['campaign_id']='unrelated-campaign'
 for a in ARMS:aggregate['arms'][a]={'tasks':1,'correct':1,'execution_failures':0,'budget_charged':1}
 ab=canonical(aggregate);(out/'aggregate.json').write_bytes(ab)
 m=json.loads((out/'manifest.json').read_bytes());m['results_sha256']=sha256(ab);mb=canonical(m);(out/'manifest.json').write_bytes(mb)
 r=json.loads((out/'receipt.json').read_bytes());r['claims']['results_sha256']=sha256(ab);r['claims']['manifest_sha256']=sha256(mb);r['claims']['custodian_id']='unrelated-custodian';r['signature_b64']=base64.b64encode(key.sign(canonical_bytes(r['claims']))).decode();(out/'receipt.json').write_bytes(canonical(r))
 try:
  verdict=verify_bundle(out,pub,expected_prereg_sha256=file_sha(pr),expected_pool_sha256=file_sha(pool),expected_candidate_hashes=hs,expected_evaluator_sha256=file_sha(Path('custody_reference/evaluator.py')),expected_task_count=2,expected_campaign_id='actual-campaign',expected_custodian_id='actual-custodian',expected_prereg_budget_per_arm=2)
 except Exception as exc:
  verdict={'blocked':True,'exception':type(exc).__name__,'reason':str(exc)}
 print(json.dumps({'attack':'GEN-AUD-025 partial run + campaign/custodian swap','real_pool_tasks':2,'signed_reported_tasks':1,'reported_campaign':aggregate['campaign_id'],'reported_custodian':r['claims']['custodian_id'],'postpatch_verdict':verdict},sort_keys=True))
