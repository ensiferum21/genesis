import copy
import unittest
from sealed_benchmark import register
from sealed_reveal import sealed_digest,audit_opening
P=[{'id':'d','split':'DEV','statement':'theorem d : True := by trivial'}, {'id':'s','split':'SELECT','statement':'theorem s : Nat := 1'}, {'id':'c','split':'CONFIRM','statement':'theorem c : Nat := 2'}]
S=[{'id':'hidden1','statement':'theorem hidden1 : Nat := 3'}, {'id':'hidden2','statement':'theorem hidden2 : Nat := 4'}]
CFG={'budget':24}; B={'solver':'baseline'}; C={'solver':'candidate'}
def run(sealed=S, public=P, seal=None, receipt=None):
    seal=seal or {'sha256':sealed_digest(S),'count':len(S),'custodian':'external'}
    receipt=receipt or register(P,seal,CFG,B,C)
    return audit_opening(public,sealed,seal,CFG,B,C,receipt)
class RevealTests(unittest.TestCase):
 def test_valid_no_promotion(self):
    r=run();self.assertEqual(r['status'],'DEV_EXACT_OPENING_MATCH');self.assertFalse(r['promotion_allowed'])
 def test_order_independent(self):self.assertEqual(sealed_digest(S),sealed_digest(list(reversed(S))))
 def test_changed_statement(self):
    s=copy.deepcopy(S);s[0]['statement']='theorem x : False := by sorry';self.assertEqual(run(s)['status'],'BLOCKED_COMMITMENT_MISMATCH')
 def test_partial_opening(self):self.assertEqual(run(S[:1])['status'],'BLOCKED_COMMITMENT_MISMATCH')
 def test_duplicate_sealed_id(self):
    with self.assertRaises(ValueError):sealed_digest(S+[dict(S[0])])
 def test_duplicate_sealed_statement(self):
    with self.assertRaises(ValueError):sealed_digest(S+[{'id':'x','statement':S[0]['statement']}])
 def test_exact_leakage(self):
    s=copy.deepcopy(S);s[0]['statement']=P[0]['statement'];seal={'sha256':sealed_digest(s),'count':2,'custodian':'external'}
    self.assertEqual(run(s,seal=seal)['status'],'BLOCKED_EXACT_LEAKAGE')
 def test_id_leakage(self):
    s=copy.deepcopy(S);s[0]['id']='d';seal={'sha256':sealed_digest(s),'count':2,'custodian':'external'}
    self.assertEqual(run(s,seal=seal)['status'],'BLOCKED_EXACT_LEAKAGE')
 def test_modified_registration(self):
    r=register(P,{'sha256':sealed_digest(S),'count':2,'custodian':'external'},CFG,B,C);r['public_counts']['DEV']=99
    self.assertEqual(run(receipt=r)['status'],'BLOCKED_REGISTRATION_MISMATCH')
 def test_invalid_record(self):self.assertEqual(run([{'id':'a','statement':'x','extra':1}])['status'],'BLOCKED_INVALID_OPENING')
 def test_near_duplicate_not_claimed(self):self.assertFalse(run()['semantic_leakage_screened'])
if __name__=='__main__':unittest.main()
