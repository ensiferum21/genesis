"""Soundness modes for abstractions, representations and transfers (CRPD-1).

Adopted from the CRPD v3 proposal (§3.1) and the handoff's representation/world rules
(§15.3, §16.2): an abstraction may be exact, sound in one direction, a bound, or merely
heuristic, and the system must know which. A mode is never taken from the proposer. It is
*derived* from checked obligations, and the requested mode is kept apart from the
established one (as requested and established claim wording are kept apart since F-01).

For a concrete object x, a target property Goal and an abstraction A with abstract
property Abs:

    forward   Abs(A x) -> Goal(x)      (sufficiency)
    backward  Goal(x) -> Abs(A x)      (necessity)

    EQ         both directions CHECKED
    SUFF       forward CHECKED          a positive abstract result lifts to a concrete one
    NEC        backward CHECKED         a failed abstract check refutes Goal(x); pruning is safe
    BOUND      a checked lower witness or upper certificate for one exact task and objective
    HEURISTIC  nothing checked, nothing refuted: search ordering only
    REJECTED   a direction is DISPROVED (or VACUOUS: it rests on an inconsistent world)
               and none is CHECKED: no use at all

Uses an established mode licenses:

    order          any mode except REJECTED (ordering never admits a claim)
    lift_positive  EQ, SUFF
    lift_negative  EQ, NEC
    prune          EQ, NEC          (discarding x because Abs(A x) fails)
    bound_lower / bound_upper       BOUND on that side
An optimum is never licensed by a mode: it needs a checked lower witness and a checked
upper certificate for the same task with equal values (``optimum_problems``).

Unresolved, timed-out or unsupported obligations are not evidence either way. An aliasing
pair (two checked concrete objects with the same abstract state and different Goal values)
disproves exactly one direction: forward if the shared abstract state satisfies Abs,
backward otherwise (``aliasing_refutation``). This is the refinement trigger of CRPD-4.
"""
from ..common import digest

SCHEMA = 'genesis-soundness-mode-v1'
MODES = ('EQ', 'SUFF', 'NEC', 'BOUND', 'HEURISTIC', 'REJECTED')
USES = ('order', 'lift_positive', 'lift_negative', 'prune', 'bound_lower', 'bound_upper')
LICENSES = {'EQ': {'order', 'lift_positive', 'lift_negative', 'prune'},
            'SUFF': {'order', 'lift_positive'},
            'NEC': {'order', 'lift_negative', 'prune'},
            'HEURISTIC': {'order'},
            'REJECTED': set()}
CHECKED, DISPROVED, VACUOUS = 'CHECKED', 'DISPROVED', 'VACUOUS'   # VACUOUS: rests on an inconsistent world
# Order for the meet of a requested and a derived mode (BOUND is a separate dimension).
_BELOW = {'EQ': {'EQ', 'SUFF', 'NEC', 'HEURISTIC', 'REJECTED'}, 'SUFF': {'SUFF', 'HEURISTIC', 'REJECTED'},
          'NEC': {'NEC', 'HEURISTIC', 'REJECTED'}, 'HEURISTIC': {'HEURISTIC', 'REJECTED'}, 'REJECTED': {'REJECTED'}}


class SoundnessError(PermissionError):
    pass


def derive(forward=None, backward=None):
    """The strongest mode the checked obligations support (statuses from the checker vocabulary)."""
    f, b = forward == CHECKED, backward == CHECKED
    if f and b:
        return 'EQ'
    if f:
        return 'SUFF'
    if b:
        return 'NEC'
    if DISPROVED in (forward, backward) or VACUOUS in (forward, backward):
        return 'REJECTED'
    return 'HEURISTIC'


def meet(a, b):
    """Greatest mode below both (requested and derived)."""
    common = _BELOW[a] & _BELOW[b]
    for m in ('EQ', 'SUFF', 'NEC', 'HEURISTIC', 'REJECTED'):
        if m in common:
            return m
    return 'REJECTED'


def establish(subject, *, requested, forward=None, backward=None, evidence=(), scope=None):
    """A mode record: requested and established modes kept apart, with the obligations and
    the evidence identities they rest on. The established mode never exceeds either the
    request or what the evidence supports."""
    if requested not in MODES or requested == 'BOUND':
        raise ValueError(f'unknown or non-abstraction mode {requested!r} (bounds use bound_record)')
    derived = derive(forward, backward)
    established = meet(requested, derived)
    body = {'schema': SCHEMA, 'subject': subject, 'scope': scope, 'requested': requested, 'derived': derived,
            'established': established, 'obligations': {'forward': forward, 'backward': backward},
            'evidence': sorted(evidence), 'downgraded': established != requested}
    return dict(body, record_id=digest(body))


def bound_record(subject, *, side, status, evidence=(), task_sha256=None, value=None, objective=None):
    """BOUND on one side ('lower' witness or 'upper' certificate) of one exact task and objective."""
    if side not in ('lower', 'upper'):
        raise ValueError('side must be lower or upper')
    body = {'schema': SCHEMA, 'subject': subject, 'requested': 'BOUND',
            'established': 'BOUND' if status in (CHECKED, 'VALID') else 'REJECTED', 'side': side,
            'status': status, 'task_sha256': task_sha256, 'value': value, 'objective': objective,
            'evidence': sorted(evidence)}
    return dict(body, record_id=digest(body))


def problems(record, use):
    """Why ``record`` does not license ``use`` (empty list: licensed). Pure."""
    out = []
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        return ['not a soundness-mode record']
    body = {k: v for k, v in record.items() if k != 'record_id'}
    if digest(body) != record.get('record_id'):
        out.append('record identity mismatch')
    if use not in USES:
        return out + [f'unknown use {use!r}']
    mode = record.get('established')
    if mode == 'BOUND':
        if use == 'order':
            return out
        if use != f'bound_{record.get("side")}':
            out.append(f'a {record.get("side")} bound does not license {use}')
        return out
    if mode == 'EQ' or mode == 'SUFF' or mode == 'NEC':
        if record.get('derived') != derive(record['obligations']['forward'], record['obligations']['backward']):
            out.append('derived mode does not follow from the recorded obligations')
        if not record.get('evidence'):
            out.append(f'{mode} without evidence identities')
    if use not in LICENSES.get(mode, set()):
        out.append(f'mode {mode} does not license {use}')
    return out


def admit(record, use):
    p = problems(record, use)
    if p:
        raise SoundnessError('; '.join(p))
    return True


def optimum_problems(lower, upper):
    """An optimum needs checked bounds on both sides of the same task and objective, equal."""
    out = []
    for rec, side in ((lower, 'lower'), (upper, 'upper')):
        out += [f'{side}: {p}' for p in problems(rec, f'bound_{side}')]
        if rec.get('established') != 'BOUND':
            out.append(f'{side} bound is not established')
    if lower.get('task_sha256') != upper.get('task_sha256') or lower.get('objective') != upper.get('objective'):
        out.append('bounds are for different tasks or objectives')
    if lower.get('value') is None or lower.get('value') != upper.get('value'):
        out.append('bounds do not meet')
    return out


def aliasing_refutation(abs_value):
    """Two checked concrete objects with one abstract state and different Goal values refute
    one direction: if Abs holds there, sufficiency fails; otherwise necessity fails."""
    return {'forward': DISPROVED} if abs_value else {'backward': DISPROVED}


# ---------------------------------------------------------------- existing Genesis artifacts

def representation_modes(package):
    """Modes of B18 representation decoders, per domain, from the checked package.

    Goal(S) = "S is a motif-free subgraph of H"; the abstraction is "S = decode(c, H) for
    some encoding c". forward needs both image (decode c H ⊆ H) and soundness CHECKED;
    backward (every motif-free subgraph is a decoding) is DISPROVED by a checked loss
    witness and otherwise unresolved."""
    st = {s['id']: s for s in package['statements']}
    out = {}
    for rep in package['representations']:
        rid = rep['id']
        image = st.get(f'{rid}_image', {}).get('status')
        loss = st.get(f'{rid}_loses_tf', {}).get('status')
        for short, dom in (('tf', 'triangle_free_host_v1'), ('c4', 'c4_host_v2')):
            snd = st.get(f'{rid}_sound_{short}', {})
            forward = CHECKED if image == CHECKED and snd.get('status') == CHECKED else (
                DISPROVED if snd.get('status') == DISPROVED else snd.get('status'))
            backward = DISPROVED if (short == 'tf' and loss == CHECKED) else None
            ev = [x for x in (st.get(f'{rid}_image', {}).get('proof_const'), snd.get('proof_const'),
                              st.get(f'{rid}_loses_tf', {}).get('proof_const') if backward else None) if x]
            out[(rid, dom)] = establish(f'representation {rid} on {dom}', requested='EQ', forward=forward,
                                       backward=backward, evidence=ev, scope=dom)
    return out


def transport_mode(decision, world_status):
    """Mode of a world transport decision (worlds.judge): a TRANSPORTED claim rests on checked
    implications from the target's assumptions to the source's (SUFF); a transport into or
    out of an inconsistent world licenses nothing (REJECTED, vacuous)."""
    if world_status.get(decision['to'], {}).get('status') == 'INCONSISTENT' or \
            world_status.get(decision['from'], {}).get('status') == 'INCONSISTENT':
        return establish(f'transport {decision["from"]}->{decision["to"]}', requested='SUFF',
                         forward=VACUOUS, evidence=decision.get('implication_proofs', ()),
                         scope='vacuous: an inconsistent world')
    forward = CHECKED if decision['verdict'] == 'TRANSPORTED' else None
    return establish(f'transport {decision["from"]}->{decision["to"]}', requested='SUFF', forward=forward,
                     evidence=decision.get('implication_proofs', ()), scope=f'assumptions of {decision["to"]}')


def certificate_bound_modes(bundle, replay_result):
    """BOUND records for both sides of a certificate bundle (v1 or v2) from its checker-only replay."""
    task = bundle['problem']['task_sha256']
    obj = bundle['problem'].get('objective', 'maximum motif-free subgraph')
    lower = bound_record(f'witness for {task[:12]}', side='lower', status=replay_result['lower'], task_sha256=task,
                         value=bundle['lower']['value'], objective=obj,
                         evidence=[bundle['lower'].get('witness_sha256') or digest(bundle['lower']['witness'])])
    up = bundle['upper']
    ev = [up.get(k) for k in ('certificate_sha256', 'cnf_sha256', 'proof_sha256', 'package_sha256') if up.get(k)] \
        or [up['method']]
    upper = bound_record(f'{up["method"]} for {task[:12]}', side='upper', status=replay_result['upper'],
                         task_sha256=task, value=up['value'], objective=obj, evidence=ev)
    return lower, upper


HEURISTIC_COMPONENTS = ('research policies (fixed, random, heuristic, bandit, learned)', 'research macros',
                        'curriculum variants', 'retrieval rankings', 'market value-of-computation estimates')


def heuristic(subject):
    """Learned or tuned guidance: ordering only, never proof admission."""
    return establish(subject, requested='HEURISTIC')


__all__ = ['SCHEMA', 'MODES', 'USES', 'LICENSES', 'SoundnessError', 'derive', 'meet', 'establish', 'bound_record',
           'problems', 'admit', 'optimum_problems', 'aliasing_refutation', 'representation_modes', 'transport_mode',
           'certificate_bound_modes', 'heuristic', 'HEURISTIC_COMPONENTS']
