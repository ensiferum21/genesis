"""Resolve pinned external tools; refuse any binary whose hash differs from PINS.json.

A checker's identity is its binary hash. If the installed binary changes, old
receipts keep their old identity and new checks fail closed until the pin is
updated deliberately (spec §15.1: no silent trust inheritance).
"""
import hashlib
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PINS = REPO / 'toolchain' / 'PINS.json'


class ToolUnavailable(RuntimeError):
    pass


def toolchain_root():
    if os.environ.get('GENESIS_TOOLCHAIN'):
        return Path(os.environ['GENESIS_TOOLCHAIN'])
    for candidate in (Path.home() / 'toolchain', REPO.parent / 'toolchain'):
        if (candidate / 'cadical').exists() or (candidate / 'drat-trim').exists():
            return candidate
    return Path.home() / 'toolchain'


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


_cache = {}


def tool(name):
    """Return {'path', 'sha256', 'identity'} for a pinned tool, or raise ToolUnavailable."""
    pins = json.loads(PINS.read_text())
    if name not in pins or 'binary' not in pins[name]:
        raise ToolUnavailable(f'{name} is not pinned')
    pin = pins[name]
    path = toolchain_root() / pin['binary']
    if not path.is_file():
        raise ToolUnavailable(f'{name} not installed at {path}; run toolchain/install_tools.sh')
    key = (str(path), path.stat().st_mtime_ns, path.stat().st_size)
    actual = _cache.get(key) or _sha(path)
    _cache[key] = actual
    if actual != pin['binary_sha256']:
        raise ToolUnavailable(f'{name} binary hash {actual[:12]} differs from pin {pin["binary_sha256"][:12]}')
    return {'path': str(path), 'sha256': actual, 'identity': f'{name}@{actual[:16]}',
            'version': pin.get('version'), 'commit': pin.get('commit')}


def available(name):
    try:
        tool(name)
        return True
    except ToolUnavailable:
        return False
