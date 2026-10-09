"""DEV-only fail-closed human review of leakage triage. Never certifies semantic independence."""
import hashlib
import hmac
from sealed_benchmark import canonical
from leakage_triage import triage

DECISIONS = {'LEAK_CONFIRMED', 'NOT_EQUIVALENT', 'UNRESOLVED'}


def review(public_tasks, sealed_tasks, decisions, reviewer_id, custodian_id, expected_triage_sha256):
    """Recompute flags; require one reviewed decision per flag and a distinct reviewer.

    Decisions are human assertions, not proof; IDs do not authenticate identities.
    """
    if not isinstance(reviewer_id, str) or not reviewer_id.strip() or not isinstance(custodian_id, str) or not custodian_id.strip() or reviewer_id == custodian_id:
        raise ValueError('distinct named reviewer and custodian required')
    if not isinstance(expected_triage_sha256, str) or len(expected_triage_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_triage_sha256):
        raise ValueError('triage hash required')
    current = triage(public_tasks, sealed_tasks)
    if not hmac.compare_digest(current['receipt_sha256'], expected_triage_sha256):
        return {'status':'BLOCKED_TRIAGE_CHANGED','promotion_allowed':False,'scientific_claim':'NONE'}
    if not isinstance(decisions, list):
        raise ValueError('decisions must be list')
    expected = {(f['sealed_id'],f['public_id']) for f in current['flags']}
    seen = set(); records = []
    for d in decisions:
        if not isinstance(d,dict) or set(d) != {'sealed_id','public_id','decision','rationale'}:
            raise ValueError('invalid adjudication schema')
        key = (d['sealed_id'],d['public_id'])
        if key in seen or key not in expected or d['decision'] not in DECISIONS or not isinstance(d['rationale'],str) or len(d['rationale'].strip()) < 12:
            raise ValueError('duplicate/unrecognized/unsupported adjudication')
        seen.add(key)
        records.append(dict(d))
    if seen != expected:
        status='BLOCKED_INCOMPLETE_REVIEW'
    elif any(d['decision']=='LEAK_CONFIRMED' for d in records):
        status='BLOCKED_CONFIRMED_LEAK'
    elif any(d['decision']=='UNRESOLVED' for d in records):
        status='BLOCKED_UNRESOLVED'
    else:
        status='DEV_REVIEWED_HEURISTIC_FLAGS' if records else 'DEV_NO_HEURISTIC_FLAGS'
    out={'schema':'genesis-leakage-adjudication-v1','status':status,
         'triage_sha256':current['receipt_sha256'],'reviewer_id':reviewer_id,
         'custodian_id':custodian_id,'flag_count':len(expected),
         'reviewed_count':len(seen),'decisions':sorted(records,key=lambda x:(x['sealed_id'],x['public_id'])),
         'semantic_leakage_cleared':False,'independent_custody_verified':False,
         'promotion_allowed':False,'scientific_claim':'NONE'}
    out['receipt_sha256']=hashlib.sha256(canonical(out)).hexdigest()
    return out
