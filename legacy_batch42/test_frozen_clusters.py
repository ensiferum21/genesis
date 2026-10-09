import unittest
from frozen_clusters import freeze_cluster_plan, analyze_precommitted_clusters
from sealed_benchmark import register

class FrozenClusterTests(unittest.TestCase):
    def setUp(self):
        self.tasks=[{'id':'d','split':'DEV','statement':'True'}, {'id':'s','split':'SELECT','statement':'False'},
                    {'id':'t1','split':'CONFIRM','statement':'Nat.succ 0 = 1'},
                    {'id':'t2','split':'CONFIRM','statement':'Nat.succ 1 = 2'}]
        self.sealed={'sha256':'a'*64,'count':2,'custodian':'external'}
        self.config={'seed':7}; self.baseline={'name':'baseline'}; self.candidate={'name':'candidate'}
        self.reg=register(self.tasks,self.sealed,self.config,self.baseline,self.candidate)
        self.clusters={'t1':'familyA','t2':'familyA'}
        self.kw=dict(registration=self.reg,public_tasks=self.tasks,sealed_commitment=self.sealed,
                     config=self.config,baseline=self.baseline,candidate=self.candidate)
        self.events=[dict(task_id=t,arm=a,attempt=1,state=state,cost_units=1,evidence_sha256='b'*64)
                     for t in ('t1','t2') for a,state in (('baseline','FAIL'),('candidate','PASS'))]
    def plan(self):return freeze_cluster_plan(**self.kw,clusters=self.clusters)
    def analyze(self,**overrides):
        kw=dict(**self.kw,plan=self.plan(),clusters=self.clusters,events=self.events,budget_per_arm=10,max_attempts=3)
        kw.update(overrides)
        return analyze_precommitted_clusters(**kw)
    def test_plan(self):self.assertEqual(self.plan()['cluster_count'],1)
    def test_cluster_sign(self):
        r=self.analyze();self.assertEqual(r['task_wins'],2);self.assertEqual(r['cluster_wins'],1)
        self.assertEqual(r['cluster_sign_p_one_sided'],.5);self.assertFalse(r['promotion_allowed'])
    def test_changed_cluster_blocks(self):
        with self.assertRaises(ValueError):self.analyze(clusters={'t1':'familyA','t2':'familyB'})
    def test_forged_plan_blocks(self):
        with self.assertRaises(ValueError):self.analyze(plan={**self.plan(),'cluster_count':2})
    def test_missing_task_blocks(self):
        with self.assertRaises(ValueError):freeze_cluster_plan(**self.kw,clusters={'t1':'familyA'})
    def test_extra_task_blocks(self):
        with self.assertRaises(ValueError):freeze_cluster_plan(**self.kw,clusters={**self.clusters,'d':'other'})
    def test_empty_label_blocks(self):
        with self.assertRaises(ValueError):freeze_cluster_plan(**self.kw,clusters={'t1':'','t2':'a'})
    def test_registration_change_blocks(self):
        with self.assertRaises(ValueError):self.analyze(config={'seed':8})
    def test_retries_use_terminal_attempt(self):
        events=[dict(e) for e in self.events]
        events=[e for e in events if not(e['task_id']=='t1' and e['arm']=='candidate')]
        events.extend([dict(task_id='t1',arm='candidate',attempt=1,state='FAIL',cost_units=1,evidence_sha256='b'*64),
                       dict(task_id='t1',arm='candidate',attempt=2,state='PASS',cost_units=1,evidence_sha256='c'*64)])
        self.assertEqual(self.analyze(events=events)['task_wins'],2)
    def test_missing_event_blocks(self):
        with self.assertRaises(ValueError):self.analyze(events=self.events[:-1])
    def test_budget_blocks(self):
        with self.assertRaises(ValueError):self.analyze(budget_per_arm=1)
    def test_checker_error_blocks_threshold(self):
        events=[dict(e) for e in self.events];events[0]['state']='CHECKER_ERROR'
        r=self.analyze(events=events);self.assertEqual(r['invalid_pairs'],1)
        self.assertFalse(r['descriptive_task_threshold_met'])
    def test_sealed_split_blocks(self):
        with self.assertRaises(ValueError):freeze_cluster_plan(**self.kw,clusters=self.clusters,split='SEALED')

if __name__=='__main__':unittest.main()
