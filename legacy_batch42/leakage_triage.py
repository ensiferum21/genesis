"""Conservative DEV-only lexical leakage triage; never certifies semantic separation."""
import hashlib
import re
from sealed_benchmark import canonical

_TOKEN = re.compile(r'\\[A-Za-z]+|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', re.UNICODE)
_KEYWORDS = {'theorem','lemma','example','by','fun','forall','∀','exists','∃','Nat','Int','Bool','Prop','True','False','Set','Graph','where','let','in','if','then','else','and','or','not'}

def tokenize(statement):
    if not isinstance(statement,str) or not statement.strip():
        raise ValueError('statement required')
    return _TOKEN.findall(statement)

def fingerprint(statement):
    """Alpha-like fingerprint. Heuristic ONLY; tokens in comments/strings are not parsed."""
    tokens=tokenize(statement)
    mapping={}; result=[]
    for token in tokens:
        if re.fullmatch(r'[a-z][A-Za-z_0-9]*',token) and token not in _KEYWORDS:
            if token not in mapping: mapping[token]=f'VAR{len(mapping)}'
            result.append(mapping[token])
        else: result.append(token)
    return tuple(result)

def triage(public_tasks, sealed_tasks):
    """Flag possible overlaps for human/AST review; no automatic clean verdict."""
    if not isinstance(public_tasks,list) or not isinstance(sealed_tasks,list):
        raise ValueError('task arrays required')
    for group in (public_tasks,sealed_tasks):
        for task in group:
            if not isinstance(task,dict) or not isinstance(task.get('id'),str) or not isinstance(task.get('statement'),str):
                raise ValueError('invalid task')
    flags=[]
    for sealed in sealed_tasks:
        a=tokenize(sealed['statement']); fa=fingerprint(sealed['statement'])
        for public in public_tasks:
            b=tokenize(public['statement']); fb=fingerprint(public['statement'])
            reasons=[]
            if sealed['id']==public['id']: reasons.append('ID_COLLISION')
            if a==b: reasons.append('TOKEN_EQUAL')
            if fa==fb: reasons.append('ALPHA_HEURISTIC')
            if reasons: flags.append({'sealed_id':sealed['id'],'public_id':public['id'],'reasons':reasons})
    result={'schema':'genesis-leakage-triage-v1','status':'DEV_REVIEW_REQUIRED' if flags else 'DEV_NO_HEURISTIC_MATCH',
            'flags':flags,'semantic_leakage_cleared':False,'independent_custody_verified':False,
            'promotion_allowed':False,'scientific_claim':'NONE'}
    result['receipt_sha256']=hashlib.sha256(canonical(result)).hexdigest()
    return result
