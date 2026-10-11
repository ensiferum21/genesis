#!/usr/bin/env python3
"""Build or audit the pinned Lean/Mathlib research workspace (roadmap W08).

  build_formal_workspace.py build OUT_DIR [--lean-root DIR] [--mirror DIR] [--jobs N]
  build_formal_workspace.py check OUT_DIR

`build` fetches Mathlib and its Lake dependencies at the commits pinned in
FORMAL_WORKSPACE.json (from GitHub, or a local mirror holding one clone per package),
builds only the import closure of the pinned roots offline with Lake's cache disabled,
and writes WORKSPACE_MANIFEST.json. `check` re-hashes the built artifacts against
the manifest and the pins; exit 1 on any difference.
"""
import argparse
import json
from pathlib import Path
import os
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'src'))

from genesis.formal_research import workspace as W  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=('build', 'check'))
    ap.add_argument('out')
    ap.add_argument('--lean-root')
    ap.add_argument('--mirror')
    ap.add_argument('--jobs', type=int)
    a = ap.parse_args(argv)
    pins = W.pins()
    root = Path(os.environ.get('GENESIS_TOOLCHAIN') or Path.home() / 'toolchain')
    lean_root = Path(a.lean_root or root / f'lean-{pins["lean_version"]}-linux')
    if a.action == 'build':
        manifest = W.build(a.out, lean_root=lean_root, mirror=a.mirror, jobs=a.jobs)
        print(json.dumps({k: manifest[k] for k in ('source_identity', 'artifact_identity', 'module_count')}))
        return 0
    import hashlib
    lean = lean_root / 'bin' / 'lean'
    lean_sha = hashlib.sha256(lean.read_bytes()).hexdigest() if lean.is_file() else None
    manifest, problems = W.audit(a.out, lean_sha256=lean_sha)
    print(json.dumps({'problems': problems, 'source_identity': (manifest or {}).get('source_identity'),
                      'artifact_identity': (manifest or {}).get('artifact_identity')}))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
