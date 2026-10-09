import copy
import hashlib
import unittest
from sealed_benchmark import register,verify_registration

TASKS=[{'id':'d','split':'DEV','statement':'theorem d : True := by trivial'},
       {'id':'s','split':'SELECT','statement':'theorem s : True := by trivial'},
       {'id':'c','split':'CONFIRM','statement':'theorem c : True := by trivial'}]
SEAL={'sha256':'a'*64,'count':10,'custodian':'external-custodian'}
CFG={'budget':24};BASE={'solver':'baseline'};CAND={'solver':'candidate'}
def reg(tasks=TASKS,seal=SEAL,config=CFG,base=BASE,cand=CAND):return register(tasks,seal,config,base,cand)
class FreezeTests(unittest.TestCase):
 def test_valid_is_not_promoted(self):
  r=reg();self.assertEqual(r['status'],'DEV_FROZEN_NOT_EVALUATED');self.assertFalse(r['promotion_allowed'])
 def test_stable_order(self):self.assertEqual(reg()['registration_sha256'],reg(list(reversed(TASKS)))['registration_sha256'])
 def test_duplicate_ids(self):
  with self.assertRaises(ValueError):reg(TASKS+[dict(TASKS[0])])
 def test_whitespace_duplicates(self):
  x=copy.deepcopy(TASKS);x[1]['statement']='  theorem d : True  := by trivial  '
  with self.assertRaises(ValueError):reg(x)
 def test_sealed_visible(self):
  x=copy.deepcopy(TASKS);x[0]['split']='SEALED'
  with self.assertRaises(ValueError):reg(x)
 def test_missing_split(self):
  with self.assertRaises(ValueError):reg(TASKS[:2])
 def test_invalid_commitment(self):
  with self.assertRaises(ValueError):reg(seal={'sha256':'0','count':10,'custodian':'x'})
 def test_missing_custodian(self):
  with self.assertRaises(ValueError):reg(seal={**SEAL,'custodian':''})
 def test_same_arms(self):
  with self.assertRaises(ValueError):reg(cand=BASE)
 def test_tamper_config(self):self.assertEqual(verify_registration(TASKS,SEAL,{'budget':25},BASE,CAND,reg())['status'],'BLOCKED')
 def test_tamper_sealed_commitment(self):self.assertEqual(verify_registration(TASKS,{**SEAL,'sha256':'b'*64},CFG,BASE,CAND,reg())['status'],'BLOCKED')
 def test_no_claim_semantic_leakage(self):self.assertFalse(reg()['semantic_leakage_screened'])
if __name__=='__main__':unittest.main()
