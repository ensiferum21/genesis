"""Replication bundle and release artifact (spec §43).

    release_<id>/
      MANIFEST.json  CLAIMS.json  resolved_config.json  system_version.json
      dependency_lock/  container_digests.json  model_identifiers.json
      events.jsonl  campaign.sqlite3.snapshot  objects/sha256/...
      certificates/  checker_receipts/  resource_receipts/  preregistration.json
      analysis_code/  report.md  REPRODUCE.md  LIMITATIONS.md

`verify_bundle` re-derives everything a reproducer needs without trusting the
bundle's own claims: every file hash, the event hash chain rebuilt from
events.jsonl + objects, the code identity of the shipped source, and (R-02)
every claim's effective level, recomputed from the rebuilt evidence graph with
the verifier's own trust root and pinned anchors and compared with CLAIMS.json.

CLAIMS.json separates history from current status: `historical` holds the
promotions as granted; `effective_levels` holds what the evidence licenses at
export time after every revocation. REVOCATIONS.json is the revocation feed.
A verifier reviewing an older release passes a later bundle's REVOCATIONS.json
as `later_revocations`; the bundle is still checked as released, and claims
downgraded since then are reported separately (`downgraded_since_release`).
A producer can omit events from a self-consistent chain; only an external
chronology or a later feed from another party can expose that.
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
from .kernel.anchors import pinned_tool_anchors
from .kernel.evidence import AXES, FLOOR, EvidenceKernel
from .kernel.wording import lint
from .store import Store, rebuild_from_export

CLAIMS_SCHEMA = 'genesis-claims-v2'


def effective_claims(store, *, trust_root=None):
    """Current, revocation-aware status of every claim in `store` (R-02)."""
    k = EvidenceKernel(store, anchors=pinned_tool_anchors(), trust_root=trust_root)
    registry, problems, source = k._registry()
    claims = [k.effective_report(cid) for cid in k.claim_ids()]
    ceiling = dict(FLOOR)
    for c in claims:
        for axis, levels in AXES.items():
            if levels.index(c['effective_levels'][axis]) > levels.index(ceiling[axis]):
                ceiling[axis] = c['effective_levels'][axis]
    return {'schema': CLAIMS_SCHEMA, 'evaluated_at': utcnow(), 'revocation_head': k.revocation_head(),
            'registry': {'root_key_sha256': source if registry else None,
                         'available': registry is not None, 'problems': problems},
            'claims': claims, 'ceiling': ceiling, 'promotion_allowed': False,
            'note': 'effective_levels are re-derived from the evidence graph at export; '
                    'historical.recorded_levels are as originally granted'}, k.revocations()

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


def build_bundle(campaign_root, destination, *, report=None, limitations=(), trust_root=None):
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
        claims, revocations = effective_claims(s, trust_root=trust_root)
        claims['event_head'] = integrity['head']
        text = report.decode() if isinstance(report, bytes) else (report or '')
        problems = lint(text, claims['ceiling'])
        if problems:
            # A cached report that outruns the current evidence is invalidated, not shipped.
            raise ValueError('report exceeds the current effective evidence: ' +
                             '; '.join(f"{p['phrase']!r} ({p['why']})" for p in problems[:5]))
        files['CLAIMS.json'] = canonical(claims)
        files['REVOCATIONS.json'] = canonical({'schema': 'genesis-revocations-v1', 'records': revocations})
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


def _compare_claims(bundled, recomputed):
    problems = []
    if bundled.get('schema') != CLAIMS_SCHEMA:
        return ['CLAIMS.json predates effective-level export (R-02); its levels cannot be trusted']
    want = {c['claim_id']: c['effective_levels'] for c in recomputed['claims']}
    have = {c.get('claim_id'): c.get('effective_levels') for c in bundled.get('claims', [])}
    if set(want) != set(have):
        problems.append(f'claim set differs: missing {sorted(set(want) - set(have))[:3]}, '
                        f'extra {sorted(set(have) - set(want))[:3]}')
    for cid in sorted(set(want) & set(have)):
        if have[cid] != want[cid]:
            diff = {a: (have[cid].get(a) if isinstance(have[cid], dict) else None, want[cid].get(a))
                    for a in set(want[cid]) | set(have[cid] or {}) if (have[cid] or {}).get(a) != want[cid].get(a)}
            problems.append(f'CLAIMS.json asserts levels the evidence graph does not license for {cid}: '
                            + ', '.join(f'{a} bundled={b} recomputed={r}' for a, (b, r) in sorted(diff.items())))
    if bundled.get('revocation_head') != recomputed['revocation_head']:
        problems.append('bundled revocation head differs from the rebuilt evidence graph')
    return problems


def verify_bundle(path, *, trust_root=None, later_revocations=None):
    """Independent check of an extracted bundle directory or a bundle zip.

    `trust_root`: the verifier's own externally controlled role registry; without
    it, confirmation-level claims cannot be re-derived and a bundle asserting
    them is rejected. `later_revocations`: path to a later REVOCATIONS.json.
    """
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
    current = None
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
        # Rebuild the event store from the append-only export and objects, then
        # re-derive every claim from the rebuilt evidence graph.
        with tempfile.TemporaryDirectory(prefix='genesis-rebuild-') as d:
            shutil.copy(path / 'events.jsonl', Path(d) / 'events.jsonl')
            shutil.copytree(path / 'objects', Path(d) / 'objects')
            try:
                record = rebuild_from_export(d)
                if record['head'] != manifest['event_head'] or record['events'] != manifest['events']:
                    problems.append('rebuilt event head differs from manifest')
                with Store(d) as s:
                    recomputed, revocations = effective_claims(s, trust_root=trust_root)
                    bundled = json.loads((path / 'CLAIMS.json').read_bytes())
                    problems += _compare_claims(bundled, recomputed)
                    feed = (path / 'REVOCATIONS.json')
                    if not feed.is_file() or json.loads(feed.read_bytes()).get('records') != \
                            json.loads(canonical(revocations)):
                        problems.append('REVOCATIONS.json differs from the revocations in the evidence graph')
                    if later_revocations is not None:
                        records = json.loads(Path(later_revocations).read_bytes())['records']
                        k = EvidenceKernel(s, anchors=pinned_tool_anchors(), trust_root=trust_root)
                        applied = k.apply_revocations(records)
                        now, _ = effective_claims(s, trust_root=trust_root)
                        before = {c['claim_id']: c['effective_levels'] for c in recomputed['claims']}
                        current = {'applied': len(applied['applied']),
                                   'skipped_unknown': len(applied['skipped_unknown']),
                                   'downgraded_since_release': sorted(
                                       c['claim_id'] for c in now['claims']
                                       if c['effective_levels'] != before[c['claim_id']]),
                                   'claims': now['claims']}
            except Exception as exc:
                problems.append(f'event rebuild or claim recomputation failed: {type(exc).__name__}: {exc}')
        identity = json.loads((path / 'analysis_code' / 'CODE_IDENTITY.json').read_bytes())
        recomputed_code = {}
        for rel in identity['files']:
            p = path / 'analysis_code' / rel
            recomputed_code[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if digest(recomputed_code) != manifest['shipped_code_identity'] or recomputed_code != identity['files']:
            problems.append('shipped analysis code does not match its code identity')
        if manifest['source_hash'] != manifest['shipped_code_identity']:
            problems.append('campaign was produced by different source than the shipped analysis code '
                            '(acceptable only with a recorded deviation)')
        out = {'ok': not problems, 'problems': problems, 'release_id': manifest['release_id'],
               'event_head': manifest['event_head']}
        if current is not None:
            out['current'] = current
        return out
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
