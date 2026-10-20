"""The cell-cycle checkpoint: before a study is preregistered, its declared design is checked against the open caveats,
the cell's own knowledge and the membrane.

A design passes only if
  * for every open caveat in scope, some live response in the library is carried out by the design at full dose and
    is new relative to the study where the caveat was last seen (repeating the design that showed the weakness does
    not answer it), or the design defers the caveat with a reason;
  * a deferral of a high-severity or chronic caveat is 'blocked: ...' (a work order names what is missing), never
    'cost: ...' (the membrane: such caveats are not deferred to save time);
  * the cell's baseline catalog is not stale (`receptors.stale_knowledge`), when a date is given;
  * it crosses no membrane rule that a design can show (validity thresholds no looser than the canonical ones; fresh
    hosts).
"""
from .design import deferrable
from .receptors import stale_knowledge
from .responses import CANONICAL_VALIDITY, RESPONSES


def membrane(design, open_entries=None):
    """Membrane violations visible in a design (the other rules are procedural and checked elsewhere)."""
    out = []
    v = design.get('validity', {})
    if v.get('min_cpu_at_half', CANONICAL_VALIDITY['min_cpu_at_half']) < CANONICAL_VALIDITY['min_cpu_at_half']:
        out.append('validity: min_cpu_at_half looser than 0.45')
    if v.get('max_fail_share', CANONICAL_VALIDITY['max_fail_share']) > CANONICAL_VALIDITY['max_fail_share']:
        out.append('validity: max_fail_share looser than 1%')
    if not design.get('fresh_hosts', False):
        out.append('hosts: the design does not declare fresh hosts')
    for k, reason in (design.get('deferred') or {}).items():
        e = (open_entries or {}).get(k)
        if e and not deferrable(e) and not str(reason).startswith('blocked:'):
            out.append(f'deferral: {k} is {e["severity"]}/{e["status"]} and may only be deferred as blocked, '
                       f'not for "{reason}"')
    return out


def check(design, ledger, scope=None, catalog=None, today=None):
    """{'pass', 'addressed': {key: response}, 'partial': {key: {response: dose}}, 'unaddressed': {key: [responses
    that would address it]}, 'deferred': {key: reason}, 'membrane': [violations]}. `scope` limits the check to
    caveats last seen in these studies."""
    every = ledger.open()
    open_ = {k: e for k, e in every.items() if scope is None or e['study'] in scope}
    addressed, partial, unaddressed, deferred = {}, {}, {}, {}
    for k, e in open_.items():
        if k in (design.get('deferred') or {}):
            deferred[k] = design['deferred'][k]
            continue
        prev = ledger.designs.get(e['study'], {})
        live = [r for r in RESPONSES[e['type']] if r.name not in e.get('retired', ())]
        hit = next((r.name for r in live if r.satisfied(design, e['evidence'])
                    and r.progress(design, e['evidence']) > r.progress(prev, e['evidence'])), None)
        if hit:
            addressed[k] = hit
            continue
        doses = {r.name: round(r.progress(design, e['evidence']), 3) for r in live
                 if 0 < r.progress(design, e['evidence']) < 1}
        if doses:
            partial[k] = doses
        unaddressed[k] = [r.name for r in live if not (r.satisfied(design, e['evidence'])
                                                       and r.satisfied(prev, e['evidence']))] \
            or ['none left: escalate to the reviewer']
    if catalog is not None and today is not None:
        for c in stale_knowledge(catalog, today):
            key = f'STALE_KNOWLEDGE@{c.evidence["problem_class"]}'
            if design.get('catalog_as_of', '') >= c.evidence['due']:
                addressed[key] = 'refresh_catalog'
            elif key in (design.get('deferred') or {}):
                deferred[key] = design['deferred'][key]
            else:
                unaddressed[key] = ['refresh_catalog']
    mem = membrane(design, every)
    return {'pass': not unaddressed and not mem, 'addressed': addressed, 'partial': partial,
            'unaddressed': unaddressed, 'deferred': deferred, 'membrane': mem}
