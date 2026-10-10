"""Custodian-side exposure registry: every host graph that research could have seen.

The registry is built by the custodian from raw sources — public campaign stores
and exports, JSON corpora, and re-executed legacy generators — never from a
builder-supplied list of fingerprints. Membership is exact graph isomorphism
after removing isolated vertices (they cannot change an optimum), using a
Weisfeiler-Lehman bucket plus a VF2 isomorphism test, so it works for every
host size the domains allow (n <= 63), including highly symmetric hosts.

Near duplicates are graphs one edge toggle away from an exposed graph. They are
not silently allowed: the custodian must store an adjudication first.
"""
from dataclasses import dataclass, field
import hashlib
import importlib
import json
from pathlib import Path
import sys
import zipfile

import networkx as nx

from .common import canonical, digest

MAX_SOURCE_BYTES = 256 * 1024 * 1024


def strip_isolated(n, edges):
    """Return (k, edges) relabelled onto the non-isolated vertices, order-preserving."""
    used = sorted({v for e in edges for v in e})
    mapping = {v: i for i, v in enumerate(used)}
    return len(used), tuple(sorted((min(mapping[u], mapping[v]), max(mapping[u], mapping[v])) for u, v in edges))


def _graph(k, edges):
    g = nx.Graph()
    g.add_nodes_from(range(k))
    g.add_edges_from(edges)
    return g


def wl_hash(k, edges):
    return nx.weisfeiler_lehman_graph_hash(_graph(k, edges), iterations=4) + f':{k}:{len(edges)}'


def _as_host(obj):
    """Interpret a JSON object as a host graph if it clearly is one."""
    if not isinstance(obj, dict):
        return None
    edges = obj.get('edges', obj.get('host'))
    n = obj.get('n')
    if type(n) is not int or not 0 <= n <= 63 or not isinstance(edges, (list, tuple)):
        return None
    out = set()
    for e in edges:
        if not isinstance(e, (list, tuple)) or len(e) != 2:
            return None
        u, v = e
        if type(u) is not int or type(v) is not int or not (0 <= u < n and 0 <= v < n) or u == v:
            return None
        out.add((min(u, v), max(u, v)))
    return n, tuple(sorted(out))


def extract_hosts(value, limit=1_000_000):
    """Walk a JSON value and yield every embedded host graph."""
    stack = [value]
    seen = 0
    while stack:
        x = stack.pop()
        seen += 1
        if seen > limit:
            raise ValueError('JSON structure too large to screen; adjudicate externally')
        host = _as_host(x)
        if host is not None:
            yield host
        if isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)


@dataclass
class GraphIndex:
    buckets: dict = field(default_factory=dict)  # wl -> list[(k, edges, source)]
    count: int = 0

    def add(self, n, edges, source):
        k, es = strip_isolated(n, edges)
        bucket = self.buckets.setdefault(wl_hash(k, es), [])
        for k2, es2, _ in bucket:
            if k2 == k and (es2 == es or nx.is_isomorphic(_graph(k, es), _graph(k2, es2))):
                return False
        bucket.append((k, es, source))
        self.count += 1
        return True

    def find(self, n, edges):
        k, es = strip_isolated(n, edges)
        for k2, es2, source in self.buckets.get(wl_hash(k, es), ()):
            if k2 == k and (es2 == es or nx.is_isomorphic(_graph(k, es), _graph(k2, es2))):
                return source
        return None

    def near(self, n, edges):
        """Sources of exposed graphs exactly one edge toggle away (same vertex set)."""
        es = set(edges)
        hits = []
        for u in range(n):
            for v in range(u + 1, n):
                toggled = tuple(sorted(es ^ {(u, v)}))
                source = self.find(n, toggled)
                if source is not None:
                    hits.append({'toggle': [u, v], 'source': source})
        return hits

    def items(self):
        for bucket in self.buckets.values():
            yield from bucket


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def ingest_json_bytes(index, data, source):
    try:
        value = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return 0
    return sum(index.add(n, es, source) for n, es in extract_hosts(value))


def ingest_campaign_store(index, root, label):
    root = Path(root)
    objects = root / 'objects' / 'sha256'
    if not objects.is_dir():
        raise ValueError(f'not a campaign store: {root}')
    added = 0
    names = []
    for path in sorted(objects.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError('unexpected object in campaign store')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != path.name:
            raise ValueError('corrupt campaign object; cannot build a trustworthy registry')
        names.append(path.name)
        added += ingest_json_bytes(index, data, label)
    return added, digest(names)


def ingest_zip(index, path, label):
    added = 0
    with zipfile.ZipFile(path) as z:
        total = sum(i.file_size for i in z.infolist())
        if total > MAX_SOURCE_BYTES:
            raise ValueError('export too large to screen')
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.filename.endswith('.json') or '/objects/sha256/' in '/' + info.filename:
                added += ingest_json_bytes(index, z.read(info), label)
    return added, _file_digest(path)


def ingest_legacy_generator(index, repo_root, module, function, kwargs, label):
    """Re-run a legacy public generator (imports confined to legacy_batch42)."""
    directory = str(Path(repo_root) / 'legacy_batch42')
    sys.path.insert(0, directory)
    try:
        mod = importlib.import_module(module)
        cases = getattr(mod, function)(**kwargs)
    finally:
        sys.path.remove(directory)
    added = 0
    for case in cases:
        host = case.get('host', case.get('edges'))
        added += index.add(case['n'], tuple(tuple(e) for e in host), label)
    return added, digest({'module': module, 'function': function, 'kwargs': kwargs,
                          'cases': [[c['n'], [list(e) for e in c.get('host', c.get('edges'))]] for c in cases]})


def build_registry(manifest, base, repo_root, extra_sources=()):
    """Build a GraphIndex from a custodian-owned manifest. Missing sources fail closed."""
    if not isinstance(manifest, dict) or manifest.get('schema') != 'genesis-exposure-manifest-v1':
        raise ValueError('exposure manifest schema')
    index = GraphIndex()
    record = []
    for entry in list(manifest['sources']) + list(extra_sources):
        kind = entry['kind']
        label = entry.get('label') or f"{kind}:{entry.get('path', entry.get('function'))}"
        if kind == 'campaign_store':
            added, h = ingest_campaign_store(index, Path(base) / entry['path'], label)
        elif kind == 'json':
            path = Path(base) / entry['path']
            added, h = ingest_json_bytes(index, path.read_bytes(), label), _file_digest(path)
        elif kind == 'zip':
            added, h = ingest_zip(index, Path(base) / entry['path'], label)
        elif kind == 'legacy_generator':
            added, h = ingest_legacy_generator(index, repo_root, entry['module'], entry['function'],
                                               entry['kwargs'], label)
        elif kind == 'ladder':
            from .ladder import ladder_task
            added = 0
            for d in entry['domains']:
                for n in range(1, entry['max_n'] + 1):
                    t = ladder_task(d, n)
                    added += index.add(t.n, t.edges, label)
            h = digest(entry)
        else:
            raise ValueError(f'unknown exposure source kind {kind}')
        record.append({'label': label, 'kind': kind, 'content_sha256': h, 'new_graphs': added})
    return index, {'sources': record, 'graphs': index.count, 'root': digest(record)}


def campaign_hosts(export_zip):
    """Every host graph present in one campaign export, as stored (isolated vertices kept)."""
    hosts = set()
    with zipfile.ZipFile(export_zip) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_SOURCE_BYTES:
            raise ValueError('export too large to screen')
        for info in z.infolist():
            if info.is_dir() or not (info.filename.endswith('.json') or '/objects/sha256/' in '/' + info.filename):
                continue
            try:
                value = json.loads(z.read(info))
            except (ValueError, UnicodeDecodeError):
                continue
            hosts.update(extract_hosts(value))
    return sorted(hosts)
