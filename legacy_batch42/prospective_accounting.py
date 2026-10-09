"""DEV-only exhaustive paired trial accounting. Never asserts real Lean validity."""
import hashlib
import json
from sealed_benchmark import canonical

STATES={'PASS','FAIL','TIMEOUT','CANCELLED','CHECKER_ERROR','UNSUPPORTED'}

def audit(registration, task_ids, events, *, budget_per_arm, max_attempts):
    if not isinstance(registration,dict) or registration.get('schema')!='genesis-prospective-freeze-v1' or registration.get('promotion_allowed') is not False:
        raise ValueError('invalid development freeze')
    if not isinstance(task_ids,list) or not task_ids or any(not isinstance(t,str) or not t for t in task_ids) or len(set(task_ids))!=len(task_ids):
        raise ValueError('invalid task roster')
    if type(budget_per_arm) is not int or budget_per_arm<=0 or type(max_attempts) is not int or not 1<=max_attempts<=100:
        raise ValueError('invalid budgets')
    if not isinstance(events,list):raise ValueError('events required')
    seen=set(); groups={}; used={'baseline':0,'candidate':0}; invalid=[]
    required={'task_id','arm','attempt','state','cost_units','evidence_sha256'}
    for e in events:
        if not isinstance(e,dict) or set(e)!=required:raise ValueError('invalid event schema')
        t,arm,attempt,state,cost,h=e['task_id'],e['arm'],e['attempt'],e['state'],e['cost_units'],e['evidence_sha256']
        if t not in task_ids or arm not in ('baseline','candidate') or type(attempt) is not int or not 1<=attempt<=max_attempts or state not in STATES or type(cost) is not int or cost<0 or not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid event fields')
        key=(t,arm,attempt)
        if key in seen:raise ValueError('duplicate event')
        seen.add(key);groups.setdefault((t,arm),[]).append(e);used[arm]+=cost
        if state in ('CHECKER_ERROR','UNSUPPORTED'):invalid.append(key)
    for t in task_ids:
        for arm in ('baseline','candidate'):
            xs=sorted(groups.get((t,arm),[]),key=lambda x:x['attempt'])
            if not xs or [x['attempt'] for x in xs]!=list(range(1,len(xs)+1)):
                raise ValueError('missing arm or retry accounting gap')
            if any(x['state']=='PASS' for x in xs[:-1]):raise ValueError('attempts after success')
            if any(x['state'] in ('CHECKER_ERROR','UNSUPPORTED') for x in xs[:-1]):raise ValueError('attempts after invalid execution')
    if any(used[a]>budget_per_arm for a in used):raise ValueError('budget exceeded')
    pairs=[]
    for t in task_ids:
        b=max(groups[(t,'baseline')],key=lambda e:e['attempt'])['state'];c=max(groups[(t,'candidate')],key=lambda e:e['attempt'])['state']
        valid=b not in ('CHECKER_ERROR','UNSUPPORTED') and c not in ('CHECKER_ERROR','UNSUPPORTED')
        pairs.append({'task_id':t,'baseline':b,'candidate':c,'candidate_win':valid and c=='PASS' and b!='PASS','baseline_win':valid and b=='PASS' and c!='PASS'})
    wins=sum(p['candidate_win'] for p in pairs);losses=sum(p['baseline_win'] for p in pairs)
    return {'schema':'genesis-prospective-accounting-dev-v1','status':'DEV_ACCOUNTED_NOT_VERIFIED','registration_sha256':registration['registration_sha256'], 'task_count':len(task_ids),'events':len(events),'used_budget':used,'candidate_wins':wins,'baseline_wins':losses,'ties':len(task_ids)-wins-losses,'invalid_executions':len(invalid),'raw_events_sha256':hashlib.sha256(canonical(events)).hexdigest(),'external_checker_verified':False,'independent_custody_verified':False,'randomization_verified':False,'promotion_allowed':False,'scientific_claim':'NONE'}
