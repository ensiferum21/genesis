"""Round-3 red-team helpers (test-side only; nothing in src/ imports this).

Reuses the production trust-path setup of rounds 1/2 (root-owned read-only trust
root, role keys held by the parent, research child as UID 65534) and adds a
small real campaign store + export builder and a custodian pool builder.
"""
from itertools import combinations
import json
import os
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'redteam_b14_round2'))
import _r2  # noqa: E402,F401
from _r2 import NOBODY, REPO, bundle_file, chown_tree, production_setup, run_research  # noqa: E402,F401

from genesis.common import bytes_hash, canonical, code_identity, digest  # noqa: E402
from genesis.models import GraphTask, SolverProgram  # noqa: E402

IDENT = code_identity(REPO)['sha256']


def campaign_store(root, *, campaign_id, domain='c4_host_v2', latest_program=None, source_hash=IDENT, extra=None):
    """A small campaign store with the identity facts the custodian reads, plus its export."""
    from genesis.cli import export_replication
    from genesis.store import Store
    root = Path(root)
    with Store(root) as s:
        s.set_state('campaign_id', campaign_id)
        s.set_state('phase', 'CREATED')
        s.save('config', 'resolved', {'schema_version': 'genesis-campaign-v1', 'domain': domain,
                                      'profile': 'offline_engineering'})
        s.set_state('source_hash', source_hash)
        if latest_program is not None:
            s.set_state('latest_program', latest_program)
        if extra:
            extra(s)
    (root / 'exports').mkdir(exist_ok=True)
    export = root / 'exports' / 'campaign_export.zip'
    export_replication(root, export)
    return root, export


def pool(seed, count=24, families=12, n_choices=(9, 10, 11), domain='c4_host_v2', split='CONFIRM'):
    rng = random.Random(seed)
    out = []
    while len(out) < count:
        n = rng.choice(n_choices)
        edges = tuple(e for e in combinations(range(n), 2) if rng.random() < 0.38)
        if 14 <= len(edges) <= 18:
            out.append(GraphTask(task_id=f's{seed}-{len(out):03}', domain=domain, n=n, edges=edges,
                                 family=f'fam{len(out) % families}', split=split))
    return out


def write_pool(path, tasks):
    Path(path).write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
    return Path(path)


def custodian_dirs(base):
    private = Path(base) / 'private'
    private.mkdir(mode=0o700)
    manifest = private / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': []}))
    manifest.chmod(0o600)
    return private, manifest
