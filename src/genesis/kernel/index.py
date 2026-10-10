"""Derived relational index with the spec §16.4 tables.

The authoritative record stays the hash-chained event journal plus CAS. This
module materializes a separate, read-only SQLite file that can be deleted and
rebuilt at any time, so it never competes with the single writer.
"""
import json
from pathlib import Path
import sqlite3
from ..common import canonical, digest

TABLES = '''
CREATE TABLE campaigns(campaign_id TEXT PRIMARY KEY, root_config_hash TEXT, research_profile TEXT, status TEXT);
CREATE TABLE system_versions(version_id TEXT PRIMARY KEY, parent_ids TEXT, config_hash TEXT, model_ids TEXT,
                             code_commit TEXT, tool_manifests TEXT, generation INTEGER);
CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY, content_hash TEXT, media_type TEXT, producer_attempt TEXT,
                       epistemic_metadata TEXT);
CREATE TABLE events(event_id INTEGER PRIMARY KEY, event_hash TEXT, timestamp TEXT, actor TEXT, type TEXT,
                    payload_hash TEXT);
CREATE TABLE tasks(task_id TEXT PRIMARY KEY, family TEXT, split_class TEXT, visibility TEXT,
                   canonical_statement_hash TEXT);
CREATE TABLE trials(trial_id TEXT PRIMARY KEY, system_version TEXT, task_id TEXT, preregistered_budget TEXT, seed TEXT);
CREATE TABLE attempts(attempt_id TEXT PRIMARY KEY, trial_id TEXT, tool TEXT, status TEXT, wall_ns INTEGER,
                      cpu_ns INTEGER, resource_receipt TEXT, request TEXT);
CREATE TABLE claims(claim_id TEXT PRIMARY KEY, text TEXT, scope TEXT, current_levels TEXT);
CREATE TABLE evidence(claim_id TEXT, artifact_id TEXT, axis TEXT, status TEXT, decision TEXT);
CREATE TABLE worlds(world_id TEXT PRIMARY KEY, parent_ids TEXT, representation TEXT, policy TEXT, status TEXT,
                    option_metrics TEXT);
CREATE TABLE modifications(mod_id TEXT PRIMARY KEY, source_version TEXT, target_version TEXT, hypothesis TEXT,
                           rollback TEXT, predicted_effects TEXT);
CREATE TABLE evaluations(eval_id TEXT PRIMARY KEY, version_id TEXT, sealed_panel_id TEXT, metrics TEXT,
                         judge_receipt TEXT);
CREATE TABLE lineage_edges(parent_version TEXT, child_version TEXT, mod_id TEXT, status TEXT);
'''
PUBLIC_SPLITS = {'DEV', 'SELECT', 'FUTURE'}


def build_index(store, destination, *, trust_root=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    head = store.verify()['head']
    db = sqlite3.connect(destination)
    try:
        db.executescript(TABLES)
        get = store.get
        from .anchors import pinned_tool_anchors
        from .evidence import EvidenceKernel
        kernel = EvidenceKernel(store, anchors=pinned_tool_anchors(), trust_root=trust_root)

        def entities(kind):
            for key, h in store.db.execute('SELECT id, object_hash FROM entities WHERE kind=? ORDER BY id', (kind,)):
                yield key, h, get(h)

        config = next((v for k, h, v in entities('config')), None)
        cid = store.state('campaign_id')
        if cid:
            db.execute('INSERT INTO campaigns VALUES (?,?,?,?)',
                       (cid, digest(config) if config else None, (config or {}).get('profile'), store.state('phase')))
        for vid, h, v in entities('system_version'):
            db.execute('INSERT INTO system_versions VALUES (?,?,?,?,?,?,?)',
                       (vid, json.dumps([v.get('parent')] if v.get('parent') else []),
                        digest(v.get('resolved_config', v.get('config'))),
                        json.dumps(v.get('model_configuration')), v.get('source'),
                        json.dumps(v.get('verifier_set')), v.get('generation')))
            if v.get('parent'):
                db.execute('INSERT INTO lineage_edges VALUES (?,?,?,?)', (v['parent'], vid, vid, 'RECORDED'))
        for kind, key, h in store.db.execute('SELECT kind, id, object_hash FROM entities'):
            db.execute('INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?,?)',
                       (h, h, 'application/json', None, json.dumps({'entity_kind': kind, 'entity_id': key})))
        for nid, h, node in entities('evidence_node'):
            db.execute('INSERT OR REPLACE INTO artifacts VALUES (?,?,?,?,?)',
                       (nid, node['payload_hash'], 'application/json', None,
                        json.dumps({'kind': node['kind'], 'effects': node['effects'], 'route': node['route'],
                                    'verdict': node['verdict'], 'parents': node['parents']})))
        for seq, h, raw in store.db.execute('SELECT seq, hash, body FROM events ORDER BY seq'):
            body = json.loads(raw)
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?)',
                       (seq, h, body['timestamp'], 'coordinator', body['kind'], body['payload']))
        tasks = {}
        for aid, trial, status, req_h, rec_h in store.db.execute('SELECT * FROM attempts'):
            req = get(req_h); rec = get(rec_h) if rec_h else {}
            task = req.get('task') if isinstance(req, dict) else None
            if isinstance(task, dict) and 'task_id' in task:
                tasks[task['task_id']] = task
            program = req.get('program') if isinstance(req, dict) else None
            db.execute('INSERT OR IGNORE INTO trials VALUES (?,?,?,?,?)',
                       (trial, digest(program) if program else None, (task or {}).get('task_id'),
                        json.dumps(req.get('limits')) if isinstance(req, dict) else None,
                        str(req.get('seed')) if isinstance(req, dict) else None))
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',
                       (aid, trial, (req.get('kind') if isinstance(req, dict) else None) or 'solver', status,
                        rec.get('wall_ns'), rec.get('cpu_ns'), rec_h, req_h))
        for tid, task in tasks.items():
            split = task.get('split', 'DEV')
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,?)',
                       (tid, task.get('family'), split, 'RESEARCH_VISIBLE' if split in PUBLIC_SPLITS else 'SEALED',
                        digest({'n': task['n'], 'edges': task['edges'], 'domain': task.get('domain')})))
        for claim_id, h, claim in entities('claim'):
            # Effective (revocation-aware, re-derived) levels, never the stored grant (R-02).
            db.execute('INSERT INTO claims VALUES (?,?,?,?)',
                       (claim_id, claim['statement'], claim['scope'], json.dumps(kernel.levels(claim_id))))
        for pid, h, decision in entities('promotion'):
            for dep in decision['dependencies']:
                db.execute('INSERT INTO evidence VALUES (?,?,?,?,?)',
                           (decision['claim'], dep, decision['axis'], decision['level'], pid))
        for wid, h, world in entities('world'):
            db.execute('INSERT INTO worlds VALUES (?,?,?,?,?,?)',
                       (wid, json.dumps(world.get('parents', [])), json.dumps(world.get('representation')),
                        json.dumps(world.get('program', world.get('policy'))), world.get('status'),
                        json.dumps(world.get('metrics', world.get('observations')))))
        for mid, h, mod in entities('modification'):
            db.execute('INSERT INTO modifications VALUES (?,?,?,?,?,?)',
                       (mid, mod.get('parent'), mod.get('child'), mod.get('hypothesis'), mod.get('rollback'),
                        mod.get('predicted_effect')))
        for eid, h, ev in entities('evaluation'):
            db.execute('INSERT INTO evaluations VALUES (?,?,?,?,?)',
                       (eid, ev.get('candidate_version'), ev.get('pool_hash'), canonical(ev).decode(), h))
        db.execute('CREATE TABLE index_meta(event_head TEXT, built_from TEXT)')
        db.execute('INSERT INTO index_meta VALUES (?,?)', (head, 'genesis-index-v1'))
        db.commit()
    finally:
        db.close()
    destination.chmod(0o444)
    return {'index': str(destination), 'event_head': head}
