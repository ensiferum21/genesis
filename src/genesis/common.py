"""Canonical, data-only serialization shared by the coordinator and checker."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_hash(data):
    return hashlib.sha256(data).hexdigest()


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
