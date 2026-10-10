"""Replication bundle and release artifact (spec §43).

    release_<id>/
      MANIFEST.json  CLAIMS.json  resolved_config.json  system_version.json
      dependency_lock/  container_digests.json  model_identifiers.json
      events.jsonl  campaign.sqlite3.snapshot  objects/sha256/...
      certificates/  checker_receipts/  resource_receipts/  preregistration.json
      analysis_code/  report.md  REPRODUCE.md  LIMITATIONS.md

`verify_bundle` re-derives everything a reproducer needs without trusting the
bundle's own claims: every file hash, the event hash chain rebuilt from
events.jsonl + objects, and the code identity of the shipped source.
"""
import hashlib
import io
import json
from importlib import metadata
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import zipfile

from .common import canonical, code_identity, digest, utcnow
from .store import Store, rebuild_from_export

REPO = Path(__file__).resolve().parents[2]
PACKAGES = ('pydantic', 'pydantic-core', 'numpy', 'scipy', 'cryptography', 'networkx', 'scikit-learn',
            'typing-extensions', 'annotated-types', 'cffi', 'joblib', 'threadpoolctl')


def observed_environment():
    """Installed distributions with the SHA-256 of their RECORD (itself a list of file hashes)."""
    dists = {}
    for name in PACKAGES:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            dists[name] = None
            continue
        record = dist.read_text('RECORD') or ''
        dists[name] = {'version': dist.version, 'record_sha256': hashlib.sha256(record.encode()).hexdigest()}
    return {'python': sys.version, 'implementation': platform.python_implementation(),
            'platform': platform.platform(), 'distributions': dists}


def _entities(s, kind):
    for key, h in s.db.execute('SELECT id, object_hash FROM entities WHERE kind=? ORDER BY id', (kind,)):
        yield key, h, s.get(h)


def build_bundle(campaign_root, destination, *, report=None, limitations=()):
    campaign_root = Path(campaign_root); destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    files = {}
    with Store(campaign_root) as s:
        integrity = s.verify()
        release_id = digest({'head': integrity['head'], 'built': utcnow()})[:16]
        base = f'release_{release_id}/'
        snap = s.snapshot(f'release-{release_id}.sqlite3')
        files['events.jsonl'] = (campaign_root / 'events.jsonl').read_bytes()
        files['campaign.sqlite3.snapshot'] = snap.read_bytes()
        for p in sorted((campaign_root / 'objects' / 'sha256').iterdir()):
            files[f'objects/sha256/{p.name}'] = p.read_bytes()
        cfg = next((v for _, _, v in _entities(s, 'config')), None) or \
            next((v for _, _, v in _entities(s, 'loop_config')), None)
        files['resolved_config.json'] = canonical(cfg)
        versions = sorted((v.get('generation', -1), k, v) for k, _, v in _entities(s, 'system_version'))
        files['system_version.json'] = canonical(versions[-1][2] if versions else {'source': s.state('source_hash')})
        claims = []
        for cid, _, claim in _entities(s, 'claim'):
            claims.append({**claim, 'levels': s.state(f'claimlevels:{cid}')})
        files['CLAIMS.json'] = canonical({'claims': claims, 'promotion_allowed': False,
                                          'note': 'levels are as granted by the evidence kernel at build time'})
        prereg = {kind: [v for _, _, v in _entities(s, kind)]
                  for kind in ('ladder_preregistration', 'experiment_b_prereg', 'frozen_request')}
        files['preregistration.json'] = canonical(prereg)
        for aid, trial, status, req, rec in s.db.execute('SELECT * FROM attempts ORDER BY id'):
            receipt = s.get(rec) if rec else None
            request = s.get(req)
            kind = request.get('kind') if isinstance(request, dict) else None
            target = 'checker_receipts' if kind in ('exact-check', 'formal-check') else 'resource_receipts'
            files[f'{target}/{aid}.json'] = canonical({'attempt': aid, 'trial': trial, 'status': status,
                                                       'request': req, 'receipt': receipt})
        for nid, _, node in _entities(s, 'evidence_node'):
            if node['kind'] in ('bound_state', 'formal_check', 'exact_check', 'witness_check'):
                files[f'certificates/{nid}.json'] = canonical({'node': node, 'payload': s.get(node['payload_hash'])})
        source_hash = s.state('source_hash')
    files['dependency_lock/requirements.lock'] = (REPO / 'requirements.lock').read_bytes()
    files['dependency_lock/observed_environment.json'] = canonical(observed_environment())
    pins = REPO / 'toolchain' / 'PINS.json'
    if pins.exists():
        files['dependency_lock/toolchain_PINS.json'] = pins.read_bytes()
    files['container_digests.json'] = canonical({'status': 'NOT_PINNED',
                                                 'reason': 'no registry access when built; sandbox root is host /usr '
                                                           'read-only; see policy and config hashes in receipts'})
    files['model_identifiers.json'] = canonical({'hosted_model': None,
                                                 'note': 'no language model was called by this campaign'})
    identity = code_identity(REPO)
    for rel in sorted(identity['files']):
        files[f'analysis_code/{rel}'] = (REPO / rel).read_bytes()
    files['analysis_code/CODE_IDENTITY.json'] = canonical(identity)
    files['report.md'] = (report or b'') if isinstance(report, bytes) else (report or '').encode()
    files['REPRODUCE.md'] = (
        '# Reproduce\n\n1. Unzip; `cd release_*`.\n2. `python -c "from genesis.release_bundle import verify_bundle; '
        'print(verify_bundle(\'.\'))"` with `PYTHONPATH=analysis_code/src`.\n3. Rebuild the store from '
        '`events.jsonl` + `objects/` and compare the event head with MANIFEST.json.\n4. Re-run attempts with '
        '`genesis trial replay` against a copy; results must match the recorded witnesses, values, queries and '
        'traces (timings excluded).\n').encode()
    files['LIMITATIONS.md'] = ('# Limitations\n\n' + ''.join(f'- {x}\n' for x in limitations) +
                               '- Built by the research operator; no independent custody or release authority.\n'
                               '- Container image not pinned by registry digest.\n').encode()
    manifest = {'release_id': release_id, 'event_head': integrity['head'], 'events': integrity['events'],
                'source_hash': source_hash, 'shipped_code_identity': identity['sha256'],
                'files': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}}
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as z:
        for k, v in sorted(files.items()):
            z.writestr(base + k, v)
        z.writestr(base + 'MANIFEST.json', canonical(manifest))
    return {'bundle': str(destination), 'release_id': release_id, 'files': len(files) + 1,
            'event_head': integrity['head']}


def verify_bundle(path):
    """Independent check of an extracted bundle directory or a bundle zip."""
    path = Path(path)
    tmp = None
    if path.is_file():
        tmp = tempfile.mkdtemp(prefix='genesis-bundle-')
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        roots = list(Path(tmp).glob('release_*'))
        if len(roots) != 1:
            raise ValueError('bundle must contain exactly one release_* directory')
        path = roots[0]
    problems = []
    try:
        manifest = json.loads((path / 'MANIFEST.json').read_bytes())
        present = {str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and p.name != 'MANIFEST.json'}
        if present != set(manifest['files']):
            problems.append(f'file set differs: missing {sorted(set(manifest["files"]) - present)[:3]}, '
                            f'extra {sorted(present - set(manifest["files"]))[:3]}')
        for rel, h in manifest['files'].items():
            p = path / rel
            if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() != h:
                problems.append(f'hash mismatch: {rel}')
        # Rebuild the event store from the append-only export and objects.
        with tempfile.TemporaryDirectory(prefix='genesis-rebuild-') as d:
            shutil.copy(path / 'events.jsonl', Path(d) / 'events.jsonl')
            shutil.copytree(path / 'objects', Path(d) / 'objects')
            try:
                record = rebuild_from_export(d)
                if record['head'] != manifest['event_head'] or record['events'] != manifest['events']:
                    problems.append('rebuilt event head differs from manifest')
            except Exception as exc:
                problems.append(f'event rebuild failed: {type(exc).__name__}: {exc}')
        identity = json.loads((path / 'analysis_code' / 'CODE_IDENTITY.json').read_bytes())
        recomputed = {}
        for rel in identity['files']:
            p = path / 'analysis_code' / rel
            recomputed[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if digest(recomputed) != manifest['shipped_code_identity'] or recomputed != identity['files']:
            problems.append('shipped analysis code does not match its code identity')
        if manifest['source_hash'] != manifest['shipped_code_identity']:
            problems.append('campaign was produced by different source than the shipped analysis code '
                            '(acceptable only with a recorded deviation)')
        return {'ok': not problems, 'problems': problems, 'release_id': manifest['release_id'],
                'event_head': manifest['event_head']}
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
