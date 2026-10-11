"""The pinned Lean/Mathlib research workspace (roadmap W08).

`toolchain/FORMAL_WORKSPACE.json` pins the Lean toolchain, the Mathlib commit and every
Lake dependency commit, and names the import roots Genesis may use. `build` fetches
those exact commits from GitHub (or a local mirror), checks that Mathlib's own manifest
names the same dependency commits, and builds only the import closure of the roots,
locally:

  * `lake build --no-cache`: no precompiled Mathlib artifacts are downloaded;
  * the build runs without proxy variables, so it cannot reach the network;
  * ProofWidgets' widget JavaScript is the copy committed upstream; a rebuild (npm) is
    refused through `-K errorOnBuild`.

The importable artifacts (.olean and companions) are then copied into one flat
`olean/` tree, the only directory a checking sandbox mounts, and hashed into
`WORKSPACE_MANIFEST.json`. `audit` re-hashes that tree before every use: an edited,
added, removed or symlinked artifact fails closed.

Two identities are kept apart. The *source identity* (pins, Lean binary hash, commits,
import roots) is what another machine reproduces. The *artifact identity* (hashes of
the built files) identifies this build. Lean does not promise byte-identical .olean
files across machines, so replay compares checked declarations and axioms, not bytes.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from ..common import canonical, digest, utcnow

REPO = Path(__file__).resolve().parents[3]
PINS_PATH = REPO / 'toolchain' / 'FORMAL_WORKSPACE.json'
MANIFEST = 'WORKSPACE_MANIFEST.json'
SCHEMA = 'genesis-formal-workspace-manifest-v1'
ERROR_ON_BUILD = 'genesis: rebuilding the ProofWidgets widget JavaScript (npm) is not allowed'
MOUNT = '/opt/mathlib'


class WorkspaceUnavailable(RuntimeError):
    pass


def pins(path=PINS_PATH):
    return json.loads(Path(path).read_text())


def source_identity(p, lean_sha256):
    return digest({'pins': p, 'lean_sha256': lean_sha256})


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _git(*args, cwd, env=None):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


def _fetch(url, rev, dest, mirror=None):
    """Fetch exactly `rev` (shallow) into a fresh directory and check out that commit."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    _git('init', '-q', cwd=dest)
    _git('remote', 'add', 'origin', url, cwd=dest)
    source = str(Path(mirror)) if mirror else url
    _git('fetch', '-q', '--depth', '1', source, rev, cwd=dest)
    _git('-c', 'advice.detachedHead=false', 'checkout', '-q', 'FETCH_HEAD', cwd=dest)
    head = _git('rev-parse', 'HEAD', cwd=dest)
    if head != rev:
        raise WorkspaceUnavailable(f'{url}: fetched {head}, pinned {rev}')


def _lean(lean_root):
    lean = Path(lean_root) / 'bin' / 'lean'
    if not lean.is_file():
        raise WorkspaceUnavailable(f'no Lean binary at {lean}')
    return lean


def module_of(rel, suffixes):
    """'Mathlib/Data/Nat/Basic.olean.server' -> ('Mathlib.Data.Nat.Basic', '.olean.server')."""
    for suf in sorted(suffixes, key=len, reverse=True):
        if rel.endswith(suf):
            return rel[:-len(suf)].replace('/', '.'), suf
    return None, None


def fetch_sources(out, *, mirror=None, pins_path=PINS_PATH):
    """Fetch Mathlib and every dependency at their pinned commits into out/src."""
    p = pins(pins_path)
    src = Path(out).resolve() / 'src'
    m = p['mathlib']
    _fetch(m['url'], m['rev'], src, mirror and Path(mirror) / m['name'])
    if (src / 'lean-toolchain').read_text().strip() != p['toolchain']:
        raise WorkspaceUnavailable('Mathlib names another Lean toolchain than the pin')
    upstream = json.loads((src / 'lake-manifest.json').read_text())
    named = sorted((x['name'], x['url'], x['rev']) for x in upstream['packages'])
    if named != sorted((x['name'], x['url'], x['rev']) for x in p['packages']):
        raise WorkspaceUnavailable('Mathlib\'s lake-manifest names other dependency commits than the pins')
    for pkg in p['packages']:
        _fetch(pkg['url'], pkg['rev'], src / '.lake' / 'packages' / pkg['name'], mirror and Path(mirror) / pkg['name'])
    return src


def lake_build(src, *, lean_root, pins_path=PINS_PATH, jobs=None, log=None):
    """Build the import closure of the pinned roots, offline and without Lake's cache."""
    p = pins(pins_path)
    src = Path(src)
    env = {'PATH': f'{Path(lean_root) / "bin"}:/usr/bin:/bin', 'HOME': str(src.parent), 'LC_ALL': 'C.UTF-8'}
    argv = [str(Path(lean_root) / 'bin' / 'lake'), 'build', '--no-cache', '-K', f'errorOnBuild={ERROR_ON_BUILD}',
            *(['-j', str(jobs)] if jobs else []), *p['import_roots']]
    proc = subprocess.run(argv, cwd=src, env=env, capture_output=True, text=True)   # no proxy variables: offline
    Path(log or src.parent / 'build.log').write_text(proc.stdout + '\n--- stderr ---\n' + proc.stderr)
    if proc.returncode:
        raise WorkspaceUnavailable(f'lake build failed (exit {proc.returncode}); see the build log')
    return argv[1:]


def collect(out, src, *, lean_root, build_command, pins_path=PINS_PATH):
    """Copy the importable artifacts into out/olean (read-only) and write the manifest."""
    p = pins(pins_path)
    out, src = Path(out).resolve(), Path(src).resolve()
    if (out / MANIFEST).exists() or (out / 'olean').exists():
        raise FileExistsError(f'{out} already holds a built workspace; audit it or build elsewhere')
    olean = out / 'olean'
    modules = {}
    libs = [src / '.lake' / 'build' / 'lib' / 'lean'] + sorted((src / '.lake' / 'packages').glob('*/.lake/build/lib/lean'))
    for lib in libs:
        for f in sorted(lib.rglob('*')):
            if not f.is_file() or f.is_symlink():
                continue
            rel = f.relative_to(lib).as_posix()
            mod, suf = module_of(rel, p['artifact_suffixes'])
            if mod is None:
                continue
            if suf in modules.get(mod, {}):
                raise WorkspaceUnavailable(f'module {mod} is built by two packages')
            target = olean / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, target)
            target.chmod(0o444)
            modules.setdefault(mod, {})[suf] = _sha(target)
    for d in sorted({x for x in olean.rglob('*') if x.is_dir()}, reverse=True):
        d.chmod(0o555)
    olean.chmod(0o555)
    lean_sha = _sha(_lean(lean_root))
    manifest = {'schema': SCHEMA, 'pins_sha256': digest(p), 'lean_version': p['lean_version'], 'lean_sha256': lean_sha,
                'source_identity': source_identity(p, lean_sha), 'mathlib_rev': p['mathlib']['rev'],
                'packages': {x['name']: x['rev'] for x in p['packages']}, 'import_roots': p['import_roots'],
                'modules': modules, 'module_count': len(modules), 'artifact_identity': digest(modules),
                'built_at': utcnow(), 'build_command': build_command}
    (out / MANIFEST).write_bytes(canonical(manifest))
    return manifest


def build(out, *, lean_root, mirror=None, pins_path=PINS_PATH, jobs=None):
    """Fetch the pinned sources and build the import closure into `out` (a new directory)."""
    p = pins(pins_path)
    out = Path(out).resolve()
    if (out / MANIFEST).exists():
        raise FileExistsError(f'{out} already holds a built workspace; audit it or build elsewhere')
    version = subprocess.run([str(_lean(lean_root)), '--version'], capture_output=True, text=True, check=True).stdout
    if f'version {p["lean_version"]}' not in version:
        raise WorkspaceUnavailable(f'Lean {p["lean_version"]} required, found {version.strip()}')
    src = fetch_sources(out, mirror=mirror, pins_path=pins_path)
    command = lake_build(src, lean_root=lean_root, pins_path=pins_path, jobs=jobs, log=out / 'build.log')
    return collect(out, src, lean_root=lean_root, build_command=command, pins_path=pins_path)


def audit(out, *, pins_path=PINS_PATH, lean_sha256=None):
    """Re-hash the artifact tree against the manifest. Returns (manifest, problems)."""
    out = Path(out)
    try:
        manifest = json.loads((out / MANIFEST).read_text())
    except (OSError, ValueError) as exc:
        return None, [f'no readable workspace manifest ({type(exc).__name__})']
    problems = []
    p = pins(pins_path)
    if manifest.get('schema') != SCHEMA:
        problems.append('not a workspace manifest')
        return manifest, problems
    if manifest.get('pins_sha256') != digest(p):
        problems.append('the workspace was built from other pins than toolchain/FORMAL_WORKSPACE.json')
    if lean_sha256 is not None and manifest.get('lean_sha256') != lean_sha256:
        problems.append('the workspace was built with another Lean binary than the pinned one')
    if manifest.get('artifact_identity') != digest(manifest.get('modules')):
        problems.append('the manifest artifact identity does not match its module table')
    olean = out / 'olean'
    seen = {}
    for f in sorted(olean.rglob('*')) if olean.is_dir() else []:
        rel = f.relative_to(olean).as_posix()
        if f.is_symlink():
            problems.append(f'symlink in the artifact tree: {rel}'); continue
        if f.is_dir():
            continue
        mod, suf = module_of(rel, p['artifact_suffixes'])
        if mod is None:
            problems.append(f'unexpected file in the artifact tree: {rel}'); continue
        seen.setdefault(mod, {})[suf] = _sha(f)
    if not olean.is_dir():
        problems.append('no artifact tree')
    want = manifest.get('modules') or {}
    for mod in sorted(set(want) | set(seen)):
        if mod not in seen:
            problems.append(f'missing artifacts for {mod}')
        elif mod not in want:
            problems.append(f'unlisted artifacts for {mod}')
        elif seen[mod] != want[mod]:
            problems.append(f'artifacts of {mod} differ from the manifest')
    return manifest, problems


def locate():
    """The workspace build directory: $GENESIS_FORMAL_WORKSPACE or <toolchain>/formal-workspace."""
    if os.environ.get('GENESIS_FORMAL_WORKSPACE'):
        return Path(os.environ['GENESIS_FORMAL_WORKSPACE'])
    from ..verification.tools import toolchain_root
    return toolchain_root() / 'formal-workspace'


_audited = {}


def _tree_state(out):
    """Cheap fingerprint (path, size, mtime, mode) of the manifest and every artifact file."""
    rows = []
    for f in [out / MANIFEST, *sorted((out / 'olean').rglob('*'))]:
        st = f.lstat()
        rows.append((str(f), st.st_size, st.st_mtime_ns, st.st_mode, st.st_ino))
    return digest(rows)


def environment(out=None):
    """Audited identity of the workspace, or WorkspaceUnavailable. A full re-hash runs
    whenever any artifact file's size, mtime, mode or inode differs from the last audit
    in this process, and at least once per process."""
    from ..verification.tools import tool, ToolUnavailable
    out = Path(out or locate())
    try:
        lean = tool('lean')
    except ToolUnavailable as exc:
        raise WorkspaceUnavailable(str(exc))
    try:
        key = (str(out), _tree_state(out))
    except OSError:
        raise WorkspaceUnavailable(f'no formal workspace at {out}; run toolchain/install_tools.sh')
    if key not in _audited:
        manifest, problems = audit(out, lean_sha256=lean['sha256'])
        if problems:
            raise WorkspaceUnavailable('formal workspace audit failed: ' + '; '.join(problems[:5]))
        _audited[key] = manifest
    manifest = _audited[key]
    return {'root': str(out), 'olean': str(out / 'olean'), 'source_identity': manifest['source_identity'],
            'artifact_identity': manifest['artifact_identity'], 'mathlib_rev': manifest['mathlib_rev'],
            'lean_sha256': manifest['lean_sha256'], 'import_roots': manifest['import_roots'],
            'modules': frozenset(manifest['modules'])}


__all__ = ['build', 'fetch_sources', 'lake_build', 'collect', 'audit', 'environment', 'locate', 'pins', 'WorkspaceUnavailable', 'MOUNT']
