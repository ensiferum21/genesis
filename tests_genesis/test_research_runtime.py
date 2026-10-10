from itertools import combinations
from pathlib import Path
import tempfile
import unittest
from genesis.models import Config,GraphTask,SolverProgram,Limits
from genesis.execution import execute
from genesis.ir import Interpreter,Value,CONTRACTS
from genesis.research import Ecology,make_panel,dominates,propose
from genesis.campaign import Campaign
from genesis.cli import request_bundle
from genesis.common import canonical


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.task=GraphTask(task_id='k4',n=4,edges=tuple(combinations(range(4),2)),family='complete')

    def test_real_subprocess_witness_and_resource_receipt(self):
        r=execute(self.task,SolverProgram(rounds=2),Limits(),27)
        self.assertEqual(r['status'],'SUCCESS');self.assertEqual(r['result']['value'],4)
        self.assertEqual(r['check']['value'],len(r['result']['selected']))
        self.assertLessEqual(r['result']['queries'],60)
        self.assertGreater(r['wall_ns'],0);self.assertGreater(r['peak_rss_bytes'],0)
        self.assertFalse(r['arbitrary_code_sandbox'])

    def test_resource_exhaustion_is_not_success(self):
        big=GraphTask(task_id='large',n=63,edges=tuple(combinations(range(63),2)),family='complete')
        r=execute(big,SolverProgram(rounds=32),Limits(wall_seconds=1,cpu_seconds=1,memory_mib=64),1)
        self.assertIn(r['status'],('TIMEOUT','CPU_LIMIT','RESOURCE_KILLED','EXECUTION_ERROR'))
        self.assertNotEqual(r['exit_code'],0)
        self.assertGreater(r['wall_ns'],0)

    def test_arbitrary_python_never_accepted(self):
        with self.assertRaises(TypeError):execute(self.task,{'code':'__import__("os")'},Limits(),1)

    def test_all_sixteen_ir_operators_execute_in_declared_scope(self):
        ir=Interpreter(max_actions=24,seed=7);done=set()
        def invoke(op,values,params=None):done.add(op);return ir.invoke(op,values,params)
        goal=invoke('FORMALIZE',[Value('RawTask',self.task.model_dump(mode='json'),('USES_DEV_DATA',),('fixture',))])
        rep=invoke('REPRESENT',[goal],{'expression':{'op':'DegreeSequence'}})
        self.assertEqual(rep.data,(3,3,3,3));self.assertIn('USES_DEV_DATA',rep.effects)
        prog=Value('Program',SolverProgram())
        invoke('DISTINGUISH',[Value('Predictions',{'a':[0,1],'b':[1,1]})],{'costs':{'a':1,'b':1}})
        invoke('FACTOR',[goal]);invoke('TRANSFORM',[goal],{'permutation':[3,2,1,0]})
        invoke('PROPOSE',[prog]);receipt=invoke('EXECUTE',[goal,prog]);invoke('OBSERVE',[receipt])
        invoke('INTERVENE',[prog],{'changes':{'exchange':True}})
        witness=Value('Witness',tuple(tuple(x) for x in receipt.data['result']['selected']))
        invoke('VERIFY',[goal,witness]);invoke('TRANSPORT',[goal,witness],{'permutation':[3,2,1,0]})
        invoke('COMPOSE',[goal,Value('Witnesses',[witness.data])]);invoke('BRANCH',[prog])
        invoke('COMPRESS',[prog,Value('Traces',[receipt.data['result']['trace']])])
        invoke('SYNTHESIZE',[prog]);invoke('REFLECT',[Value('Rows',[])])
        self.assertEqual(done,set(CONTRACTS))

    def test_ir_rejects_type_privilege_and_action_overflow(self):
        ir=Interpreter(max_actions=1)
        with self.assertRaises(ValueError):ir.invoke('VERIFY',[Value('Hypothesis',True)])
        ir.invoke('PROPOSE',[Value('Program',SolverProgram())])
        with self.assertRaises(RuntimeError):ir.invoke('PROPOSE',[Value('Program',SolverProgram())])
        with self.assertRaises(PermissionError):Interpreter().invoke('INTERVENE',[Value('Program',SolverProgram())],{'changes':{'kernel':'edit'}})

    def test_world_caps_and_retirement(self):
        e=Ecology();ids=[e.birth(SolverProgram(rounds=i+1)) for i in range(4)]
        with self.assertRaises(ValueError):e.birth(SolverProgram())
        e.next_epoch();child=e.birth(SolverProgram(),parents=tuple(ids[:2]))
        with self.assertRaises(ValueError):e.birth(SolverProgram(),parents=tuple(ids[2:]))
        e.observe(child,(1,-1),{'failure':'none'});e.observe(child,(2,-1),{'gain':1})
        self.assertEqual(e.worlds[child].state,'DORMANT');e.retire(child,'no fresh utility')
        self.assertEqual(e.worlds[child].state,'RETIRED')

    def test_panel_isomorphism_disjointness(self):
        a,seen=make_panel(31,10,'c4_host_v2','DEV')
        b,seen=make_panel(32,10,'c4_host_v2','FUTURE',seen)
        self.assertEqual(len(seen),20)

    def test_end_to_end_campaign_replay_request_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'campaign'
            cfg=Config(generations=1,tasks_per_panel=2,proposals_per_epoch=2,research_trials=8)
            Campaign.initialize(root,cfg)
            with Campaign(root) as c:
                summary=c.run()
                self.assertFalse(summary['promotion_allowed']);self.assertEqual(summary['scientific_generations_confirmed'],0)
                self.assertEqual(c.store.state('phase'),'CANDIDATE_FROZEN')
                self.assertTrue(c.replay(2)['all_matched'])
                path=request_bundle(c,300);self.assertTrue(path.exists())
                self.assertEqual(summary['generations'][0]['causal_controls']['placebo_delta'],0)
            with Campaign(root) as c:self.assertEqual(c.run(),summary)
