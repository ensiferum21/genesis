"""Supported-deployment definition and checks (roadmap W04, defect R-04).

The supported platform is data (deployment/SUPPORTED_PLATFORM.json). This module
checks a host against it and checks the running Python environment against the
dependency lock. It reports what it observed; it never "fixes" a host.

The lock fingerprints hold a per-file manifest (path, size, SHA-256) of every
locked distribution's installed bytes, taken when the lock is written and only if
those bytes agree with each wheel's RECORD. The check re-reads the files on disk
(B15-REV-01: it used to hash RECORD's own strings). Excluded, explicitly: console
scripts outside site-packages (their shebang names the local interpreter) and the
installer-written dist-info files in EXCLUDED_DIST_INFO. Bytecode in site-packages
is never deserialized here; it must be inert (a private PYTHONPYCACHEPREFIX).
Wheel archive hashes are a separate stage and are not pinned here (PyPI was
unreachable from the build host).
"""
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / 'deployment' / 'SUPPORTED_PLATFORM.json'
LOCK_PATH = REPO / 'requirements.lock'
FINGERPRINTS_PATH = REPO / 'environment' / 'lock_fingerprints.json'
LOCK_SCHEMA = 'genesis-lock-v2'
FINGERPRINT_SCHEMA = 'genesis-lock-fingerprints-v2'
# Installer-written dist-info files: they are not wheel content, so they are not compared.
# Everything else listed in RECORD, including native libraries and package data, is.
EXCLUDED_DIST_INFO = {'RECORD': 'cannot contain its own hash',
                      'INSTALLER': 'names the installing tool',
                      'REQUESTED': 'marks a direct request to the installer',
                      'direct_url.json': 'records where the installer obtained the wheel'}
EXCLUDED_OUTSIDE = 'console script outside site-packages: its shebang names the local interpreter'
STARTUP_HOOK_NAMES = ('sitecustomize.py', 'usercustomize.py')


def _norm(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def project_dependencies(pyproject=None):
    import tomllib
    data = tomllib.loads((pyproject or REPO / 'pyproject.toml').read_text())
    return list(data['project']['dependencies']), data['project'].get('requires-python')


def lock_closure(roots=None):
    """Installed distributions reachable from the project's dependencies."""
    from packaging.requirements import Requirement
    roots = roots if roots is not None else project_dependencies()[0]
    seen, queue = {}, [Requirement(r) for r in roots]
    while queue:
        req = queue.pop()
        if req.marker is not None and not req.marker.evaluate({'extra': ''}):
            continue
        name = _norm(req.name)
        if name in seen:
            continue
        try:
            dist = metadata.distribution(req.name)
        except metadata.PackageNotFoundError:
            seen[name] = None
            continue
        seen[name] = dist
        queue.extend(Requirement(r) for r in (dist.requires or []))
    return dict(sorted(seen.items()))


# ---------------------------------------------------------------- installed bytes (B15-REV-01)

_hash_cache = {}


def _file_sha256(path):
    """SHA-256 of a file's actual bytes, cached per (path, inode, size, mtime) within a process."""
    st = os.stat(path, follow_symlinks=False)
    key = (str(path), st.st_ino, st.st_size, st.st_mtime_ns)
    if key not in _hash_cache:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        _hash_cache[key] = h.hexdigest()
    return _hash_cache[key], st.st_size


def _record_rows(dist):
    import csv
    import io
    text = dist.read_text('RECORD') or ''
    return [tuple(row) for row in csv.reader(io.StringIO(text)) if row and len(row) == 3]


def _unsafe(path):
    parts = path.split('/')
    return path.startswith('/') or '\\' in path or any(p in ('', '.', '..') for p in parts)


def record_entries(dist):
    """(verifiable {path: (algorithm, expected hex, size)}, excluded [{path, reason}], problems) from RECORD."""
    import base64
    files, excluded, problems = {}, [], []
    for path, h, size in _record_rows(dist):
        name = path.rsplit('/', 1)[-1]
        if path.startswith('../'):
            excluded.append({'path': path, 'reason': EXCLUDED_OUTSIDE}); continue
        if path.split('/')[0].endswith('.dist-info') and name in EXCLUDED_DIST_INFO:
            excluded.append({'path': path, 'reason': EXCLUDED_DIST_INFO[name]}); continue
        if _unsafe(path):
            problems.append(f'unsafe RECORD path {path!r}'); continue
        if not h:
            if '/__pycache__/' in f'/{path}' and path.endswith('.pyc'):
                continue          # compiled at install time: inert under a private PYTHONPYCACHEPREFIX
            problems.append(f'RECORD entry without a hash: {path}'); continue
        algo, _, b64 = h.partition('=')
        if algo != 'sha256':
            problems.append(f'RECORD hash algorithm {algo!r} for {path}'); continue
        try:
            hexd = base64.urlsafe_b64decode(b64 + '=' * (-len(b64) % 4)).hex()
        except ValueError:
            problems.append(f'malformed RECORD hash for {path}'); continue
        files[path] = (hexd, int(size) if size.isdigit() else None)
    return files, excluded, problems


def installed_manifest(dist):
    """Per-file manifest {path: {sha256, size}} of what is installed NOW, read from the bytes on
    disk; at lock time it must also agree with the wheel's RECORD (otherwise refuse to lock)."""
    base = Path(dist.locate_file(''))
    entries, excluded, problems = record_entries(dist)
    manifest = {}
    for path, (expected, size) in sorted(entries.items()):
        target = base / path
        if target.is_symlink() or not target.is_file():
            problems.append(f'missing or not a regular file: {path}'); continue
        actual, actual_size = _file_sha256(target)
        if actual != expected or (size is not None and size != actual_size):
            problems.append(f'installed bytes differ from RECORD: {path}')
        manifest[path] = {'sha256': actual, 'size': actual_size}
    return manifest, excluded, problems


def content_fingerprint(dist):
    """Digest of the ACTUAL installed bytes of every verifiable file RECORD lists (a missing
    file contributes a MISSING marker). B15-REV-01: this used to hash RECORD's strings."""
    base = Path(dist.locate_file(''))
    entries, _, problems = record_entries(dist)
    rows = [f'PROBLEM\t{p}' for p in problems]
    for path in sorted(entries):
        target = base / path
        if target.is_symlink() or not target.is_file():
            rows.append(f'{path}\tMISSING')
        else:
            rows.append(f'{path}\t{_file_sha256(target)[0]}')
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()


def _top_level(dist):
    text = dist.read_text('top_level.txt')
    if text:
        return [t for t in text.split() if t and not t.startswith('_')] or text.split()
    names = set()
    for f in dist.files or ():
        first = str(f).split('/', 1)[0]
        if first.endswith('.dist-info') or first.startswith('..') or first == '__pycache__':
            continue
        names.add(first[:-3] if first.endswith('.py') else first)
    return sorted(n for n in names if n.isidentifier())


def _package_dirs(manifest):
    """Top-level directories a distribution installs into (owned code and data trees)."""
    return sorted({p.split('/', 1)[0] for p in manifest if '/' in p and not p.split('/', 1)[0].endswith('.dist-info')})


def _site_dirs(closure):
    return sorted({str(Path(d.locate_file('')).resolve()) for d in closure.values() if d is not None})


def startup_hooks(site_dirs):
    """Files the interpreter executes or follows at start-up from these site directories:
    every .pth file and any sitecustomize/usercustomize module."""
    hooks = {}
    for site in site_dirs:
        for p in sorted(Path(site).iterdir()):
            if p.name.endswith('.pth') or p.name in STARTUP_HOOK_NAMES:
                hooks[str(p)] = _file_sha256(p)[0] if p.is_file() else 'NOT_A_FILE'
    return hooks


def render_lock(closure=None):
    closure = closure if closure is not None else lock_closure()
    missing = [n for n, d in closure.items() if d is None]
    if missing:
        raise RuntimeError(f'cannot lock: not installed: {missing}')
    vi = sys.version_info
    header = [f'# {LOCK_SCHEMA} python={vi.major}.{vi.minor} platform={sys.platform}-{platform.machine()}',
              '# Generated by scripts/environment_lock.py from the installed environment (transitive closure',
              '# of pyproject dependencies). Wheel archive hashes are not included: PyPI was denied by the build',
              '# host egress policy. environment/lock_fingerprints.json holds the per-file manifest of the',
              '# installed bytes, which genesis platform check compares file by file.']
    body = [f'{_norm(n)}=={d.version}' for n, d in closure.items()]
    dists, refused = {}, []
    for n, d in closure.items():
        manifest, excluded, problems = installed_manifest(d)
        refused += [f'{n}: {p}' for p in problems]
        dists[n] = {'version': d.version, 'top_level': _top_level(d), 'files': manifest, 'excluded': excluded,
                    'content_sha256': content_fingerprint(d)}
    if refused:
        raise RuntimeError('refusing to lock an environment whose installed bytes differ from the wheels: '
                           + '; '.join(refused[:5]))
    fingerprints = {'schema': FINGERPRINT_SCHEMA, 'python': f'{vi.major}.{vi.minor}', 'distributions': dists,
                    'startup_hooks': startup_hooks(_site_dirs(closure)),
                    'wheel_archives': {'status': 'NOT_PINNED',
                                       'reason': 'PyPI denied by the build host egress policy; archive hashes '
                                                 'must be added where the wheels can be downloaded'}}
    return '\n'.join(header + body) + '\n', fingerprints


def parse_lock(text):
    head = text.splitlines()[0] if text else ''
    m = re.match(rf'# {LOCK_SCHEMA} python=(\d+\.\d+) platform=(\S+)$', head)
    if not m:
        raise ValueError('lock header missing or not ' + LOCK_SCHEMA)
    pins = {}
    for line in text.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, _, version = line.partition('==')
        if not version or _norm(name) in pins:
            raise ValueError(f'bad lock line: {line!r}')
        pins[_norm(name)] = version
    return {'python': m.group(1), 'platform': m.group(2), 'pins': pins}


def _verify_tree(base, package_dirs, owned):
    """Every file under a distribution's directories must be owned by a locked distribution,
    except __pycache__ bytecode of an owned source (made inert by bytecode_problems); no
    symlinks. Catches modules dropped in for optional imports. Returns problems."""
    problems = []
    for top in package_dirs:
        root = base / top
        if not root.is_dir():
            continue
        for p in root.rglob('*'):
            rel = p.relative_to(base).as_posix()
            if p.is_symlink():
                problems.append(f'symlink inside a locked distribution: {rel}'); continue
            if p.is_dir() or rel in owned:
                continue
            if p.parent.name == '__pycache__' and p.name.endswith('.pyc'):
                try:
                    source = Path(importlib.util.source_from_cache(str(p)))
                except ValueError:
                    problems.append(f'unrecognised bytecode file {rel}'); continue
                src_rel = source.relative_to(base).as_posix() if source.is_relative_to(base) else None
                if src_rel not in owned:
                    problems.append(f'bytecode without an owned source: {rel}')
                continue
            problems.append(f'file not owned by the locked distribution: {rel}')
    return problems


def bytecode_problems(site_dirs):
    """Compiled bytecode cannot be verified without deserializing it, and Python trusts a
    .pyc whose header matches its source. So site-packages bytecode must be INERT: the
    interpreter must read and write bytecode under a private PYTHONPYCACHEPREFIX outside the
    site directories (then every import compiles from the verified source)."""
    prefix = sys.pycache_prefix
    if not prefix:
        return ['compiled bytecode in site-packages would be loaded unverified: run with PYTHONPYCACHEPREFIX '
                'set to a private directory (the supported runtime does)']
    p = Path(prefix).resolve()
    out = []
    if any(p.is_relative_to(Path(s)) for s in site_dirs):
        out.append('PYTHONPYCACHEPREFIX lies inside a site directory')
    for q in [p, *p.parents]:
        if q.exists():
            st = q.stat()
            if q == p and st.st_uid != os.geteuid():
                out.append('PYTHONPYCACHEPREFIX is not owned by this account')
            if st.st_mode & 0o002 and not st.st_mode & 0o1000:
                out.append(f'PYTHONPYCACHEPREFIX path {q} is world-writable without the sticky bit')
            if q == p and st.st_mode & 0o022:
                out.append('PYTHONPYCACHEPREFIX is group- or world-writable')
            break
    return out


def check_lock(lock_text=None, fingerprints=None, *, bytecode=True):  # noqa: C901
    """Compare the running interpreter and the INSTALLED BYTES of every locked distribution
    with the lock (B15-REV-01): each file of the per-file manifest must exist with the same
    size and SHA-256; RECORD may not list files the manifest lacks; no unowned file may sit
    in a distribution's directories; site-packages bytecode must be inert (private
    PYTHONPYCACHEPREFIX); each top-level import must resolve to a file the distribution owns; start-up
    hooks (.pth, sitecustomize) must be the recorded ones."""
    lock = parse_lock(lock_text if lock_text is not None else LOCK_PATH.read_text())
    fps = fingerprints if fingerprints is not None else json.loads(FINGERPRINTS_PATH.read_text())
    problems = []
    vi = sys.version_info
    if f'{vi.major}.{vi.minor}' != lock['python']:
        problems.append(f"python {vi.major}.{vi.minor} != locked {lock['python']}")
    if fps.get('python') != lock['python']:
        problems.append('fingerprints were generated for a different python than the lock')
    if set(fps.get('distributions', {})) != set(lock['pins']):
        problems.append('fingerprints and lock name different distributions')
    found = {}
    owned_by_base = {}          # files owned by ANY locked distribution, per site directory
    for name in lock['pins']:
        try:
            d = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        owned_by_base.setdefault(Path(d.locate_file('')).resolve(), set()).update(
            (fps.get('distributions', {}).get(name, {}).get('files') or {}))
    for name, version in lock['pins'].items():
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            problems.append(f'{name}: not installed'); continue
        found[name] = dist
        if dist.version != version:
            problems.append(f'{name}: installed {dist.version} != locked {version}'); continue
        fp = fps.get('distributions', {}).get(name, {})
        if fp.get('version') != version:
            problems.append(f'{name}: fingerprint is for version {fp.get("version")}'); continue
        base = Path(dist.locate_file('')).resolve()
        if content_fingerprint(dist) != fp.get('content_sha256'):
            problems.append(f'{name}: installed bytes differ from the locked content')
        manifest = fp.get('files')
        if manifest is None:
            problems.append(f'{name}: fingerprint has no per-file manifest (regenerate the lock)')
            manifest = {}
        else:
            entries, _, record_problems = record_entries(dist)
            problems += [f'{name}: {p}' for p in record_problems]
            for path in sorted(set(entries) - set(manifest)):
                problems.append(f'{name}: RECORD lists a file the lock does not: {path}')
            for path, want in sorted(manifest.items()):
                if _unsafe(path):
                    problems.append(f'{name}: unsafe manifest path {path!r}'); continue
                target = base / path
                if target.is_symlink() or not target.is_file():
                    problems.append(f'{name}: missing installed file {path}'); continue
                if not target.resolve().is_relative_to(base):
                    problems.append(f'{name}: {path} resolves outside the site directory'); continue
                actual, size = _file_sha256(target)
                if size != want['size'] or actual != want['sha256']:
                    problems.append(f'{name}: installed file changed: {path}')
            problems += [f'{name}: {p}' for p in
                         _verify_tree(base, _package_dirs(manifest), owned_by_base.get(base, set()))]
        for top in fp.get('top_level', []):
            spec = importlib.util.find_spec(top)
            if spec is None:
                problems.append(f'{name}: top-level {top} not importable'); continue
            if spec.origin not in (None, 'namespace'):
                origin = Path(spec.origin).resolve()
                rel = origin.relative_to(base).as_posix() if origin.is_relative_to(base) else None
                if rel not in manifest:
                    problems.append(f'{name}: {top} is imported from {spec.origin}, a file the locked '
                                    f'distribution does not own')
            else:
                for loc in spec.submodule_search_locations or []:
                    if not Path(loc).resolve().is_relative_to(base):
                        problems.append(f'{name}: namespace {top} includes {loc}, outside the locked distribution')
    if bytecode:
        problems += bytecode_problems(_site_dirs(found))
    recorded_hooks = fps.get('startup_hooks')
    if recorded_hooks is None:
        problems.append('fingerprints do not record start-up hooks (regenerate the lock)')
    else:
        current = startup_hooks(_site_dirs(found))
        for path in sorted(set(current) | set(recorded_hooks)):
            if current.get(path) != recorded_hooks.get(path):
                problems.append(f'start-up hook differs from the lock: {path}')
    # pyproject ranges must admit the pins (one source of truth for versions).
    from packaging.requirements import Requirement
    deps, requires_python = project_dependencies()
    for r in deps:
        req = Requirement(r)
        pinned = lock['pins'].get(_norm(req.name))
        if pinned is None:
            problems.append(f'{req.name}: pyproject dependency missing from the lock')
        elif not req.specifier.contains(pinned, prereleases=True):
            problems.append(f'{req.name}: locked {pinned} outside pyproject range {req.specifier}')
    if requires_python:
        from packaging.specifiers import SpecifierSet
        if not SpecifierSet(requires_python).contains(f"{lock['python']}.0"):
            problems.append(f"lock python {lock['python']} outside requires-python {requires_python}")
    return {'ok': not problems, 'problems': problems, 'locked': len(lock['pins'])}


# ---------------------------------------------------------------- host checks

def _version_tuple(text):
    return tuple(int(x) for x in re.findall(r'\d+', text)[:3])


def _mounts(path='/proc/mounts'):
    out = []
    try:
        for line in Path(path).read_text().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                out.append((parts[1].replace('\\040', ' '), parts[2], parts[3].split(',')))
    except OSError:
        pass
    return out


def filesystem_type(path, mounts=None):
    path = str(Path(path).resolve())
    best = ('', None)
    for point, fstype, _ in mounts if mounts is not None else _mounts():
        if (path == point or path.startswith(point.rstrip('/') + '/')) and len(point) >= len(best[0]):
            best = (point, fstype)
    return best[1]


def cgroup_layout(mounts=None, root='/sys/fs/cgroup'):
    """Return ('v1', controllers) / ('v2', controllers) / (None, [])."""
    mounts = mounts if mounts is not None else _mounts()
    v1 = sorted({opt for point, fstype, opts in mounts if fstype == 'cgroup'
                 for opt in opts if opt in ('cpu', 'cpuacct', 'memory', 'pids', 'devices', 'freezer')})
    if v1:
        return 'v1', v1
    for point, fstype, _ in mounts:
        if fstype == 'cgroup2' and point == root:
            try:
                return 'v2', sorted((Path(root) / 'cgroup.controllers').read_text().split())
            except OSError:
                return 'v2', []
    return None, []


def _check(name, ok, observed, required, *, mandatory=True):
    status = 'UNVERIFIED' if ok is None else ('PASS' if ok else 'FAIL')
    return {'check': name, 'status': status, 'observed': observed, 'required': required, 'mandatory': mandatory}


def platform_report(spec=None, *, store_root=None, toolchain=None, mounts=None):
    spec = spec or json.loads(SPEC_PATH.read_text())
    req = spec['requirements']
    checks = []
    checks.append(_check('os', platform.system() == req['os'], platform.system(), req['os']))
    checks.append(_check('machine', platform.machine() == req['machine'], platform.machine(), req['machine']))
    pyver = f'{sys.version_info.major}.{sys.version_info.minor}'
    checks.append(_check('python', pyver == req['python'] and platform.python_implementation() == req['implementation'],
                         f'{platform.python_implementation()} {platform.python_version()}',
                         f"{req['implementation']} {req['python']}.x"))
    kernel = platform.release()
    checks.append(_check('kernel', _version_tuple(kernel) >= _version_tuple(req['kernel_min']), kernel,
                         '>= ' + req['kernel_min']))
    libc = platform.libc_ver()
    checks.append(_check('glibc', libc[0] == 'glibc' and _version_tuple(libc[1]) >= _version_tuple(req['glibc_min']),
                         '-'.join(libc), '>= ' + req['glibc_min']))
    try:
        lock = check_lock()
        checks.append(_check('dependency_lock', lock['ok'], lock['problems'] or f"{lock['locked']} pins match",
                             'installed distributions equal requirements.lock'))
    except (OSError, ValueError) as exc:
        checks.append(_check('dependency_lock', False, f'{type(exc).__name__}: {exc}', 'readable lock'))
    runc = shutil.which('runc')
    rv = None
    if runc:
        try:
            rv = subprocess.run([runc, '--version'], capture_output=True, text=True, timeout=10).stdout.split('\n')[0]
        except (OSError, subprocess.SubprocessError):
            rv = None
    checks.append(_check('runc', bool(rv) and _version_tuple(rv) >= _version_tuple(req['runc_min']), rv,
                         '>= ' + req['runc_min']))
    layout, controllers = cgroup_layout(mounts)
    needed = req['cgroup_controllers'].get(layout or '', None)
    checks.append(_check('cgroup', None if needed is None else set(needed) <= set(controllers),
                         {'layout': layout, 'controllers': controllers}, req['cgroup_controllers']))
    try:
        seccomp = 'Seccomp:' in Path('/proc/self/status').read_text()
    except OSError:
        seccomp = False
    checks.append(_check('seccomp', seccomp, seccomp, True))
    if store_root is not None:
        fs = filesystem_type(store_root, mounts)
        checks.append(_check('store_filesystem', fs in req['store_filesystems'], fs, req['store_filesystems']))
    tool_root = Path(toolchain or os.environ.get('GENESIS_TOOLCHAIN') or Path.home() / 'toolchain')
    pins = json.loads((REPO / 'toolchain' / 'PINS.json').read_text())
    bad = []
    for name, pin in pins.items():
        if 'binary' in pin:
            p = tool_root / pin['binary']
            actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
            if actual != pin['binary_sha256']:
                bad.append(f'{name}: {actual}')
    checks.append(_check('toolchain_pins', not bad, bad or 'all pinned binaries match', 'PINS.json binary hashes'))
    history = check_pins_history(pins)
    checks.append(_check('toolchain_pin_history', not history, history or 'PINS.json is the last recorded revision',
                         'hash-chained PINS_HISTORY.jsonl'))
    fault = os.environ.get('GENESIS_FAULT')
    checks.append(_check('fault_injection_disabled', not fault, fault or 'unset', 'GENESIS_FAULT unset'))
    failed = [c['check'] for c in checks if c['mandatory'] and c['status'] == 'FAIL']
    unverified = [c['check'] for c in checks if c['mandatory'] and c['status'] == 'UNVERIFIED']
    verdict = 'UNSUPPORTED' if failed else ('UNVERIFIED' if unverified else 'SUPPORTED')
    return {'schema': 'genesis-platform-report-v1', 'spec': spec['schema'], 'verdict': verdict,
            'failed': failed, 'unverified': unverified, 'checks': checks,
            'host': {'node_sha256': hashlib.sha256(platform.node().encode()).hexdigest()[:16],
                     'platform': platform.platform()}}


# ---------------------------------------------------------------- toolchain pin revisions

PINS_PATH = REPO / 'toolchain' / 'PINS.json'
HISTORY_PATH = REPO / 'toolchain' / 'PINS_HISTORY.jsonl'
RECIPE_PATH = REPO / 'toolchain' / 'build_reproducible.sh'


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def pins_diff(old, new):
    out = []
    for tool in sorted(set(old) | set(new)):
        a, b = old.get(tool), new.get(tool)
        if not isinstance(a, dict) or not isinstance(b, dict):
            if a != b:
                out.append({'tool': tool, 'field': None, 'old': a, 'new': b})
            continue
        for field in sorted(set(a) | set(b)):
            if a.get(field) != b.get(field):
                out.append({'tool': tool, 'field': field, 'old': a.get(field), 'new': b.get(field)})
    return out


def read_history(path=None):
    lines = (path or HISTORY_PATH).read_bytes().split(b'\n')
    if lines[-1] != b'':
        raise ValueError('pin history does not end with a newline')
    return [(line, json.loads(line)) for line in lines[:-1]]


def check_pins_history(pins=None, history=None, *, check_recipe=True):
    """The current PINS.json must be the last entry of an intact, hash-chained
    revision history in which every binary change came with passing known answers
    for exactly the new binaries. Returns a list of problems (empty = consistent)."""
    problems = []
    pins = pins if pins is not None else json.loads(PINS_PATH.read_text())
    try:
        entries = history if history is not None else read_history()
    except (OSError, ValueError) as exc:
        return [f'pin history unreadable: {exc}']
    if not entries:
        return ['pin history is empty']
    prev_hash, prev_pins = None, None
    for i, (raw, e) in enumerate(entries, 1):
        if raw != _canon(e):
            problems.append(f'entry {i} is not canonical JSON')
        if e.get('seq') != i or e.get('prev') != prev_hash:
            problems.append(f'entry {i} breaks the chain')
        if e.get('pins_sha256') != hashlib.sha256(_canon(e.get('pins'))).hexdigest():
            problems.append(f'entry {i} pins hash mismatch')
        if not isinstance(e.get('reason'), str) or not e['reason'].strip():
            problems.append(f'entry {i} has no reason')
        if prev_pins is not None:
            changes = pins_diff(prev_pins, e['pins'])
            if e.get('changes') != changes:
                problems.append(f'entry {i} changes do not match the pins it records')
            if not changes:
                problems.append(f'entry {i} changes nothing')
            changed = {c['tool'] for c in changes if c['field'] in ('binary_sha256', 'binary', 'commit')}
            ka = e.get('known_answers')
            if changed:
                if not isinstance(ka, dict) or ka.get('ok') is not True:
                    problems.append(f'entry {i} changes binaries without passing known answers')
                else:
                    for tool in changed:
                        if ka.get('binaries', {}).get(tool) != e['pins'][tool].get('binary_sha256'):
                            problems.append(f'entry {i}: known answers did not run the new {tool} binary')
            retired = sorted(c['old'] for c in changes if c['field'] == 'binary_sha256' and c['old'])
            if e.get('retired_anchors') != retired:
                problems.append(f'entry {i} must list the anchors it retires')
        prev_hash, prev_pins = hashlib.sha256(raw).hexdigest(), e.get('pins')
    if prev_pins != pins:
        problems.append('PINS.json differs from the last recorded revision (edit pins only via toolchain/revise_pins.py)')
    recipe = (pins.get('built_with') or {}).get('recipe_sha256')
    if check_recipe and recipe is not None and RECIPE_PATH.exists() and \
            recipe != hashlib.sha256(RECIPE_PATH.read_bytes()).hexdigest():
        problems.append('build_reproducible.sh changed after the pins were recorded; revise the pins')
    return problems


def history_entry(entries, new_pins, *, reason, known_answers=None, build_record=None, recorded_at=None):
    prev_raw, prev = entries[-1] if entries else (None, None)
    changes = pins_diff(prev['pins'], new_pins) if prev else []
    entry = {'seq': len(entries) + 1, 'prev': hashlib.sha256(prev_raw).hexdigest() if prev_raw else None,
             'pins_sha256': hashlib.sha256(_canon(new_pins)).hexdigest(), 'pins': new_pins, 'changes': changes,
             'retired_anchors': sorted(c['old'] for c in changes if c['field'] == 'binary_sha256' and c['old']),
             'reason': reason, 'known_answers': known_answers, 'build_record': build_record,
             'recorded_at': recorded_at}
    return _canon(entry), entry
