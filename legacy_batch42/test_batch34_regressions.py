import math
import unittest
from prospective_statistics import _pvalue, analyze_frozen_trial
from sealed_benchmark import register

class Batch34Regressions(unittest.TestCase):
    def test_large_all_wins(self):
        self.assertEqual(_pvalue(2000,0), 0.0)  # IEEE float underflow, not a zero exact probability
    def test_large_all_losses(self):
        self.assertEqual(_pvalue(0,2000), 1.0)
    def test_large_balanced(self):
        self.assertGreater(_pvalue(1000,1000),0.5)
        self.assertLess(_pvalue(1000,1000),0.52)
    def test_tiny_exact(self):
        self.assertEqual(_pvalue(3,0),1/8)
        self.assertEqual(_pvalue(2,1),.5)
        self.assertEqual(_pvalue(0,0),None)
    def test_terminal_retry_independent_of_event_order(self):
        tasks=[{'id':'t','split':'CONFIRM','statement':'True'}, {'id':'d','split':'DEV','statement':'False'}, {'id':'s','split':'SELECT','statement':'Nat.succ 0 = 1'}]
        sealed={'sha256':'a'*64,'count':1,'custodian':'external'}
        config={'seed':1}; baseline={'name':'b'}; candidate={'name':'c'}
        reg=register(tasks,sealed,config,baseline,candidate)
        def e(arm,attempt,state):
            return {'task_id':'t','arm':arm,'attempt':attempt,'state':state,'cost_units':1,'evidence_sha256':'b'*64}
        events=[e('candidate',2,'FAIL'),e('baseline',1,'FAIL'),e('candidate',1,'PASS')]
        # Accounting correctly rejects attempts after PASS.
        with self.assertRaises(ValueError):
            analyze_frozen_trial(registration=reg,public_tasks=tasks,sealed_commitment=sealed,config=config,baseline=baseline,candidate=candidate,events=events,budget_per_arm=10,max_attempts=3)
        events=[e('candidate',2,'PASS'),e('baseline',1,'FAIL'),e('candidate',1,'FAIL')]
        result=analyze_frozen_trial(registration=reg,public_tasks=tasks,sealed_commitment=sealed,config=config,baseline=baseline,candidate=candidate,events=events,budget_per_arm=10,max_attempts=3)
        self.assertEqual(result['task_wins'],1)
    def test_large_one_sided_near_half(self):
        self.assertGreater(_pvalue(1001,999),.45)
        self.assertLess(_pvalue(1001,999),.51)

if __name__=='__main__':unittest.main()
