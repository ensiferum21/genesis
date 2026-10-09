import unittest
from prospective_statistics import analyze_pairs, analyze_frozen_trial
from sealed_benchmark import register


def pair(i, b='FAIL', c='PASS'):
    return {'task_id':str(i),'baseline':b,'candidate':c}

class StatisticsTests(unittest.TestCase):
    def run_analysis(self, ps, clusters=None):
        return analyze_pairs(ps, task_clusters=clusters or {p['task_id']:p['task_id'] for p in ps})
    def test_exact_ten_wins(self):
        r=self.run_analysis([pair(i) for i in range(10)])
        self.assertAlmostEqual(r['task_sign_p_one_sided'], 1/1024)
        self.assertTrue(r['descriptive_task_threshold_met'])
        self.assertFalse(r['promotion_allowed'])
    def test_one_cluster_prevents_false_confidence(self):
        ps=[pair(i) for i in range(10)]
        r=self.run_analysis(ps, {str(i):'family1' for i in range(10)})
        self.assertEqual(r['cluster_sign_p_one_sided'], .5)
        self.assertFalse(r['descriptive_cluster_threshold_met'])
    def test_ties_excluded(self):
        r=self.run_analysis([pair('1'),pair('2','PASS','PASS')])
        self.assertEqual(r['task_ties'],1)
        self.assertEqual(r['task_sign_p_one_sided'],.5)
    def test_no_discordance(self):
        r=self.run_analysis([pair('1','FAIL','FAIL')]);self.assertIsNone(r['task_sign_p_one_sided'])
    def test_invalid_not_tie(self):
        r=self.run_analysis([pair('1','CHECKER_ERROR','PASS')]);self.assertEqual(r['invalid_pairs'],1)
        self.assertEqual(r['task_ties'],0)
        self.assertIsNone(r['task_sign_p_one_sided'])
    def test_invalid_blocks_significance(self):
        ps=[pair(i) for i in range(10)]+[pair('bad','UNSUPPORTED','FAIL')]
        r=self.run_analysis(ps);self.assertFalse(r['descriptive_task_threshold_met'])
    def test_loss(self):
        r=self.run_analysis([pair('a','PASS','FAIL')]);self.assertEqual(r['task_sign_p_one_sided'],1.)
    def test_duplicate(self):
        with self.assertRaises(ValueError):self.run_analysis([pair('a'),pair('a')])
    def test_missing_cluster(self):
        with self.assertRaises(ValueError):self.run_analysis([pair('a')], {'other':'x'})
    def test_bad_cluster(self):
        with self.assertRaises(ValueError):self.run_analysis([pair('a')], {'a':''})
    def test_invalid_alpha(self):
        with self.assertRaises(ValueError):analyze_pairs([pair('a')],task_clusters={'a':'x'},alpha=True)
    def test_empty(self):
        with self.assertRaises(ValueError):self.run_analysis([])
    def test_frozen_integration(self):
        tasks=[{'id':'t1','split':'CONFIRM','statement':'Nat.succ 0 = 1'}, {'id':'d','split':'DEV','statement':'True'}, {'id':'s','split':'SELECT','statement':'False'}]
        sealed={'sha256':'a'*64,'count':1,'custodian':'external'}
        config={'seed':1};baseline={'name':'b'};candidate={'name':'c'}
        reg=register(tasks,sealed,config,baseline,candidate)
        events=[{'task_id':'t1','arm':a,'attempt':1,'state':s,'cost_units':1,'evidence_sha256':'b'*64}
                for a,s in [('baseline','FAIL'),('candidate','PASS')]]
        r=analyze_frozen_trial(registration=reg,public_tasks=tasks,sealed_commitment=sealed,
            config=config,baseline=baseline,candidate=candidate,events=events,
            budget_per_arm=5,max_attempts=2)
        self.assertEqual(r['task_wins'],1)
        self.assertFalse(r['cluster_independence_supported'])
        self.assertFalse(r['promotion_allowed'])

if __name__=='__main__':unittest.main()
