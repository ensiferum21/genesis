"""Canonical, data-only serialization shared by the coordinator and checker."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import uuid


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_hash(data):
    return hashlib.sha256(data).hexdigest()


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


TEMP_MARK = '.tmp-'


def is_temp_name(name):
    return name.startswith('.') and TEMP_MARK in name


def atomic_write(path, data, *, overwrite=False, mode=0o644, fault=None):
    """Write `data` so that `path` is either absent/old or complete - never torn.

    The bytes go to a hidden temporary file in the same directory, are fsynced,
    then linked (overwrite=False: FileExistsError if `path` exists) or renamed
    (overwrite=True) into place, and the directory is fsynced. `fault` names a
    crash-injection point hit after half the bytes are written.
    """
    path = Path(path)
    tmp = path.with_name(f'.{path.name}{TEMP_MARK}{os.getpid()}-{uuid.uuid4().hex[:8]}')
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        with os.fdopen(fd, 'wb') as f:
            if fault:
                from .faults import point
                f.write(data[:len(data) // 2]); f.flush(); point(fault)
                f.write(data[len(data) // 2:])
            else:
                f.write(data)
            f.flush(); os.fsync(f.fileno())
        if overwrite:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
            os.unlink(tmp)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    fsync_dir(path.parent)
    return path


def atomic_zip(destination):
    """Context manager: a ZipFile whose bytes appear at `destination` only when complete.

    Refuses an existing destination. A crash leaves at most a hidden temporary
    file (see is_temp_name), never a torn archive under the final name.
    """
    import contextlib
    import zipfile
    from .faults import point

    @contextlib.contextmanager
    def cm():
        dest = Path(destination)
        if dest.exists():
            raise FileExistsError(dest)
        tmp = dest.with_name(f'.{dest.name}{TEMP_MARK}{os.getpid()}-{uuid.uuid4().hex[:8]}')
        try:
            with zipfile.ZipFile(tmp, 'x', zipfile.ZIP_DEFLATED) as z:
                yield z
            point('zip.write')
            with open(tmp, 'rb') as f:
                os.fsync(f.fileno())
            os.link(tmp, dest)
        finally:
            tmp.unlink(missing_ok=True)
        fsync_dir(dest.parent)
    return cm()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, cap=8*1024*1024):
    path = Path(path)
    if path.stat().st_size > cap:
        raise ValueError('JSON input exceeds size bound')
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def code_identity(root):
    root = Path(root)
    paths = []
    for directory in ('src', 'custody_reference', 'scripts', 'legacy_batch42'):
        paths.extend(p for p in (root/directory).rglob('*.py') if '__pycache__' not in p.parts)
    paths.extend(p for p in (root/'pyproject.toml', root/'requirements.lock') if p.exists())
    files = {str(p.relative_to(root)):bytes_hash(p.read_bytes()) for p in sorted(paths)}
    return {'files':files, 'sha256':digest(files)}
