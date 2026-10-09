import unittest
from prospective_accounting import audit
R={'schema':'genesis-prospective-freeze-v1','promotion_allowed':False,'registration_sha256':'a'*64}
H='b'*64

def ev(t,a,n=1,s='FAIL',c=1):return dict(task_id=t,arm=a,attempt=n,state=s,cost_units=c,evidence_sha256=H)
class AccountingTests(unittest.TestCase):
 def ok(self,es=None,**kw):return audit(R,['t1'],es if es is not None else [ev('t1','baseline'),ev('t1','candidate',s='PASS')],budget_per_arm=5,max_attempts=3,**kw)
 def test_accounting(self):
  x=self.ok();self.assertEqual(x['candidate_wins'],1);self.assertFalse(x['promotion_allowed'])
 def test_retry(self):self.assertEqual(self.ok([ev('t1','baseline'),ev('t1','candidate'),ev('t1','candidate',2,'PASS')])['events'],3)
 def test_gap(self):
  with self.assertRaises(ValueError):self.ok([ev('t1','baseline'),ev('t1','candidate',2)])
 def test_missing_arm(self):
  with self.assertRaises(ValueError):self.ok([ev('t1','baseline')])
 def test_duplicate(self):
  with self.assertRaises(ValueError):self.ok([ev('t1','baseline'),ev('t1','baseline'),ev('t1','candidate')])
 def test_budget(self):
  with self.assertRaises(ValueError):self.ok([ev('t1','baseline',c=6),ev('t1','candidate')])
 def test_post_success(self):
  with self.assertRaises(ValueError):self.ok([ev('t1','baseline'),ev('t1','candidate',s='PASS'),ev('t1','candidate',2)])
 def test_invalid_not_promoted(self):self.assertEqual(self.ok([ev('t1','baseline',s='CHECKER_ERROR'),ev('t1','candidate')])['invalid_executions'],1)
 def test_invalid_not_win(self):
  x=self.ok([ev('t1','baseline',s='CHECKER_ERROR'),ev('t1','candidate',s='PASS')]);self.assertEqual(x['candidate_wins'],0)
 def test_cancel_cost(self):self.assertEqual(self.ok([ev('t1','baseline',s='CANCELLED',c=3),ev('t1','candidate')])['used_budget']['baseline'],3)
 def test_invalid_hash(self):
  x=ev('t1','baseline');x['evidence_sha256']='no'
  with self.assertRaises(ValueError):self.ok([x,ev('t1','candidate')])
 def test_unknown_task(self):
  with self.assertRaises(ValueError):self.ok([ev('t2','baseline'),ev('t1','candidate')])
 def test_invalid_freeze(self):
  with self.assertRaises(ValueError):audit({},['t1'],[ev('t1','baseline'),ev('t1','candidate')],budget_per_arm=5,max_attempts=3)
