"""Compare two externally collected Lean canary runs; never assert independence by itself."""
import argparse
import hashlib
import json
from pathlib import Path
from canary_receipts import verify_pair
from evidence_custody import regular_beneath


def compare(run_a, run_b, executable_pin, positive_pin, negative_pin):
    def fail(reason):
        return {'schema':'genesis-cross-host-replay-v1','status':'BLOCKED','reason':reason,'promotion_allowed':False}
    roots=[Path(run_a),Path(run_b)]
    if roots[0].resolve()==roots[1].resolve():return fail('same run directory')
    receipts=[]
    for i,root in enumerate(roots):
        try:
            pair=json.loads(regular_beneath(root,'pair.json'))
            summary=json.loads(regular_beneath(root,'SUMMARY.json'))
        except (OSError,ValueError,TypeError,UnicodeError):return fail('missing or invalid run metadata')
        if summary.get('pair_status')!='DEV_CANARY_PAIR_PASS' or summary.get('receipt_status')!='DEV_CANARY_RECEIPTS_CONSISTENT' or summary.get('promotion_allowed') is not False:
            return fail('run summary not verified')
        checked=verify_pair(pair,root/'evidence',executable_pin,positive_pin,negative_pin)
        if checked['status']!='DEV_CANARY_RECEIPTS_CONSISTENT':return fail('raw receipt verification failed: '+checked['reason'])
        receipts.append(pair)
    for label in ('positive','negative'):
        x,y=[r[label] for r in receipts]
        if x['manifest_sha256']!=y['manifest_sha256']:
            return fail('project mismatch across runs')
        if x['evidence']['lean_sha256']!=y['evidence']['lean_sha256']:
            return fail('binary mismatch across runs')
        if x['evidence']['exit_code']!=y['evidence']['exit_code']:
            return fail('outcome disagreement')
    return {'schema':'genesis-cross-host-replay-v1','status':'DEV_TWO_RUNS_CONSISTENT',
            'promotion_allowed':False,'independent_hosts_verified':False,
            'independent_binary_provenance_verified':False,
            'reason':'two local evidence bundles agree; host independence and authentic Lean provenance require external custody'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('run_a');p.add_argument('run_b')
    p.add_argument('--lean-sha256',required=True)
    p.add_argument('--positive-manifest-sha256',required=True)
    p.add_argument('--negative-manifest-sha256',required=True)
    a=p.parse_args()
    result=compare(a.run_a,a.run_b,a.lean_sha256,a.positive_manifest_sha256,a.negative_manifest_sha256)
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0 if result['status']=='DEV_TWO_RUNS_CONSISTENT' else 2

if __name__=='__main__':raise SystemExit(main())
