"""DEV-only post-freeze sealed-set opening audit. Does not certify semantic non-overlap."""
import hashlib
import hmac
from sealed_benchmark import canonical, register


def sealed_digest(tasks):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('sealed tasks required')
    ids=set(); norms=set()
    for t in tasks:
        if not isinstance(t,dict) or set(t)!={'id','statement'}:
            raise ValueError('sealed record schema invalid')
        if not isinstance(t['id'],str) or not t['id'].strip() or t['id'] in ids:
            raise ValueError('duplicate or invalid sealed id')
        if not isinstance(t['statement'],str) or not t['statement'].strip():
            raise ValueError('empty sealed statement')
        ids.add(t['id']); norm=' '.join(t['statement'].split())
        if norm in norms: raise ValueError('duplicate sealed theorem')
        norms.add(norm)
    return hashlib.sha256(canonical(sorted(tasks,key=lambda x:x['id']))).hexdigest()


def audit_opening(public_tasks, sealed_tasks, sealed_commitment, config, baseline, candidate, registration):
    """Check commitment and exact normalized overlaps after custodian opening."""
    expected=register(public_tasks,sealed_commitment,config,baseline,candidate)
    if expected != registration:
        return {'status':'BLOCKED_REGISTRATION_MISMATCH','promotion_allowed':False,'scientific_claim':'NONE'}
    try:
        digest=sealed_digest(sealed_tasks)
    except (ValueError,TypeError):
        return {'status':'BLOCKED_INVALID_OPENING','promotion_allowed':False,'scientific_claim':'NONE'}
    if len(sealed_tasks)!=sealed_commitment['count'] or not hmac.compare_digest(digest,sealed_commitment['sha256']):
        return {'status':'BLOCKED_COMMITMENT_MISMATCH','promotion_allowed':False,'scientific_claim':'NONE'}
    public_ids={t['id'] for t in public_tasks}
    public_norms={' '.join(t['statement'].split()) for t in public_tasks}
    overlaps=sorted(t['id'] for t in sealed_tasks if t['id'] in public_ids or ' '.join(t['statement'].split()) in public_norms)
    return {'status':'BLOCKED_EXACT_LEAKAGE' if overlaps else 'DEV_EXACT_OPENING_MATCH',
            'sealed_sha256':digest,'exact_overlap_ids':overlaps,
            'semantic_leakage_screened':False,'independent_custody_verified':False,
            'real_lean_replay_verified':False,'promotion_allowed':False,'scientific_claim':'NONE'}
