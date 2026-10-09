#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, os, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / 'experiments/cache/task_pool_genesis_batch1_seed424243.json'
PREREG = ROOT / 'experiments/prereg/genesis_batch1_repair.json'
OUT = ROOT / 'experiments/results/genesis_batch1_repair.json'
CACHE = ROOT / 'experiments/cache/batch1_worlds'
BUDGET = 150.0
PARTITION_SEED = 57721
N_TEST = 5
CAL_WEIGHT = 0.10
WEIGHTS = [CAL_WEIGHT] + [(1.0-CAL_WEIGHT)/N_TEST]*N_TEST
SPLIT = (0.15, 0.125, 0.125)
ARMS = ['D','U','V2n','V2r']

from gap_engine.adapters.induction.adapter import build_world_from_suite, judge_sealed
from gap_engine.adapters.induction.suite import exclude_handwritten, partition_weighted
from gap_engine.engine.admission import admit_proposals
from gap_engine.engine.arms import arm_dropout
from gap_engine.engine.loop import Campaign
from gap_engine.experiments.induction_bench import GRIDS
from gap_engine.experiments.prereg import write_prereg, load_verified
from gap_engine.kernel.budget import BudgetBroker
from gap_engine.kernel.gates import GateJ, Library
from gap_engine.kernel.ledger import Ledger


def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''):
            h.update(b)
    return h.hexdigest()

def canonical_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def suites():
    doc=json.loads(POOL.read_text())
    kept, removed=exclude_handwritten(doc['tasks'])
    parts=partition_weighted(kept, WEIGHTS, PARTITION_SEED)
    return parts, {
        'pool_sha256':sha256_file(POOL),'pool_tasks':len(doc['tasks']),
        'excluded_handwritten':len(removed),'kept_tasks':len(kept),
        'partition_seed':PARTITION_SEED,'weights':WEIGHTS,'split':SPLIT,
        'suite_sha256':canonical_hash(parts),'sizes':[len(x) for x in parts],
    }

def names():
    return ['g-b1-cal']+[f'g-b1-w{i}' for i in range(1,N_TEST+1)]

def load_world(name):
    parts,_=suites(); k=names().index(name)
    return build_world_from_suite(name+'-c5', parts[k], seed=1400+k, cache_dir=str(CACHE), split=SPLIT,
                                  screen_visible=True, conj_size=5)

def gate_summary(ledger):
    out=[]
    for e in ledger.entries:
        if e['kind'].startswith('gate.'):
            p=e['payload']
            out.append({'gate':p.get('gate'),'passed':p.get('passed'),'stage':p.get('stage'),
                        'bundle_n':len(p.get('bundle') or []),'stats':p.get('stats') or {},'reasons':p.get('reasons') or []})
    return out

def run_arm(arm,name,threshold=None):
    t0=time.time(); w=load_world(name); seed=1400+names().index(name); led=Ledger()
    out={'arm':arm,'world':name,'budget':BUDGET}
    if arm=='D':
        fuel=int(min(200000, BUDGET*w.n_tasks('DEV')*w.solver.fuel/max(1,w.sealed.size('SEALED'))))
        j=judge_sealed(w,[],seed=seed,actor='D',fuel=fuel,max_depth=3, unsafe_dev=True)
        out.update(admitted=[],spent=BUDGET,fuel=fuel,gates=[])
    elif arm in ('V2n','V2r'):
        strategy='select_split' if arm=='V2n' else 'dev_build_full_select'
        c=Campaign(w,BUDGET,seed,policy='u5',ledger=led,round_policy='power',admission_strategy=strategy)
        r=c.run(max_steps=80)
        j=judge_sealed(w,[],seed=seed,actor=arm, unsafe_dev=True)
        out.update(admitted=[w.statement(i) for i in w.accepted_extra],spent=r.spent,steps=r.steps,
                   generations=r.generations,stops=r.stops,gates=gate_summary(led),strategy=strategy)
    else:
        search=BudgetBroker.from_policy(0.85*BUDGET,Ledger(),name='U-search')
        res=arm_dropout(w,0.85*BUDGET,seed,False,threshold,broker=search)
        gb=BudgetBroker.from_policy(BUDGET-search.used,led,name='U-gate')
        lib=Library(led); gate=GateJ(w,gb,led,alpha=0.05,reps=1)
        props=[(b.members,b.evidence.pvalue,b.kind) for b in res.bundles if b.evidence.fdr_rejected]
        props.sort(key=lambda x:x[1])
        admit_proposals(w,lib,gate,props,seed,strategy='select_split')
        j=judge_sealed(w,[],seed=seed,actor='U', unsafe_dev=True)
        out.update(admitted=[w.statement(i) for i in w.accepted_extra],spent=search.used+gb.used,
                   proposals=len(props),gates=gate_summary(led))
    keys=sorted(j['outcomes']); sealed=[int(j['outcomes'][k]) for k in keys]
    out.update(sealed=sealed,sealed_solved=int(sum(sealed)),sealed_n=len(sealed),
               sealed_rate=float(np.mean(sealed)) if sealed else 0.0,
               visible_screened=w.meta.get('visible_screened'),seconds=round(time.time()-t0,3))
    return out

def _job(x): return run_arm(*x)

def exact_sign(a,b):
    d=np.asarray(a)-np.asarray(b); wins=int((d>0).sum()); losses=int((d<0).sum()); ties=int((d==0).sum())
    n=wins+losses; p=float(binomtest(wins,n,.5,alternative='greater').pvalue) if n else 1.0
    return {'wins':wins,'losses':losses,'ties':ties,'p_one_sided':p,'mean_diff':float(d.mean()),'diffs':d.tolist()}

def prereg(info):
    plan={
      'experiment':'Genesis Batch 1 repair: preserve full SELECT validation by building incremental batches on DEV',
      'status':'development/falsification batch; not confirmatory evidence',
      'created_before_results':True,'pool':str(POOL.relative_to(ROOT)),'suite':info,
      'script_sha256':sha256_file(Path(__file__).resolve()),'budget':BUDGET,'arms':ARMS,
      'candidate_change':'V2r differs from frozen V2n only by admission strategy: proposal composition on DEV, full SELECT untouched for validation; alpha=0.05 and CONFIRM unchanged',
      'primary':'V2r vs V2n paired by world on fresh sealed solve rate',
      'support_rule':'repair advances to Batch 2 if V2r strictly beats V2n in >=3/5 worlds, mean difference >0, and introduces no leak/regression-test failure',
      'harm_rule':'repair rejected if V2n strictly beats V2r in >=3/5 worlds or any trust invariant/regression fails',
      'otherwise':'INCONCLUSIVE; keep repair experimental and diagnose visible gates only',
      'secondary':['V2r vs U','V2r vs D','admissions and gate stages on visible splits'],
      'u_threshold':GRIDS['U'][0],
      'no_tuning':'No change to candidate or thresholds after sealed results; next repair must use a new pool.',
      'limitations':['local induction checker, not Lean 4 kernel','five-world repair batch is underpowered for broad claims'],
    }
    if not PREREG.exists(): write_prereg(str(PREREG),plan)
    return load_verified(str(PREREG))

def main():
    parts,info=suites(); plan=prereg(info)
    print('PREREG',PREREG,PREREG.with_suffix(PREREG.suffix+'.lock'),flush=True)
    print('POOL',info,flush=True)
    # Build/cache worlds only after prereg; this exposes no arm outcome.
    metas=[]
    for nm in names():
        w=load_world(nm)
        metas.append({'world':nm,'DEV':w.n_tasks('DEV'),'SELECT':w.n_tasks('SELECT'),'CONFIRM':w.n_tasks('CONFIRM'),
                      'SEALED':w.sealed.size('SEALED'),'pool':len(w.pool),'visible_screened':w.meta.get('visible_screened')})
        print('WORLD',metas[-1],flush=True)
    results=[]; t0=time.time()
    with ProcessPoolExecutor(max_workers=2) as pool:
        # U is a baseline, not the object under repair. Freeze its first pre-existing grid point
        # before touching any test-world outcome instead of spending a calibration world here.
        threshold=GRIDS['U'][0]
        print('U THRESHOLD frozen',threshold,flush=True)
        jobs=[(a,nm,threshold if a=='U' else None) for nm in names()[1:] for a in ARMS]
        for r in pool.map(_job,jobs):
            results.append(r)
            print('RESULT',r['world'],r['arm'],f"{r['sealed_solved']}/{r['sealed_n']}",
                  'admit',len(r['admitted']),'spent',round(r['spent'],1),'sec',r['seconds'],flush=True)
            OUT.with_suffix('.partial.json').write_text(json.dumps(results,indent=1,default=str))
    by={a:sorted([r for r in results if r['arm']==a],key=lambda z:z['world']) for a in ARMS}
    rates={a:[r['sealed_rate'] for r in by[a]] for a in ARMS}
    primary=exact_sign(rates['V2r'],rates['V2n'])
    if primary['wins']>=3 and primary['mean_diff']>0: verdict='REPAIR_ADVANCES_TO_BATCH2'
    elif primary['losses']>=3: verdict='REPAIR_REJECTED'
    else: verdict='INCONCLUSIVE'
    analysis={'means':{a:float(np.mean(v)) for a,v in rates.items()},'primary':primary,
              'V2r_vs_U':exact_sign(rates['V2r'],rates['U']),'V2r_vs_D':exact_sign(rates['V2r'],rates['D']),
              'admissions':{a:[len(r['admitted']) for r in by[a]] for a in ARMS},'verdict':verdict}
    doc={'plan':plan,'world_meta':metas,'u_threshold':threshold,'results':results,'analysis':analysis,
         'elapsed_seconds':round(time.time()-t0,2)}
    OUT.write_text(json.dumps(doc,indent=2,default=str))
    print('ANALYSIS',json.dumps(analysis,indent=2),flush=True)
    print('OUT',OUT,flush=True)

if __name__=='__main__': main()
