"""Deterministic scoring worker prototype; not proof of independent custody."""
import json, hashlib, sys
from pathlib import Path

def run(pool_path, candidate_path, output_path):
    pool=json.loads(Path(pool_path).read_text())
    candidate=json.loads(Path(candidate_path).read_text())
    if not isinstance(pool,list) or not all(isinstance(x,dict) and set(x)=={'id','answer'} for x in pool):
        raise ValueError('invalid pool')
    if not isinstance(candidate,dict) or set(candidate)!={'answers'} or not isinstance(candidate['answers'],dict):
        raise ValueError('invalid candidate')
    ids=[x['id'] for x in pool]
    if len(ids)!=len(set(ids)) or any(k not in ids for k in candidate['answers']):
        raise ValueError('invalid task ids')
    outcomes=[{'id':x['id'],'correct':candidate['answers'].get(x['id'])==x['answer']} for x in pool]
    result={'schema':'genesis-evaluator-prototype-v1','count':len(pool),'correct':sum(x['correct'] for x in outcomes),
            'outcomes':outcomes,'pool_sha256':hashlib.sha256(Path(pool_path).read_bytes()).hexdigest(),
            'candidate_sha256':hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest(),
            'independent_custody_proven':False}
    Path(output_path).write_text(json.dumps(result,sort_keys=True,indent=2))
    return result

if __name__=='__main__':
    if len(sys.argv)!=4: raise SystemExit('usage: worker pool.json candidate.json result.json')
    run(*sys.argv[1:])
