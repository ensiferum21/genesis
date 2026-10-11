"""Store backup and restore (roadmap W04).

A backup is the evidence itself: events.jsonl, every content-addressed object
and the campaign's own files (config, exports, quarantine). The SQLite database
and snapshots are derived and are rebuilt on restore, so a restore re-checks
the whole hash chain rather than trusting a copied database.

Integrity here is local hash integrity, as everywhere in the store: someone who
can rewrite the archive can recompute its manifest. Pin a restore to a head
recorded elsewhere (a release bundle manifest or a signed receipt) with
`expected_head`.
"""
import json
import os
from pathlib import Path
import shutil
import stat
import uuid
import zipfile

from .common import atomic_zip, bytes_hash, canonical, fsync_dir, is_temp_name, utcnow
from .store import Store, rebuild_from_export

SCHEMA = 'genesis-store-backup-v1'
DERIVED = ('writer.lock', 'campaign.sqlite3', 'campaign.sqlite3-wal', 'campaign.sqlite3-shm',
           'campaign.sqlite3-journal', 'campaign.sqlite3.rebuild-tmp')
SKIP_DIRS = (('snapshots',), ('objects', 'tmp'))
MAX_MEMBER = 1 << 30
MAX_TOTAL = 8 << 30
MAX_RATIO = 200


def _members(root):
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.is_symlink():
            raise ValueError(f'symlink in store: {rel}')
        if not p.is_file() or p.name in DERIVED or is_temp_name(p.name):
            continue
        if any(rel.parts[:len(d)] == d for d in SKIP_DIRS):
            continue
        yield rel.as_posix(), p


def backup(root, destination):
    """Write a verified backup of the store at `root`. Holds the writer lock throughout."""
    with Store(root) as s:
        integrity = s.verify()
        files, members = {}, []
        for rel, path in _members(s.root):
            data = path.read_bytes()
            if rel.startswith('objects/sha256/') and bytes_hash(data) != rel.rsplit('/', 1)[1]:
                raise RuntimeError(f'object corruption: {rel}')
            files[rel] = bytes_hash(data); members.append((rel, data))
        manifest = {'schema': SCHEMA, 'event_head': integrity['head'], 'events': integrity['events'],
                    'created_at': utcnow(), 'files': files}
        with atomic_zip(destination) as z:
            for rel, data in members:
                z.writestr(rel, data)
            z.writestr('MANIFEST.json', canonical(manifest))
    return {'backup': str(destination), 'event_head': integrity['head'], 'events': integrity['events'],
            'files': len(files)}


def _check_member(info):
    name = info.filename
    if (not name or name.startswith('/') or '\\' in name or any(part in ('', '.', '..') for part in name.split('/'))
            or name.endswith('/')):
        raise ValueError(f'unsafe archive member name: {name!r}')
    kind = stat.S_IFMT(info.external_attr >> 16)
    if kind and kind != stat.S_IFREG:      # symlinks, devices, directories (zip writers may omit type bits)
        raise ValueError(f'archive member is not a regular file: {name!r}')
    if info.file_size > MAX_MEMBER:
        raise ValueError(f'archive member too large: {name!r}')
    if info.compress_size and info.file_size / info.compress_size > MAX_RATIO and info.file_size > (1 << 20):
        raise ValueError(f'archive member compression ratio is implausible: {name!r}')


def restore(archive, destination, *, expected_head=None):
    """Restore a backup into `destination` (absent or empty). Nothing appears at
    `destination` unless every member hash, the event chain, every referenced
    object and the derived database check out."""
    destination = Path(destination)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise FileExistsError(f'restore destination must be absent or empty: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f'.{destination.name}.restore-tmp-{uuid.uuid4().hex[:8]}'
    staging.mkdir(mode=0o700)
    try:
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise ValueError('duplicate archive members')
            for info in infos:
                _check_member(info)
            if sum(i.file_size for i in infos) > MAX_TOTAL:
                raise ValueError('archive too large')
            if 'MANIFEST.json' not in names:
                raise ValueError('backup manifest missing')
            manifest = json.loads(z.read('MANIFEST.json'))
            if manifest.get('schema') != SCHEMA or not isinstance(manifest.get('files'), dict):
                raise ValueError('not a genesis store backup')
            if set(manifest['files']) != set(names) - {'MANIFEST.json'}:
                raise ValueError('archive members differ from the backup manifest')
            if 'events.jsonl' not in manifest['files']:
                raise ValueError('backup has no event export')
            for name in sorted(manifest['files']):
                parts = name.split('/')
                if parts[0] in ('snapshots',) or name in DERIVED or parts[-1] in DERIVED or \
                        is_temp_name(parts[-1]) or parts[:2] == ['objects', 'tmp']:
                    raise ValueError(f'derived or temporary file in backup: {name}')
                data = z.read(name)
                if bytes_hash(data) != manifest['files'][name]:
                    raise ValueError(f'member hash differs from the manifest: {name}')
                if name.startswith('objects/sha256/') and bytes_hash(data) != parts[-1]:
                    raise ValueError(f'object name is not its content hash: {name}')
                target = staging.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                             0o400 if parts[0] == 'objects' else 0o600)
                with os.fdopen(fd, 'wb') as f:
                    f.write(data); f.flush(); os.fsync(f.fileno())
        record = rebuild_from_export(staging)
        if record['partial_tail_dropped']:
            raise ValueError('backup event export ends in a partial line')
        with Store(staging) as s:
            integrity = s.verify()
        if integrity['head'] != manifest['event_head'] or integrity['events'] != manifest['events']:
            raise ValueError('rebuilt event chain differs from the backup manifest')
        if expected_head is not None and integrity['head'] != expected_head:
            raise ValueError('restored event head is not the expected head')
        if destination.exists():
            destination.rmdir()
        os.rename(staging, destination)
        fsync_dir(destination.parent)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {'restored': str(destination), 'event_head': integrity['head'], 'events': integrity['events'],
            'files': len(manifest['files'])}
