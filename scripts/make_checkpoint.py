#!/usr/bin/env python3
"""Create a batch checkpoint ZIP from the committed tree.

Contents: `git archive HEAD`, a full git bundle, the test-matrix report, a
checkpoint record and a SHA-256 manifest of every member. Refuses to run on a
dirty tree so the checkpoint always corresponds to one commit.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args, **kw):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, **kw).stdout


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _lock_check():
    sys.path.insert(0, str(ROOT / 'src'))
    from genesis.deployment import check_lock
    try:
        return check_lock()
    except (OSError, ValueError) as exc:
        return {'ok': False, 'problems': [f'{type(exc).__name__}: {exc}']}


def environment():
    packages = {}
    for name in ('pydantic', 'pydantic-core', 'numpy', 'scipy', 'cryptography', 'scikit-learn', 'networkx'):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    pins = ROOT / 'toolchain' / 'PINS.json'
    return {
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'packages': packages,
        'toolchain_pins': json.loads(pins.read_text()) if pins.exists() else None,
        'dependency_lock_check': _lock_check(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--out', default=str(ROOT.parent / 'checkpoints'))
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--parent', default=None, help='parent checkpoint zip (its SHA-256 is recorded)')
    parser.add_argument('--parent-ref', default=None, help='git ref of the parent checkpoint commit')
    parser.add_argument('--suffix', default='', help='name suffix for a follow-up checkpoint of the same batch')
    args = parser.parse_args(argv)
    if git('status', '--porcelain').strip():
        raise SystemExit('working tree is dirty; commit before making a checkpoint')
    commit = git('rev-parse', 'HEAD').decode().strip()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        report = tmp / 'test_report.json'
        cmd = [sys.executable, str(ROOT / 'scripts' / 'run_test_matrix.py'), '--report', str(report)]
        if args.quick:
            cmd.append('--quick')
        tests = subprocess.run(cmd, cwd=ROOT)
        if tests.returncode != 0:
            raise SystemExit('test matrix failed; no checkpoint written')
        bundle = tmp / 'source-history.bundle'
        git('bundle', 'create', str(bundle), '--all')
        archive = tmp / 'tree.tar'
        git('archive', '--format=tar', '-o', str(archive), 'HEAD')
        state = json.loads((ROOT / 'batch_state.json').read_text())
        record = {
            'schema': 'genesis-completion-checkpoint-v1',
            'batch': args.batch,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'commit': commit,
            'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
            'environment': environment(),
            'batch_state': state,
            'test_report': json.loads(report.read_text()),
            'claim_ceiling': ('Engineering checkpoint only. No sealed evaluation, independent custody, '
                              'scientific promotion, novelty or self-improvement claim.'),
        }
        # Roadmap §14.1 mandatory checkpoint contents.
        if args.parent:
            parent = Path(args.parent)
            record['parent_checkpoint'] = {'name': parent.name, 'sha256': sha256(parent.read_bytes())}
        if args.parent_ref:
            record['changes_since_parent'] = git('log', '--oneline', f'{args.parent_ref}..HEAD').decode().splitlines()
        ledger = ROOT / 'ledger' / 'requirements_ledger.json'
        if ledger.exists():
            from collections import Counter
            rows = json.loads(ledger.read_text())['rows']
            record['requirements_ledger'] = {
                'rows': len(rows), 'dispositions': dict(Counter(r['disposition'] for r in rows)),
                'accepted': sum(r['acceptance']['decision'] == 'IMPLEMENTED_AND_ACCEPTED' for r in rows)}
        record['open_defects'] = state.get('open_defects', [])
        record['failure_and_repair_logs'] = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob('audit/**/logs*/*')
                                                   if p.is_file())
        record['model_identities'] = {'hosted_model': None, 'note': 'no language model is called by any campaign'}
        notes = ROOT / 'docs' / 'checkpoints' / f'B{args.batch}{args.suffix}_RECORD.md'
        if notes.exists():
            record['record_notes'] = notes.read_text()
        name = f'GENESIS_COMPLETION_CHECKPOINT_B{args.batch:02d}{args.suffix}'
        dest = out / f'{name}.zip'
        if dest.exists():
            raise SystemExit(f'{dest} exists; checkpoints are never overwritten (use --suffix)')
        import tarfile
        members = {}
        with tarfile.open(archive) as tar:
            for info in tar.getmembers():
                if info.isfile():
                    members[f'genesis/{info.name}'] = tar.extractfile(info).read()
        members['genesis/source-history.bundle'] = bundle.read_bytes()
        members['genesis/CHECKPOINT_RECORD.json'] = (json.dumps(record, indent=2) + '\n').encode()
        manifest = {path: {'sha256': sha256(data), 'bytes': len(data)} for path, data in sorted(members.items())}
        members['genesis/CHECKPOINT_MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
            for path, data in sorted(members.items()):
                z.writestr(path, data)
    digest = sha256(dest.read_bytes())
    (out / f'{name}.sha256').write_text(f'{digest}  {dest.name}\n')
    print(json.dumps({'checkpoint': str(dest), 'sha256': digest, 'commit': commit}))


if __name__ == '__main__':
    main()
