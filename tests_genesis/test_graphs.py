import unittest
import random
from itertools import combinations
from genesis.models import GraphTask,SolverProgram,Limits,Config
from genesis.graphs import (forbidden_a,forbidden_b,certified_optimum,exact_producer,exact_checker,
    check_witness,canonical_graph,relabel,universal_upper,check_ghost,SearchLimit)
from genesis.dsl import solve
from genesis.mrdl import evaluate
from pydantic import ValidationError


def task(n,edges,domain='c4_host_v2'):
    return GraphTask(task_id='fixture',n=n,edges=tuple(sorted(edges)),family='fixture',domain=domain)


class GraphTests(unittest.TestCase):
    def test_all_labeled_hosts_through_five_vertices(self):
        checked=0
        for n in range(1,6):
            edges=tuple(combinations(range(n),2))
            for mask in range(1<<len(edges)):
                host=tuple(e for i,e in enumerate(edges) if mask>>i&1)
                for domain in ('c4_host_v2','triangle_free_host_v1'):
                    t=task(n,host,domain)
                    self.assertEqual(forbidden_a(t,host),forbidden_b(t,host))
                    r=certified_optimum(t)
                    self.assertLessEqual(r['value'],universal_upper(t)['value'])
                    self.assertEqual(len(r['checker']['selected']),r['value'])
                checked+=1
        self.assertEqual(checked,1099)

    def test_k1_through_k6(self):
        c4=[0,1,3,4,6,7]
        for n in range(1,7):
            self.assertEqual(certified_optimum(task(n,combinations(range(n),2)))['value'],c4[n-1])
            t=task(n,combinations(range(n),2),'triangle_free_host_v1')
            self.assertEqual(certified_optimum(t)['value'],n*n//4)

    def test_random_larger_hosts_exact_agreement(self):
        rng=random.Random(912)
        for i in range(30):
            es=[e for e in combinations(range(7),2) if rng.random()<.5]
            t=task(7,es,'triangle_free_host_v1' if i%2 else 'c4_host_v2')
            self.assertEqual(exact_producer(t)['value'],exact_checker(t)['value'])

    def test_isomorphism_and_semantic_metadata(self):
        rng=random.Random(512)
        for i in range(20):
            t=task(6,[e for e in combinations(range(6),2) if rng.random()<.5])
            permutation=list(range(6));rng.shuffle(permutation)
            other=relabel(t,permutation)
            self.assertEqual(canonical_graph(t),canonical_graph(other))
            other=GraphTask.model_validate_json(other.model_dump_json().replace('fixture','renamed'))
            self.assertEqual(canonical_graph(t),canonical_graph(other))

    def test_isomorphic_domain_identity_excluded(self):
        es=tuple(combinations(range(4),2))
        self.assertEqual(canonical_graph(task(4,es)),canonical_graph(task(4,es,'triangle_free_host_v1')))

    def test_isomorphism_budget_is_not_freshness(self):
        with self.assertRaises(SearchLimit):canonical_graph(task(10,combinations(range(10),2)),1)

    def test_noninduced_cycle(self):
        t=task(4,combinations(range(4),2))
        self.assertTrue(forbidden_a(t,t.edges));self.assertTrue(forbidden_b(t,t.edges))

    def test_forged_edge_and_duplicate_rejected(self):
        t=task(4,[(0,1),(1,2)])
        for edges in (((0,3),),((0,1),(0,1)),((0,0),),((True,2),)):
            with self.assertRaises(ValueError):check_witness(t,edges)

    def test_ghost_semantics(self):
        t=task(3,[(0,1),(1,2),(0,2)])
        self.assertEqual(check_ghost(t,t.edges,2)['status'],'GHOST_FOUND')
        self.assertEqual(check_ghost(t,t.edges,3)['status'],'UNSETTLED')
        self.assertFalse(check_ghost(t,t.edges,3)['proof'])

    def test_dsl_budget_and_replay(self):
        t=task(6,combinations(range(6),2))
        for budget in (1,10,60):
            for exchange in (False,True):
                p=SolverProgram(weights=(1,-1,0,1),exchange=exchange,rounds=32)
                a=solve(t,p,budget,77);b=solve(t,p,budget,77)
                self.assertEqual(a,b);self.assertLessEqual(a['queries'],budget)
                self.assertEqual(a['value'],check_witness(t,a['selected'])['value'])

    def test_strict_schemas(self):
        for kwargs in ({'rounds':True},{'weights':(0,0,0,999)},{'code':'print(1)'}):
            with self.assertRaises(ValidationError):SolverProgram(**kwargs)
        with self.assertRaises(ValidationError):Config(network=True)
        with self.assertRaises(ValidationError):Config(paid_api_budget=1)

    def test_mrdl_exact_representations(self):
        t=task(4,combinations(range(4),2))
        self.assertEqual(evaluate({'op':'Degree','params':{'u':1}},t),3)
        self.assertEqual(evaluate({'op':'Codegree','params':{'u':0,'v':1}},t),2)
        self.assertEqual(evaluate({'op':'TracePower','params':{'k':2}},t),12)
        self.assertEqual(evaluate({'op':'MotifCount'},t),3)
        self.assertEqual(evaluate({'op':'VertexOrbitId'},t),(0,0,0,0))
        self.assertEqual(evaluate({'op':'EdgeOrbitId'},t),(0,0,0,0,0,0))
        self.assertEqual(len(evaluate({'op':'PBEncode'},t)['constraints']),3)

    def test_pb_encoding_exhaustively_matches_predicate(self):
        for domain in ('c4_host_v2','triangle_free_host_v1'):
            t=task(5,combinations(range(5),2),domain)
            constraints=evaluate({'op':'PBEncode'},t)['constraints']
            for mask in range(1<<len(t.edges)):
                legal=all(sum(mask>>i&1 for i in c['indices'])<=c['at_most'] for c in constraints)
                selected=tuple(e for i,e in enumerate(t.edges) if mask>>i&1)
                self.assertEqual(legal,not forbidden_b(t,selected))

    def test_mrdl_denies_code_floats_and_unbounded_terms(self):
        t=task(2,[(0,1)])
        for expr in ({'op':'eval','params':{'value':'os'}},{'op':'Const','params':{'value':1.2}},
                     {'op':'TracePower','params':{'k':9}},{'op':'Const','params':{'value':1<<1025}}):
            with self.assertRaises(ValueError):evaluate(expr,t)
