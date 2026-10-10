#!/usr/bin/env python3
"""Operator-only CLI. Run under an account isolated from the research worker.

This interface is intentionally not a research CLI subcommand and creates no keys.
"""
import argparse
import json
from pathlib import Path
from genesis.common import load_json,canonical
from genesis.custodian import register,evaluate

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','evaluate'])
    p.add_argument('--private-root',type=Path,required=True);p.add_argument('--key',type=Path,required=True)
    p.add_argument('--operator-id',required=True);p.add_argument('--request',type=Path)
    p.add_argument('--request-id');p.add_argument('--pool',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    if a.action=='register':
        if a.request is None:p.error('--request required')
        result=register(a.private_root,load_json(a.request),a.key,a.operator_id)
    else:
        if a.request_id is None or a.pool is None:p.error('--request-id and --pool required')
        result=evaluate(a.private_root,a.request_id,a.pool,a.key,a.operator_id)
    a.output.write_bytes(canonical(result));print(json.dumps({'output':str(a.output),'promotion_allowed':False}))

if __name__=='__main__':main()
