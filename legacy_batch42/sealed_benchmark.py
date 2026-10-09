"""DEV-only prospective benchmark registration. No sealed data or success claims.

Custodian publishes commitment before any solver runs; sealed contents remain offline.
"""
import hashlib
import json
import re
from pathlib import Path

HEX = re.compile(r'^[0-9a-f]{64}$')
SPLITS = ('DEV', 'SELECT', 'CONFIRM', 'SEALED')


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def register(public_tasks, sealed_commitment, config, baseline, candidate):
    """Fail closed on exact normalized overlap and duplicate task IDs.

    Near-duplicate/semantic overlap is NOT established by this test.
    """
    if not isinstance(public_tasks, list) or not public_tasks:
        raise ValueError('nonempty public task list required')
    if not isinstance(sealed_commitment, dict) or set(sealed_commitment) != {'sha256', 'count', 'custodian'}:
        raise ValueError('external sealed commitment required')
    if not isinstance(sealed_commitment['sha256'], str) or not HEX.fullmatch(sealed_commitment['sha256']):
        raise ValueError('invalid sealed commitment')
    if type(sealed_commitment['count']) is not int or sealed_commitment['count'] <= 0:
        raise ValueError('sealed count required')
    if not isinstance(sealed_commitment['custodian'], str) or not sealed_commitment['custodian'].strip():
        raise ValueError('independent custodian identifier required')
    for name, value in [('config',config),('baseline',baseline),('candidate',candidate)]:
        if not isinstance(value, dict) or not value:
            raise ValueError(name+' must be a nonempty frozen configuration')
    if canonical(baseline) == canonical(candidate):
        raise ValueError('baseline and candidate identical')
    ids=set(); statements={}; counts={s:0 for s in SPLITS if s!='SEALED'}
    for t in public_tasks:
        if not isinstance(t, dict) or set(t) != {'id','split','statement'}:
            raise ValueError('task must have exactly id, split, statement')
        tid,split,stmt=t['id'],t['split'],t['statement']
        if not isinstance(tid,str) or not tid.strip() or tid in ids:
            raise ValueError('duplicate/invalid task id')
        ids.add(tid)
        if split not in counts:raise ValueError('SEALED tasks must not be research-visible')
        if not isinstance(stmt,str) or not stmt.strip():raise ValueError('missing theorem statement')
        norm=' '.join(stmt.split())
        if norm in statements:raise ValueError('duplicate normalized theorem in public splits')
        statements[norm]=split
        counts[split]+=1
    if any(v==0 for v in counts.values()):raise ValueError('all public splits must be represented')
    public_hash=hashlib.sha256(canonical(sorted(public_tasks,key=lambda t:t['id']))).hexdigest()
    out={'schema':'genesis-prospective-freeze-v1','status':'DEV_FROZEN_NOT_EVALUATED',
         'public_tasks_sha256':public_hash,'public_counts':counts,
         'sealed_commitment':sealed_commitment,
         'config_sha256':hashlib.sha256(canonical(config)).hexdigest(),
         'baseline_sha256':hashlib.sha256(canonical(baseline)).hexdigest(),
         'candidate_sha256':hashlib.sha256(canonical(candidate)).hexdigest(),
         'semantic_leakage_screened':False,'sealed_tasks_inspected':False,
         'independent_custody_verified':False,'real_lean_replay_verified':False,
         'promotion_allowed':False,'scientific_claim':'NONE'}
    out['registration_sha256']=hashlib.sha256(canonical(out)).hexdigest()
    return out


def verify_registration(public_tasks, sealed_commitment, config, baseline, candidate, receipt):
    expected=register(public_tasks,sealed_commitment,config,baseline,candidate)
    return {'status':'DEV_FREEZE_MATCH' if expected==receipt else 'BLOCKED',
            'promotion_allowed':False,'scientific_claim':'NONE'}
