import unittest
from scripts.promotion_preflight import preflight

class TestPromotionPreflight(unittest.TestCase):
    def test_current_dev_branch_always_blocked(self):
        state={'status':'FAILED_REPAIR_REQUIRED','current_batch':1}
        audit={'audit_status':'CRITICAL','findings':[{'severity':'CRITICAL'}]}
        r=preflight(state,audit)
        self.assertEqual(r['status'],'BLOCK')
        self.assertTrue(any('CRITICAL' in s for s in r['reasons']))
        self.assertTrue(any('fresh' in s for s in r['reasons']))

    def test_fake_evidence_flags_cannot_replace_signed_custody(self):
        state={'status':'READY_FOR_PROMOTION','current_batch':1}
        audit={'audit_status':'PASS','findings':[]}
        evidence={'historical_pool_reused':False,'fresh_task_count':300,
                  'completed_jobs':20,'preregistered_jobs':20,
                  'matched_baselines_passed':True,'regression_passed':True,
                  'near_duplicate_scan_passed':True,'checker_replay_passed':True}
        r=preflight(state,audit,evidence)
        self.assertEqual(r['status'],'BLOCK')
        self.assertTrue(any('custody' in s for s in r['reasons']))

if __name__=='__main__':
    unittest.main()
