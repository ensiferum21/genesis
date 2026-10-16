"""Custody and checker-only replay for C4 tree certificates over generated rows (B20_R51; built, opt-in).

`verification.lp_dual_tree_c4` (B20_R48) checks branch-and-bound certificates for c4_host_v2 hosts. Their
leaves are exact LP duals over the host's 4-cycles and copies of generated C4 patterns. Each pattern is a
Lean-checked bound of a theory package (B20_R46). B20_R48/R49 found the route useful in certification, and
the utility attributable to the generated rows. B20_R50 used it as the reference of a DRAFT C4 rule. Before
an evaluator relies on it, its results need the custody every other upper bound has. This module provides
that custody under its own schema. It mirrors `verification.certificates_rows` (B20_R39), and that module
and its schema are unchanged.

The evaluator, `certificates.replay` and `certificates_rows.replay` do not accept this schema. The custodian
reaches it only through a v5 request that names the route `generated-rows-tree-c4-v1` (B20_R51, opt-in).
Adopting that route is a trust-path change for a reviewer (B20R48-OPEN-1).

**Bundle (`genesis-certificate-bundle-tree-c4-v1`).** It records:
  * the problem: the task JSON and its hash;
  * the lower witness, an object re-checked by the dual graph predicates;
  * the upper justification, method LP_DUAL_TREE_C4_EXACT, with three objects: the tree certificate, the
    theory package it rests on, and the registry derived from that package;
  * the identities of the tree checker (`lp_dual_tree_c4.checker_identity`) and of the package
    (`package_sha256`), the claimed bound, and the tree's leaf count.

**Replay** never runs the producer. It:
  1. re-checks the problem hash and the witness;
  2. checks the package's integrity (theory_package.integrity_problems) and its identity;
  3. re-derives the registry from the package (trusted GTDefs and G4Defs) and compares it with the stored
     registry;
  4. re-checks the tree exactly against that registry, and compares the bound;
  5. refuses revoked checker or package identities;
  6. with `replay_package=True`, also replays the Lean package in the pinned workspace.
The upper side is VALID only if every step passes.
"""
import json

from ..common import canonical, digest
from ..graphs import check_witness
from ..models import GraphTask
from . import lp_dual_rows_c4 as V4
from . import lp_dual_tree_c4 as VT
from .certificates import _sha

SCHEMA = 'genesis-certificate-bundle-tree-c4-v1'
METHOD = 'LP_DUAL_TREE_C4_EXACT'
OBJECTIVE = 'maximum number of host edges in a C4-free subgraph'


def _registry(package):
    from ..formal_research.triangle_theory import DEFS_SOURCE
    from ..invention.representations import C4_SOURCE
    return V4.registry_from_package(package, defs_source=DEFS_SOURCE, c4_source=C4_SOURCE)


def build(task, *, witness, lower, certificate, package, attempts=()):
    """(bundle, objects {sha256: bytes}). Refuses a certificate that does not check, a package that fails its
    integrity checks, or a lower bound above the certified upper bound (ValueError)."""
    from ..formal_research import theory_package as TP
    problems = TP.integrity_problems(package)
    if problems:
        raise ValueError(f'theory package fails its integrity checks: {problems}')
    registry = _registry(package)
    verdict = VT.check_certificate(task, certificate, registry)
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
          'patterns': sorted(registry['patterns']), 'leaves': verdict['leaves'],
          'rounding': 'at every dual leaf, |F1| + floor of the exact rational dual objective (integer primal)',
          'checker': VT.checker_identity(), 'checker_verdict': 'VALID',
          'validity': ('each pattern row is a CHECKED Lean statement of the package; 4-cycle rows: at most 3 of a '
                       '4-cycle\'s edges; the tree partitions every C4-free edge set by its fixings')}
    gap = up['value'] - lower
    if gap < 0:
        raise ValueError('lower witness exceeds the certified upper bound: inconsistent bounds')
    bundle = {'schema': SCHEMA, 'problem': {'domain': task.domain, 'task': task_json, 'task_sha256': digest(task_json),
                                            'objective': OBJECTIVE},
              'lower': lower_rec, 'upper': up, 'gap': gap, 'status': 'OPTIMALITY_CHECKED' if gap == 0 else 'BOUNDS_ONLY',
              'attempts': json.loads(canonical(list(attempts))),
              'replay': 'genesis.verification.certificates_tree_c4.replay(bundle, get_bytes)'}
    return bundle, blobs


def custody_problems(bundle, has_object, revoked=()):
    """Problems visible without re-checking (objects present, identities not revoked, hashes)."""
    out = []
    if bundle.get('schema') != SCHEMA:
        return ['not a C4 tree certificate bundle']
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
    problems = []
    if bundle.get('schema') != SCHEMA:
        return {'status': 'REJECTED', 'lower': 'REJECTED', 'upper': 'REJECTED', 'gap': None,
                'problems': ['not a C4 tree certificate bundle']}
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
    if VT.checker_identity() in dead or up.get('checker') in dead:
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
            registry = _registry(package)
            if registry != stored_registry or digest(registry) != up['registry_digest']:
                raise ValueError('stored registry is not the one the package yields')
            v = VT.check_certificate(task, certificate, registry)
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
