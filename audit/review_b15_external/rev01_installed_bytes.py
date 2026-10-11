# B15-REV-01 reproduction, verbatim from the external review.
import tempfile, sys, hashlib, base64, json
import importlib.metadata as metadata
from pathlib import Path
from genesis import deployment as D

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    site = root / 'site'; site.mkdir()
    package = site / 'reviewprobe'; package.mkdir()
    module = package / '__init__.py'
    module.write_bytes(b'VALUE = 1\n')
    info = site / 'reviewprobe-1.0.dist-info'; info.mkdir()
    (info / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: reviewprobe\nVersion: 1.0\n')
    (info / 'top_level.txt').write_text('reviewprobe\n')
    recorded_hash = base64.urlsafe_b64encode(
        hashlib.sha256(module.read_bytes()).digest()).decode().rstrip('=')
    (info / 'RECORD').write_text(
        'reviewprobe/__init__.py,sha256=' + recorded_hash + ',10\n')
    version = f'{sys.version_info.major}.{sys.version_info.minor}'
    (root / 'pyproject.toml').write_text(
        '[project]\nname="probe"\nversion="1.0"\n'
        'dependencies=["reviewprobe==1.0"]\nrequires-python=">=' + version + '"\n')
    original_root = D.REPO
    D.REPO = root
    sys.path.insert(0, str(site))
    try:
        dist = metadata.distribution('reviewprobe')
        lock = ('# genesis-lock-v2 python=' + version +
                ' platform=linux-x86_64\nreviewprobe==1.0\n')
        fingerprints = {'python': version, 'distributions': {
            'reviewprobe': {'version': '1.0', 'top_level': ['reviewprobe'],
                           'content_sha256': D.content_fingerprint(dist)}}}
        before = D.check_lock(lock, fingerprints)
        module.write_bytes(b'VALUE = 999\n')
        after = D.check_lock(lock, fingerprints)
        import reviewprobe
        print(json.dumps({'before': before, 'after_file_change': after,
                          'imported_value': reviewprobe.VALUE}, indent=2))
        assert before['ok'] and after['ok'] and reviewprobe.VALUE == 999
    finally:
        D.REPO = original_root
        sys.path.remove(str(site))
        sys.modules.pop('reviewprobe', None)
