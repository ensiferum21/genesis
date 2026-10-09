"""Fail-closed local verification of both canary streams; never scientific promotion."""
import hashlib, json, re
from pathlib import Path
from evidence_custody import regular_beneath

HEX=re.compile(r'^[0-9a-f]{64}$')

def verify_pair(pair, root, exe_pin, positive_pin, negative_pin):
    def block(reason):return {'status':'BLOCKED','promotion_allowed':False,'reason':reason}
    if not all(isinstance(v,str) and HEX.fullmatch(v) for v in (exe_pin,positive_pin,negative_pin)):
        return block('invalid external pins')
    if positive_pin==negative_pin:return block('duplicate project pins')
    if not isinstance(pair,dict) or pair.get('status')!='DEV_CANARY_PAIR_PASS' or pair.get('promotion_allowed') is not False:
        return block('pair status invalid')
    root=Path(root)
    for label,pin,exit_ok in [('positive',positive_pin,True),('negative',negative_pin,False)]:
        receipt=pair.get(label)
        if not isinstance(receipt,dict) or receipt.get('schema')!='genesis-real-lean-attempt-v1' or receipt.get('promotion_allowed') is not False:
            return block(label+' invalid receipt')
        if receipt.get('manifest_sha256')!=pin:return block(label+' project mismatch')
        ev=receipt.get('evidence')
        if not isinstance(ev,dict) or ev.get('lean_sha256')!=exe_pin:return block(label+' executable mismatch')
        exit_code=ev.get('exit_code')
        if type(exit_code) is not int or (exit_code==0)!=exit_ok:return block(label+' exit mismatch')
        if receipt.get('status')!=('DEV_REPLAY_PASS' if exit_ok else 'REPLAY_REJECTED') or receipt.get('proof_replayed') is not exit_ok:
            return block(label+' execution status mismatch')
        for name in ('stdout','stderr'):
            try:
                data=regular_beneath(root,label,name+'.bin')
            except (OSError,ValueError):
                return block(label+' stream missing, unsafe or oversized')
            if ev.get(name+'_sha256')!=hashlib.sha256(data).hexdigest() or ev.get(name+'_bytes')!=len(data):
                return block(label+' stream mismatch')
    return {'status':'DEV_CANARY_RECEIPTS_CONSISTENT','promotion_allowed':False,'reason':'both raw local receipts consistent; toolchain provenance and independent proof checking not established'}
