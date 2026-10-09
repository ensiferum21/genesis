import unittest
from prospective_accounting import audit
from frozen_trial import audit_frozen_trial
from sealed_benchmark import register

R={'schema':'genesis-prospective-freeze-v1','promotion_allowed':False,'registration_sha256':'a'*64}
H='b'*64

def e(t,arm,n,state,cost=1):
    return dict(task_id=t,arm=arm,attempt=n,state=state,cost_units=cost,evidence_sha256=H)

class TerminalAttemptOrderTests(unittest.TestCase):
    def run_audit(self,events,roster=None):
        return audit(R,roster or ['t'],events,budget_per_arm=20,max_attempts=4)
    def test_candidate_final_success_unsorted(self):
        es=[e('t','candidate',2,'PASS'),e('t','baseline',1,'FAIL'),e('t','candidate',1,'FAIL')]
        self.assertEqual(self.run_audit(es)['candidate_wins'],1)
    def test_candidate_final_failure_unsorted(self):
        es=[e('t','candidate',2,'FAIL'),e('t','baseline',1,'PASS'),e('t','candidate',1,'TIMEOUT')]
        self.assertEqual(self.run_audit(es)['baseline_wins'],1)
    def test_baseline_final_success_unsorted(self):
        es=[e('t','baseline',2,'PASS'),e('t','baseline',1,'FAIL'),e('t','candidate',1,'FAIL')]
        self.assertEqual(self.run_audit(es)['baseline_wins'],1)
    def test_permutation_does_not_change_outcomes(self):
        es=[e('t','baseline',1,'FAIL'),e('t','baseline',2,'PASS'),e('t','candidate',1,'FAIL'),e('t','candidate',2,'PASS')]
        a=self.run_audit(es);b=self.run_audit(es[::-1]);
        for k in ('candidate_wins','baseline_wins','ties','invalid_executions','used_budget'):
            self.assertEqual(a[k],b[k],k)
        self.assertNotEqual(a['raw_events_sha256'],b['raw_events_sha256'])
    def test_multiple_tasks_interleaved(self):
        es=[e('x','candidate',2,'PASS'),e('y','baseline',1,'PASS'),e('x','baseline',1,'FAIL'),e('y','candidate',1,'FAIL'),e('x','candidate',1,'FAIL')]
        a=self.run_audit(es,['x','y']);self.assertEqual((a['candidate_wins'],a['baseline_wins']),(1,1))
    def test_missing_retry_still_rejected(self):
        with self.assertRaisesRegex(ValueError,'gap'):
            self.run_audit([e('t','candidate',2,'PASS'),e('t','baseline',1,'FAIL')])
    def test_after_success_still_rejected(self):
        with self.assertRaisesRegex(ValueError,'after success'):
            self.run_audit([e('t','candidate',2,'FAIL'),e('t','candidate',1,'PASS'),e('t','baseline',1,'FAIL')])

if __name__=='__main__':unittest.main()
