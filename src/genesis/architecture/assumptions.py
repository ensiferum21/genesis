"""Assumptions as challengeable objects (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §5.3; ARA-1).

Three kinds:
  * **generated**: every fixed choice in a non-kernel node of an AG (its operator, each constant, and each absent
    edge between type-compatible ports), each with the rewrite that would challenge it;
  * **recorded**: assumptions taken from studies, each with the study that tested it;
  * **protected**: the judge, sealed datasets, proof acceptance rules, security boundaries, external resource limits,
    promotion thresholds, audit records and the supervisor. `challenge` refuses them, always.
"""
from . import graph as G

PROTECTED = ('the judge', 'sealed datasets', 'proof acceptance rules', 'security boundaries',
             'external resource limits', 'promotion thresholds', 'audit records', 'the supervisor')
RECORDED = (
    {'id': 'engine-on-original-representation', 'statement': 'engine search operates on the original instance '
     'representation', 'tested_by': ['B20_R133', 'B20_R135'], 'status': 'challenged: chosen encodings beat one-hot '
     'on colouring (B20_R135)'},
    {'id': 'judge-thresholds-from-global-noise', 'statement': "the judge's release thresholds come from the noise of "
     'random engines', 'tested_by': ['B20_R132'], 'status': 'challenged: a local calibration (version 3) is finer; '
     'not validated, nothing released by either'},
    {'id': 'one-fixed-discovery-process', 'statement': "Genesis's inventor runs one fixed discovery process",
     'tested_by': ['B20_R148'], 'status': 'challenged: a portfolio was not distinguishable at 1,024 evaluations'},
    {'id': 'level-two-needs-level-one', 'statement': 'improving the process of invention needs a level 1 that '
     'releases', 'tested_by': ['B20_R128'], 'status': 'observed: no inner release, nothing to select on'},
)


class Refused(Exception):
    """A challenge to a protected assumption."""


def generated(ag, lib=G.LIB):
    out = []
    for n in sorted(ag['nodes']):
        nd = ag['nodes'][n]
        if nd['kernel']:
            continue
        alts = [o for o in lib[nd['role']] if o != nd['op']]
        if alts:
            out.append({'id': f'{n}.op', 'kind': 'generated', 'location': n, 'fixed': f"{nd['role']}.{nd['op']}",
                        'alternative': {'op': 'SUBSTITUTE', 'target': n, 'choices': alts}})
        for p, v in sorted(nd['params'].items()):
            liftable = p in G.LIFTABLE.get(nd['op'], ())
            out.append({'id': f'{n}.{p}', 'kind': 'generated', 'location': n, 'fixed': {p: v},
                        'alternative': {'op': 'LIFT' if liftable else 'TUNE', 'target': n, 'param': p}})
    for n in sorted(ag['nodes']):
        nd = ag['nodes'][n]
        if nd['kernel']:
            continue
        spec = lib[nd['role']][nd['op']]
        for port, want in spec['in'].items():
            elem = want[1] if isinstance(want, list) else want
            if not isinstance(want, list):
                continue
            have = set(G.inputs_of(ag, n).get(port, []))
            for s in sorted(ag['nodes']):
                sd = ag['nodes'][s]
                if s != n and s not in have and not sd['kernel'] and lib[sd['role']][sd['op']]['out'] == elem:
                    out.append({'id': f'{s}->{n}.{port}', 'kind': 'generated', 'location': n,
                                'fixed': f'no edge {s} -> {n}.{port}',
                                'alternative': {'op': 'CONNECT', 'source': s, 'target': n, 'port': port}})
    return out


def protected():
    return [{'id': f'protected:{p}', 'kind': 'protected', 'location': 'kernel', 'fixed': p} for p in PROTECTED]


def recorded():
    return [dict(r, kind='recorded') for r in RECORDED]


def registry(ag=None):
    return {'generated': generated(ag) if ag is not None else [], 'recorded': recorded(), 'protected': protected()}


def challenge(assumption, ag=None):
    """The rewrite that challenges an assumption; protected ones, and anything located in the kernel, are refused."""
    if assumption.get('kind') == 'protected' or assumption.get('location') == 'kernel':
        raise Refused(f"protected: {assumption.get('fixed')}")
    if ag is not None and assumption.get('location') in ag['nodes'] and ag['nodes'][assumption['location']]['kernel']:
        raise Refused(f"in the kernel: {assumption['location']}")
    return assumption.get('alternative')


__all__ = ['PROTECTED', 'RECORDED', 'Refused', 'generated', 'protected', 'recorded', 'registry', 'challenge']
