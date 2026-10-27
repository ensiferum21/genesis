"""The consolidator (X2, B20_R154; `docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §3; `OMEGA_META_ADAPTIVE.md` §5.3): what
the language judge admits is kept, with what it is, how it was checked and where it fails; what it refuses is kept
dormant with its failure, never deleted.

**Records** (in the vault, `genesis.vault`, immutable and content-addressed):
  * a LANGUAGE VERSION: a CapabilityRecord {kind: 'language', version, parent, library (the JSON, which rebuilds to
    its version)}, its parent the previous version's record, so the registry of versions is the chain of parents;
  * a STATEMENT: a CapabilityRecord {kind: 'statement', name, language, contract, implementation, tests,
    verification, cost, failure_envelope, provenance}:
      - contract: the expansion semantics (parameters and their ranges, the body, whether it is a guard, and the rule:
        a call is one item; its expansion is the body with the arguments substituted, in a block if longer than one
        item);
      - implementation: the body text and the language version it is written in;
      - tests: property tests run here, now (the trial expansions at both ends of every range parse, are canonical
        and are valid mcx3 programs; the definition rebuilds from the library JSON; its expansion is stable);
      - verification: the judge's verdict {admitted, failed, claim} and the ledger entry the study holds;
      - cost: description length (items and bits of the body), and the CPU it was given (the judge's budget);
      - failure_envelope: the classes and claims for which it was refused, if any;
      - provenance: how it was found (the learner's generation, uses, compression), and by whom;
    with `requires` edges to the statements it calls and an `improves` edge from the new language version to its
    parent once admitted.
**Statuses.** An admitted statement and its version enter as `exploratory` and become `reproducible` (the judge has
checked them on sealed graphs); `verified` and `promoted` need an EvidenceRecord naming a recorded study and its
record test (`vault.annotate`), which only a recorded study supplies. A refused statement is `dormant` with failure
`context_limited` (refused on sealed graphs) or `incorrect` (refused by correctness).
"""
from ..candidate_kinds import mcx3 as K
from . import lambda1 as L1

DOMAIN = 'maxcut_v1'


def property_tests(library, name):
    """The statement's tests, run now: {name: passed}."""
    d = library.get(name)
    out = {}
    try:
        L1.Library.from_json(library.to_json())
        out['rebuilds'] = True
    except ValueError:
        out['rebuilds'] = False
    for end, args in (('low', [lo for lo, _ in d['ranges']]), ('high', [hi for _, hi in d['ranges']])):
        call = name + (f'({",".join(map(str, args))})' if args else '')
        try:
            prog = L1.expand(K.parse(call + ' b1', calls=True), library)
            text = K.render(prog)
            out[f'expands_{end}'] = K.check(prog) is None and K.render(K.canonical(K.parse(text))) == text
            out[f'stable_{end}'] = K.render(L1.expand(K.parse(call + ' b1', calls=True), library)) == text
        except ValueError:
            out[f'expands_{end}'] = out[f'stable_{end}'] = False
    return out


def language_record(vault, library, parent_id=None, creator='genesis'):
    rec = vault.record('CapabilityRecord', {'kind': 'language', 'version': library.version,
                                            'parent': library.parent, 'library': library.to_json()},
                       domain=DOMAIN, creator=creator, parents=[parent_id] if parent_id else [])
    return vault.put(rec, status='exploratory')


def find_language(vault, version):
    for aid in vault.ids():
        r = vault.get(aid)
        if r['type'] == 'CapabilityRecord' and r['content'].get('kind') == 'language' \
                and r['content']['version'] == version:
            return aid
    return None


def statement_record(vault, library, name, decision, ledger_entry=None, budget=None, creator='genesis'):
    """Store one statement of `library` with the judge's decision; returns its ID."""
    d = library.get(name)
    body = K.parse(d['body'], calls=True, params=True)
    sub = L1._substitute
    body1 = tuple(sub(x, [1] * d['params']) for x in body)
    content = {
        'kind': 'statement', 'name': name, 'language': library.version,
        'contract': {'params': d['params'], 'ranges': [list(r) for r in d['ranges']], 'body': d['body'],
                     'guard': d['guard'], 'rule': 'a call is one item: the body with the arguments substituted, in '
                                                  'a block if it has more than one item (lambda1.expand)'},
        'implementation': {'body': d['body'], 'written_in': library.parent},
        'tests': property_tests(library, name),
        'verification': {'admitted': bool(decision.get('admitted')), 'failed': decision.get('failed'),
                         'claim': decision.get('claim'), 'ledger': ledger_entry},
        'cost': {'items': L1.length(body), 'bits': round(L1.bits(body1, library), 3), 'budget': budget},
        'failure_envelope': [] if decision.get('admitted') else [{'claim': decision.get('claim'),
                                                                  'failed': decision.get('failed')}],
        'provenance': d.get('provenance'),
    }
    rec = vault.record('CapabilityRecord', content, domain=DOMAIN, creator=creator)
    aid = vault.put(rec, status='generated')
    if decision.get('admitted') and all(content['tests'].values()):
        vault.annotate(aid, status='exploratory', reason='property tests passed')
        vault.annotate(aid, status='reproducible', reason=f"admitted by the language judge ({decision.get('claim')})")
    else:
        failure = 'incorrect' if decision.get('failed') == 'correctness' or not all(content['tests'].values()) \
            else 'context_limited'
        vault.annotate(aid, status='dormant', failure=failure,
                       reason=f"refused by the language judge ({decision.get('failed')})")
    for name_ in sorted({x[1] for x in K.walk(body) if x[0] == 'call'}):        # one edge per statement called
        dep = find_statement(vault, name_)
        if dep is not None:
            vault.edge('requires', aid, dep, confidence=1.0, scope='expansion', provenance='consolidator')
    return aid


def find_statement(vault, name):
    for aid in vault.ids():
        r = vault.get(aid)
        if r['type'] == 'CapabilityRecord' and r['content'].get('kind') == 'statement' and r['content']['name'] == name:
            return aid
    return None


def consolidate(vault, parent, candidate, names, decision, ledger_entry=None, budget=None):
    """Store the candidate's new statements with the decision, and, if admitted, the new language version with an
    `improves` edge to its parent's version. Returns {'statements': {name: id}, 'language': id or None}."""
    parent_id = find_language(vault, parent.version) or language_record(vault, parent)
    ids = {n: statement_record(vault, candidate, n, decision, ledger_entry, budget) for n in names}
    lang = None
    if decision.get('admitted'):
        lang = language_record(vault, candidate, parent_id)
        vault.annotate(lang, status='reproducible', reason='its statements were admitted by the language judge')
        vault.edge('improves', lang, parent_id, confidence=0.5, scope=f"claim {decision.get('claim')}",
                   provenance='language judge, sealed graphs')
        for aid in ids.values():
            vault.edge('combines_with', aid, lang, confidence=1.0, scope='member', provenance='consolidator')
    return {'statements': ids, 'language': lang}


def registry(vault):
    """The language versions, oldest first: [(record id, version, parent version)]."""
    out = []
    for aid in vault.ids():
        r = vault.get(aid)
        if r['type'] == 'CapabilityRecord' and r['content'].get('kind') == 'language':
            out.append((aid, r['content']['version'], r['content']['parent']))
    order, seen = [], set()
    by_parent = {}
    for x in out:
        by_parent.setdefault(x[2], []).append(x)
    roots = [x for x in out if x[2] not in {v for _, v, _ in out}]
    stack = sorted(roots, key=lambda x: x[1])
    while stack:
        x = stack.pop(0)
        if x[1] in seen:
            continue
        seen.add(x[1])
        order.append(x)
        stack += sorted(by_parent.get(x[1], []), key=lambda y: y[1])
    return order
