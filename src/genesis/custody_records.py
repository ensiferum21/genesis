"""Custody records (roadmap W06): the public registration log and control declarations.

Registration log. The custodian appends one hash-chained entry per event:
REGISTERED (with the hypothesis family and its declared size), RESERVED (panel
consumed), PUBLISHED (receipt hash, outcome, primary p-value) and RECOVERED. The
custodian signs exported snapshots; the log names no task. From it anyone can see
every registered hypothesis, which family it belongs to, which have results and
which are still OUTSTANDING (B15-OPEN-1: an evaluation that was registered but never
reported is visible to everyone, not only to whoever holds its anchor), and can
check that a claim's multiplicity correction used exactly the family results that
were public when it was evaluated (B14-OPEN-2).

Control declarations. Distinct keys do not establish independence. Each role
declares who controls its machines, keys, data and analysis, signed with that role's
pinned key; the custodian's declaration also names the research operator. Shared
control between roles is disclosed and limits what may be claimed.
"""
import hashlib

from .common import canonical, digest, utcnow
from .kernel.analysis import PLAN_SCHEMA

LOG_SCHEMA = 'genesis-registration-log-v1'
ENTRY_KINDS = ('REGISTERED', 'RESERVED', 'PUBLISHED', 'RECOVERED')
CONTROL_SCHEMA = 'genesis-control-declaration-v1'
DECLARED_ROLES = {'custodian': 'custodian_key', 'auditor': 'auditor_key', 'release_authority': 'release_key'}
CONTROL_FIELDS = ('machines', 'keys', 'data', 'analysis')


# ---------------------------------------------------------------- hypothesis families

def custodian_family(request):
    """The hypothesis family is assigned by the custodian, not chosen by the requester: every
    registration of the same evidence kind in the same domain at this custodian. A requester
    who could name a fresh family per candidate could escape the multiplicity correction
    ("family shopping"); new campaigns or renamed claims do not change this family."""
    return f"{request['evidence_kind']}:{request['domain']}"


def family_of(request):
    a = request['analysis']
    if isinstance(a, dict) and a.get('schema') == PLAN_SCHEMA:
        return a['multiplicity']['family_id']
    return custodian_family(request)


def family_size_of(request):
    a = request['analysis']
    if isinstance(a, dict) and a.get('schema') == PLAN_SCHEMA:
        return a['multiplicity']['family_size']
    return a.get('hypotheses', 1)


# ---------------------------------------------------------------- the log

def new_entry(entries, kind, fields):
    if kind not in ENTRY_KINDS:
        raise ValueError(f'unknown log entry kind {kind!r}')
    prev = hashlib.sha256(canonical(entries[-1])).hexdigest() if entries else None
    return {'seq': len(entries) + 1, 'prev': prev, 'kind': kind, 'time': utcnow(), **fields}


def chain_problems(entries):
    out, prev = [], None
    for i, e in enumerate(entries, 1):
        if e.get('seq') != i or e.get('prev') != prev or e.get('kind') not in ENTRY_KINDS:
            out.append(f'log entry {i} breaks the chain')
        prev = hashlib.sha256(canonical(e)).hexdigest()
    return out


def head(entries):
    return hashlib.sha256(canonical(entries[-1])).hexdigest() if entries else None


def family_state(entries, family):
    registered, sizes, results = [], set(), {}
    for e in entries:
        if e.get('family') != family:
            continue
        if e['kind'] == 'REGISTERED':
            registered.append(e['request_hash'])
            sizes.add(e['family_size'])
        elif e['kind'] in ('PUBLISHED', 'RECOVERED'):
            results[e['request_hash']] = {'seq': e['seq'], 'outcome': e['outcome'], 'p_value': e['p_value'],
                                         'receipt_sha256': e['receipt_sha256']}
    return {'family': family, 'registered': registered, 'declared_sizes': sorted(sizes), 'results': results,
            'outstanding': [r for r in registered if r not in results]}


def registration_problems(entries, request):
    """Would registering `request` keep its family honest? (checked by the custodian)."""
    fam, size = family_of(request), family_size_of(request)
    state = family_state(entries, fam)
    out = []
    if fam != custodian_family(request):
        out.append(f'the hypothesis family is assigned by the custodian: family_id must be {custodian_family(request)!r}')
    if state['declared_sizes'] and state['declared_sizes'] != [size]:
        out.append(f'family {fam!r} was declared with size {state["declared_sizes"]}; this request says {size}')
    if len(state['registered']) + 1 > size:
        out.append(f'family {fam!r} already holds {len(state["registered"])} of its declared {size} hypotheses')
    return out


def published_p_values_before(entries, family, request_hash):
    """p-values of other family members published before `request_hash`'s own result entry
    (or before now, if it has none yet). Outstanding members are not included: the analysis
    counts them as p = 1, which is conservative for every member."""
    own = next((e['seq'] for e in entries if e['kind'] in ('PUBLISHED', 'RECOVERED')
                and e['request_hash'] == request_hash), None)
    return sorted(e['p_value'] for e in entries
                  if e.get('family') == family and e['kind'] in ('PUBLISHED', 'RECOVERED')
                  and e['request_hash'] != request_hash and e['p_value'] is not None
                  and (own is None or e['seq'] < own))


def export_log(entries, sign, key_path):
    payload = {'schema': LOG_SCHEMA, 'entries': entries, 'head': head(entries), 'exported_at': utcnow()}
    return sign(payload, key_path)


def check_log(envelope, public_key, verify):
    try:
        payload = verify(envelope, public_key)
    except Exception as exc:
        return None, [f'registration log signature does not verify ({type(exc).__name__})']
    if not isinstance(payload, dict) or payload.get('schema') != LOG_SCHEMA:
        return None, ['not a registration log']
    out = chain_problems(payload['entries'])
    if payload['head'] != head(payload['entries']):
        out.append('registration log head does not match its entries')
    return payload, out


def receipt_log_problems(log_entries, request, receipt_envelope):
    """Release-side checks of one receipt against the signed public log."""
    from .kernel import receipts as R
    rid = digest(request)
    fam = family_of(request)
    out = []
    regs = [e for e in log_entries if e['kind'] == 'REGISTERED' and e['request_hash'] == rid]
    if len(regs) != 1:
        out.append('the request is not registered exactly once in the public registration log')
    elif regs[0]['family'] != fam or regs[0]['family_size'] != family_size_of(request):
        out.append('the logged hypothesis family differs from the request')
    pubs = [e for e in log_entries if e['kind'] in ('PUBLISHED', 'RECOVERED') and e['request_hash'] == rid]
    if len(pubs) != 1:
        out.append('the receipt is not published exactly once in the registration log')
    elif pubs[0]['receipt_sha256'] != digest(receipt_envelope):
        out.append('the logged receipt differs from the receipt presented')
    state = family_state(log_entries, fam)
    if len(state['declared_sizes']) > 1:
        out.append('the hypothesis family was declared with different sizes')
    if state['declared_sizes'] and len(state['registered']) > state['declared_sizes'][0]:
        out.append('more hypotheses were registered in the family than its declared size')
    p = receipt_envelope['payload']
    if p.get('schema') == R.SCIENTIFIC_RECEIPT_V3:
        used = p['analysis_result'].get('family_p_values')
        want = [round(float(x), 10) for x in published_p_values_before(log_entries, fam, rid)]
        if used != want:
            out.append('the multiplicity correction did not use exactly the family results published before it')
    return out, state


# ---------------------------------------------------------------- control declarations

def declaration(role, controller, *, machines, keys, data, analysis, research_operator=None):
    if role not in DECLARED_ROLES:
        raise ValueError(f'unknown role {role!r}')
    payload = {'schema': CONTROL_SCHEMA, 'role': role, 'controller': controller, 'machines': sorted(machines),
               'keys': sorted(keys), 'data': sorted(data), 'analysis': sorted(analysis), 'declared_at': utcnow()}
    if role == 'custodian':
        if not research_operator:
            raise ValueError('the custodian declaration must name the research operator')
        payload['research_operator'] = research_operator
    return payload


def independence(declarations, pins, verify):
    """{'status': INDEPENDENT | SAME_OPERATOR_DISCLOSED | UNDECLARED, ...} from signed declarations.

    `declarations`: role -> signed envelope. Each must verify under that role's pinned key."""
    reasons, payloads = [], {}
    for role, pin in DECLARED_ROLES.items():
        env = (declarations or {}).get(role)
        if env is None:
            reasons.append(f'no control declaration for {role}')
            continue
        try:
            p = verify(env, pins[pin])
        except Exception as exc:
            reasons.append(f'{role} declaration does not verify under the pinned {pin} ({type(exc).__name__})')
            continue
        if not isinstance(p, dict) or p.get('schema') != CONTROL_SCHEMA or p.get('role') != role or \
                not isinstance(p.get('controller'), str) or not p['controller']:
            reasons.append(f'{role} declaration is malformed')
            continue
        payloads[role] = p
    if reasons:
        return {'status': 'UNDECLARED', 'reasons': reasons, 'shared': [], 'limitation': None}
    parties = dict(payloads)
    parties['research_operator'] = {'controller': payloads['custodian']['research_operator'],
                                    **{f: [] for f in CONTROL_FIELDS}}
    shared = []
    names = sorted(parties)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if parties[a]['controller'] == parties[b]['controller']:
                shared.append({'roles': [a, b], 'shared': 'controller'})
            for f in CONTROL_FIELDS:
                common = sorted(set(parties[a].get(f, [])) & set(parties[b].get(f, [])))
                if common:
                    shared.append({'roles': [a, b], 'shared': f, 'items': common})
    if not shared:
        return {'status': 'INDEPENDENT', 'reasons': [], 'shared': [], 'limitation': None}
    roles = sorted({r for s in shared for r in s['roles']})
    return {'status': 'SAME_OPERATOR_DISCLOSED', 'reasons': [], 'shared': shared,
            'limitation': f'Roles {", ".join(roles)} share control; the result is not an independent evaluation '
                          f'and may be described only as an operator-attested evaluation.'}
