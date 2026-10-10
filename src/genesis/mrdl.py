"""Bounded exact graph representations. No eval, floating proof values or imports."""
from fractions import Fraction
from itertools import combinations,permutations
from math import factorial
from .graphs import neighbors,motifs,normalize,relabel,SearchLimit


OPS={'Allowed','Adj','Degree','Codegree','Neighbors','CommonNeighborTable','DegreeSequence',
     'Induced','ComplementOnHost','MotifCount','TracePower','PartitionByFeature','QuotientLabels',
     'PBEncode','VertexOrbitId','EdgeOrbitId','Const','Add','Sub','Mul','Rat'}


def evaluate(expr,task):
    nodes=[0]
    def run(e,depth=0):
        nodes[0]+=1
        if nodes[0]>256 or depth>16:raise ValueError('MRDL syntax bounds')
        if not isinstance(e,dict) or set(e)-{'op','args','params'} or e.get('op') not in OPS:
            raise ValueError('MRDL expression schema')
        op=e['op'];args=e.get('args',[]);p=e.get('params',{})
        if not isinstance(args,list) or not isinstance(p,dict):raise ValueError('MRDL fields')
        if len(p)>12:raise ValueError('MRDL parameter cap')
        expected={'Allowed':{'u','v'},'Adj':{'u','v'},'Degree':{'u'},'Codegree':{'u','v'},'Neighbors':{'u'},
                  'Induced':{'vertices'},'ComplementOnHost':{'selected'},'TracePower':{'k'},
                  'PartitionByFeature':{'values'},'QuotientLabels':{'values'},'Const':{'value'},'Rat':{'num','den'}}.get(op,set())
        if set(p)!=expected:raise ValueError('unexpected MRDL parameters')
        arity=2 if op in ('Add','Sub','Mul') else 0
        if len(args)!=arity:raise ValueError('MRDL arity')
        vals=[run(x,depth+1) for x in args]
        a=neighbors(task.n,task.edges)
        def vertex(k):
            v=p[k]
            if type(v) is not int or not 0<=v<task.n:raise ValueError('vertex range/type')
            return v
        if op in ('Allowed','Adj'):out=bool(a[vertex('u')]>>vertex('v')&1)
        elif op=='Degree':out=a[vertex('u')].bit_count()
        elif op=='Codegree':out=(a[vertex('u')]&a[vertex('v')]).bit_count()
        elif op=='Neighbors':out=tuple(v for v in range(task.n) if a[vertex('u')]>>v&1)
        elif op=='CommonNeighborTable':out=tuple(tuple((a[u]&a[v]).bit_count() for v in range(task.n)) for u in range(task.n))
        elif op=='DegreeSequence':out=tuple(sorted((x.bit_count() for x in a),reverse=True))
        elif op=='MotifCount':out=len(motifs(task))
        elif op=='Induced':
            vertices=p['vertices']
            if not isinstance(vertices,list) or len(set(vertices))!=len(vertices) or any(type(v) is not int or not 0<=v<task.n for v in vertices):
                raise ValueError('vertex subset')
            out=tuple(e for e in task.edges if set(e)<=set(vertices))
        elif op=='ComplementOnHost':
            selected=normalize(task.n,p['selected'])
            if not set(selected)<=set(task.edges):raise ValueError('host complement subset')
            out=tuple(e for e in task.edges if e not in set(selected))
        elif op in ('PartitionByFeature','QuotientLabels'):
            values=p['values']
            if not isinstance(values,list) or len(values)!=task.n or any(type(x) is not int for x in values):
                raise ValueError('integer feature vector')
            classes={x:i for i,x in enumerate(sorted(set(values)))}
            out=tuple(classes[x] for x in values) if op=='QuotientLabels' else tuple(tuple(i for i,x in enumerate(values) if x==v) for v in sorted(classes))
        elif op=='TracePower':
            k=p['k']
            if type(k) is not int or not 0<=k<=8:raise ValueError('trace power cap')
            matrix=[[int(i==j) for j in range(task.n)] for i in range(task.n)]
            for _ in range(k):
                matrix=[[sum(matrix[i][z] for z in range(task.n) if a[z]>>j&1) for j in range(task.n)] for i in range(task.n)]
            out=sum(matrix[i][i] for i in range(task.n))
        elif op=='PBEncode':
            out={'variables':len(task.edges),'objective':[1]*len(task.edges),
                 'constraints':[{'indices':[i for i in range(len(task.edges)) if c>>i&1],
                                 'at_most':c.bit_count()-1} for c in motifs(task)],
                 'semantics':'one Boolean per allowed edge; excludes every forbidden motif'}
        elif op in ('VertexOrbitId','EdgeOrbitId'):
            if factorial(task.n)>200000:raise SearchLimit('exact automorphism cap')
            items=list(range(task.n)) if op=='VertexOrbitId' else list(task.edges)
            parent={x:x for x in items}
            def root(x):
                while parent[x]!=x:x=parent[x]
                return x
            for order in permutations(range(task.n)):
                if relabel(task,order).edges!=task.edges:continue
                for item in items:
                    mapped=order[item] if op=='VertexOrbitId' else tuple(sorted(order[v] for v in item))
                    x,y=root(item),root(mapped);parent[max(x,y)]=min(x,y)
            roots=sorted({root(x) for x in items});out=tuple(roots.index(root(x)) for x in items)
        elif op=='Const':
            if type(p['value']) not in (int,bool):raise ValueError('exact scalar required')
            out=p['value']
        elif op=='Rat':
            if type(p['num']) is not int or type(p['den']) is not int or p['den']==0:raise ValueError('rational scalar')
            out=Fraction(p['num'],p['den'])
        else:
            if any(type(x) not in (int,Fraction) for x in vals):raise ValueError('numeric type mismatch')
            out={'Add':lambda:vals[0]+vals[1],'Sub':lambda:vals[0]-vals[1],'Mul':lambda:vals[0]*vals[1]}[op]()
        def bounded(x):
            if type(x) is int and x.bit_length()>1024:raise ValueError('integer bit cap')
            if isinstance(x,Fraction):bounded(x.numerator);bounded(x.denominator)
            if isinstance(x,(list,tuple)):
                for y in x:bounded(y)
            if isinstance(x,dict):
                for y in x.values():bounded(y)
        bounded(out);return out
    return run(expr)
