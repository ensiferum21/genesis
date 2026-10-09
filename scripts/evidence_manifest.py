#!/usr/bin/env python3
"""Content-addressed snapshot manifest for DEV artifacts (not a digital signature).

Run from outside the source tree or pass an explicit root. This authenticates
internal file consistency *only if* the root hash is anchored independently.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def build_manifest(root: Path, *, exclude: tuple[str, ...] = ('EVIDENCE_MANIFEST.json',)) -> dict:
    # Resolve only after rejecting a symlinked evidence root. The manifest is
    # not allowed to silently omit extra links that may expose sealed material.
    if root.is_symlink():
        raise ValueError('symlink evidence root')
    root = root.resolve()
    if set(exclude) != {'EVIDENCE_MANIFEST.json'}:
        raise ValueError('only EVIDENCE_MANIFEST.json may be excluded')
    entries = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError(f'symlink evidence entry: {p.relative_to(root).as_posix()}')
        # GEN-AUD-017: excluding cache directories hides arbitrary untracked
        # regular files (including protected material). Reject rather than skip.
        if ('__pycache__' in p.relative_to(root).parts
                or '.pytest_cache' in p.relative_to(root).parts
                or p.suffix in ('.pyc', '.pyo')):
            if p.is_file():
                raise ValueError(f'forbidden cache file in evidence tree: {p.relative_to(root).as_posix()}')
            # Empty cache directories are harmless, but no files may be hidden.
            if p.is_dir():
                continue
        if p.is_dir():
            continue
        if not p.is_file():
            raise ValueError(f'special evidence entry: {p.relative_to(root).as_posix()}')
        name = p.relative_to(root).as_posix()
        if name in exclude:
            if name != 'EVIDENCE_MANIFEST.json':
                raise ValueError(f'forbidden manifest exclusion: {name}')
            continue
        entries[name] = {'sha256': digest(p), 'bytes': p.stat().st_size}
    body = {'schema': 'genesis-content-manifest-v1', 'files': entries}
    return {**body, 'root_sha256': hashlib.sha256(canonical(body)).hexdigest(),
            'note': 'Not a signature; independent anchor required.'}


def verify_manifest(root: Path, manifest: dict) -> list[str]:
    if (not isinstance(manifest, dict)
            or manifest.get('schema') != 'genesis-content-manifest-v1'
            or not isinstance(manifest.get('files'), dict)):
        return ['invalid manifest schema']
    body = {k: manifest[k] for k in ('schema', 'files')}
    expected = hashlib.sha256(canonical(body)).hexdigest()
    issues = []
    if expected != manifest.get('root_sha256'):
        issues.append('manifest root mismatch')
    try:
        actual = build_manifest(root)
    except (ValueError, OSError) as exc:
        return sorted(issues + ['unsafe evidence tree: ' + str(exc)])
    expected_files = manifest['files']
    for path, data in expected_files.items():
        if path not in actual['files']:
            issues.append(f'missing: {path}')
        elif actual['files'][path] != data:
            issues.append(f'changed: {path}')
    for path in set(actual['files']) - set(expected_files):
        issues.append(f'unexpected: {path}')
    return sorted(issues)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    out = args.root / 'EVIDENCE_MANIFEST.json'
    if args.verify:
        if not out.exists():
            raise SystemExit('Missing manifest')
        issues = verify_manifest(args.root, json.loads(out.read_text()))
        print(json.dumps({'status': 'PASS' if not issues else 'FAIL', 'issues': issues}))
        raise SystemExit(bool(issues))
    manifest = build_manifest(args.root)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(manifest['root_sha256'])


if __name__ == '__main__':
    main()
