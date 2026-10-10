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


def derived_files(s, *, trust_root=None, head=None):
    """Every bundle file that is a function of the evidence store. The verifier
    regenerates these from the rebuilt store and requires byte equality (except
    the export timestamp in CLAIMS.json), so no derived file can be edited."""
    files = {}
    cfg = next((v for _, _, v in _entities(s, 'config')), None) or \
        next((v for _, _, v in _entities(s, 'loop_config')), None)
    files['resolved_config.json'] = canonical(cfg)
    versions = sorted((v.get('generation', -1), k, v) for k, _, v in _entities(s, 'system_version'))
    files['system_version.json'] = canonical(versions[-1][2] if versions else {'source': s.state('source_hash')})
    claims, revocations = effective_claims(s, trust_root=trust_root)
    claims['event_head'] = head
    files['CLAIMS.json'] = claims  # serialized by the caller (carries the export timestamp)
    files['report.md'] = render_report(claims).encode()
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
            payload = s.get(node['payload_hash'])
            files[f'certificates/{nid}.json'] = canonical({'node': node, 'payload': payload})
            ref = payload.get('certificate_bundle') if isinstance(payload, dict) else None
            if ref:  # the full CertificateBundle; its CNF/proof objects are under objects/sha256/
                files[f'certificates/bundle_{ref}.json'] = s.get_bytes(ref)
    return files


def render_report(claims):
    """report.md is DERIVED from the per-claim current wording, never free prose: every
    sentence that asserts a result is one claim's own established statement, beside that
    claim's effective levels. Requested-but-unproved propositions appear only as marked
    conjectures. (B14-OPEN-5 and external review F-01.)"""
    lines = ['# Claims as currently established', '',
             'Generated from CLAIMS.json. Each statement below is asserted only at the levels shown beside it; '
             'items marked NOT ESTABLISHED are requests or conjectures, not results.', '']
    for c in claims['claims']:
        levels = ', '.join(f'{a} {v}' for a, v in sorted(c['effective_levels'].items()) if a != 'invalidated')
        lines.append(f"## {c['claim_id']}")
        lines.append('')
        if c['current_statement'] is not None:
            lines.append(f"- Established: {c['current_statement']}")
        else:
            lines.append('- Established: nothing.')
        if c['conjecture'] is not None:
            lines.append(f"- {c['conjecture']}")
        lines.append(f"- Scope: {c['scope']}")
        lines.append(f"- Levels: {levels}{' (invalidated by revocation)' if c['effective_levels'].get('invalidated') else ''}")
        lines.append(f"- Wording contract: {c['statement_contract']}")
        lines.append('')
    return '\n'.join(lines) + '\n'


def wording_problems(notes, claims):
    """Per-claim, structural: each claim's current statement and scope are checked against
    THAT claim's effective levels (another claim's stronger evidence never licenses them);
    operator notes carry no claims at all and are checked at the floor."""
    floor = dict(FLOOR)
    out = [f"operator_notes.md: {p['phrase']!r} ({p['why']})" for p in lint(notes, floor)]
    for c in claims['claims']:
        own = {a: v for a, v in c['effective_levels'].items() if a in AXES}
        if c['current_statement'] is not None:
            out += [f"claim {c['claim_id']} current statement: {p['phrase']!r} ({p['why']})"
                    for p in lint(c['current_statement'], own)]
        out += [f"claim {c['claim_id']} scope: {p['phrase']!r} ({p['why']})" for p in lint(c['scope'], own)]
        if c['conjecture'] is not None and not c['conjecture'].startswith('NOT ESTABLISHED (requested, unproved): '):
            out.append(f"claim {c['claim_id']}: unmarked conjecture")
    return out


REPRODUCE = (
    '# Reproduce\n\n'
    '1. Verify with your OWN trusted installation of genesis, never with code shipped in this bundle:\n'
    '   `genesis verify-bundle <bundle.zip> --trust-root <your trust root>` (exit status 0 only if ok).\n'
    '2. The verifier rebuilds the store from `events.jsonl` + `objects/`, regenerates every derived file, '
    're-derives every claim and replays every bound certificate with the solver disabled.\n'
    '3. `analysis_code/` is the producer\'s source, for diffing against your trusted copy; its identity is '
    'checked, but do not execute it before that check passes.\n'
    '4. Re-run attempts with `genesis trial replay` against a copy; results must match the recorded witnesses, '
    'values, queries and traces (timings excluded).\n')

MANDATORY_LIMITATIONS = ('- Built by the research operator; no independent custody or release authority.\n',
                         '- Container image not pinned by registry digest.\n')


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
        derived = derived_files(s, trust_root=trust_root, head=integrity['head'])
        claims = derived.pop('CLAIMS.json')
        text = report.decode() if isinstance(report, bytes) else (report or '')
        problems = wording_problems(text, claims)
        if problems:
            # Notes or wording that outrun the current evidence are invalidated, not shipped.
            raise ValueError('report exceeds the current effective evidence: ' + '; '.join(problems[:5]))
        files['CLAIMS.json'] = canonical(claims)
        files.update(derived)
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
    # Caller prose is kept only as operator notes, checked at the floor: it cannot carry a claim.
    files['operator_notes.md'] = (report or b'') if isinstance(report, bytes) else (report or '').encode()
    files['REPRODUCE.md'] = REPRODUCE.encode()
    files['LIMITATIONS.md'] = ('# Limitations\n\n' + ''.join(f'- {x}\n' for x in limitations) +
                               ''.join(MANDATORY_LIMITATIONS)).encode()
    manifest = {'release_id': release_id, 'event_head': integrity['head'], 'events': integrity['events'],
                'source_hash': source_hash, 'shipped_code_identity': identity['sha256'],
                'files': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}}
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as z:
        for k, v in sorted(files.items()):
            z.writestr(base + k, v)
        z.writestr(base + 'MANIFEST.json', canonical(manifest))
    return {'bundle': str(destination), 'release_id': release_id, 'files': len(files) + 1,
            'event_head': integrity['head']}


def replay_certificates(store, claims, *, trust_root=None):
    """Checker-only replay (producer disabled) of every certificate behind an
    effective OPTIMALITY_CHECKED claim (R-03). Returns (records, problems)."""
    import os
    from .verification.certificates import replay
    k = EvidenceKernel(store, anchors=pinned_tool_anchors(), trust_root=trust_root)
    records, problems = [], []
    previous = os.environ.get('GENESIS_CHECKER_ONLY')
    os.environ['GENESIS_CHECKER_ONLY'] = '1'
    try:
        for c in claims:
            if c['effective_levels'].get('math') != 'OPTIMALITY_CHECKED':
                continue
            bounds = [n for n in sorted(k.closure(c['dependencies'])) if k.node(n)['kind'] == 'bound_state'
                      and k._bound_state_problems(n) is None]
            if not bounds:
                problems.append(f'{c["claim_id"]}: no custody-held certificate to replay')
                continue
            for n in bounds:
                ref = k.payload(n)['certificate_bundle']
                try:
                    result = replay(store.get(ref), store.get_bytes)
                except Exception as exc:
                    result = {'status': 'CHECKER_ERROR', 'problems': [f'{type(exc).__name__}: {exc}']}
                records.append({'claim': c['claim_id'], 'bound_state': n, 'certificate': ref, **result})
                if result['status'] != 'OPTIMALITY_CHECKED' or result.get('problems'):
                    problems.append(f'{c["claim_id"]}: certificate replay {result["status"]}: '
                                    + '; '.join(result.get('problems', []))[:200])
    finally:
        if previous is None:
            os.environ.pop('GENESIS_CHECKER_ONLY', None)
        else:
            os.environ['GENESIS_CHECKER_ONLY'] = previous
    return records, problems


def _strict_json(data):
    """JSON with duplicate keys and NaN/Infinity rejected (readers must not disagree)."""
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f'duplicate JSON key {key!r}')
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def _compare_claims(bundled, recomputed):
    """Whole-object comparison of CLAIMS.json with the re-derived one (only the export
    time and the exporter's registry description may differ)."""
    problems = []
    if bundled.get('schema') != CLAIMS_SCHEMA:
        return ['CLAIMS.json predates effective-level export (R-02); its levels cannot be trusted']
    ids = [c.get('claim_id') for c in bundled.get('claims', [])]
    if len(ids) != len(set(ids)):
        problems.append('CLAIMS.json lists a claim more than once')
    want = {c['claim_id']: c['effective_levels'] for c in recomputed['claims']}
    have = {c.get('claim_id'): c.get('effective_levels') for c in bundled.get('claims', [])}
    for cid in sorted(set(want) & set(have)):
        if have[cid] != want[cid]:
            diff = {a: ((have[cid] or {}).get(a), want[cid].get(a))
                    for a in set(want[cid]) | set(have[cid] or {}) if (have[cid] or {}).get(a) != want[cid].get(a)}
            problems.append(f'CLAIMS.json asserts levels the evidence graph does not license for {cid}: '
                            + ', '.join(f'{a} bundled={b} recomputed={r}' for a, (b, r) in sorted(diff.items())))
    if set(want) != set(have):
        problems.append(f'claim set differs: missing {sorted(set(want) - set(have))[:3]}, '
                        f'extra {sorted(set(have) - set(want))[:3]}')
    if bundled.get('revocation_head') != recomputed['revocation_head']:
        problems.append('bundled revocation head differs from the rebuilt evidence graph')
    strip = lambda c: {k: v for k, v in c.items() if k not in ('evaluated_at', 'registry')}
    if not problems and canonical(strip(bundled)) != canonical(strip(recomputed)):
        fields = sorted(k for k in set(strip(bundled)) | set(strip(recomputed))
                        if canonical(strip(bundled).get(k)) != canonical(strip(recomputed).get(k)))
        problems.append(f'CLAIMS.json differs from the re-derived claims in: {fields}')
    return problems


def _snapshot_problems(snapshot, store):
    """The shipped SQLite snapshot must hold exactly the rebuilt journal, entities, attempts and state."""
    import sqlite3
    with tempfile.TemporaryDirectory(prefix='genesis-snap-') as d:
        copy = Path(d) / 'snap.sqlite3'
        shutil.copy(snapshot, copy)
        db = sqlite3.connect(f'file:{copy}?mode=ro', uri=True)
        try:
            out = []
            for table, order in (('events', 'seq'), ('entities', 'kind, id'), ('attempts', 'id'), ('state', 'key')):
                a = db.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall()
                b = store.db.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall()
                if a != b:
                    out.append(f'campaign.sqlite3.snapshot table {table} differs from the rebuilt store')
            return out
        except Exception as exc:
            return [f'campaign.sqlite3.snapshot unreadable: {type(exc).__name__}']
        finally:
            db.close()


def _safe_rel(rel):
    p = Path(rel)
    return not p.is_absolute() and '..' not in p.parts and rel == p.as_posix()


def verify_bundle(path, *, trust_root=None, later_revocations=None, replay_proofs=True):
    """Independent check of an extracted bundle directory or a bundle zip.

    Rebuilds the store from events.jsonl + objects, then regenerates every
    store-derived file (claims, revocations, preregistration, receipts,
    certificates, config, version) and requires byte equality; checks the
    SQLite snapshot against the rebuilt store; lints the report and every claim
    statement against the re-derived levels; replays every certificate behind an
    optimality claim with the solver disabled; checks the shipped code identity.

    `trust_root`: the verifier's own externally controlled role registry; without
    it, confirmation-level claims cannot be re-derived and a bundle asserting
    them is rejected. `later_revocations`: path to a later REVOCATIONS.json.
    """
    path = Path(path)
    tmp = None
    if path.is_file():
        tmp = tempfile.mkdtemp(prefix='genesis-bundle-')
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for name in names:
                if not _safe_rel(name.rstrip('/')):
                    raise ValueError(f'unsafe path in bundle: {name!r}')
            tops = {n.split('/')[0] for n in names}
            if len(tops) != 1 or not next(iter(tops)).startswith('release_'):
                raise ValueError('bundle must contain exactly one release_* directory and nothing else')
            z.extractall(tmp)
        path = Path(tmp) / next(iter(tops))
    problems = []
    current = None
    replayed = []
    try:
        manifest = _strict_json((path / 'MANIFEST.json').read_bytes())
        for p in path.rglob('*'):
            if p.is_symlink() or not (p.is_file() or p.is_dir()):
                problems.append(f'not a regular file: {p.relative_to(path)}')
        present = {str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and not p.is_symlink()} - {'MANIFEST.json'}
        if present != set(manifest['files']):
            problems.append(f'file set differs: missing {sorted(set(manifest["files"]) - present)[:3]}, '
                            f'extra {sorted(present - set(manifest["files"]))[:3]}')
        for rel, h in manifest['files'].items():
            p = path / rel
            if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() != h:
                problems.append(f'hash mismatch: {rel}')
        limitations = (path / 'LIMITATIONS.md').read_text() if (path / 'LIMITATIONS.md').is_file() else ''
        if any(line not in limitations for line in MANDATORY_LIMITATIONS):
            problems.append('LIMITATIONS.md omits a mandatory limitation')
        # Rebuild the event store from the append-only export and objects, then
        # re-derive every store-derived file from the rebuilt evidence graph.
        with tempfile.TemporaryDirectory(prefix='genesis-rebuild-') as d:
            shutil.copy(path / 'events.jsonl', Path(d) / 'events.jsonl')
            shutil.copytree(path / 'objects', Path(d) / 'objects')
            try:
                record = rebuild_from_export(d)
                if record.get('partial_tail_dropped'):
                    problems.append('events.jsonl ends in a partial line that the rebuild would drop')
                if record['head'] != manifest['event_head'] or record['events'] != manifest['events']:
                    problems.append('rebuilt event head differs from manifest')
                with Store(d) as s:
                    if s.state('source_hash') != manifest['source_hash']:
                        problems.append('MANIFEST source_hash differs from the source recorded in the evidence store')
                    derived = derived_files(s, trust_root=trust_root, head=record['head'])
                    recomputed = derived.pop('CLAIMS.json')
                    raw_claims = (path / 'CLAIMS.json').read_bytes()
                    bundled = _strict_json(raw_claims)
                    problems += _compare_claims(bundled, recomputed)
                    expected = dict(recomputed, evaluated_at=bundled.get('evaluated_at'), registry=bundled.get('registry'))
                    if not problems and raw_claims != canonical(expected):
                        problems.append('CLAIMS.json bytes are not the canonical re-derived claims')
                    for rel, data in derived.items():
                        f = path / rel
                        if not f.is_file() or f.read_bytes() != data:
                            problems.append(f'{rel} differs from the file re-derived from the evidence store')
                    stray = {r for r in present if r.split('/')[0] in ('checker_receipts', 'resource_receipts',
                                                                          'certificates')} - set(derived)
                    if stray:
                        problems.append(f'files not derivable from the evidence store: {sorted(stray)[:3]}')
                    problems += _snapshot_problems(path / 'campaign.sqlite3.snapshot', s)
                    notes = (path / 'operator_notes.md').read_text() if (path / 'operator_notes.md').is_file() else ''
                    problems += wording_problems(notes, recomputed)
                    for prose in ('LIMITATIONS.md', 'REPRODUCE.md'):
                        text = (path / prose).read_text() if (path / prose).is_file() else ''
                        problems += [f"{prose}: {p['phrase']!r} ({p['why']})" for p in lint(text, recomputed['ceiling'])]
                    if (path / 'REPRODUCE.md').is_file() and (path / 'REPRODUCE.md').read_text() != REPRODUCE:
                        problems.append('REPRODUCE.md is not the standard reproduction text')
                    if replay_proofs:
                        replayed, why = replay_certificates(s, recomputed['claims'], trust_root=trust_root)
                        problems += why
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
        identity = _strict_json((path / 'analysis_code' / 'CODE_IDENTITY.json').read_bytes())
        shipped = {r[len('analysis_code/'):] for r in present if r.startswith('analysis_code/')} - {'CODE_IDENTITY.json'}
        if shipped != set(identity['files']):
            problems.append(f'analysis_code/ holds files outside its code identity: '
                            f'{sorted(shipped - set(identity["files"]))[:3]}')
        recomputed_code = {}
        for rel in identity['files']:
            if not _safe_rel(rel):
                problems.append(f'code identity lists an unsafe path {rel!r}')
                continue
            p = path / 'analysis_code' / rel
            recomputed_code[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if digest(recomputed_code) != manifest['shipped_code_identity'] or recomputed_code != identity['files']:
            problems.append('shipped analysis code does not match its code identity')
        if manifest['source_hash'] != manifest['shipped_code_identity']:
            problems.append('campaign was produced by different source than the shipped analysis code '
                            '(acceptable only with a recorded deviation)')
        out = {'ok': not problems, 'problems': problems, 'release_id': manifest['release_id'],
               'event_head': manifest['event_head']}
        if replay_proofs:
            out['certificate_replays'] = replayed
        if current is not None:
            out['current'] = current
        return out
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
