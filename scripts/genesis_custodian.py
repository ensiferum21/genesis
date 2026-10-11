#!/usr/bin/env python3
"""Operator-only CLI. Run under an account isolated from the research worker.

This interface is intentionally not a research CLI subcommand and creates no keys.
The operator owns the exposure manifest and every public source it lists.
"""
import argparse
import json
from pathlib import Path
from genesis.common import atomic_write,load_json,canonical
from genesis.custodian import register,evaluate,adjudicate,recover
from genesis.models import GraphTask

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','evaluate','adjudicate','recover'])
    p.add_argument('--private-root',type=Path,required=True);p.add_argument('--key',type=Path,required=True)
    p.add_argument('--operator-id',required=True);p.add_argument('--request',type=Path)
    p.add_argument('--exposure-manifest',type=Path);p.add_argument('--campaign-export',type=Path)
    p.add_argument('--request-id');p.add_argument('--pool',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--task',type=Path);p.add_argument('--decision',choices=['ALLOW','BLOCK']);p.add_argument('--reason')
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    if a.action=='register':
        if a.request is None or a.exposure_manifest is None or a.campaign_export is None:
            p.error('--request, --exposure-manifest and --campaign-export required')
        if a.pool is None:p.error('--pool required: registration commits to the sealed panel')
        result=register(a.private_root,load_json(a.request),a.key,a.operator_id,
                        exposure_manifest=a.exposure_manifest,campaign_export=a.campaign_export,pool=a.pool)
    elif a.action=='adjudicate':
        if a.task is None or a.decision is None or not a.reason:p.error('--task, --decision and --reason required')
        result=adjudicate(a.private_root,GraphTask.model_validate_json(a.task.read_bytes()),a.decision,a.key,a.operator_id,a.reason)
    else:
        if a.request_id is None or a.pool is None:p.error('--request-id and --pool required')
        act=evaluate if a.action=='evaluate' else recover
        result=act(a.private_root,a.request_id,a.pool,a.key,a.operator_id)
    atomic_write(a.output,canonical(result));print(json.dumps({'output':str(a.output),'promotion_allowed':False}))

if __name__=='__main__':main()
