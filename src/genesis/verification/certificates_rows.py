"""Custody and checker-only replay for certificates over generated rows (B20_R39; built, not wired).

`verification.certificates` keeps bundles (v1, v2) for the evaluator's own upper bounds:
HOST_EDGE_COUNT, LP_DUAL_EXACT over host motifs, SAT_DRAT and PAIR_COUNT_LEAN. B20_R32–R37 built
a further route: an exact LP dual whose rows include copies of *generated* patterns, each a bound
Lean checked in a theory package (B20_R31, B20_R37). B20_R35 found that route useful in
certification. Before an evaluator could rely on it, its results would need the same custody as
any other upper bound. This module provides that custody under its own schema.

It is deliberately separate:
  * the evaluator, the custodian and `certificates.replay` do not accept this schema;
  * `certificates.CHECKED_METHODS_V2` is unchanged.
Adopting it is a trust-path change that a reviewer must make (B20R35-OPEN-1). Until then it is a
DEV component with the same custody discipline as the others.

**Bundle (`genesis-certificate-bundle-rows-v1`).** It records:
  * the problem: the task JSON and its hash;
  * the lower witness, an object re-checked by the dual graph predicates;
  * the upper justification, method LP_DUAL_GENERATED_EXACT, with three objects: the exact
    certificate, the theory package it rests on, and the registry derived from that package;
  * the identities of the certificate checker (`lp_dual_rows.checker_identity`) and of the
    package (`package_sha256`).

**Replay** never runs the producer. It:
  1. re-checks the problem hash and the witness;
  2. checks the package's integrity (theory_package.integrity_problems);
  3. re-derives the registry from the package and compares it with the stored registry;
  4. re-checks the certificate exactly against that registry, and compares the bound;
  5. refuses revoked checker or package identities;
  6. with `replay_package=True`, also replays the Lean package in the pinned workspace
     (theory_package.replay), as PAIR_COUNT_LEAN bundles do.
The upper side is VALID only if every step passes.
"""
import json

from ..common import canonical, digest
from ..graphs import check_witness
from ..models import GraphTask
from . import lp_dual_rows as V
from .certificates import _sha

SCHEMA = 'genesis-certificate-bundle-rows-v1'
METHOD = 'LP_DUAL_GENERATED_EXACT'
OBJECTIVE = 'maximum number of host edges in a triangle-free subgraph'


def build(task, *, witness, lower, certificate, package, attempts=()):
    """(bundle, objects {sha256: bytes}). Refuses a certificate that does not check, a package that
    fails its integrity checks, or a lower bound above the certified upper bound (ValueError)."""
    from ..formal_research import theory_package as TP
    from ..formal_research.triangle_theory import DEFS_SOURCE
    problems = TP.integrity_problems(package)
    if problems:
        raise ValueError(f'theory package fails its integrity checks: {problems}')
    registry = V.registry_from_package(package, defs_source=DEFS_SOURCE)
    verdict = V.check_certificate(task, certificate, registry)
    if verdict['verdict'] != 'VALID':
        raise ValueError(f'certificate does not check: {verdict["reason"]}')
    checked = check_witness(task, [tuple(e) for e in witness])
    if checked['value'] != lower:
        raise ValueError('lower witness does not have the recorded value')
    task_json = task.model_dump(mode='json')
    blobs = {}

    def put(obj):
        data = canonical(obj)
        blobs[_sha(data)] = data
        return _sha(data)
    lower_rec = {'value': lower, 'witness': [list(e) for e in witness], 'witness_sha256': put([list(e) for e in witness]),
                 'checker': 'genesis.graphs.check_witness (dual predicates)'}
    up = {'method': METHOD, 'value': verdict['bound'], 'certificate_sha256': put(certificate),
          'package_sha256': put(package), 'theory_package_sha256': package['package_sha256'],
          'registry_sha256': put(registry), 'registry_digest': digest(registry),
          'patterns': sorted(registry['patterns']), 'objective_rational': certificate['objective'],
          'rounding': 'floor of the exact rational dual objective (integer primal)',
          'checker': V.checker_identity(), 'checker_verdict': 'VALID',
          'validity': 'each pattern row is a CHECKED Lean statement of the package; triangle rows: motif_not_all'}
    gap = up['value'] - lower
    if gap < 0:
        raise ValueError('lower witness exceeds the certified upper bound: inconsistent bounds')
    bundle = {'schema': SCHEMA, 'problem': {'domain': task.domain, 'task': task_json, 'task_sha256': digest(task_json),
                                            'objective': OBJECTIVE},
              'lower': lower_rec, 'upper': up, 'gap': gap, 'status': 'OPTIMALITY_CHECKED' if gap == 0 else 'BOUNDS_ONLY',
              'attempts': json.loads(canonical(list(attempts))),
              'replay': 'genesis.verification.certificates_rows.replay(bundle, get_bytes)'}
    return bundle, blobs


def custody_problems(bundle, has_object, revoked=()):
    """Problems visible without re-checking (objects present, identities not revoked, hashes)."""
    out = []
    if bundle.get('schema') != SCHEMA:
        return ['not a generated-rows certificate bundle']
    up, low = bundle.get('upper') or {}, bundle.get('lower') or {}
    if up.get('method') != METHOD:
        out.append(f'unexpected upper-bound method {up.get("method")!r}')
    for k in ('certificate_sha256', 'package_sha256', 'registry_sha256'):
        if not has_object(up.get(k)):
            out.append(f'{k[:-7]} object missing or altered')
    if not has_object(low.get('witness_sha256')):
        out.append('lower witness object missing or altered')
    dead = set(revoked)
    if up.get('checker') in dead:
        out.append('certificate checker identity is revoked')
    if up.get('theory_package_sha256') in dead:
        out.append('theory package identity is revoked')
    try:
        if digest(bundle['problem']['task']) != bundle['problem']['task_sha256']:
            out.append('problem hash mismatch')
    except (KeyError, TypeError):
        out.append('problem missing')
    if bundle.get('status') == 'OPTIMALITY_CHECKED' and bundle.get('gap') != 0:
        out.append('OPTIMALITY_CHECKED recorded with a non-zero gap')
    return out


def replay(bundle, get_bytes, revoked=(), *, replay_package=False):
    """Checker-only replay. Returns {'status', 'lower', 'upper', 'gap', 'problems'}."""
    from ..formal_research import theory_package as TP
    from ..formal_research.triangle_theory import DEFS_SOURCE
    problems = []
    if bundle.get('schema') != SCHEMA:
        return {'status': 'REJECTED', 'lower': 'REJECTED', 'upper': 'REJECTED', 'gap': None,
                'problems': ['not a generated-rows certificate bundle']}
    task = GraphTask.model_validate_json(canonical(bundle['problem']['task']))
    if digest(task.model_dump(mode='json')) != bundle['problem']['task_sha256']:
        problems.append('problem does not match its hash')
    low, up = bundle['lower'], bundle['upper']
    try:
        wit = json.loads(get_bytes(low['witness_sha256']))
        if [list(e) for e in wit] != low['witness']:
            raise ValueError('witness object differs from the recorded witness')
        lower = 'VALID' if check_witness(task, tuple(tuple(e) for e in wit))['value'] == low['value'] else 'REJECTED'
        if lower != 'VALID':
            problems.append('lower witness value does not match')
    except Exception as exc:
        lower = 'REJECTED'
        problems.append(f'lower witness rejected: {type(exc).__name__}')
    upper = 'VALID'
    dead = set(revoked)
    if V.checker_identity() in dead or up.get('checker') in dead:
        upper = 'REJECTED'
        problems.append('certificate checker identity is revoked')
    if up.get('theory_package_sha256') in dead:
        upper = 'REJECTED'
        problems.append('theory package identity is revoked')
    if upper == 'VALID':
        try:
            package = json.loads(get_bytes(up['package_sha256']))
            stored_registry = json.loads(get_bytes(up['registry_sha256']))
            certificate = json.loads(get_bytes(up['certificate_sha256']))
            why = TP.integrity_problems(package)
            if why or package.get('package_sha256') != up['theory_package_sha256']:
                raise ValueError(f'package integrity: {why or "identity differs"}')
            registry = V.registry_from_package(package, defs_source=DEFS_SOURCE)
            if registry != stored_registry or digest(registry) != up['registry_digest']:
                raise ValueError('stored registry is not the one the package yields')
            v = V.check_certificate(task, certificate, registry)
            if v['verdict'] != 'VALID':
                raise ValueError(f'certificate rejected: {v["reason"]}')
            if v['bound'] != up['value']:
                raise ValueError('certificate certifies a different bound')
            if replay_package and TP.replay(package)['verdict'] != 'REPLAYED':
                raise ValueError('theory package does not replay in Lean')
        except Exception as exc:
            upper = 'REJECTED'
            problems.append(f'upper bound rejected: {exc}')
    gap = up['value'] - low['value']
    if lower == 'VALID' and upper == 'VALID':
        status = 'REJECTED' if gap < 0 else 'OPTIMALITY_CHECKED' if gap == 0 else 'BOUNDS_CHECKED'
        if gap < 0:
            problems.append('lower bound exceeds upper bound')
    else:
        status = 'REJECTED'
    if bundle.get('status') == 'OPTIMALITY_CHECKED' and status != 'OPTIMALITY_CHECKED':
        problems.append(f'recorded OPTIMALITY_CHECKED does not replay (replayed {status})')
    return {'status': status, 'lower': lower, 'upper': upper, 'gap': gap, 'problems': problems}


__all__ = ['SCHEMA', 'METHOD', 'build', 'custody_problems', 'replay']
