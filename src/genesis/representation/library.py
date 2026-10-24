"""The representation library: verified representations, preserved exactly, with lineage, announced as capabilities
(directive items 7-8).

**Library values.** A library is an immutable JSON value {'schema', 'parent', 'entries'}; `register` returns a new
library whose `parent` is the old one's version (its content digest), so every version names its predecessor and an
earlier version is still a value one can return to (rollback is using it). An entry is keyed by its relation's orbit
(`Relation.id`: renaming and negating variables), so one gadget serves the whole orbit (`lookup` transports it);
each orbit keeps two slots, the best exact gadget and the best uniform one.

**Admission.** `register` admits a gadget only if `gadgets.check` (exhaustive enumeration, independent of whatever
synthesised it) says it is exact; an slot is replaced only by a gadget with fewer ancillas, or as many and fewer
non-zero coefficients (an improvement). The lineage (synthesiser, its parameters, parents) is kept in the entry.

**The vault** (`archive`, `announce`, `park`, `cascade`):
  * `archive` stores an entry exactly as a WorldSpec artifact (`content.kind = 'gadget'`), with its certificate, and
    marks it `reproducible` (its correctness is an exhaustive check anyone can repeat); `verified` and `promoted`
    stay for recorded studies (the vault enforces it).
  * `announce` stores a CapabilityRecord unlocking `relation:<orbit id>`, with the representation as its parent.
  * `park` stores a ProblemSpec that could not be compiled as `dormant` with a `failed_due_to` edge to the tag of
    the relation it lacked (failure kind `missing_prerequisite`).
  * `cascade` runs the vault's cascade from announced capabilities: dormant problems waiting for those relations are
    reactivated (at most `fuel` per trigger, `depth` levels, never twice by the same trigger) and re-tested by the
    caller's function. Unexplained representations are archived like any other: explanation stays `unknown`.
"""
import copy

from ..common import digest
from . import gadgets as GD
from .relations import Relation, relation_from_json

SCHEMA = 'genesis-representation-library-v1'
EMPTY = {'schema': SCHEMA, 'parent': None, 'entries': {}}


def version(lib):
    return digest(lib)[:16]


def _better(new, old):
    return old is None or (new['ancillas'], new['nonzero']) < (old['ancillas'], old['nonzero'])


def register(lib, rel, gadget, lineage):
    """A new library with the gadget for rel's orbit; ValueError if it is not exact or improves neither slot. Each
    orbit has two slots: the best exact gadget, and the best uniform one (every violation costs exactly the gap, so
    sums count violated constraints)."""
    ver = GD.check(gadget, rel)
    if not ver['exact']:
        raise ValueError(f'not exact: {ver["violations"][:3]}')
    if not GD.check_matrix(gadget, rel):
        raise ValueError('the second checker disagrees')
    key = rel.id()
    nonzero, largest = gadget.size()
    entry = {'relation': rel.to_json(), 'relation_id': key, 'gadget': gadget.to_json(), 'gap': ver['gap'],
             'uniform': ver['uniform'], 'ancillas': gadget.m, 'nonzero': nonzero, 'largest': largest,
             'lineage': copy.deepcopy(lineage)}
    slots = dict(lib['entries'].get(key, {'exact': None, 'uniform': None}))
    changed = False
    if _better(entry, slots['exact']):
        slots['exact'], changed = entry, True
    if ver['uniform'] and _better(entry, slots['uniform']):
        slots['uniform'], changed = entry, True
    if not changed:
        raise ValueError('not an improvement on the entries for this relation')
    new = {'schema': SCHEMA, 'parent': version(lib), 'entries': dict(lib['entries'])}
    new['entries'][key] = slots
    return new


def entry(lib, rel, uniform=False):
    """The library's entry for rel's orbit (the uniform slot if `uniform`), or None."""
    slots = lib['entries'].get(rel.id())
    if slots is None:
        return None
    return slots['uniform'] if uniform else slots['exact']


def lookup(lib, rel, uniform=False):
    """An exact gadget for rel (uniform if asked), transported from its orbit's entry, or None."""
    e = entry(lib, rel, uniform)
    if e is None:
        return None
    src = relation_from_json(e['relation'])
    g = GD.Gadget.from_json(e['gadget'])
    c1, (p1, f1) = src.canonical()
    c2, (p2, f2) = rel.canonical()
    g_canon = GD.transport(g, src, p1, f1)
    ip, iflips = inverse(p2, f2, rel.k)
    out = GD.transport(g_canon, c1, ip, iflips)
    if not GD.check(out, rel)['exact']:                    # never trust the transport blindly
        raise AssertionError('transport broke exactness')
    return out


def inverse(perm, flips, k):
    """(perm', flips') with r.transform(perm, flips).transform(perm', flips') == r."""
    ip = [0] * k
    for j, p in enumerate(perm):
        ip[p] = j
    f = 0
    for j in range(k):
        if flips >> perm[j] & 1:
            f |= 1 << j
    return ip, f


def supports(lib, rel, uniform=False):
    return entry(lib, rel, uniform) is not None


# ----------------------------------------------------------------------------------------------- the vault

def archive(vault, lib, rel, creator, parents=(), domain='representation'):
    """Store rel's entry exactly (a WorldSpec) and mark it reproducible; returns the artifact ID."""
    e = entry(lib, rel)
    rec = vault.record('WorldSpec', {'kind': 'gadget', 'entry': e, 'library': version(lib)}, domain=domain,
                       creator=creator, parents=parents, contracts={'exact': True, 'gap': e['gap'],
                                                                     'checker': 'gadgets.check and check_matrix'},
                       costs=e['lineage'].get('cost'))
    aid = vault.put(rec, status='generated')
    st = vault.status(aid)['status']
    if st == 'generated':
        vault.annotate(aid, status='exploratory', reason='admitted to the representation library')
        vault.annotate(aid, status='reproducible', reason='exact by exhaustive check (two checkers)')
    return aid


def announce(vault, rel, rep_aid, creator='representation-library'):
    """A CapabilityRecord unlocking relation:<orbit id>, with the representation as parent; returns its ID."""
    rec = vault.record('CapabilityRecord', {'name': f'gadget for relation {rel.id()}',
                                            'unlocks': [f'relation:{rel.id()}']},
                       domain='representation', creator=creator, parents=[rep_aid])
    aid = vault.put(rec, status='generated')
    if vault.status(aid)['status'] == 'generated':
        vault.annotate(aid, status='exploratory', reason='announced by the representation library')
        vault.annotate(aid, status='reproducible', reason='its representation is exact by exhaustive check')
    return aid


def park(vault, problem, missing, creator, score=None, domain='problems'):
    """Store a problem that could not be compiled as dormant, failed_due_to tag:relation:<id> for each missing
    relation; returns its ID."""
    rec = vault.record('ProblemSpec', problem, domain=domain, creator=creator)
    aid = vault.put(rec, status='generated')
    if vault.status(aid)['status'] == 'generated':
        vault.annotate(aid, status='dormant', failure='missing_prerequisite',
                       reason='no exact representation for ' + ', '.join(r.id() for r in missing))
        for r in missing:
            vault.edge('failed_due_to', aid, f'tag:relation:{r.id()}', confidence=1.0, scope='compilation',
                       provenance={'by': creator}, score=score)
    return aid


def cascade(vault, triggers, retest, fuel, depth=2):
    return vault.cascade(triggers, retest, fuel, depth)


__all__ = ['SCHEMA', 'EMPTY', 'version', 'register', 'entry', 'lookup', 'inverse', 'supports', 'archive', 'announce', 'park',
           'cascade']
