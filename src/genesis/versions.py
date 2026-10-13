"""Active version, rollback and version revocation (handoff H08, s20.6).

The campaign freezes every SystemVersion it produces (``system_version`` entities, id = content
digest, ``parent`` edge). This module adds the pointer that says which frozen version is in use and
the records that change it. Everything is append-only in the campaign store:

  active_pointer      entity per change, id ``p{seq:06}``: {seq, version, previous, kind, reason,
                      actor}; kind ACTIVATE (forward, to a descendant of the active version, or the
                      first activation) or ROLLBACK (back, to an ancestor). State ``active_version``
                      mirrors the last record and is written in the same transaction.
  version_revocation  entity per revoked version: {version, reason, actor}.

Rules (each refusal raises VersionError with a stable code):
  * only a stored, content-addressed version whose parent chain reaches the initial version is
    ever active (VERSION_MISSING, VERSION_ID_MISMATCH, BROKEN_CHAIN);
  * neither it nor an ancestor may be revoked (REVOKED);
  * a move is forward (ACTIVATE) or back (ROLLBACK); a sideways switch is refused (NOT_ON_PATH):
    roll back to the common ancestor first, so each change is its own recorded decision;
  * a reason and an actor are required for every change (UNEXPLAINED);
  * rollback never erases: the version rolled away from stays stored and is reported ROLLED_BACK;
  * revoking a version makes every descendant REVOKED_ANCESTOR; if that reaches the active version,
    the pointer is INVALID and ``resume_problems`` reports it until a rollback to a valid ancestor.

``status`` recomputes every version's state from these records on each call (nothing cached), and
``dependent_nodes`` finds the evidence-kernel nodes that name an affected version so a caller can
revoke them and let the kernel recompute effective claims (``revoke(..., kernel=...)``).
"""
from .common import digest

POINTER = 'active_pointer'
REVOCATION = 'version_revocation'
KINDS = ('ACTIVATE', 'ROLLBACK')
STATUSES = ('ACTIVE', 'RETAINED', 'ROLLED_BACK', 'REVOKED', 'REVOKED_ANCESTOR', 'INACTIVE')


class VersionError(ValueError):
    def __init__(self, code, detail=''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code


def _entities(store, kind):
    rows = store.db.execute('SELECT id,object_hash FROM entities WHERE kind=? ORDER BY id', (kind,)).fetchall()
    return {i: store.get(h) for i, h in rows}


def versions(store):
    """{version_id: SystemVersion dict} as stored."""
    return _entities(store, 'system_version')


def pointer_history(store):
    return [r for _, r in sorted(_entities(store, POINTER).items())]


def revoked(store):
    return {v: r for v, r in _entities(store, REVOCATION).items()}


def active(store):
    hist = pointer_history(store)
    return hist[-1]['version'] if hist else None


def ancestors(vs, vid):
    """[parent, grandparent, ..., initial] of ``vid``; raises on a missing or cyclic chain."""
    out, seen, cur = [], {vid}, vs[vid].get('parent')
    while cur is not None:
        if cur not in vs:
            raise VersionError('BROKEN_CHAIN', f'{vid[:12]} has a missing ancestor {cur[:12]}')
        if cur in seen:
            raise VersionError('BROKEN_CHAIN', f'cycle at {cur[:12]}')
        seen.add(cur); out.append(cur); cur = vs[cur].get('parent')
    return out


def descendants(vs, vid):
    children = {}
    for v, doc in vs.items():
        children.setdefault(doc.get('parent'), []).append(v)
    out, stack = set(), [vid]
    while stack:
        for c in children.get(stack.pop(), ()):
            if c not in out:
                out.add(c); stack.append(c)
    return out


def _check_target(store, vs, vid):
    if vid not in vs:
        raise VersionError('VERSION_MISSING', vid[:12] if isinstance(vid, str) else repr(vid))
    if digest(vs[vid]) != vid:
        raise VersionError('VERSION_ID_MISMATCH', vid[:12])
    chain = ancestors(vs, vid)
    dead = set(revoked(store))
    hit = [v for v in [vid] + chain if v in dead]
    if hit:
        raise VersionError('REVOKED', f'{vid[:12]} or its ancestor {hit[0][:12]} is revoked')
    return chain


def pointer_change(store, vid, *, reason, actor):
    """(entities, states) that move the pointer to ``vid``; for one atomic ``commit_batch`` together
    with the caller's own records (the campaign's generation commit). Raises VersionError."""
    if not isinstance(reason, str) or not reason.strip() or not isinstance(actor, str) or not actor.strip():
        raise VersionError('UNEXPLAINED', 'every pointer change records a reason and an actor')
    vs = versions(store)
    chain = _check_target(store, vs, vid)
    hist = pointer_history(store)
    current = hist[-1]['version'] if hist else None
    if current == vid:
        return [], []
    if current is None or current in chain:
        kind = 'ACTIVATE'
    elif current in vs and vid in ancestors(vs, current):
        kind = 'ROLLBACK'
    else:
        raise VersionError('NOT_ON_PATH', f'{vid[:12]} is neither a descendant nor an ancestor of the active '
                                          f'version {current[:12]}; roll back to the common ancestor first')
    rec = {'seq': len(hist), 'version': vid, 'previous': current, 'kind': kind, 'reason': reason, 'actor': actor}
    return [(POINTER, f'p{len(hist):06}', rec)], [('active_version', vid)]


def activate(store, vid, *, reason, actor):
    entities, states = pointer_change(store, vid, reason=reason, actor=actor)
    if entities:
        store.commit_batch(entities=entities, states=states)
    return entities[0][2] if entities else None


rollback = activate      # a move back is the same recorded pointer change; its kind says ROLLBACK


def revoke(store, vid, *, reason, actor, kernel=None):
    """Record ``vid`` as revoked (its descendants inherit it). With ``kernel``, also revoke every
    kernel node that names an affected version, so effective claims are recomputed. Returns the
    affected versions."""
    vs = versions(store)
    if vid not in vs:
        raise VersionError('VERSION_MISSING', vid[:12])
    if not isinstance(reason, str) or not reason.strip() or not isinstance(actor, str) or not actor.strip():
        raise VersionError('UNEXPLAINED', 'a revocation records a reason and an actor')
    if vid not in revoked(store):
        store.save(REVOCATION, vid, {'version': vid, 'reason': reason, 'actor': actor})
    affected = {vid} | descendants(vs, vid)
    if kernel is not None:
        for nid in dependent_nodes(kernel, affected):
            if nid not in kernel._revoked('node'):
                kernel.revoke(nid, f'depends on revoked version {vid[:12]}: {reason}', actor)
    return sorted(affected)


def status(store):
    """{version_id: one of STATUSES}, recomputed from the stored records."""
    vs = versions(store)
    dead = set(revoked(store))
    act = active(store)
    on_path = set()
    if act in vs:
        try:
            on_path = set(ancestors(vs, act))
        except VersionError:
            on_path = set()
    left = {r['previous'] for r in pointer_history(store) if r['kind'] == 'ROLLBACK' and r['previous']}
    rolled = set()
    for v in left:
        rolled |= {v} | {d for d in descendants(vs, v) if d in left}
    out = {}
    for v in vs:
        try:
            chain = ancestors(vs, v)
        except VersionError:
            chain = []
        if v in dead:
            out[v] = 'REVOKED'
        elif any(a in dead for a in chain):
            out[v] = 'REVOKED_ANCESTOR'
        elif v == act:
            out[v] = 'ACTIVE'
        elif v in on_path:
            out[v] = 'RETAINED'
        elif v in rolled:
            out[v] = 'ROLLED_BACK'
        else:
            out[v] = 'INACTIVE'
    return out


def resume_problems(store, version=None):
    """Why work may not resume from ``version`` (default: the active one). Empty: it may."""
    vid = version if version is not None else active(store)
    if vid is None:
        return []
    try:
        _check_target(store, versions(store), vid)
    except VersionError as exc:
        return [f'INVALID {exc}; roll back to a valid ancestor before resuming']
    return []


def dependent_nodes(kernel, affected):
    """Kernel nodes whose stored payload names one of ``affected`` (keys version, version_id,
    from_version, to_version, parent_version, candidate_version)."""
    keys = ('version', 'version_id', 'from_version', 'to_version', 'parent_version', 'candidate_version')
    affected = set(affected)
    out = []
    for nid in kernel._all_nodes():
        try:
            p = kernel.payload(nid)
        except Exception:
            continue
        if isinstance(p, dict) and any(p.get(k) in affected for k in keys if isinstance(p.get(k), str)):
            out.append(nid)
    return sorted(out)


__all__ = ['VersionError', 'versions', 'pointer_history', 'revoked', 'active', 'ancestors', 'descendants',
           'pointer_change', 'activate', 'rollback', 'revoke', 'status', 'resume_problems', 'dependent_nodes',
           'STATUSES']
