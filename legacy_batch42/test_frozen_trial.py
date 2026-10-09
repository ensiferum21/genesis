import copy
import unittest
from sealed_benchmark import register
from frozen_trial import audit_frozen_trial

TASKS=[{'id':'d','split':'DEV','statement':'theorem d : True'},
       {'id':'s','split':'SELECT','statement':'theorem s : True'},
       {'id':'c','split':'CONFIRM','statement':'theorem c : True'}]
COMMIT={'sha256':'a'*64,'count':1,'custodian':'external'}
CONFIG={'seed':123}; BASE={'solver':'baseline'}; CAND={'solver':'candidate'}
H='b'*64

def event(t,a,s='FAIL'):
    return {'task_id':t,'arm':a,'attempt':1,'state':s,'cost_units':1,'evidence_sha256':H}

class FrozenTrialTests(unittest.TestCase):
    def setUp(self):
        self.k=dict(public_tasks=copy.deepcopy(TASKS),sealed_commitment=copy.deepcopy(COMMIT),
                    config=copy.deepcopy(CONFIG),baseline=copy.deepcopy(BASE),
                    candidate=copy.deepcopy(CAND),registration=register(TASKS,COMMIT,CONFIG,BASE,CAND),
                    events=[event('c','baseline'),event('c','candidate','PASS')],
                    budget_per_arm=2,max_attempts=1)
    def run_trial(self,**changes):
        k=copy.deepcopy(self.k);k.update(changes);return audit_frozen_trial(**k)
    def test_valid_development(self):
        r=self.run_trial();self.assertEqual(r['candidate_wins'],1);self.assertFalse(r['promotion_allowed'])
        self.assertTrue(r['registration_recomputed']);self.assertFalse(r['execution_evidence_replayed'])
    def test_changed_config(self):
        with self.assertRaises(ValueError):self.run_trial(config={'seed':124})
    def test_changed_candidate(self):
        with self.assertRaises(ValueError):self.run_trial(candidate={'solver':'other'})
    def test_changed_baseline(self):
        with self.assertRaises(ValueError):self.run_trial(baseline={'solver':'other'})
    def test_changed_commitment(self):
        with self.assertRaises(ValueError):self.run_trial(sealed_commitment={'sha256':'c'*64,'count':1,'custodian':'external'})
    def test_changed_task_statement(self):
        t=copy.deepcopy(TASKS);t[-1]['statement']='theorem c : False'
        with self.assertRaises(ValueError):self.run_trial(public_tasks=t)
    def test_changed_task_id(self):
        t=copy.deepcopy(TASKS);t[-1]['id']='other'
        with self.assertRaises(ValueError):self.run_trial(public_tasks=t)
    def test_forged_registration(self):
        r=copy.deepcopy(self.k['registration']);r['registration_sha256']='f'*64
        with self.assertRaises(ValueError):self.run_trial(registration=r)
    def test_wrong_split_event(self):
        with self.assertRaises(ValueError):self.run_trial(events=[event('d','baseline'),event('d','candidate')])
    def test_sealed_forbidden(self):
        with self.assertRaises(ValueError):self.run_trial(split='SEALED')
    def test_dev_split(self):
        r=self.run_trial(split='DEV',events=[event('d','baseline'),event('d','candidate')]);self.assertEqual(r['split'],'DEV')
    def test_duplicate_tasks(self):
        t=copy.deepcopy(TASKS);t.append(copy.deepcopy(t[0]))
        with self.assertRaises(ValueError):self.run_trial(public_tasks=t)

if __name__=='__main__':unittest.main()
