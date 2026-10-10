"""Custodian-only semantic contract and raw execution evidence.

The contract is supplied by the custodian, not inferred from candidate programs.
Changing it requires a new independently reviewed evaluator; it cannot reset exposure.
"""
import json
import os
import sqlite3
import stat
from pathlib import Path
from genesis.common import canonical,bytes_hash


def configure_semantics(root, *, domain, required_features, ignored_features=()):
    root=Path(root)
    body={'schema':'integer-feature-contract-v1','domain':domain,
          'required_features':sorted(required_features),'ignored_features':sorted(ignored_features)}
    path=root/'semantic_contract.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(canonical(body));f.flush();os.fsync(f.fileno())
    return bytes_hash(canonical(body))


def semantic_keys(root,pool):
    path=Path(root)/'semantic_contract.json'
    if not path.is_file() or path.is_symlink():raise ValueError('custodian semantic contract required')
    if path.stat().st_mode & (stat.S_IRWXG|stat.S_IRWXO):raise ValueError('semantic contract must be private')
    data=path.read_bytes();body=json.loads(data)
    if set(body)!={'schema','domain','required_features','ignored_features'} or body['schema']!='integer-feature-contract-v1':
        raise ValueError('semantic contract schema')
    if not isinstance(body['domain'],str) or not body['domain']:raise ValueError('semantic domain')
    required=body['required_features'];ignored=body['ignored_features']
    if not isinstance(required,list) or not isinstance(ignored,list) or not required:
        raise ValueError('nonempty explicit feature schema required')
    if any(not isinstance(x,str) or not x.isidentifier() for x in required+ignored):raise ValueError('feature name')
    if len(set(required+ignored))!=len(required+ignored):raise ValueError('feature collision')
    keys=[]
    for task in pool:
        fields=set(task['features'])
        if not set(required)<=fields or not fields<=set(required+ignored):
            raise ValueError('task violates custodian semantic contract')
        # Labels and answers are not part of question identity. An answer change
        # therefore cannot transform an exposed question into a fresh one.
        keys.append(bytes_hash(canonical({'domain':body['domain'],
                    'features':{k:task['features'][k] for k in required}})))
    return keys,bytes_hash(data)


def append_raw(root,attempt,record):
    db=sqlite3.connect(Path(root)/'sealed_attempts.sqlite3',timeout=30)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS raw_results(attempt TEXT, arm TEXT, task_id TEXT, body BLOB, '
                   'sha256 TEXT, PRIMARY KEY(attempt,arm,task_id))')
        raw=canonical(record)
        db.execute('INSERT INTO raw_results VALUES (?,?,?,?,?)',
                   (attempt,record['arm'],record['task_id'],raw,bytes_hash(raw)))
        db.commit()
    finally:db.close()


def raw_commitment(root,attempt):
    db=sqlite3.connect(Path(root)/'sealed_attempts.sqlite3')
    try:
        rows=db.execute('SELECT body,sha256 FROM raw_results WHERE attempt=? ORDER BY arm,task_id',(attempt,)).fetchall()
        for body,h in rows:
            if bytes_hash(body)!=h:raise RuntimeError('private evidence corruption')
        return bytes_hash(canonical([h for _,h in rows]))
    finally:db.close()


def replay_private(root,attempt):
    """Recompute actual predictions/correctness and counts from private raw records."""
    from custody_reference.evaluator import eval_expr
    db=sqlite3.connect(Path(root)/'sealed_attempts.sqlite3')
    out={}
    try:
        rows=db.execute('SELECT body,sha256 FROM raw_results WHERE attempt=? ORDER BY arm,task_id',(attempt,)).fetchall()
        for raw,h in rows:
            if bytes_hash(raw)!=h:raise RuntimeError('private evidence corruption')
            r=json.loads(raw)
            try:
                prediction=eval_expr(r['program'],r['features'])
                valid=type(prediction) is int
            except (ValueError,KeyError,OverflowError,TypeError):prediction=None;valid=False
            correct=valid and prediction==r['answer']
            if prediction!=r['predicted'] or bool(correct)!=r['correct'] or (not valid)!=r['failed']:
                raise RuntimeError('raw prediction replay mismatch')
            a=out.setdefault(r['arm'],{'tasks':0,'correct':0,'execution_failures':0,'budget_charged':0})
            a['tasks']+=1;a['correct']+=int(correct);a['execution_failures']+=int(not valid);a['budget_charged']+=1
        return out
    finally:db.close()
